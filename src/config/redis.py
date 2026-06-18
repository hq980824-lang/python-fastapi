from typing import AsyncGenerator
from redis.asyncio import ConnectionPool, Redis
from src.config.settings import settings

redis_pool = ConnectionPool.from_url(
    url=settings.redis_url,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    decode_responses=True
)

redis_client = Redis(connection_pool=redis_pool)

async def get_redis() -> AsyncGenerator[Redis, None]:
    yield redis_client