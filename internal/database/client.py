import logging
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .models import Base, ResearchNode, ResearchTask, Template

logger = logging.getLogger(__name__)


class DatabaseClient:
    def __init__(self, database_url: str, pool_size: int = 10, max_overflow: int = 20):
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=False,
        )
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)

    async def init_db(self):
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        """Close database connection"""
        await self.engine.dispose()

    async def create_template(self, name: str, description: str, schema_json: dict) -> Template:
        """Create a new template"""
        async with self.async_session() as session:
            template = Template(name=name, description=description, schema_json=schema_json)
            session.add(template)
            await session.commit()
            await session.refresh(template)
            return template

    async def get_template(self, template_id: str) -> Optional[Template]:
        """Get a template by ID"""
        async with self.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(Template).where(Template.id == template_id))
            return result.scalar_one_or_none()

    async def create_research_task(self, goal: str, template_id: str, depth_limit: int) -> ResearchTask:
        """Create a new research task"""
        async with self.async_session() as session:
            task = ResearchTask(goal=goal, template_id=template_id, depth_limit=depth_limit)
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task

    async def get_research_task(self, task_id: str) -> Optional[ResearchTask]:
        """Get a research task by ID"""
        async with self.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(select(ResearchTask).where(ResearchTask.id == task_id))
            return result.scalar_one_or_none()

    async def create_node(self, **kwargs) -> ResearchNode:
        """Create a new research node"""
        async with self.async_session() as session:
            node = ResearchNode(**kwargs)
            session.add(node)
            await session.commit()
            await session.refresh(node)
            return node

    async def update_node(self, node_id: str, **kwargs) -> Optional[ResearchNode]:
        """Update a research node"""
        async with self.async_session() as session:
            result = await session.execute(ResearchNode.__table__.select().where(ResearchNode.id == node_id))
            node = result.scalar_one_or_none()
            if not node:
                return None
            for key, value in kwargs.items():
                setattr(node, key, value)
            await session.commit()
            await session.refresh(node)
            return node

    async def get_nodes_by_task(self, task_id: str) -> list[ResearchNode]:
        """Get all nodes for a task"""
        async with self.async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(ResearchNode).where(ResearchNode.task_id == task_id).order_by(ResearchNode.created_at)
            )
            return list(result.scalars().all())

    async def vector_similarity_search(self, query_vector: list[float], limit: int = 10) -> list[ResearchNode]:
        """Search for similar content by vector"""
        async with self.async_session() as session:
            from sqlalchemy import func
            from sqlalchemy.sql import select
            result = await session.execute(
                select(ResearchNode, ResearchNode.content_vector.cosine_distance(query_vector).label("distance"))
                .where(ResearchNode.content_vector.isnot(None))
                .order_by("distance")
                .limit(limit)
            )
            return [row[0] for row in result.all()]