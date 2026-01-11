import logging
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB
import uuid

logger = logging.getLogger(__name__)

# SQLAlchemy base class for all ORM models
Base = declarative_base()


class Template(Base):
    """
    Represents a research template that defines the structure of information to extract.
    
    Templates contain JSON schema definitions that specify what fields the LLM should
    extract from documents during the research process.
    
    Attributes:
        id: Unique identifier for the template (UUID string)
        name: Human-readable name of the template (must be unique)
        description: Optional description of the template's purpose
        schema_json: JSONB field containing the dynamic schema for extraction
        created_at: Timestamp when the template was created
    """
    __tablename__ = "templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    schema_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, server_default="now()")


class ResearchTask(Base):
    """
    Represents a single research task initiated by a user.
    
    A research task contains a goal, uses a template to structure extraction,
    and produces a tree of research nodes as it recursively explores the topic.
    
    Attributes:
        id: Unique identifier for the task (UUID string)
        goal: The research goal/question to investigate
        template_id: Foreign key to the Template defining extraction structure
        depth_limit: Maximum recursion depth for research (default: 3)
        status: Current status of the task (pending, processing, synthesis_ready, completed)
        created_at: Timestamp when the task was created
        template: Relationship to the associated Template
        nodes: Relationship to all ResearchNodes belonging to this task
    """
    __tablename__ = "research_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    goal = Column(String, nullable=False)
    template_id = Column(String, ForeignKey("templates.id"), nullable=False)
    depth_limit = Column(Integer, default=3)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default="now()")

    template = relationship("Template", backref="research_tasks")
    nodes = relationship("ResearchNode", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_research_tasks_template_id", "template_id"),
        Index("ix_research_tasks_status", "status"),
        Index("ix_research_tasks_created_at", "created_at"),
    )


class ResearchNode(Base):
    """
    Represents a single step in the research process.
    
    Research nodes form a tree structure where each node represents either:
    - A research question (scout/initiation nodes)
    - A processed URL with extracted facts (process nodes)
    - A discovery step that identified new leads (discovery nodes)
    
    Attributes:
        id: Unique identifier for the node (UUID string)
        task_id: Foreign key to the parent ResearchTask
        parent_node_id: Self-referencing foreign key to parent node (for tree structure)
        node_type: Type of node (initiation, scout, process, discovery, synthesis)
        url: The URL crawled (for process nodes)
        question_text: The research question being answered
        depth_level: Depth level in the research tree (0 = root)
        extracted_facts: JSONB field containing structured extracted data
        content_vector: pgvector for semantic similarity search (768-dim dense embedding)
        priority_score: Relevance score for prioritizing tasks (0.0-1.0)
        status: Processing status (pending, processing, completed, failed)
        created_at: Timestamp when the node was created
        updated_at: Timestamp when the node was last updated
        task: Relationship to the parent ResearchTask
        parent: Relationship to the parent ResearchNode
        children: Relationship to child ResearchNodes (backref)
    """
    __tablename__ = "research_nodes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("research_tasks.id"), nullable=False)
    parent_node_id = Column(String, ForeignKey("research_nodes.id"), nullable=True)
    node_type = Column(String, nullable=False)
    url = Column(String, nullable=True)
    question_text = Column(String, nullable=True)
    depth_level = Column(Integer, default=0)
    extracted_facts = Column(JSONB, nullable=True)
    content_vector = Column(Vector(768), nullable=True)
    priority_score = Column(Float, default=0.0)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default="now()")
    updated_at = Column(DateTime, server_default="now()", onupdate="now()")

    task = relationship("ResearchTask", back_populates="nodes")
    parent = relationship("ResearchNode", remote_side=[id], backref="children")

    # HNSW index for fast approximate nearest neighbor search on content vectors
    # m=16: Number of bidirectional links per node (higher = better recall, more memory)
    # ef_construction=64: Size of dynamic candidate list during index construction
    __table_args__ = (
        Index("ix_research_nodes_content_vector", "content_vector", postgresql_using="hnsw", postgresql_with={"m": 16, "ef_construction": 64}, postgresql_ops={"content_vector": "vector_cosine_ops"}),
        Index("ix_research_nodes_url", "url"),
        Index("ix_research_nodes_question_text", "question_text"),
        Index("ix_research_nodes_parent_node_id", "parent_node_id"),
        Index("ix_research_nodes_task_id", "task_id"),
        Index("ix_research_nodes_status", "status"),
    )
