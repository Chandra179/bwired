import logging
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .models import Base, ResearchNode, ResearchTask, Template

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    Async PostgreSQL database client using SQLAlchemy 2.0+.
    
    Provides CRUD operations for templates, research tasks, and research nodes.
    Uses async session maker for non-blocking database operations,
    and pgvector extension for vector similarity search.

    Attributes:
        engine: SQLAlchemy async engine with connection pooling
        async_session: Session factory for creating database sessions

    Configuration:
        - pool_size: Number of persistent connections to maintain
        - max_overflow: Additional connections allowed beyond pool_size
        - echo: SQL logging (disabled by default)
    """
    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 20):
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=False,
        )
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)

    async def init_db(self):
        """
        Initialize database tables using SQLAlchemy's create_all.
        
        Creates all tables defined in Base.metadata if they don't exist.
        This is idempotent and safe to call on startup.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        """
        Close database connection and dispose of engine.
        
        Should be called on application shutdown to release all connections.
        """
        await self.engine.dispose()

    async def create_template(self, name: str, description: str, schema_json: dict) -> Template:
        """
        Create a new research template.
        
        Templates define the JSON schema structure for fact extraction
        during research. They can be reused across multiple research tasks.

        Args:
            name: Unique template name
            description: Optional description of template's purpose
            schema_json: JSON schema defining fields to extract

        Returns:
            Created Template instance with auto-generated ID
        """
        async with self.async_session() as session:
            template = Template(name=name, description=description, schema_json=schema_json)
            session.add(template)
            await session.commit()
            await session.refresh(template)
            return template

    async def get_template(self, template_id: str) -> Optional[Template]:
        """
        Retrieve a template by ID.

        Args:
            template_id: UUID string of template to retrieve

        Returns:
            Template instance or None if not found
        """
        async with self.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(Template).where(Template.id == template_id))
            return result.scalar_one_or_none()

    # TODO: Should not insert if goal is exist in database
    async def create_research_task(self, goal: str, template_id: str, depth_limit: int) -> ResearchTask:
        """
        Create a new research task.

        Research tasks track the entire research process from initiation
        to synthesis. Each task has a goal, uses a template,
        and produces a tree of research nodes.

        Args:
            goal: The research question or topic
            template_id: Foreign key to Template for extraction schema
            depth_limit: Maximum recursion depth for this research

        Returns:
            Created ResearchTask instance with auto-generated ID
        """
        async with self.async_session() as session:
            task = ResearchTask(goal=goal, template_id=template_id, depth_limit=depth_limit)
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task

    async def get_research_task(self, task_id: str) -> Optional[ResearchTask]:
        """
        Retrieve a research task by ID.

        Args:
            task_id: UUID string of task to retrieve

        Returns:
            ResearchTask instance or None if not found
        """
        async with self.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(ResearchTask).where(ResearchTask.id == task_id))
            return result.scalar_one_or_none()

    async def create_node(self, **kwargs) -> ResearchNode:
        """
        Create a new research node.

        Research nodes represent individual steps in the research tree,
        including scout tasks, processed URLs, and discovery steps.

        Args:
            **kwargs: Fields for ResearchNode (task_id, node_type, etc.)

        Returns:
            Created ResearchNode instance with auto-generated ID
        """
        async with self.async_session() as session:
            node = ResearchNode(**kwargs)
            session.add(node)
            await session.commit()
            await session.refresh(node)
            return node
        
    async def get_nodes_by_task(self, task_id: str) -> list[ResearchNode]:
        """
        Get all nodes for a task, ordered by creation time.

        Args:
            task_id: UUID string of parent research task

        Returns:
            List of all ResearchNode instances for the task
        """
        async with self.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(ResearchNode).where(ResearchNode.task_id == task_id).order_by(ResearchNode.created_at)
            )
            return list(result.scalars().all())

    async def update_research_task(self, task_id: str, **kwargs) -> Optional[ResearchTask]:
        """
        Update a research task.

        Commonly used to change task status (e.g., to "synthesis_ready")
        when research is complete.

        Args:
            task_id: UUID string of task to update
            **kwargs: Fields to update (e.g., status)

        Returns:
            Updated ResearchTask instance or None if not found
        """
        async with self.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(ResearchTask).where(ResearchTask.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return None
            for key, value in kwargs.items():
                setattr(task, key, value)
            await session.commit()
            await session.refresh(task)
            return task

    async def get_completed_nodes_by_task(self, task_id: str) -> list[ResearchNode]:
        """
        Get completed nodes with extracted facts for a task.

        This filters for nodes that have finished processing and
        contain meaningful extracted data, which is used by
        synthesis node to generate reports.

        Args:
            task_id: UUID string of parent research task

        Returns:
            List of ResearchNode instances with status="completed"
            and non-null extracted_facts
        """
        async with self.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(ResearchNode)
                .where(ResearchNode.task_id == task_id)
                .where(ResearchNode.status == "completed")
                .where(ResearchNode.extracted_facts.isnot(None))
                .order_by(ResearchNode.created_at)
            )
            return list(result.scalars().all())