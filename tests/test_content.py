import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def get_tokens(client, username, password):
    await client.post("/auth/register", json={"username": username, "password": password, "role": "user"})
    login = await client.post("/auth/login", json={"username": username, "password": password})
    return login.json()["access_token"]

async def get_admin_tokens(client):
    await client.post("/auth/register", json={"username": "admin1", "password": "admin", "role": "admin"})
    login = await client.post("/auth/login", json={"username": "admin1", "password": "admin"})
    return login.json()["access_token"]

async def test_common_content_accessible(client: AsyncClient):
    token = await get_tokens(client, "commonuser", "pass")
    resp = await client.get("/content/common", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["content"] == "This is common content for all authenticated users"
    assert resp.json()["user"] == "commonuser"

async def test_common_content_unauthenticated(client: AsyncClient):
    resp = await client.get("/content/common")
    assert resp.status_code == 403  # HTTPBearer возвращает 403 при отсутствии заголовка

async def test_user_content_allowed_for_user(client: AsyncClient):
    token = await get_tokens(client, "user1", "123")
    resp = await client.get("/content/user", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["content"] == "User exclusive content"
    assert resp.json()["user"] == "user1"

async def test_user_content_forbidden_for_admin(client: AsyncClient):
    token = await get_admin_tokens(client)
    resp = await client.get("/content/user", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Insufficient permissions"

async def test_admin_content_allowed_for_admin(client: AsyncClient):
    token = await get_admin_tokens(client)
    resp = await client.get("/content/admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["content"] == "Admin exclusive content"
    assert resp.json()["admin"] == "admin1"

async def test_admin_content_forbidden_for_user(client: AsyncClient):
    token = await get_tokens(client, "regular", "pass")
    resp = await client.get("/content/admin", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Insufficient permissions"

async def test_access_with_blacklisted_token_fails(client: AsyncClient):
    token = await get_tokens(client, "blacklistme", "pass")
    await client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    resp = await client.get("/content/common", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token revoked"