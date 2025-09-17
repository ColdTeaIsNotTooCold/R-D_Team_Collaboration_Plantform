from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..api.deps import get_current_active_user

router = APIRouter()


@router.get("/", response_model=List[dict])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    # TODO: 实现用户列表查询逻辑
    return [
        {"id": 1, "username": "user1", "email": "user1@example.com", "is_active": True},
        {"id": 2, "username": "user2", "email": "user2@example.com", "is_active": True}
    ]


@router.get("/me", response_model=dict)
async def read_users_me(current_user: dict = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


@router.get("/{user_id}", response_model=dict)
async def read_user(
    user_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取指定用户信息"""
    # TODO: 实现用户查询逻辑
    if user_id == 1:
        return {"id": user_id, "username": "user1", "email": "user1@example.com", "is_active": True}
    raise HTTPException(status_code=404, detail="User not found")