"""
对话历史管理服务
提供对话历史存储、检索、管理等功能
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from ...models.conversation import Conversation, ConversationMessage, ConversationSession
from ...models.user import User
from ...models.context import Context
from ...core.database import get_db
from ...core.config import settings

logger = logging.getLogger(__name__)


class ConversationHistoryManager:
    """对话历史管理器"""

    def __init__(self, db: Session):
        self.db = db

    async def create_conversation(
        self,
        user_id: int,
        title: str,
        description: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Conversation:
        """创建新对话"""
        try:
            conversation = Conversation(
                user_id=user_id,
                title=title,
                description=description,
                session_id=session_id,
                model=model,
                system_prompt=system_prompt,
                **kwargs
            )

            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

            logger.info(f"创建新对话: {conversation.id} - {title}")
            return conversation

        except Exception as e:
            self.db.rollback()
            logger.error(f"创建对话失败: {str(e)}")
            raise

    async def get_conversation(
        self,
        conversation_id: int,
        user_id: Optional[int] = None
    ) -> Optional[Conversation]:
        """获取对话"""
        try:
            query = self.db.query(Conversation).filter(Conversation.id == conversation_id)

            if user_id:
                query = query.filter(Conversation.user_id == user_id)

            return query.first()

        except Exception as e:
            logger.error(f"获取对话失败: {str(e)}")
            raise

    async def get_conversation_by_session(
        self,
        session_id: str,
        user_id: Optional[int] = None
    ) -> Optional[Conversation]:
        """根据会话ID获取对话"""
        try:
            query = self.db.query(Conversation).filter(
                Conversation.session_id == session_id,
                Conversation.is_active == True
            )

            if user_id:
                query = query.filter(Conversation.user_id == user_id)

            return query.first()

        except Exception as e:
            logger.error(f"根据会话ID获取对话失败: {str(e)}")
            raise

    async def list_conversations(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        is_archived: bool = False,
        is_pinned: Optional[bool] = None,
        tags: Optional[List[str]] = None
    ) -> List[Conversation]:
        """列出用户的对话"""
        try:
            query = self.db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.is_archived == is_archived
            )

            if is_pinned is not None:
                query = query.filter(Conversation.is_pinned == is_pinned)

            if tags:
                # 使用JSON查询标签
                for tag in tags:
                    query = query.filter(Conversation.tags.contains([tag]))

            # 按最后消息时间排序
            query = query.order_by(desc(Conversation.last_message_at))

            return query.offset(skip).limit(limit).all()

        except Exception as e:
            logger.error(f"列出对话失败: {str(e)}")
            raise

    async def add_message(
        self,
        conversation_id: int,
        user_id: int,
        role: str,
        content: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        tokens: Optional[int] = None,
        cost: float = 0.0,
        latency: float = 0.0,
        finish_reason: Optional[str] = None,
        context_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """添加消息到对话"""
        try:
            # 获取当前序列号
            last_message = self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id
            ).order_by(desc(ConversationMessage.sequence)).first()

            sequence = (last_message.sequence + 1) if last_message else 1

            message = ConversationMessage(
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                content=content,
                sequence=sequence,
                model=model,
                provider=provider,
                tokens=tokens,
                cost=cost,
                latency=latency,
                finish_reason=finish_reason,
                context_id=context_id,
                parent_id=parent_id,
                metadata=metadata or {}
            )

            self.db.add(message)

            # 更新对话统计
            conversation = await self.get_conversation(conversation_id)
            if conversation:
                conversation.message_count += 1
                conversation.total_tokens += tokens or 0
                conversation.total_cost += cost
                conversation.last_message_at = datetime.utcnow()

                # 更新平均延迟
                if conversation.message_count > 1:
                    conversation.average_latency = (
                        (conversation.average_latency * (conversation.message_count - 1) + latency)
                        / conversation.message_count
                    )
                else:
                    conversation.average_latency = latency

            self.db.commit()
            self.db.refresh(message)

            logger.info(f"添加消息到对话 {conversation_id}: {role} - {content[:50]}...")
            return message

        except Exception as e:
            self.db.rollback()
            logger.error(f"添加消息失败: {str(e)}")
            raise

    async def get_conversation_messages(
        self,
        conversation_id: int,
        user_id: Optional[int] = None,
        limit: Optional[int] = None,
        include_deleted: bool = False,
        include_hidden: bool = False
    ) -> List[ConversationMessage]:
        """获取对话消息"""
        try:
            # 验证对话权限
            conversation = await self.get_conversation(conversation_id, user_id)
            if not conversation:
                return []

            query = self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id
            )

            if not include_deleted:
                query = query.filter(ConversationMessage.is_deleted == False)

            if not include_hidden:
                query = query.filter(ConversationMessage.is_visible == True)

            query = query.order_by(ConversationMessage.sequence)

            if limit:
                query = query.limit(limit)

            return query.all()

        except Exception as e:
            logger.error(f"获取对话消息失败: {str(e)}")
            raise

    async def get_context_messages(
        self,
        conversation_id: int,
        max_tokens: int = 4000,
        max_messages: int = 50,
        compression_strategy: str = "truncate"
    ) -> List[Dict[str, Any]]:
        """获取用于AI回复的上下文消息"""
        try:
            # 获取最近的对话消息
            messages = await self.get_conversation_messages(
                conversation_id=conversation_id,
                limit=max_messages,
                include_deleted=False,
                include_hidden=False
            )

            # 转换为LLM格式
            context_messages = []
            total_tokens = 0

            for message in reversed(messages):  # 从最新的消息开始
                msg_dict = {
                    "role": message.role,
                    "content": message.content
                }

                # 简单估算token数（实际应该使用tokenizer）
                estimated_tokens = len(message.content.split()) * 1.3

                if total_tokens + estimated_tokens <= max_tokens:
                    context_messages.insert(0, msg_dict)  # 保持原始顺序
                    total_tokens += estimated_tokens
                else:
                    # 根据压缩策略处理
                    if compression_strategy == "truncate":
                        break
                    elif compression_strategy == "summarize":
                        # 这里可以添加总结逻辑
                        pass

            return context_messages

        except Exception as e:
            logger.error(f"获取上下文消息失败: {str(e)}")
            raise

    async def update_conversation(
        self,
        conversation_id: int,
        user_id: int,
        **kwargs
    ) -> Optional[Conversation]:
        """更新对话信息"""
        try:
            conversation = await self.get_conversation(conversation_id, user_id)
            if not conversation:
                return None

            for key, value in kwargs.items():
                if hasattr(conversation, key):
                    setattr(conversation, key, value)

            conversation.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(conversation)

            logger.info(f"更新对话 {conversation_id}")
            return conversation

        except Exception as e:
            self.db.rollback()
            logger.error(f"更新对话失败: {str(e)}")
            raise

    async def delete_conversation(
        self,
        conversation_id: int,
        user_id: int,
        soft_delete: bool = True
    ) -> bool:
        """删除对话"""
        try:
            if soft_delete:
                # 软删除：标记为已归档
                success = await self.update_conversation(
                    conversation_id, user_id, is_archived=True
                )
            else:
                # 硬删除
                conversation = await self.get_conversation(conversation_id, user_id)
                if conversation:
                    self.db.delete(conversation)
                    self.db.commit()
                    success = True
                else:
                    success = False

            if success:
                logger.info(f"删除对话 {conversation_id} (软删除: {soft_delete})")

            return success

        except Exception as e:
            self.db.rollback()
            logger.error(f"删除对话失败: {str(e)}")
            raise

    async def search_conversations(
        self,
        user_id: int,
        query: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Tuple[Conversation, float]]:
        """搜索对话"""
        try:
            # 搜索对话标题和描述
            conversations = self.db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.is_archived == False,
                or_(
                    Conversation.title.ilike(f"%{query}%"),
                    Conversation.description.ilike(f"%{query}%")
                )
            ).all()

            # 搜索消息内容
            messages = self.db.query(ConversationMessage).join(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.is_archived == False,
                ConversationMessage.content.ilike(f"%{query}%"),
                ConversationMessage.is_deleted == False
            ).all()

            # 收集相关对话并计算相关性分数
            conversation_scores = {}

            # 对话标题/描述匹配
            for conv in conversations:
                score = 1.0  # 标题匹配的基础分数
                if query.lower() in conv.title.lower():
                    score += 2.0
                if conv.description and query.lower() in conv.description.lower():
                    score += 1.0
                conversation_scores[conv.id] = {
                    'conversation': conv,
                    'score': score
                }

            # 消息内容匹配
            for msg in messages:
                if msg.conversation_id not in conversation_scores:
                    conversation_scores[msg.conversation_id] = {
                        'conversation': msg.conversation,
                        'score': 0.0
                    }

                # 消息匹配分数
                msg_score = 0.5
                if query.lower() in msg.content.lower():
                    msg_score += len(query) / len(msg.content)  # 基于匹配长度

                conversation_scores[msg.conversation_id]['score'] += msg_score

            # 按分数排序并返回结果
            results = sorted(
                [(data['conversation'], data['score']) for data in conversation_scores.values()],
                key=lambda x: x[1],
                reverse=True
            )

            return results[skip:skip + limit]

        except Exception as e:
            logger.error(f"搜索对话失败: {str(e)}")
            raise

    async def get_conversation_stats(
        self,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取对话统计信息"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # 基础统计
            total_conversations = self.db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date
            ).count()

            active_conversations = self.db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.is_active == True,
                Conversation.is_archived == False
            ).count()

            # 消息统计
            total_messages = self.db.query(ConversationMessage).join(Conversation).filter(
                Conversation.user_id == user_id,
                ConversationMessage.created_at >= start_date
            ).count()

            # 成本统计
            total_cost = self.db.query(
                func.sum(Conversation.total_cost)
            ).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date
            ).scalar() or 0.0

            # Token统计
            total_tokens = self.db.query(
                func.sum(Conversation.total_tokens)
            ).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date
            ).scalar() or 0

            # 平均延迟
            avg_latency = self.db.query(
                func.avg(Conversation.average_latency)
            ).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date
            ).scalar() or 0.0

            return {
                "total_conversations": total_conversations,
                "active_conversations": active_conversations,
                "total_messages": total_messages,
                "total_cost": float(total_cost),
                "total_tokens": total_tokens,
                "average_latency": float(avg_latency),
                "period_days": days
            }

        except Exception as e:
            logger.error(f"获取对话统计失败: {str(e)}")
            raise

    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """清理旧的会话"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            deleted_count = self.db.query(ConversationSession).filter(
                ConversationSession.last_activity < cutoff_date,
                ConversationSession.is_active == True
            ).update({"is_active": False})

            self.db.commit()

            logger.info(f"清理了 {deleted_count} 个旧会话")
            return deleted_count

        except Exception as e:
            self.db.rollback()
            logger.error(f"清理旧会话失败: {str(e)}")
            raise