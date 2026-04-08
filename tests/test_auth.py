import pytest
from httpx import AsyncClient
from app.redis_client import redis_client

pytestmark = pytest.mark.asyncio

async def test_register_success(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "username": "testuser",
        "password": "pass123",
        "role": "user"
    })
    assert resp.status_code == 200
    assert resp.json() == {"msg": "User created"}

async def test_register_duplicate(client: AsyncClient):
    await client.post("/auth/register", json={"username": "duplicate", "password": "123", "role": "user"})
    resp = await client.post("/auth/register", json={"username": "duplicate", "password": "123", "role": "user"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Username already exists"

async def test_register_invalid_role(client: AsyncClient):
    resp = await client.post("/auth/register", json={
        "username": "badrole",
        "password": "123",
        "role": "superuser"
    })
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid role"

async def test_login_success(client: AsyncClient):
    await client.post("/auth/register", json={"username": "logintest", "password": "secret", "role": "user"})
    resp = await client.post("/auth/login", json={"username": "logintest", "password": "secret"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/register", json={"username": "wrongpass", "password": "correct", "role": "user"})
    resp = await client.post("/auth/login", json={"username": "wrongpass", "password": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"

async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/auth/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401

async def test_logout_revokes_token(client: AsyncClient):
    await client.post("/auth/register", json={"username": "logoutuser", "password": "123", "role": "user"})
    login = await client.post("/auth/login", json={"username": "logoutuser", "password": "123"})
    access_token = login.json()["access_token"]

    logout_resp = await client.post("/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert logout_resp.status_code == 200
    assert logout_resp.json() == {"msg": "Logged out"}

    blacklisted = await redis_client.exists(f"blacklist:{access_token}")
    assert blacklisted == 1

    resp = await client.get("/content/common", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Token revoked"

async def test_refresh_success(client: AsyncClient):
    await client.post("/auth/register", json={"username": "refreshuser", "password": "123", "role": "user"})
    login = await client.post("/auth/login", json={"username": "refreshuser", "password": "123"})
    refresh_token = login.json()["refresh_token"]

    refresh_resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data
    assert new_data["refresh_token"] != refresh_token

    old_refresh_stored = await redis_client.get(f"refresh:refreshuser")
    assert old_refresh_stored != refresh_token
    assert old_refresh_stored == new_data["refresh_token"]

async def test_refresh_with_revoked_token_fails(client: AsyncClient):
    await client.post("/auth/register", json={"username": "revokedrefresh", "password": "123", "role": "user"})
    login = await client.post("/auth/login", json={"username": "revokedrefresh", "password": "123"})
    refresh_token = login.json()["refresh_token"]
    access_token = login.json()["access_token"]

    await client.post("/auth/logout", headers={"Authorization": f"Bearer {access_token}"})

    refresh_resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401
    assert refresh_resp.json()["detail"] == "Refresh token not found or revoked"

async def test_refresh_with_invalid_token_fails(client: AsyncClient):
    resp = await client.post("/auth/refresh", json={"refresh_token": "invalid.token.here"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid refresh token"