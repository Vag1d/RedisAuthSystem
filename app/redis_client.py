import os
from redis.asyncio import Redis
from app.config import REDIS_URL

class FakeRedisClient:
    """Заглушка для тестирования имитирует Redis"""
    def __init__(self):
        self.store = {}

    async def setex(self, key, ttl, value):
        self.store[key] = value
        return True

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, key):
        self.store.pop(key, None)
        return 1

    async def exists(self, key):
        return 1 if key in self.store else 0

    async def close(self):
        pass


if os.getenv("TESTING"):
    redis_client = FakeRedisClient()
else:
    redis_client = Redis.from_url(REDIS_URL, decode_responses=True)