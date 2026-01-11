import logging
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB
import uuid

logger = logging.getLogger(__name__)

Base = declarative_base()


class Template(Base):
    __tablename__ = "templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    schema_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, server_default="now()")


class ResearchTask(Base):
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
    __tablename__ = "research_nodes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("research_tasks.id"), nullable=False)
    parent_node_id = Column(String, ForeignKey("research_nodes.id"), nullable=True)
    node_type = Column(String, nullable=False)
    url = Column(String, nullable=True)
    question_text = Column(String, nullable=True)
    depth_level = Column(Integer, default=0)
    extracted_facts = Column(JSONB, nullable=True)
    content_vector = Column(Vector(1536), nullable=True)
    priority_score = Column(Float, default=0.0)
    status = Column(String, default="pending")
    created_at = Column(DateTime, server_default="now()")
    updated_at = Column(DateTime, server_default="now()", onupdate="now()")

    task = relationship("ResearchTask", back_populates="nodes")
    parent = relationship("ResearchNode", remote_side=[id], backref="children")

    __table_args__ = (
        Index("ix_research_nodes_content_vector", "content_vector", postgresql_using="hnsw", postgresql_with={"m": 16, "ef_construction": 64}, postgresql_ops={"content_vector": "vector_cosine_ops"}),
        Index("ix_research_nodes_url", "url"),
        Index("ix_research_nodes_question_text", "question_text"),
        Index("ix_research_nodes_parent_node_id", "parent_node_id"),
        Index("ix_research_nodes_task_id", "task_id"),
        Index("ix_research_nodes_status", "status"),
    )
