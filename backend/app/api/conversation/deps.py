"""
对话管理API依赖项
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.auth import get_current_user
from ...models.user import User
from ...services.conversation import (
    ConversationHistoryManager,
    SmartContextManager,
    SessionManager,
    ContextCompressionManager,
    RAGLLMIntegration
)

security = HTTPBearer()


def get_conversation_manager(db: Session = Depends(get_db)) -> ConversationHistoryManager:
    """获取对话历史管理器"""
    return ConversationHistoryManager(db)


def get_context_manager(db: Session = Depends(get_db)) -> SmartContextManager:
    """获取智能上下文管理器"""
    return SmartContextManager(db)


def get_session_manager(db: Session = Depends(get_db)) -> SessionManager:
    """获取会话管理器"""
    return SessionManager(db)


def get_compression_manager(db: Session = Depends(get_db)) -> ContextCompressionManager:
    """获取压缩管理器"""
    return ContextCompressionManager(db)


def get_rag_integration(db: Session = Depends(get_db)) -> RAGLLMIntegration:
    """获取RAG集成服务"""
    return RAGLLMIntegration(db)


async def get_conversation_or_404(
    conversation_id: int,
    user: User = Depends(get_current_user),
    manager: ConversationHistoryManager = Depends(get_conversation_manager),
    db: Session = Depends(get_db)
):
    """获取对话或返回404错误"""
    conversation = await manager.get_conversation(conversation_id, user.id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="对话不存在或无权限访问"
        )
    return conversation


async def get_session_or_404(
    session_id: str,
    user: Optional[User] = Depends(get_current_user),
    manager: SessionManager = Depends(get_session_manager)
):
    """获取会话或返回404错误"""
    session = await manager.get_session(session_id, user.id if user else None)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权限访问"
        )
    return session


def validate_conversation_access(
    conversation_id: int,
    user: User = Depends(get_current_user),
    manager: ConversationHistoryManager = Depends(get_conversation_manager)
):
    """验证对话访问权限"""
    from ...models.conversation import Conversation
    conversation = manager.db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此对话"
    )
    return conversation


def validate_session_access(
    session_id: str,
    user: Optional[User] = Depends(get_current_user),
    manager: SessionManager = Depends(get_session_manager),
    ip_address: Optional[str] = None
):
    """验证会话访问权限"""
    access_valid = await manager.validate_session_access(
        session_id, user.id if user else None, ip_address
    )

    if not access_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此会话或会话已过期"
        )

    return session_id


def get_optional_user():
    """获取可选用户（支持匿名访问）"""
    try:
        return Depends(get_current_user)
    except:
        return None