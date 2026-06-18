from redis.asyncio import Redis


class RedisUtil:
    @staticmethod
    async def set_value(client: Redis, key: str, value: str | int, expire: int | None = None):
        await client.set(key, value, ex=expire)

    @staticmethod
    async def get_value(client: Redis, key: str) -> str | None:
        return await client.get(key)

    @staticmethod
    async def delete_value(client: Redis, key: str):
        return await client.delete(key)
    
    @staticmethod
    async def exists(client: Redis, key: str) -> int:
        return await client.exists(key)