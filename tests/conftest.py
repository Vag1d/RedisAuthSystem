import os
import sys
from pathlib import Path

# Включаем тестовый режим до импорта app
os.environ["TESTING"] = "1"

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from app.main import app
from app.routers.auth import users_db
from app.redis_client import redis_client

@pytest_asyncio.fixture(autouse=True)
async def clear_state():
    """Очищает хранилище Redis-заглушки перед каждым тестом"""
    users_db.clear()
    if hasattr(redis_client, 'store'):
        redis_client.store.clear()
    yield
    users_db.clear()
    if hasattr(redis_client, 'store'):
        redis_client.store.clear()

@pytest_asyncio.fixture
async def client() -> AsyncGenerator:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac