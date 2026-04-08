from fastapi import APIRouter, Depends
from app.dependencies import any_authenticated, role_required

router = APIRouter(prefix="/content", tags=["content"])

@router.get("/common")
async def common_content(current_user: dict = Depends(any_authenticated)):
    return {"content": "This is common content for all authenticated users", "user": current_user["sub"]}

@router.get("/admin")
async def admin_content(current_user: dict = Depends(role_required("admin"))):
    return {"content": "Admin exclusive content", "admin": current_user["sub"]}

@router.get("/user")
async def user_content(current_user: dict = Depends(role_required("user"))):
    return {"content": "User exclusive content", "user": current_user["sub"]}