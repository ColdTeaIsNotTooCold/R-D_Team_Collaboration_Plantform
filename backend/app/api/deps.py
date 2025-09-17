from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Generator

from ..core.database import get_db
from ..core.security import verify_token
from ..core.redis import (
    get_redis_cache,
    get_redis_stream,
    get_redis_session,
    get_redis_manager
)

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[dict]:
    """获取当前用户"""
    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # TODO: 根据token中的用户ID获取用户信息
    return payload


def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    """获取当前活跃用户"""
    if not current_user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Redis依赖注入
def get_redis_cache_dep():
    """获取Redis缓存依赖"""
    return get_redis_cache()


def get_redis_stream_dep():
    """获取Redis Stream依赖"""
    return get_redis_stream()


def get_redis_session_dep():
    """获取Redis会话依赖"""
    return get_redis_session()


def get_redis_manager_dep():
    """获取Redis管理器依赖"""
    return get_redis_manager()


def get_cached_user(
    token: str,
    db: Session = Depends(get_db),
    redis_cache=Depends(get_redis_cache_dep)
) -> Optional[dict]:
    """从缓存获取用户信息"""
    cache_key = f"user:{token}"
    cached_user = redis_cache.get(cache_key)

    if cached_user:
        return cached_user

    # 如果缓存中没有，从数据库获取
    # TODO: 实现数据库查询逻辑
    return None


def cache_user_data(
    token: str,
    user_data: dict,
    redis_cache=Depends(get_redis_cache_dep)
) -> bool:
    """缓存用户数据"""
    cache_key = f"user:{token}"
    return redis_cache.set(cache_key, user_data, ttl=3600)  # 1小时缓存