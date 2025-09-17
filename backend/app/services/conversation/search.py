"""
对话搜索和检索服务
提供对话内容搜索、语义搜索、智能检索等功能
"""
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import json
import re
import logging
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.sql import text

from ...models.conversation import Conversation, ConversationMessage
from ...models.context import Context as ContextModel
from ...core.config import settings

# 尝试导入向量搜索
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False

logger = logging.getLogger(__name__)


class SearchType(Enum):
    """搜索类型"""
    KEYWORD = "keyword"  # 关键词搜索
    SEMANTIC = "semantic"  # 语义搜索
    HYBRID = "hybrid"  # 混合搜索
    FUZZY = "fuzzy"  # 模糊搜索


class SearchScope(Enum):
    """搜索范围"""
    TITLES = "titles"  # 仅标题
    CONTENTS = "contents"  # 仅内容
    BOTH = "both"  # 标题和内容
    METADATA = "metadata"  # 元数据


@dataclass
class SearchResult:
    """搜索结果"""
    conversation_id: int
    title: str
    relevance_score: float
    matched_messages: List[Dict[str, Any]]
    conversation_metadata: Dict[str, Any]
    search_type: SearchType
    match_highlights: List[str]


@dataclass
class SearchQuery:
    """搜索查询"""
    query: str
    search_type: SearchType = SearchType.HYBRID
    scope: SearchScope = SearchScope.BOTH
    user_id: Optional[int] = None
    limit: int = 20
    offset: int = 0
    filters: Optional[Dict[str, Any]] = None
    include_archived: bool = False
    date_range: Optional[Tuple[datetime, datetime]] = None
    min_relevance_score: float = 0.1


