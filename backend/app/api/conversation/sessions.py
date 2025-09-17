"""
会话管理API路由
提供会话创建、管理、维护等功能
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer
import logging
from datetime import datetime

from ...models.user import User
from ...core.auth import get_current_user
from .schemas import *
from .deps import *

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["会话管理"])


@router.post("/", response_model=SessionResponse)
async def create_session(
    session: SessionCreate,
    user: Optional[User] = Depends(get_current_user),
    manager: SessionManager = Depends(get_session_manager)
):
    """创建新会话"""
    try:
        user_id = user.id if user else None
        new_session = await manager.create_session(
            user_id=user_id,
            session_id=session.session_id,
            title=session.title,
            model=session.model,
            system_prompt=session.system_prompt,
            temperature=session.temperature,
            max_tokens=session.max_tokens,
            user_agent=session.user_agent,
            ip_address=session.ip_address,
            metadata=session.metadata
        )
        return new_session

    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建会话失败: {str(e)}"
        )


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    active_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    manager: SessionManager = Depends(get_session_manager)
):
    """列出用户会话"""
    try:
        sessions = await manager.list_user_sessions(
            user_id=user.id,
            active_only=active_only,
            limit=limit,
            offset=offset
        )
        return sessions

    except Exception as e:
        logger.error(f"列出会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话列表失败: {str(e)}"
        )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session: Session = Depends(get_session_or_404)
):
    """获取会话详情"""
    return session


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_update: SessionUpdate,
    session: Session = Depends(get_session_or_404),
    manager: SessionManager = Depends(get_session_manager)
):
    """更新会话配置"""
    try:
        # 过滤None值
        update_data = {k: v for k, v in session_update.dict().items() if v is not None}

        updated_session = await manager.update_session_config(
            session_id=session.session_id,
            user_id=session.user_id,
            **update_data
        )

        if not updated_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )

        return updated_session

    except Exception as e:
        logger.error(f"更新会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新会话失败: {str(e)}"
        )


@router.post("/{session_id}/activity")
async def update_session_activity(
    session_id: str = Depends(validate_session_access),
    user: Optional[User] = Depends(get_current_user),
    manager: SessionManager = Depends(get_session_manager)
):
    """更新会话活动时间"""
    try:
        success = await manager.update_session_activity(
            session_id=session_id,
            user_id=user.id if user else None
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )

        return {"message": "会话活动时间已更新"}

    except Exception as e:
        logger.error(f"更新会话活动时间失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新失败: {str(e)}"
        )


@router.delete("/{session_id}")
async def deactivate_session(
    session_id: str = Depends(validate_session_access),
    user: Optional[User] = Depends(get_current_user),
    manager: SessionManager = Depends(get_session_manager)
):
    """停用会话"""
    try:
        success = await manager.deactivate_session(
            session_id=session_id,
            user_id=user.id if user else None
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )

        return {"message": "会话已停用"}

    except Exception as e:
        logger.error(f"停用会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停用会话失败: {str(e)}"
        )


@router.post("/{session_id}/link-conversation/{conversation_id}")
async def link_conversation(
    conversation_id: int,
    session_id: str = Depends(validate_session_access),
    user: Optional[User] = Depends(get_current_user),
    manager: SessionManager = Depends(get_session_manager)
):
    """将对话链接到会话"""
    try:
        success = await manager.link_conversation(
            session_id=session_id,
            conversation_id=conversation_id,
            user_id=user.id if user else None
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话或对话不存在"
            )

        return {"message": "对话已链接到会话"}

    except Exception as e:
        logger.error(f"链接对话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"链接对话失败: {str(e)}"
        )


@router.get("/{session_id}/stats")
async def get_session_stats(
    session_id: str = Depends(validate_session_access),
    user: Optional[User] = Depends(get_current_user),
    manager: SessionManager = Depends(get_session_manager)
):
    """获取会话统计"""
    try:
        stats = await manager.get_session_stats(
            session_id=session_id,
            user_id=user.id if user else None
        )

        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在"
            )

        return stats

    except Exception as e:
        logger.error(f"获取会话统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计失败: {str(e)}"
        )


@router.post("/transfer")
async def transfer_session(
    from_user_id: int,
    to_user_id: int,
    session_id: str,
    user: User = Depends(get_current_user),
    manager: SessionManager = Depends(get_session_manager)
):
    """转移会话所有权"""
    try:
        # 验证权限
        if not user.is_superuser and user.id != from_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权转移此会话"
            )

        success = await manager.transfer_session(
            session_id=session_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或转移失败"
            )

        return {"message": "会话转移成功"}

    except Exception as e:
        logger.error(f"转移会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"转移会话失败: {str(e)}"
        )


@router.post("/merge")
async def merge_sessions(
    primary_session_id: str,
    secondary_session_ids: List[str],
    user: User = Depends(get_current_user),
    manager: SessionManager = Depends(get_session_manager)
):
    """合并多个会话"""
    try:
        success = await manager.merge_sessions(
            primary_session_id=primary_session_id,
            secondary_session_ids=secondary_session_ids,
            user_id=user.id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或合并失败"
            )

        return {"message": "会话合并成功"}

    except Exception as e:
        logger.error(f"合并会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"合并会话失败: {str(e)}"
        )


@router.get("/active/count")
async def get_active_session_count(
    user: Optional[User] = Depends(get_current_user),
    manager: SessionManager = Depends(get_session_manager)
):
    """获取活跃会话数量"""
    try:
        user_id = user.id if user else None
        count = await manager.get_active_session_count(user_id=user_id)
        return {"active_sessions": count}

    except Exception as e:
        logger.error(f"获取活跃会话数量失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数量失败: {str(e)}"
        )