from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi import Request
from pydantic import BaseModel
from app.auth import (
    hash_password, verify_password, create_access_token, create_refresh_token, decode_token
)
from app.dependencies import any_authenticated
from app.redis_client import redis_client
from app.config import REFRESH_TOKEN_EXPIRE_DAYS


router = APIRouter(prefix="/auth", tags=["auth"])


# Простая имитация базы 
users_db = {}


class UserRegister(BaseModel):
    username: str
    password: str
    role: str = "user"  # "user" или "admin"


class UserLogin(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register")
async def register(user: UserRegister):
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="Username already exists")
    if user.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Invalid role")
    hashed = hash_password(user.password)
    users_db[user.username] = {
        "username": user.username,
        "password": hashed,
        "role": user.role
    }
    return {"msg": "User created"}


@router.post("/login")
async def login(form: UserLogin):
    user = users_db.get(form.username)
    if not user or not verify_password(form.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    refresh_token = create_refresh_token(data={"sub": user["username"], "role": user["role"]})
    
    # Сохраняем refresh-токен в Redis (активный, с TTL)
    await redis_client.setex(
        f"refresh:{user['username']}",
        REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        refresh_token
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


# logout с получением токена
@router.post("/logout")
async def logout(request: Request, current_user: dict = Depends(any_authenticated)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    token = auth_header.split(" ")[1]
    # Добавляем access-токен в чёрный список до его истечения
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        exp = payload.get("exp")
        if exp:
            ttl = max(exp - int(datetime.now(timezone.utc).timestamp()), 0)
            if ttl > 0:
                await redis_client.setex(f"blacklist:{token}", ttl, "revoked")
    # Удаляем refresh-токен пользователя
    username = current_user.get("sub")
    await redis_client.delete(f"refresh:{username}")
    return {"msg": "Logged out"}


@router.post("/refresh")
async def refresh(refresh_req: RefreshRequest):
    payload = decode_token(refresh_req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    username = payload.get("sub")
    stored_refresh = await redis_client.get(f"refresh:{username}")
    if not stored_refresh or stored_refresh != refresh_req.refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token not found or revoked")
    
    # Создаём новые токены
    new_access = create_access_token(data={"sub": username, "role": payload.get("role")})
    new_refresh = create_refresh_token(data={"sub": username, "role": payload.get("role")})
    # Обновляем refresh в Redis
    await redis_client.setex(
        f"refresh:{username}",
        REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        new_refresh
    )
    # старый refresh можно добавить в чёрный список, но не обязательно, т.к. он удалён.
    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}