class ConversationSearchEngine:
    """对话搜索引擎"""

    def __init__(self, db: Session):
        self.db = db
        self.vector_search_available = VECTOR_SEARCH_AVAILABLE

    async def search_conversations(
        self,
        query: SearchQuery
    ) -> Tuple[List[SearchResult], int]:
        """搜索对话"""
        try:
            if query.search_type == SearchType.KEYWORD:
                return await self._keyword_search(query)
            elif query.search_type == SearchType.SEMANTIC:
                return await self._semantic_search(query)
            elif query.search_type == SearchType.HYBRID:
                return await self._hybrid_search(query)
            elif query.search_type == SearchType.FUZZY:
                return await self._fuzzy_search(query)
            else:
                raise ValueError(f"不支持的搜索类型: {query.search_type}")

        except Exception as e:
            logger.error(f"搜索对话失败: {str(e)}")
            raise

    async def _keyword_search(self, query: SearchQuery) -> Tuple[List[SearchResult], int]:
        """关键词搜索"""
        try:
            # 构建基础查询
            base_query = self.db.query(Conversation).filter(
                Conversation.is_archived == query.include_archived
            )

            if query.user_id:
                base_query = base_query.filter(Conversation.user_id == query.user_id)

            # 日期范围过滤
            if query.date_range:
                start_date, end_date = query.date_range
                base_query = base_query.filter(
                    Conversation.created_at.between(start_date, end_date)
                )

            # 根据搜索范围构建条件
            search_conditions = []

            if query.scope in [SearchScope.TITLES, SearchScope.BOTH]:
                search_conditions.append(
                    Conversation.title.ilike(f"%{query.query}%")
                )
                search_conditions.append(
                    Conversation.description.ilike(f"%{query.query}%")
                )

            if query.scope in [SearchScope.CONTENTS, SearchScope.BOTH]:
                # 子查询搜索消息内容
                message_subquery = self.db.query(ConversationMessage.conversation_id).filter(
                    ConversationMessage.content.ilike(f"%{query.query}%"),
                    ConversationMessage.is_deleted == False
                ).distinct()

                if query.user_id:
                    message_subquery = message_subquery.filter(
                        ConversationMessage.user_id == query.user_id
                    )

                search_conditions.append(Conversation.id.in_(message_subquery))

            if query.scope == SearchScope.METADATA:
                # JSON搜索元数据
                if hasattr(Conversation, 'tags'):
                    search_conditions.append(
                        Conversation.tags.contains([query.query])
                    )

            # 应用搜索条件
            if search_conditions:
                base_query = base_query.filter(or_(*search_conditions))

            # 获取总数
            total_count = base_query.count()

            # 应用分页和排序
            conversations = base_query.order_by(
                desc(Conversation.last_message_at)
            ).offset(query.offset).limit(query.limit).all()

            # 构建搜索结果
            results = []
            for conv in conversations:
                relevance_score = self._calculate_keyword_relevance(conv, query.query)
                matched_messages = await self._get_matched_messages(conv.id, query.query)

                if relevance_score >= query.min_relevance_score:
                    result = SearchResult(
                        conversation_id=conv.id,
                        title=conv.title,
                        relevance_score=relevance_score,
                        matched_messages=matched_messages,
                        conversation_metadata={
                            "description": conv.description,
                            "created_at": conv.created_at.isoformat(),
                            "message_count": conv.message_count,
                            "tags": conv.tags or []
                        },
                        search_type=query.search_type,
                        match_highlights=self._extract_highlights(conv, query.query)
                    )
                    results.append(result)

            # 按相关性排序
            results.sort(key=lambda x: x.relevance_score, reverse=True)

            return results, total_count

        except Exception as e:
            logger.error(f"关键词搜索失败: {str(e)}")
            raise

    async def _semantic_search(self, query: SearchQuery) -> Tuple[List[SearchResult], int]:
        """语义搜索"""
        try:
            if not self.vector_search_available:
                logger.warning("向量搜索不可用，回退到关键词搜索")
                return await self._keyword_search(query)

            # 获取所有候选对话
            base_query = self.db.query(Conversation).filter(
                Conversation.is_archived == query.include_archived
            )

            if query.user_id:
                base_query = base_query.filter(Conversation.user_id == query.user_id)

            if query.date_range:
                start_date, end_date = query.date_range
                base_query = base_query.filter(
                    Conversation.created_at.between(start_date, end_date)
                )

            conversations = base_query.all()
            total_count = len(conversations)

            # 构建文档向量
            documents = []
            for conv in conversations:
                # 组合标题、描述和消息内容
                content_parts = [conv.title]
                if conv.description:
                    content_parts.append(conv.description)

                # 获取最近的消息
                recent_messages = self.db.query(ConversationMessage).filter(
                    ConversationMessage.conversation_id == conv.id,
                    ConversationMessage.is_deleted == False
                ).order_by(ConversationMessage.created_at.desc()).limit(10).all()

                for msg in recent_messages:
                    content_parts.append(msg.content)

                full_content = " ".join(content_parts)
                documents.append({
                    "conversation_id": conv.id,
                    "content": full_content,
                    "conversation": conv
                })

            if not documents:
                return [], total_count

            # 使用TF-IDF进行语义搜索
            try:
                vectorizer = TfidfVectorizer(
                    max_features=1000,
                    stop_words='english' if query.query.isascii() else None,
                    ngram_range=(1, 2)
                )

                # 构建文档向量
                doc_contents = [doc["content"] for doc in documents]
                tfidf_matrix = vectorizer.fit_transform(doc_contents)

                # 查询向量
                query_vector = vectorizer.transform([query.query])

                # 计算相似度
                similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()

                # 构建结果
                results = []
                for i, similarity in enumerate(similarities):
                    if similarity >= query.min_relevance_score:
                        conv = documents[i]["conversation"]
                        matched_messages = await self._get_matched_messages(conv.id, query.query)

                        result = SearchResult(
                            conversation_id=conv.id,
                            title=conv.title,
                            relevance_score=float(similarity),
                            matched_messages=matched_messages,
                            conversation_metadata={
                                "description": conv.description,
                                "created_at": conv.created_at.isoformat(),
                                "message_count": conv.message_count,
                                "tags": conv.tags or []
                            },
                            search_type=query.search_type,
                            match_highlights=self._extract_semantic_highlights(conv, query.query)
                        )
                        results.append(result)

                # 按相关性排序
                results.sort(key=lambda x: x.relevance_score, reverse=True)

                # 应用分页
                paginated_results = results[query.offset:query.offset + query.limit]

                return paginated_results, total_count

            except Exception as e:
                logger.error(f"向量搜索失败: {str(e)}")
                return await self._keyword_search(query)

        except Exception as e:
            logger.error(f"语义搜索失败: {str(e)}")
            raise

    async def _hybrid_search(self, query: SearchQuery) -> Tuple[List[SearchResult], int]:
        """混合搜索"""
        try:
            # 执行关键词搜索和语义搜索
            keyword_results, keyword_total = await self._keyword_search(query)
            semantic_results, semantic_total = await self._semantic_search(query)

            # 合并结果
            conversation_scores = {}

            # 处理关键词搜索结果
            for result in keyword_results:
                conv_id = result.conversation_id
                if conv_id not in conversation_scores:
                    conversation_scores[conv_id] = {
                        "result": result,
                        "keyword_score": result.relevance_score,
                        "semantic_score": 0.0,
                        "combined_score": 0.0
                    }
                else:
                    conversation_scores[conv_id]["keyword_score"] = result.relevance_score

            # 处理语义搜索结果
            for result in semantic_results:
                conv_id = result.conversation_id
                if conv_id not in conversation_scores:
                    conversation_scores[conv_id] = {
                        "result": result,
                        "keyword_score": 0.0,
                        "semantic_score": result.relevance_score,
                        "combined_score": 0.0
                    }
                else:
                    conversation_scores[conv_id]["semantic_score"] = result.relevance_score

            # 计算综合分数
            for conv_id, data in conversation_scores.items():
                # 加权平均：关键词40%，语义60%
                combined_score = (
                    data["keyword_score"] * 0.4 + data["semantic_score"] * 0.6
                )
                data["combined_score"] = combined_score
                data["result"].relevance_score = combined_score
                data["result"].search_type = SearchType.HYBRID

            # 按综合分数排序
            sorted_results = [
                data["result"] for data in sorted(
                    conversation_scores.values(),
                    key=lambda x: x["combined_score"],
                    reverse=True
                )
            ]

            # 应用相关性阈值
            filtered_results = [
                result for result in sorted_results
                if result.relevance_score >= query.min_relevance_score
            ]

            # 应用分页
            paginated_results = filtered_results[query.offset:query.offset + query.limit]
            total_count = len(filtered_results)

            return paginated_results, total_count

        except Exception as e:
            logger.error(f"混合搜索失败: {str(e)}")
            raise

    async def _fuzzy_search(self, query: SearchQuery) -> Tuple[List[SearchResult], int]:
        """模糊搜索"""
        try:
            # 使用正则表达式进行模糊匹配
            fuzzy_pattern = self._build_fuzzy_pattern(query.query)

            # 构建基础查询
            base_query = self.db.query(Conversation).filter(
                Conversation.is_archived == query.include_archived
            )

            if query.user_id:
                base_query = base_query.filter(Conversation.user_id == query.user_id)

            # 应用模糊搜索条件
            search_conditions = []

            if query.scope in [SearchScope.TITLES, SearchScope.BOTH]:
                search_conditions.append(
                    Conversation.title.op('~')(fuzzy_pattern)
                )

            if query.scope in [SearchScope.CONTENTS, SearchScope.BOTH]:
                message_subquery = self.db.query(ConversationMessage.conversation_id).filter(
                    ConversationMessage.content.op('~')(fuzzy_pattern),
                    ConversationMessage.is_deleted == False
                ).distinct()

                if query.user_id:
                    message_subquery = message_subquery.filter(
                        ConversationMessage.user_id == query.user_id
                    )

                search_conditions.append(Conversation.id.in_(message_subquery))

            if search_conditions:
                base_query = base_query.filter(or_(*search_conditions))

            total_count = base_query.count()
            conversations = base_query.order_by(
                desc(Conversation.last_message_at)
            ).offset(query.offset).limit(query.limit).all()

            # 构建结果
            results = []
            for conv in conversations:
                relevance_score = self._calculate_fuzzy_relevance(conv, query.query)
                matched_messages = await self._get_matched_messages(conv.id, query.query, fuzzy=True)

                if relevance_score >= query.min_relevance_score:
                    result = SearchResult(
                        conversation_id=conv.id,
                        title=conv.title,
                        relevance_score=relevance_score,
                        matched_messages=matched_messages,
                        conversation_metadata={
                            "description": conv.description,
                            "created_at": conv.created_at.isoformat(),
                            "message_count": conv.message_count,
                            "tags": conv.tags or []
                        },
                        search_type=query.search_type,
                        match_highlights=self._extract_fuzzy_highlights(conv, query.query)
                    )
                    results.append(result)

            results.sort(key=lambda x: x.relevance_score, reverse=True)

            return results, total_count

        except Exception as e:
            logger.error(f"模糊搜索失败: {str(e)}")
            raise

    async def _get_matched_messages(
        self,
        conversation_id: int,
        query: str,
        fuzzy: bool = False,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """获取匹配的消息"""
        try:
            messages_query = self.db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id,
                ConversationMessage.is_deleted == False
            )

            if fuzzy:
                # 模糊匹配
                fuzzy_pattern = self._build_fuzzy_pattern(query)
                messages_query = messages_query.filter(
                    ConversationMessage.content.op('~')(fuzzy_pattern)
                )
            else:
                # 精确匹配
                messages_query = messages_query.filter(
                    ConversationMessage.content.ilike(f"%{query}%")
                )

            messages = messages_query.order_by(
                ConversationMessage.created_at.desc()
            ).limit(limit).all()

            return [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                    "relevance": self._calculate_message_relevance(msg.content, query)
                }
                for msg in messages
            ]

        except Exception as e:
            logger.error(f"获取匹配消息失败: {str(e)}")
            return []

    def _calculate_keyword_relevance(self, conversation: Conversation, query: str) -> float:
        """计算关键词相关性分数"""
        score = 0.0
        query_lower = query.lower()

        # 标题匹配
        if query_lower in conversation.title.lower():
            score += 2.0

        # 描述匹配
        if conversation.description and query_lower in conversation.description.lower():
            score += 1.0

        # 消息匹配
        message_count = self.db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conversation.id,
            ConversationMessage.content.ilike(f"%{query}%"),
            ConversationMessage.is_deleted == False
        ).count()

        score += message_count * 0.5

        return score

    def _calculate_fuzzy_relevance(self, conversation: Conversation, query: str) -> float:
        """计算模糊相关性分数"""
        # 简化的模糊相关性计算
        score = 0.0
        query_words = query.lower().split()

        # 检查标题中的模糊匹配
        title_lower = conversation.title.lower()
        for word in query_words:
            if word in title_lower:
                score += 0.5

        # 检查消息中的模糊匹配
        message_count = self.db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conversation.id,
            ConversationMessage.is_deleted == False
        ).count()

        if message_count > 0:
            score += 0.1  # 基础分数

        return score

    def _calculate_message_relevance(self, content: str, query: str) -> float:
        """计算消息相关性"""
        if not content or not query:
            return 0.0

        content_lower = content.lower()
        query_lower = query.lower()

        # 精确匹配
        if query_lower in content_lower:
            return 1.0

        # 部分匹配
        query_words = query_lower.split()
        matched_words = sum(1 for word in query_words if word in content_lower)

        if matched_words > 0:
            return matched_words / len(query_words)

        return 0.0

    def _extract_highlights(self, conversation: Conversation, query: str) -> List[str]:
        """提取匹配高亮"""
        highlights = []
        query_lower = query.lower()

        # 标题高亮
        if query_lower in conversation.title.lower():
            highlights.append(f"标题: {conversation.title}")

        # 消息高亮
        messages = self.db.query(ConversationMessage).filter(
            ConversationMessage.conversation_id == conversation.id,
            ConversationMessage.content.ilike(f"%{query}%"),
            ConversationMessage.is_deleted == False
        ).limit(3).all()

        for msg in messages:
            # 截取匹配部分的上下文
            content = msg.content
            query_pos = content.lower().find(query_lower)
            if query_pos != -1:
                start = max(0, query_pos - 50)
                end = min(len(content), query_pos + len(query) + 50)
                highlight = content[start:end]
                highlights.append(f"{msg.role}: ...{highlight}...")

        return highlights

    def _extract_semantic_highlights(self, conversation: Conversation, query: str) -> List[str]:
        """提取语义高亮"""
        # 简化的语义高亮
        return [f"语义匹配: {conversation.title}"]

    def _extract_fuzzy_highlights(self, conversation: Conversation, query: str) -> List[str]:
        """提取模糊高亮"""
        highlights = []
        query_words = query.lower().split()

        # 检查标题中的模糊匹配
        title_lower = conversation.title.lower()
        for word in query_words:
            if word in title_lower:
                highlights.append(f"模糊匹配标题: {conversation.title}")
                break

        return highlights

    def _build_fuzzy_pattern(self, query: str) -> str:
        """构建模糊搜索模式"""
        # 简单的模糊模式：允许字符间有其他字符
        words = query.split()
        patterns = []

        for word in words:
            if len(word) > 2:
                # 构建允许编辑距离的模式
                pattern = ''.join(f"{char}.*" for char in word)
                patterns.append(f"({pattern})")

        return '|'.join(patterns) if patterns else query

    async def get_search_suggestions(
        self,
        partial_query: str,
        user_id: Optional[int] = None,
        limit: int = 10
    ) -> List[str]:
        """获取搜索建议"""
        try:
            suggestions = []

            # 从对话标题获取建议
            title_suggestions = self.db.query(Conversation.title).filter(
                Conversation.title.ilike(f"%{partial_query}%")
            )

            if user_id:
                title_suggestions = title_suggestions.filter(Conversation.user_id == user_id)

            title_suggestions = title_suggestions.distinct().limit(limit).all()

            suggestions.extend([title[0] for title in title_suggestions])

            # 从标签获取建议
            if hasattr(Conversation, 'tags'):
                conversations = self.db.query(Conversation).filter(
                    Conversation.tags.isnot(None)
                )

                if user_id:
                    conversations = conversations.filter(Conversation.user_id == user_id)

                for conv in conversations.limit(limit):
                    if conv.tags:
                        for tag in conv.tags:
                            if partial_query.lower() in tag.lower():
                                suggestions.append(f"标签: {tag}")

            # 去重并限制数量
            unique_suggestions = list(set(suggestions))
            return unique_suggestions[:limit]

        except Exception as e:
            logger.error(f"获取搜索建议失败: {str(e)}")
            return []

    async def get_popular_search_terms(
        self,
        user_id: Optional[int] = None,
        days: int = 30,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取热门搜索词"""
        try:
            # 这里应该从搜索日志中获取热门词
            # 简化版本：返回一些示例数据
            return [
                {"term": "代码", "count": 15},
                {"term": "文档", "count": 12},
                {"term": "任务", "count": 10},
                {"term": "项目", "count": 8},
                {"term": "API", "count": 7}
            ][:limit]

        except Exception as e:
            logger.error(f"获取热门搜索词失败: {str(e)}")
            return []