"""
上下文压缩和长度控制服务
提供多种上下文压缩策略和长度控制机制
"""
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import json
import re
import logging
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

from ...models.conversation import Conversation, ConversationMessage
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CompressionType(Enum):
    """压缩类型"""
    TRUNCATE = "truncate"  # 截断
    SUMMARIZE = "summarize"  # 总结
    SEMANTIC = "semantic"  # 语义压缩
    HIERARCHICAL = "hierarchical"  # 分层压缩
    SLIDING_WINDOW = "sliding_window"  # 滑动窗口
    IMPORTANCE_BASED = "importance_based"  # 基于重要性


@dataclass
class CompressionResult:
    """压缩结果"""
    messages: List[Dict[str, Any]]
    original_token_count: int
    compressed_token_count: int
    compression_ratio: float
    strategy_used: str
    metadata: Dict[str, Any]


class CompressionStrategy(ABC):
    """压缩策略抽象基类"""

    @abstractmethod
    async def compress(
        self,
        messages: List[ConversationMessage],
        max_tokens: int,
        **kwargs
    ) -> CompressionResult:
        """执行压缩"""
        pass


class TruncateStrategy(CompressionStrategy):
    """截断策略"""

    async def compress(
        self,
        messages: List[ConversationMessage],
        max_tokens: int,
        **kwargs
    ) -> CompressionResult:
        """截断策略：保留最近的N条消息"""
        try:
            original_tokens = self._calculate_total_tokens(messages)

            # 按时间排序，保留最新的消息
            sorted_messages = sorted(messages, key=lambda x: x.created_at, reverse=True)

            compressed_messages = []
            current_tokens = 0

            for msg in sorted_messages:
                msg_tokens = msg.tokens or self._estimate_tokens(msg.content)
                if current_tokens + msg_tokens <= max_tokens:
                    compressed_messages.insert(0, {  # 保持原始顺序
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat()
                    })
                    current_tokens += msg_tokens
                else:
                    break

            compression_ratio = (1 - current_tokens / original_tokens) if original_tokens > 0 else 0

            return CompressionResult(
                messages=compressed_messages,
                original_token_count=original_tokens,
                compressed_token_count=current_tokens,
                compression_ratio=compression_ratio,
                strategy_used="truncate",
                metadata={"truncated_count": len(messages) - len(compressed_messages)}
            )

        except Exception as e:
            logger.error(f"截断压缩失败: {str(e)}")
            raise

    def _calculate_total_tokens(self, messages: List[ConversationMessage]) -> int:
        """计算总token数"""
        return sum(msg.tokens or self._estimate_tokens(msg.content) for msg in messages)

    def _estimate_tokens(self, text: str) -> int:
        """估算token数"""
        if not text:
            return 0

        # 简单估算：中文字符*1.5 + 英文字符/4
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        other_chars = len(text) - chinese_chars - english_chars

        tokens = (chinese_chars * 1.5) + (english_chars / 4) + (other_chars / 6)
        return int(tokens)


