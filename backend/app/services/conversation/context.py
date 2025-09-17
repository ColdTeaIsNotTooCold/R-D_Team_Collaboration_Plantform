"""
智能上下文维护系统
提供上下文管理、优化、压缩等功能
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import re
import logging
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from ...models.conversation import Conversation, ConversationMessage
from ...models.context import Context
from ...core.config import settings

logger = logging.getLogger(__name__)


class ContextCompressionStrategy(Enum):
    """上下文压缩策略"""
    TRUNCATE = "truncate"  # 截断
    SUMMARIZE = "summarize"  # 总结
    SEMANTIC = "semantic"  # 语义压缩
    HIERARCHICAL = "hierarchical"  # 分层压缩


class ContextPriority(Enum):
    """上下文优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ContextMessage:
    """上下文消息数据结构"""
    role: str
    content: str
    tokens: int
    priority: ContextPriority
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class ContextWindow:
    """上下文窗口"""
    messages: List[ContextMessage]
    total_tokens: int
    max_tokens: int
    compression_strategy: ContextCompressionStrategy


class SmartContextManager:
    """智能上下文管理器"""

    def __init__(self, db: Session):
        self.db = db
        self.compression_strategies = {
            ContextCompressionStrategy.TRUNCATE: self._truncate_strategy,
            ContextCompressionStrategy.SUMMARIZE: self._summarize_strategy,
            ContextCompressionStrategy.SEMANTIC: self._semantic_strategy,
            ContextCompressionStrategy.HIERARCHICAL: self._hierarchical_strategy
        }

    async def build_context_window(
        self,
        conversation_id: int,
        max_tokens: int = 4000,
        compression_strategy: str = "truncate",
        include_system_prompt: bool = True,
        context_priority_rules: Optional[Dict[str, Any]] = None
    ) -> ContextWindow:
        """构建智能上下文窗口"""
        try:
            # 获取对话
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

            if not conversation:
                raise ValueError(f"对话 {conversation_id} 不存在")

            # 获取对话消息
            messages = await self._get_conversation_messages(conversation_id)

            # 转换为上下文消息格式
            context_messages = []
            for msg in messages:
                priority = self._calculate_message_priority(msg, context_priority_rules)
                context_msg = ContextMessage(
                    role=msg.role,
                    content=msg.content,
                    tokens=msg.tokens or self._estimate_tokens(msg.content),
                    priority=priority,
                    timestamp=msg.created_at,
                    metadata=msg.metadata or {}
                )
                context_messages.append(context_msg)

            # 应用压缩策略
            strategy = ContextCompressionStrategy(compression_strategy)
            compressed_messages = await self._apply_compression_strategy(
                context_messages, max_tokens, strategy
            )

            # 添加系统提示
            final_messages = []
            if include_system_prompt and conversation.system_prompt:
                final_messages.append(ContextMessage(
                    role="system",
                    content=conversation.system_prompt,
                    tokens=self._estimate_tokens(conversation.system_prompt),
                    priority=ContextPriority.HIGH,
                    timestamp=datetime.utcnow(),
                    metadata={"type": "system_prompt"}
                ))

            final_messages.extend(compressed_messages)

            # 计算总token数
            total_tokens = sum(msg.tokens for msg in final_messages)

            return ContextWindow(
                messages=final_messages,
                total_tokens=total_tokens,
                max_tokens=max_tokens,
                compression_strategy=strategy
            )

        except Exception as e:
            logger.error(f"构建上下文窗口失败: {str(e)}")
            raise

    async def optimize_context_for_retrieval(
        self,
        conversation_id: int,
        query: str,
        max_tokens: int = 4000
    ) -> List[Dict[str, Any]]:
        """为检索优化上下文"""
        try:
            # 构建基础上下文
            context_window = await self.build_context_window(
                conversation_id=conversation_id,
                max_tokens=max_tokens,
                compression_strategy="semantic"
            )

            # 根据查询内容优化消息选择
            optimized_messages = []
            query_keywords = self._extract_keywords(query)

            for msg in context_window.messages:
                relevance_score = self._calculate_relevance_score(
                    msg.content, query_keywords
                )

                # 只保留相关性高的消息
                if relevance_score > 0.3 or msg.priority == ContextPriority.HIGH:
                    optimized_messages.append({
                        "role": msg.role,
                        "content": msg.content,
                        "relevance": relevance_score,
                        "priority": msg.priority.value
                    })

            return optimized_messages

        except Exception as e:
            logger.error(f"优化检索上下文失败: {str(e)}")
            raise

    async def maintain_context_health(
        self,
        conversation_id: int,
        health_check_interval: int = 3600  # 1小时
    ) -> Dict[str, Any]:
        """维护上下文健康状态"""
        try:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

            if not conversation:
                return {"status": "error", "message": "对话不存在"}

            health_report = {
                "conversation_id": conversation_id,
                "check_time": datetime.utcnow().isoformat(),
                "metrics": {},
                "recommendations": []
            }

            # 检查消息数量
            if conversation.message_count > 100:
                health_report["recommendations"].append(
                    "消息数量过多，建议启用上下文压缩"
                )

            # 检查token使用
            if conversation.total_tokens > 100000:
                health_report["recommendations"].append(
                    "Token使用量过高，建议清理历史消息"
                )

            # 检查成本
            if conversation.total_cost > 10.0:
                health_report["recommendations"].append(
                    "成本较高，建议设置成本限制"
                )

            # 计算健康分数
            health_score = self._calculate_health_score(conversation)
            health_report["health_score"] = health_score

            # 记录健康检查
            health_report["metrics"] = {
                "message_count": conversation.message_count,
                "total_tokens": conversation.total_tokens,
                "total_cost": conversation.total_cost,
                "average_latency": conversation.average_latency,
                "context_length": conversation.context_length,
                "compression_strategy": conversation.context_compression
            }

            return health_report

        except Exception as e:
            logger.error(f"上下文健康检查失败: {str(e)}")
            raise

    async def auto_compress_context(
        self,
        conversation_id: int,
        trigger_threshold: int = 80  # 使用率达到80%时触发
    ) -> bool:
        """自动压缩上下文"""
        try:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

            if not conversation:
                return False

            # 计算上下文使用率
            context_usage = (conversation.total_tokens / conversation.max_context_tokens) * 100

            if context_usage < trigger_threshold:
                return False

            # 执行压缩
            messages = await self._get_conversation_messages(conversation_id)
            compressed_count = 0

            for msg in messages:
                if msg.role == "user" and len(msg.content) > 500:
                    # 压缩长消息
                    compressed_content = await self._compress_message_content(
                        msg.content, conversation.context_compression
                    )

                    if compressed_content != msg.content:
                        msg.content = compressed_content
                        msg.is_edited = True
                        compressed_count += 1

            self.db.commit()

            logger.info(f"自动压缩对话 {conversation_id}，压缩了 {compressed_count} 条消息")
            return compressed_count > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"自动压缩上下文失败: {str(e)}")
            raise

    async def _get_conversation_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """获取对话消息"""
        query = self.db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conversation_id,
            ConversationMessage.is_deleted == False
        ).order_by(ConversationMessage.sequence)

        if limit:
            query = query.limit(limit)

        return query.all()

    def _calculate_message_priority(
        self,
        message: ConversationMessage,
        rules: Optional[Dict[str, Any]] = None
    ) -> ContextPriority:
        """计算消息优先级"""
        # 系统消息最高优先级
        if message.role == "system":
            return ContextPriority.HIGH

        # 最近的用户消息高优先级
        if message.role == "user":
            time_diff = datetime.utcnow() - message.created_at
            if time_diff.total_seconds() < 3600:  # 1小时内
                return ContextPriority.HIGH
            return ContextPriority.MEDIUM

        # 助手消息中等优先级
        if message.role == "assistant":
            # 包含代码或结构化内容的消息优先级更高
            if "```" in message.content or "```" in message.content:
                return ContextPriority.MEDIUM
            return ContextPriority.LOW

        return ContextPriority.LOW

    def _estimate_tokens(self, text: str) -> int:
        """估算文本token数"""
        # 简单估算：1个token ≈ 4个字符（英文）或 1.5个汉字
        if not text:
            return 0

        # 统计中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        # 统计英文字符
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        # 统计空格和标点
        other_chars = len(text) - chinese_chars - english_chars

        # 估算token数
        tokens = (chinese_chars * 1.5) + (english_chars / 4) + (other_chars / 6)
        return int(tokens)

    async def _apply_compression_strategy(
        self,
        messages: List[ContextMessage],
        max_tokens: int,
        strategy: ContextCompressionStrategy
    ) -> List[ContextMessage]:
        """应用压缩策略"""
        if strategy not in self.compression_strategies:
            raise ValueError(f"不支持的压缩策略: {strategy}")

        return await self.compression_strategies[strategy](messages, max_tokens)

    async def _truncate_strategy(
        self,
        messages: List[ContextMessage],
        max_tokens: int
    ) -> List[ContextMessage]:
        """截断策略"""
        result = []
        current_tokens = 0

        # 按优先级和时间排序
        sorted_messages = sorted(
            messages,
            key=lambda x: (
                x.priority.value == "high",
                x.priority.value == "medium",
                x.timestamp
            ),
            reverse=True
        )

        for msg in sorted_messages:
            if current_tokens + msg.tokens <= max_tokens:
                result.insert(0, msg)  # 保持原始顺序
                current_tokens += msg.tokens
            else:
                break

        return result

    async def _summarize_strategy(
        self,
        messages: List[ContextMessage],
        max_tokens: int
    ) -> List[ContextMessage]:
        """总结策略（简化版）"""
        # 这里应该调用LLM进行总结，暂时使用简单方法
        result = []
        current_tokens = 0

        # 保留最近的几条消息，其余总结
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        old_messages = messages[:-10] if len(messages) > 10 else []

        # 处理旧消息
        if old_messages:
            # 按角色分组总结
            user_messages = [msg for msg in old_messages if msg.role == "user"]
            assistant_messages = [msg for msg in old_messages if msg.role == "assistant"]

            summary_content = f"历史对话包含 {len(user_messages)} 条用户消息和 {len(assistant_messages)} 条助手回复"
            summary_tokens = self._estimate_tokens(summary_content)

            if current_tokens + summary_tokens <= max_tokens:
                result.append(ContextMessage(
                    role="system",
                    content=summary_content,
                    tokens=summary_tokens,
                    priority=ContextPriority.LOW,
                    timestamp=datetime.utcnow(),
                    metadata={"type": "summary"}
                ))
                current_tokens += summary_tokens

        # 添加最近的完整消息
        for msg in recent_messages:
            if current_tokens + msg.tokens <= max_tokens:
                result.append(msg)
                current_tokens += msg.tokens
            else:
                break

        return result

    async def _semantic_strategy(
        self,
        messages: List[ContextMessage],
        max_tokens: int
    ) -> List[ContextMessage]:
        """语义压缩策略（简化版）"""
        # 这里应该使用语义相似度进行压缩，暂时使用截断
        return await self._truncate_strategy(messages, max_tokens)

    async def _hierarchical_strategy(
        self,
        messages: List[ContextMessage],
        max_tokens: int
    ) -> List[ContextMessage]:
        """分层压缩策略"""
        # 按优先级分层处理
        high_priority = [msg for msg in messages if msg.priority == ContextPriority.HIGH]
        medium_priority = [msg for msg in messages if msg.priority == ContextPriority.MEDIUM]
        low_priority = [msg for msg in messages if msg.priority == ContextPriority.LOW]

        result = []
        current_tokens = 0

        # 添加高优先级消息
        for msg in high_priority:
            if current_tokens + msg.tokens <= max_tokens:
                result.append(msg)
                current_tokens += msg.tokens

        # 添加中等优先级消息
        for msg in medium_priority:
            if current_tokens + msg.tokens <= max_tokens:
                result.append(msg)
                current_tokens += msg.tokens

        # 添加低优先级消息（如果有空间）
        remaining_tokens = max_tokens - current_tokens
        if remaining_tokens > 0:
            low_priority_result = await self._truncate_strategy(low_priority, remaining_tokens)
            result.extend(low_priority_result)

        return result

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        words = re.findall(r'\b\w+\b', text.lower())
        # 过滤停用词
        stopwords = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are', 'was', 'were', 'been', 'be'}
        keywords = [word for word in words if word not in stopwords and len(word) > 2]
        return list(set(keywords))

    def _calculate_relevance_score(self, content: str, keywords: List[str]) -> float:
        """计算相关性分数"""
        if not keywords:
            return 0.0

        content_lower = content.lower()
        matches = sum(1 for keyword in keywords if keyword in content_lower)
        return matches / len(keywords)

    def _calculate_health_score(self, conversation: Conversation) -> float:
        """计算健康分数"""
        score = 100.0

        # 消息数量惩罚
        if conversation.message_count > 100:
            score -= (conversation.message_count - 100) * 0.1

        # Token使用惩罚
        if conversation.total_tokens > 100000:
            score -= (conversation.total_tokens - 100000) / 10000

        # 成本惩罚
        if conversation.total_cost > 10.0:
            score -= (conversation.total_cost - 10.0) * 2.0

        # 延迟惩罚
        if conversation.average_latency > 5.0:
            score -= (conversation.average_latency - 5.0) * 2.0

        return max(0.0, min(100.0, score))

    async def _compress_message_content(
        self,
        content: str,
        strategy: str
    ) -> str:
        """压缩消息内容"""
        if strategy == "truncate":
            # 截断到前300个字符
            if len(content) > 300:
                return content[:300] + "..."
        elif strategy == "summarize":
            # 简单总结
            sentences = content.split('。')
            if len(sentences) > 3:
                return '。'.join(sentences[:2]) + "。"

        return content