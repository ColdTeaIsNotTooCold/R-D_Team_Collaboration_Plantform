"""
RAG系统和LLM服务集成
提供对话系统与RAG、LLM的集成功能
"""
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import json
import logging
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from ...models.conversation import Conversation, ConversationMessage, Context
from ...models.context import Context as ContextModel
from ...core.config import settings

# 尝试导入现有的RAG和LLM服务
try:
    from ...core.rag_pipeline import get_rag_system
    from ...services.llm.manager import get_llm_manager
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("RAG或LLM服务不可用，将使用模拟服务")

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ResponseMode(Enum):
    """响应模式"""
    CHAT_ONLY = "chat_only"  # 仅对话
    RAG_ENHANCED = "rag_enhanced"  # RAG增强
    HYBRID = "hybrid"  # 混合模式


@dataclass
class RAGEnhancedRequest:
    """RAG增强请求"""
    conversation_id: int
    user_id: int
    message: str
    mode: ResponseMode = ResponseMode.HYBRID
    max_tokens: int = 2000
    temperature: float = 0.7
    enable_context: bool = True
    enable_rag: bool = True
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RAGEnhancedResponse:
    """RAG增强响应"""
    content: str
    sources: List[Dict[str, Any]]
    context_messages: List[Dict[str, Any]]
    usage: Dict[str, Any]
    cost: float
    latency: float
    mode: ResponseMode
    metadata: Dict[str, Any]


