"""
LLM API依赖项
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...services.llm.manager import get_llm_manager
from ...services.llm.exceptions import LLMException
from ...models.user import User
from ...api.deps import get_current_user

security = HTTPBearer()


async def get_llm_manager():
    """获取LLM管理器"""
    try:
        return await get_llm_manager()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM服务不可用: {e}"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[User]:
    """获取当前用户"""
    # 这里简化实现，实际应该从JWT token中获取用户信息
    # 暂时返回一个默认用户
    return User(
        id="default_user",
        username="default_user",
        email="default@example.com",
        is_active=True
    )


async def validate_model(model: str):
    """验证模型是否可用"""
    try:
        manager = await get_llm_manager()
        available_models = await manager.get_available_models()
        if model not in available_models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"模型 '{model}' 不可用"
            )
        return model
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"验证模型失败: {e}"
        )