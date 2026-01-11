import logging
from redis.asyncio import Redis, ConnectionPool
from typing import Optional, Any

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self, redis_url: str, db: int = 0, max_connections: int = 50):
        self.url = redis_url
        self.db = db
        self.pool = ConnectionPool.from_url(
            redis_url,
            db=db,
            max_connections=max_connections,
            decode_responses=True,
        )
        self.client: Optional[Redis] = None

    async def connect(self):
        """Connect to Redis"""
        self.client = Redis(connection_pool=self.pool)
        await self.client.ping()
        logger.info("Connected to Redis")

    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            await self.pool.disconnect()
            logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        raise NotImplementedError

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set key-value pair"""
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        """Delete key"""
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        raise NotImplementedError