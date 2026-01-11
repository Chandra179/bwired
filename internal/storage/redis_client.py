import logging
from redis.asyncio import Redis, ConnectionPool
from typing import Optional

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
        self.client = Redis(connection_pool=self.pool)
        await self.client.ping()
        logger.info("Connected to Redis")

    async def close(self):
        if self.client:
            await self.client.close()
            await self.pool.disconnect()
            logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[str]:
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None):
        if not self.client:
            raise RuntimeError("Redis client not connected")
        await self.client.set(key, value, ex=ex)

    async def exists(self, key: str) -> int:
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.exists(key)

    async def zadd(self, key: str, score: float, member: str) -> int:
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.zadd(key, {member: score})

    async def zpopmax(self, key: str) -> Optional[tuple]:
        if not self.client:
            raise RuntimeError("Redis client not connected")
        result = await self.client.zpopmax(key, count=1)
        return result[0] if result else None

    async def zcard(self, key: str) -> int:
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.zcard(key)

    async def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.zremrangebyscore(key, min_score, max_score)

    async def remove_key(self, key: str) -> int:
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.delete(key)
