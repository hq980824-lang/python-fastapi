from sqlalchemy import text
from src.config.db import mysql_engine
from src.config.redis import redis_client


async def check_redis() -> bool:
    try:
        await redis_client.ping()
        return True
    except Exception:
        return False


async def check_mysql() -> bool:
    try:
        async with mysql_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
