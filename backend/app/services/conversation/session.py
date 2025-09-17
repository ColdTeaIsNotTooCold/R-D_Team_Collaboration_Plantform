"""
会话管理服务
提供用户会话创建、维护、清理等功能
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from ...models.conversation import ConversationSession, Conversation
from ...models.user import User
from ...core.config import settings

logger = logging.getLogger(__name__)


class SessionManager:
    """会话管理器"""

    def __init__(self, db: Session):
        self.db = db
        self.default_session_timeout = 3600 * 24  # 24小时
        self.anonymous_session_timeout = 3600 * 2  # 2小时

    async def create_session(
        self,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationSession:
        """创建新会话"""
        try:
            # 生成会话ID
            if not session_id:
                session_id = str(uuid.uuid4())

            # 设置会话过期时间
            if user_id:
                expires_at = datetime.utcnow() + timedelta(seconds=self.default_session_timeout)
            else:
                expires_at = datetime.utcnow() + timedelta(seconds=self.anonymous_session_timeout)

            session = ConversationSession(
                session_id=session_id,
                user_id=user_id,
                title=title,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                user_agent=user_agent,
                ip_address=ip_address,
                metadata=metadata or {},
                is_active=True,
                expires_at=expires_at
            )

            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)

            logger.info(f"创建新会话: {session_id} (用户: {user_id})")
            return session

        except Exception as e:
            self.db.rollback()
            logger.error(f"创建会话失败: {str(e)}")
            raise

    async def get_session(
        self,
        session_id: str,
        user_id: Optional[int] = None,
        validate_expiration: bool = True
    ) -> Optional[ConversationSession]:
        """获取会话"""
        try:
            query = self.db.query(ConversationSession).filter(
                ConversationSession.session_id == session_id
            )

            if user_id:
                query = query.filter(ConversationSession.user_id == user_id)

            session = query.first()

            if not session:
                return None

            # 检查会话是否过期
            if validate_expiration and session.expires_at:
                if datetime.utcnow() > session.expires_at:
                    await self.deactivate_session(session_id)
                    return None

            return session

        except Exception as e:
            logger.error(f"获取会话失败: {str(e)}")
            raise

    async def update_session_activity(
        self,
        session_id: str,
        user_id: Optional[int] = None
    ) -> bool:
        """更新会话活动时间"""
        try:
            session = await self.get_session(session_id, user_id)
            if not session:
                return False

            session.last_activity = datetime.utcnow()

            # 延长过期时间
            if session.user_id:
                session.expires_at = datetime.utcnow() + timedelta(seconds=self.default_session_timeout)
            else:
                session.expires_at = datetime.utcnow() + timedelta(seconds=self.anonymous_session_timeout)

            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"更新会话活动时间失败: {str(e)}")
            raise

    async def update_session_config(
        self,
        session_id: str,
        user_id: Optional[int] = None,
        **kwargs
    ) -> Optional[ConversationSession]:
        """更新会话配置"""
        try:
            session = await self.get_session(session_id, user_id)
            if not session:
                return None

            # 更新可配置的字段
            updatable_fields = {
                'title', 'model', 'system_prompt', 'temperature', 'max_tokens'
            }

            for key, value in kwargs.items():
                if key in updatable_fields and hasattr(session, key):
                    setattr(session, key, value)

            session.last_activity = datetime.utcnow()
            self.db.commit()
            self.db.refresh(session)

            logger.info(f"更新会话配置: {session_id}")
            return session

        except Exception as e:
            self.db.rollback()
            logger.error(f"更新会话配置失败: {str(e)}")
            raise

    async def link_conversation(
        self,
        session_id: str,
        conversation_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """将对话链接到会话"""
        try:
            session = await self.get_session(session_id, user_id)
            if not session:
                return False

            # 验证对话权限
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            )

            if user_id:
                conversation = conversation.filter(Conversation.user_id == user_id)

            conversation = conversation.first()

            if not conversation:
                return False

            session.conversation_id = conversation_id
            session.last_activity = datetime.utcnow()
            self.db.commit()

            logger.info(f"链接对话 {conversation_id} 到会话 {session_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"链接对话到会话失败: {str(e)}")
            raise

    async def deactivate_session(
        self,
        session_id: str,
        user_id: Optional[int] = None
    ) -> bool:
        """停用会话"""
        try:
            session = await self.get_session(session_id, user_id, validate_expiration=False)
            if not session:
                return False

            session.is_active = False
            session.expires_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"停用会话: {session_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"停用会话失败: {str(e)}")
            raise

    async def cleanup_expired_sessions(self, batch_size: int = 100) -> int:
        """清理过期会话"""
        try:
            expired_sessions = self.db.query(ConversationSession).filter(
                and_(
                    ConversationSession.is_active == True,
                    ConversationSession.expires_at < datetime.utcnow()
                )
            ).limit(batch_size).all()

            count = 0
            for session in expired_sessions:
                session.is_active = False
                count += 1

            self.db.commit()

            logger.info(f"清理了 {count} 个过期会话")
            return count

        except Exception as e:
            self.db.rollback()
            logger.error(f"清理过期会话失败: {str(e)}")
            raise

    async def list_user_sessions(
        self,
        user_id: int,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[ConversationSession]:
        """列出用户会话"""
        try:
            query = self.db.query(ConversationSession).filter(
                ConversationSession.user_id == user_id
            )

            if active_only:
                query = query.filter(ConversationSession.is_active == True)

            query = query.order_by(desc(ConversationSession.last_activity))
            return query.offset(offset).limit(limit).all()

        except Exception as e:
            logger.error(f"列出用户会话失败: {str(e)}")
            raise

    async def get_session_stats(
        self,
        session_id: str,
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """获取会话统计"""
        try:
            session = await self.get_session(session_id, user_id)
            if not session:
                return None

            # 计算会话时长
            duration = datetime.utcnow() - session.created_at
            duration_seconds = duration.total_seconds()

            stats = {
                "session_id": session_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "duration_seconds": duration_seconds,
                "is_active": session.is_active,
                "message_count": session.message_count,
                "total_tokens": session.total_tokens,
                "total_cost": session.total_cost,
                "model": session.model,
                "temperature": session.temperature,
                "max_tokens": session.max_tokens
            }

            # 添加关联对话信息
            if session.conversation_id:
                conversation = self.db.query(Conversation).filter(
                    Conversation.id == session.conversation_id
                ).first()

                if conversation:
                    stats["conversation"] = {
                        "id": conversation.id,
                        "title": conversation.title,
                        "message_count": conversation.message_count
                    }

            return stats

        except Exception as e:
            logger.error(f"获取会话统计失败: {str(e)}")
            raise

    async def transfer_session(
        self,
        session_id: str,
        from_user_id: Optional[int],
        to_user_id: int
    ) -> bool:
        """转移会话所有权"""
        try:
            session = await self.get_session(session_id, from_user_id)
            if not session:
                return False

            session.user_id = to_user_id
            session.last_activity = datetime.utcnow()
            self.db.commit()

            logger.info(f"将会话 {session_id} 从用户 {from_user_id} 转移到用户 {to_user_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"转移会话失败: {str(e)}")
            raise

    async def merge_sessions(
        self,
        primary_session_id: str,
        secondary_session_ids: List[str],
        user_id: Optional[int] = None
    ) -> bool:
        """合并多个会话"""
        try:
            primary_session = await self.get_session(primary_session_id, user_id)
            if not primary_session:
                return False

            # 获取所有要合并的会话
            secondary_sessions = []
            for session_id in secondary_session_ids:
                session = await self.get_session(session_id, user_id)
                if session:
                    secondary_sessions.append(session)

            if not secondary_sessions:
                return False

            # 合并统计信息
            total_messages = primary_session.message_count
            total_tokens = primary_session.total_tokens
            total_cost = primary_session.total_cost

            for session in secondary_sessions:
                total_messages += session.message_count
                total_tokens += session.total_tokens
                total_cost += session.total_cost

                # 停用次要会话
                session.is_active = False

            # 更新主会话
            primary_session.message_count = total_messages
            primary_session.total_tokens = total_tokens
            primary_session.total_cost = total_cost
            primary_session.last_activity = datetime.utcnow()

            self.db.commit()

            logger.info(f"合并会话: {primary_session_id} 吸收了 {len(secondary_sessions)} 个会话")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"合并会话失败: {str(e)}")
            raise

    async def validate_session_access(
        self,
        session_id: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """验证会话访问权限"""
        try:
            session = await self.get_session(session_id, user_id)
            if not session:
                return False

            # 检查IP地址限制（如果启用）
            if ip_address and session.ip_address:
                # 简单的IP匹配检查，可以扩展为更复杂的规则
                if session.ip_address != ip_address:
                    logger.warning(f"IP地址不匹配: 会话 {session_id} 期望 {session.ip_address}, 实际 {ip_address}")
                    return False

            return True

        except Exception as e:
            logger.error(f"验证会话访问失败: {str(e)}")
            return False

    async def get_active_session_count(
        self,
        user_id: Optional[int] = None
    ) -> int:
        """获取活跃会话数量"""
        try:
            query = self.db.query(ConversationSession).filter(
                ConversationSession.is_active == True,
                ConversationSession.expires_at > datetime.utcnow()
            )

            if user_id:
                query = query.filter(ConversationSession.user_id == user_id)

            return query.count()

        except Exception as e:
            logger.error(f"获取活跃会话数量失败: {str(e)}")
            return 0