class RAGLLMIntegration:
    """RAG和LLM集成服务"""

    def __init__(self, db: Session):
        self.db = db
        self.rag_available = RAG_AVAILABLE
        self.llm_available = RAG_AVAILABLE

    async def process_message(
        self,
        request: RAGEnhancedRequest
    ) -> RAGEnhancedResponse:
        """处理用户消息"""
        try:
            start_time = datetime.utcnow()

            # 保存用户消息
            await self._save_user_message(request)

            # 构建上下文
            context_messages = []
            if request.enable_context:
                context_messages = await self._build_conversation_context(
                    request.conversation_id,
                    request.system_prompt
                )

            # RAG检索
            rag_sources = []
            if request.enable_rag and self.rag_available:
                rag_sources = await self._perform_rag_retrieval(request.message)

            # 生成响应
            response_content, usage = await self._generate_response(
                request,
                context_messages,
                rag_sources
            )

            # 保存助手回复
            await self._save_assistant_response(
                request,
                response_content,
                usage,
                start_time
            )

            # 更新对话统计
            await self._update_conversation_stats(
                request.conversation_id,
                usage,
                start_time
            )

            latency = (datetime.utcnow() - start_time).total_seconds()
            cost = self._calculate_cost(usage)

            return RAGEnhancedResponse(
                content=response_content,
                sources=rag_sources,
                context_messages=context_messages,
                usage=usage,
                cost=cost,
                latency=latency,
                mode=request.mode,
                metadata={
                    "conversation_id": request.conversation_id,
                    "processing_time": latency,
                    "rag_enabled": request.enable_rag,
                    "context_enabled": request.enable_context
                }
            )

        except Exception as e:
            logger.error(f"处理消息失败: {str(e)}")
            raise

    async def _save_user_message(self, request: RAGEnhancedRequest) -> ConversationMessage:
        """保存用户消息"""
        try:
            # 获取消息序列号
            last_message = self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == request.conversation_id
            ).order_by(ConversationMessage.sequence.desc()).first()

            sequence = (last_message.sequence + 1) if last_message else 1

            message = ConversationMessage(
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                role=MessageType.USER.value,
                content=request.message,
                sequence=sequence,
                metadata=request.metadata or {}
            )

            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)

            return message

        except Exception as e:
            self.db.rollback()
            logger.error(f"保存用户消息失败: {str(e)}")
            raise

    async def _build_conversation_context(
        self,
        conversation_id: int,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """构建对话上下文"""
        try:
            # 获取对话历史
            messages = self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.is_deleted == False
            ).order_by(ConversationMessage.sequence.desc()).limit(20).all()

            # 转换为上下文格式
            context_messages = []

            # 添加系统提示
            if system_prompt:
                context_messages.append({
                    "role": MessageType.SYSTEM.value,
                    "content": system_prompt
                })

            # 添加历史消息（按时间顺序）
            for msg in reversed(messages[-10:]):  # 最近10条消息
                context_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

            return context_messages

        except Exception as e:
            logger.error(f"构建对话上下文失败: {str(e)}")
            return []

    async def _perform_rag_retrieval(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """执行RAG检索"""
        try:
            if not self.rag_available:
                logger.warning("RAG服务不可用，返回空结果")
                return []

            # 获取RAG系统
            rag_system = await get_rag_system()

            # 执行检索
            search_results = await rag_system.search_documents(
                query=query,
                n_results=max_results
            )

            # 格式化结果
            sources = []
            for result in search_results:
                sources.append({
                    "id": result.get("id", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0.0),
                    "metadata": result.get("metadata", {})
                })

            return sources

        except Exception as e:
            logger.error(f"RAG检索失败: {str(e)}")
            return []

    async def _generate_response(
        self,
        request: RAGEnhancedRequest,
        context_messages: List[Dict[str, Any]],
        rag_sources: List[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any]]:
        """生成响应"""
        try:
            if not self.llm_available:
                # 模拟响应
                mock_response = self._generate_mock_response(request.message, rag_sources)
                mock_usage = {
                    "prompt_tokens": 100,
                    "completion_tokens": 200,
                    "total_tokens": 300
                }
                return mock_response, mock_usage

            # 获取LLM管理器
            llm_manager = await get_llm_manager()

            # 构建完整提示
            full_prompt = self._build_full_prompt(
                request.message,
                context_messages,
                rag_sources
            )

            # 构建LLM请求
            from ...models.llm import LLMRequest, LLMMessage

            llm_messages = [
                LLMMessage(role=msg["role"], content=msg["content"])
                for msg in full_prompt
            ]

            llm_request = LLMRequest(
                model=request.system_prompt or "gpt-3.5-turbo",
                messages=llm_messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                user_id=request.user_id,
                session_id=str(request.conversation_id)
            )

            # 生成响应
            response = await llm_manager.generate_response(llm_request)

            usage = {
                "prompt_tokens": response.usage.get("prompt_tokens", 0),
                "completion_tokens": response.usage.get("completion_tokens", 0),
                "total_tokens": response.usage.get("total_tokens", 0)
            }

            return response.content, usage

        except Exception as e:
            logger.error(f"生成响应失败: {str(e)}")
            # 返回错误响应
            error_response = f"抱歉，生成回复时出现错误: {str(e)}"
            error_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            return error_response, error_usage

    def _build_full_prompt(
        self,
        user_message: str,
        context_messages: List[Dict[str, Any]],
        rag_sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """构建完整提示"""
        full_prompt = context_messages.copy()

        # 添加RAG上下文
        if rag_sources:
            rag_context = "\n\n相关资料：\n"
            for i, source in enumerate(rag_sources[:3], 1):
                rag_context += f"{i}. {source['content']}\n"

            full_prompt.append({
                "role": MessageType.SYSTEM.value,
                "content": f"请参考以下相关资料来回答用户的问题：{rag_context}"
            })

        # 添加用户消息
        full_prompt.append({
            "role": MessageType.USER.value,
            "content": user_message
        })

        return full_prompt

    def _generate_mock_response(self, user_message: str, rag_sources: List[Dict[str, Any]]) -> str:
        """生成模拟响应"""
        if rag_sources:
            response = "基于检索到的资料，我可以为您提供以下信息：\n\n"
            for source in rag_sources[:2]:
                response += f"- {source['content'][:100]}...\n"
            response += f"\n关于您提到的'{user_message}'，建议您参考以上资料。"
        else:
            response = f"我收到了您的问题：'{user_message}'。这是一个模拟响应。"

        return response

    async def _save_assistant_response(
        self,
        request: RAGEnhancedRequest,
        content: str,
        usage: Dict[str, Any],
        start_time: datetime
    ) -> ConversationMessage:
        """保存助手响应"""
        try:
            # 获取消息序列号
            last_message = self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == request.conversation_id
            ).order_by(ConversationMessage.sequence.desc()).first()

            sequence = (last_message.sequence + 1) if last_message else 1

            latency = (datetime.utcnow() - start_time).total_seconds()
            cost = self._calculate_cost(usage)

            message = ConversationMessage(
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                role=MessageType.ASSISTANT.value,
                content=content,
                sequence=sequence,
                tokens=usage.get("total_tokens", 0),
                cost=cost,
                latency=latency,
                metadata={
                    "usage": usage,
                    "mode": request.mode.value,
                    "rag_sources_count": len(request.metadata.get("sources", [])) if request.metadata else 0
                }
            )

            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)

            return message

        except Exception as e:
            self.db.rollback()
            logger.error(f"保存助手响应失败: {str(e)}")
            raise

    async def _update_conversation_stats(
        self,
        conversation_id: int,
        usage: Dict[str, Any],
        start_time: datetime
    ) -> None:
        """更新对话统计"""
        try:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

            if conversation:
                conversation.message_count += 2  # 用户消息 + 助手响应
                conversation.total_tokens += usage.get("total_tokens", 0)
                conversation.total_cost += self._calculate_cost(usage)

                # 更新平均延迟
                latency = (datetime.utcnow() - start_time).total_seconds()
                if conversation.message_count > 2:
                    conversation.average_latency = (
                        (conversation.average_latency * (conversation.message_count - 2) + latency)
                        / (conversation.message_count - 1)
                    )
                else:
                    conversation.average_latency = latency

                conversation.last_message_at = datetime.utcnow()
                self.db.commit()

        except Exception as e:
            logger.error(f"更新对话统计失败: {str(e)}")
            self.db.rollback()

    def _calculate_cost(self, usage: Dict[str, Any]) -> float:
        """计算成本"""
        # 简单的成本计算（实际应该根据具体模型定价）
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        # 假设价格：$0.002/1K tokens (input), $0.002/1K tokens (output)
        cost = (prompt_tokens * 0.002 / 1000) + (completion_tokens * 0.002 / 1000)
        return cost

    async def get_conversation_rag_stats(
        self,
        conversation_id: int
    ) -> Dict[str, Any]:
        """获取对话的RAG统计"""
        try:
            # 统计RAG使用情况
            messages = self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.role == MessageType.ASSISTANT.value
            ).all()

            rag_enabled_count = 0
            total_rag_sources = 0

            for msg in messages:
                if msg.metadata and msg.metadata.get("mode") in ["rag_enhanced", "hybrid"]:
                    rag_enabled_count += 1
                    total_rag_sources += msg.metadata.get("rag_sources_count", 0)

            total_messages = len(messages)
            rag_usage_rate = (rag_enabled_count / total_messages) if total_messages > 0 else 0
            avg_sources_per_message = (total_rag_sources / rag_enabled_count) if rag_enabled_count > 0 else 0

            return {
                "conversation_id": conversation_id,
                "total_assistant_messages": total_messages,
                "rag_enabled_messages": rag_enabled_count,
                "rag_usage_rate": rag_usage_rate,
                "total_rag_sources": total_rag_sources,
                "average_sources_per_message": avg_sources_per_message
            }

        except Exception as e:
            logger.error(f"获取RAG统计失败: {str(e)}")
            return {}

    async def add_conversation_to_rag(
        self,
        conversation_id: int,
        user_id: int
    ) -> bool:
        """将对话内容添加到RAG知识库"""
        try:
            if not self.rag_available:
                logger.warning("RAG服务不可用，无法添加对话到知识库")
                return False

            # 获取对话内容
            messages = self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.is_deleted == False
            ).all()

            if not messages:
                return False

            # 构建文档内容
            conversation_content = []
            for msg in messages:
                conversation_content.append(f"{msg.role}: {msg.content}")

            full_content = "\n".join(conversation_content)

            # 获取RAG系统
            rag_system = await get_rag_system()

            # 添加到知识库
            success = await rag_system.add_documents(
                documents=[full_content],
                metadatas=[{
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "type": "conversation",
                    "message_count": len(messages),
                    "created_at": datetime.utcnow().isoformat()
                }]
            )

            if success:
                logger.info(f"对话 {conversation_id} 已添加到RAG知识库")
                return True

            return False

        except Exception as e:
            logger.error(f"添加对话到RAG知识库失败: {str(e)}")
            return False