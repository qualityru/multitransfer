import json

from redis import asyncio as aioredis

from config import settings


class RedisStorage:
    def __init__(self):
        self.data = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASS,
            encoding="utf-8",
            decode_responses=True,
            db=0,
        )

    async def get(self, key):
        return await self.data.get(key)

    async def set_json(self, key, value: dict):
        await self.data.set(key, json.dumps(value))

    async def get_json(self, key):
        data = await self.data.get(key)
        return json.loads(data) if data else None

    async def delete(self, key):
        await self.data.delete(key)

    async def redis_set_json(self, key: str, value: dict, ttl: int = 120):
        await self.data.set(key, json.dumps(value), ex=ttl)

    async def redis_get_json(self, key: str):
        data = await self.data.get(key)
        return json.loads(data) if data else None


redis = RedisStorage()