class SummarizeStrategy(CompressionStrategy):
    """总结策略"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def compress(
        self,
        messages: List[ConversationMessage],
        max_tokens: int,
        **kwargs
    ) -> CompressionResult:
        """总结策略：将旧消息总结为概要"""
        try:
            original_tokens = self._calculate_total_tokens(messages)

            if len(messages) <= 5:  # 消息太少，不需要总结
                formatted_messages = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat()
                    }
                    for msg in messages
                ]
                return CompressionResult(
                    messages=formatted_messages,
                    original_token_count=original_tokens,
                    compressed_token_count=original_tokens,
                    compression_ratio=0.0,
                    strategy_used="summarize",
                    metadata={"message": "消息数量太少，无需总结"}
                )

            # 分组：保留最近的消息，总结旧消息
            recent_messages = messages[-3:]  # 保留最近3条
            old_messages = messages[:-3]     # 其余消息需要总结

            compressed_messages = []
            current_tokens = 0

            # 添加总结
            if old_messages:
                summary = await self._create_summary(old_messages)
                summary_tokens = self._estimate_tokens(summary)

                if current_tokens + summary_tokens <= max_tokens:
                    compressed_messages.append({
                        "role": "system",
                        "content": f"之前的对话摘要: {summary}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "metadata": {"type": "summary", "original_count": len(old_messages)}
                    })
                    current_tokens += summary_tokens

            # 添加最近的完整消息
            for msg in recent_messages:
                msg_tokens = msg.tokens or self._estimate_tokens(msg.content)
                if current_tokens + msg_tokens <= max_tokens:
                    compressed_messages.append({
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat()
                    })
                    current_tokens += msg_tokens
                else:
                    break

            compression_ratio = (1 - current_tokens / original_tokens) if original_tokens > 0 else 0

            return CompressionResult(
                messages=compressed_messages,
                original_token_count=original_tokens,
                compressed_token_count=current_tokens,
                compression_ratio=compression_ratio,
                strategy_used="summarize",
                metadata={
                    "summarized_count": len(old_messages),
                    "retained_count": len(compressed_messages) - (1 if old_messages else 0)
                }
            )

        except Exception as e:
            logger.error(f"总结压缩失败: {str(e)}")
            raise

    async def _create_summary(self, messages: List[ConversationMessage]) -> str:
        """创建对话总结"""
        try:
            # 简单的总结策略（实际应该调用LLM）
            user_messages = [msg for msg in messages if msg.role == "user"]
            assistant_messages = [msg for msg in messages if msg.role == "assistant"]

            # 提取关键词
            all_content = " ".join([msg.content for msg in messages])
            keywords = self._extract_keywords(all_content)

            summary = f"历史对话包含 {len(user_messages)} 条用户询问和 {len(assistant_messages)} 条助手回复"
            if keywords:
                summary += f"，主要涉及主题: {', '.join(keywords[:5])}"

            return summary

        except Exception as e:
            logger.error(f"创建总结失败: {str(e)}")
            return "历史对话摘要"

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are', 'was', 'were', 'been', 'be'}
        keywords = [word for word in words if word not in stopwords and len(word) > 2]
        return list(set(keywords))

    def _calculate_total_tokens(self, messages: List[ConversationMessage]) -> int:
        """计算总token数"""
        return sum(msg.tokens or self._estimate_tokens(msg.content) for msg in messages)

    def _estimate_tokens(self, text: str) -> int:
        """估算token数"""
        if not text:
            return 0

        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        other_chars = len(text) - chinese_chars - english_chars

        tokens = (chinese_chars * 1.5) + (english_chars / 4) + (other_chars / 6)
        return int(tokens)


class SemanticStrategy(CompressionStrategy):
    """语义压缩策略"""

    async def compress(
        self,
        messages: List[ConversationMessage],
        max_tokens: int,
        **kwargs
    ) -> CompressionResult:
        """语义压缩：基于语义相似性去重"""
        try:
            original_tokens = self._calculate_total_tokens(messages)

            # 简化的语义压缩：基于内容相似性
            compressed_messages = []
            current_tokens = 0
            seen_content = set()

            # 按时间顺序处理
            for msg in sorted(messages, key=lambda x: x.created_at):
                content_hash = self._content_hash(msg.content)

                # 如果内容与之前的不同，则保留
                if content_hash not in seen_content:
                    msg_tokens = msg.tokens or self._estimate_tokens(msg.content)

                    if current_tokens + msg_tokens <= max_tokens:
                        compressed_messages.append({
                            "role": msg.role,
                            "content": msg.content,
                            "timestamp": msg.created_at.isoformat()
                        })
                        current_tokens += msg_tokens
                        seen_content.add(content_hash)

            compression_ratio = (1 - current_tokens / original_tokens) if original_tokens > 0 else 0

            return CompressionResult(
                messages=compressed_messages,
                original_token_count=original_tokens,
                compressed_token_count=current_tokens,
                compression_ratio=compression_ratio,
                strategy_used="semantic",
                metadata={
                    "deduplicated_count": len(messages) - len(compressed_messages),
                    "unique_content": len(compressed_messages)
                }
            )

        except Exception as e:
            logger.error(f"语义压缩失败: {str(e)}")
            raise

    def _content_hash(self, content: str) -> str:
        """生成内容哈希"""
        # 简单的内容哈希（实际可以使用更复杂的语义哈希）
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _calculate_total_tokens(self, messages: List[ConversationMessage]) -> int:
        """计算总token数"""
        return sum(msg.tokens or self._estimate_tokens(msg.content) for msg in messages)

    def _estimate_tokens(self, text: str) -> int:
        """估算token数"""
        if not text:
            return 0

        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        other_chars = len(text) - chinese_chars - english_chars

        tokens = (chinese_chars * 1.5) + (english_chars / 4) + (other_chars / 6)
        return int(tokens)


class ContextCompressionManager:
    """上下文压缩管理器"""

    def __init__(self, db: Session):
        self.db = db
        self.strategies = {
            CompressionType.TRUNCATE: TruncateStrategy(),
            CompressionType.SUMMARIZE: SummarizeStrategy(),
            CompressionType.SEMANTIC: SemanticStrategy()
        }

    async def compress_conversation_context(
        self,
        conversation_id: int,
        max_tokens: int = 4000,
        compression_type: str = "truncate",
        **kwargs
    ) -> CompressionResult:
        """压缩对话上下文"""
        try:
            # 获取对话消息
            messages = self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.is_deleted == False
            ).order_by(ConversationMessage.sequence).all()

            if not messages:
                return CompressionResult(
                    messages=[],
                    original_token_count=0,
                    compressed_token_count=0,
                    compression_ratio=0.0,
                    strategy_used=compression_type,
                    metadata={"message": "没有消息需要压缩"}
                )

            # 选择压缩策略
            strategy_type = CompressionType(compression_type)
            strategy = self.strategies.get(strategy_type)

            if not strategy:
                raise ValueError(f"不支持的压缩策略: {compression_type}")

            # 执行压缩
            result = await strategy.compress(messages, max_tokens, **kwargs)

            # 记录压缩结果
            await self._log_compression_result(conversation_id, result)

            return result

        except Exception as e:
            logger.error(f"压缩对话上下文失败: {str(e)}")
            raise

    async def auto_compress_when_needed(
        self,
        conversation_id: int,
        threshold_ratio: float = 0.8
    ) -> Optional[CompressionResult]:
        """在需要时自动压缩"""
        try:
            # 获取对话配置
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()

            if not conversation:
                return None

            # 计算当前上下文使用率
            context_usage = conversation.total_tokens / conversation.max_context_tokens

            if context_usage < threshold_ratio:
                return None

            # 自动选择压缩策略
            compression_type = conversation.context_compression or "truncate"

            # 执行压缩
            result = await self.compress_conversation_context(
                conversation_id,
                conversation.max_context_tokens,
                compression_type
            )

            # 更新对话压缩统计
            if result.compression_ratio > 0.1:  # 只记录有效的压缩
                logger.info(f"对话 {conversation_id} 自动压缩完成，压缩率: {result.compression_ratio:.2%}")

            return result

        except Exception as e:
            logger.error(f"自动压缩失败: {str(e)}")
            raise

    async def get_compression_stats(
        self,
        conversation_id: int
    ) -> Dict[str, Any]:
        """获取压缩统计"""
        try:
            # 计算对话的压缩潜力
            messages = self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.is_deleted == False
            ).all()

            if not messages:
                return {
                    "conversation_id": conversation_id,
                    "total_messages": 0,
                    "total_tokens": 0,
                    "compression_potential": 0.0,
                    "recommendations": []
                }

            total_tokens = sum(msg.tokens or self._estimate_tokens(msg.content) for msg in messages)

            # 计算各种压缩策略的潜力
            strategies_potential = {}
            for strategy_type in [CompressionType.TRUNCATE, CompressionType.SUMMARIZE, CompressionType.SEMANTIC]:
                strategy = self.strategies[strategy_type]
                result = await strategy.compress(messages, max_tokens=2000)
                strategies_potential[strategy_type.value] = result.compression_ratio

            # 推荐最佳策略
            best_strategy = max(strategies_potential.items(), key=lambda x: x[1])

            recommendations = []
            if best_strategy[1] > 0.2:
                recommendations.append(f"建议使用 {best_strategy[0]} 策略，可压缩 {best_strategy[1]:.1%}")

            return {
                "conversation_id": conversation_id,
                "total_messages": len(messages),
                "total_tokens": total_tokens,
                "compression_potential": strategies_potential,
                "best_strategy": best_strategy[0],
                "best_potential": best_strategy[1],
                "recommendations": recommendations
            }

        except Exception as e:
            logger.error(f"获取压缩统计失败: {str(e)}")
            raise

    async def _log_compression_result(
        self,
        conversation_id: int,
        result: CompressionResult
    ) -> None:
        """记录压缩结果"""
        try:
            # 这里可以添加压缩日志记录
            logger.info(
                f"对话 {conversation_id} 压缩完成: "
                f"策略={result.strategy_used}, "
                f"原始token={result.original_token_count}, "
                f"压缩token={result.compressed_token_count}, "
                f"压缩率={result.compression_ratio:.2%}"
            )
        except Exception as e:
            logger.error(f"记录压缩结果失败: {str(e)}")

    def _estimate_tokens(self, text: str) -> int:
        """估算token数"""
        if not text:
            return 0

        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        other_chars = len(text) - chinese_chars - english_chars

        tokens = (chinese_chars * 1.5) + (english_chars / 4) + (other_chars / 6)
        return int(tokens)