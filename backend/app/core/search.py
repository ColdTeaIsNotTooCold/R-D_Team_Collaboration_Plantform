import logging
import time
import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
import re
from dataclasses import dataclass

from ..models.context import Context
from ..schemas.search import (
    SearchQuery, SearchResult, SearchResponse, SearchType, SortOrder,
    VectorSearchConfig, IndexDocument, IndexResponse
)

logger = logging.getLogger(__name__)


@dataclass
class SearchHighlight:
    """搜索高亮信息"""
    text: str
    start_pos: int
    end_pos: int
    score: float


class SearchEngine:
    """搜索引擎核心类"""

    def __init__(self, db: Session):
        self.db = db
        self.chroma_client = None
        self.embedding_model = None

    async def search(self, query: SearchQuery) -> SearchResponse:
        """执行搜索"""
        start_time = time.time()

        try:
            if query.search_type == SearchType.KEYWORD:
                results = await self._keyword_search(query)
            elif query.search_type == SearchType.SEMANTIC:
                results = await self._semantic_search(query)
            else:  # HYBRID
                results = await self._hybrid_search(query)

            # 应用分页
            paginated_results = self._apply_pagination(results, query.page, query.page_size)

            # 应用最小分数过滤
            if query.min_score is not None:
                paginated_results = [r for r in paginated_results if r.score >= query.min_score]

            execution_time = time.time() - start_time

            return SearchResponse(
                results=paginated_results,
                total=len(results),
                page=query.page,
                page_size=query.page_size,
                total_pages=(len(results) + query.page_size - 1) // query.page_size,
                query=query.query,
                search_type=query.search_type,
                execution_time=execution_time
            )

        except Exception as e:
            logger.error(f"搜索执行失败: {str(e)}")
            raise

    async def _keyword_search(self, query: SearchQuery) -> List[SearchResult]:
        """关键词搜索"""
        # 构建数据库查询
        db_query = self.db.query(Context)

        # 应用过滤条件
        if query.context_types:
            db_query = db_query.filter(Context.context_type.in_(query.context_types))
        if query.task_id:
            db_query = db_query.filter(Context.task_id == query.task_id)
        if query.conversation_id:
            db_query = db_query.filter(Context.conversation_id == query.conversation_id)

        # 构建关键词搜索条件
        search_conditions = []
        keywords = self._extract_keywords(query.query)

        for keyword in keywords:
            # 在标题中搜索
            title_condition = Context.title.ilike(f"%{keyword}%")
            # 在内容中搜索
            content_condition = Context.content.ilike(f"%{keyword}%")
            # 在元数据中搜索
            metadata_condition = Context.metadata.ilike(f"%{keyword}%")

            search_conditions.append(or_(title_condition, content_condition, metadata_condition))

        if search_conditions:
            db_query = db_query.filter(and_(*search_conditions))

        # 执行查询
        contexts = db_query.all()

        # 转换为搜索结果
        results = []
        for context in contexts:
            score = self._calculate_keyword_score(context, keywords)
            highlights = self._extract_highlights(context, keywords)

            metadata_dict = {}
            if context.metadata:
                try:
                    metadata_dict = json.loads(context.metadata)
                except json.JSONDecodeError:
                    pass

            result = SearchResult(
                id=context.id,
                context_type=context.context_type,
                title=context.title,
                content=context.content,
                metadata=metadata_dict,
                score=score,
                highlights=highlights,
                created_at=context.created_at,
                task_id=context.task_id,
                conversation_id=context.conversation_id
            )
            results.append(result)

        # 排序
        return self._sort_results(results, query.sort_by)

    async def _semantic_search(self, query: SearchQuery) -> List[SearchResult]:
        """语义搜索"""
        # 暂时返回空结果，等待ChromaDB集成
        logger.warning("语义搜索尚未完全实现，返回空结果")
        return []

    async def _hybrid_search(self, query: SearchQuery) -> List[SearchResult]:
        """混合搜索"""
        # 先执行关键词搜索
        keyword_results = await self._keyword_search(query)

        # 然后执行语义搜索
        semantic_results = await self._semantic_search(query)

        # 合并结果
        return self._merge_results(keyword_results, semantic_results)

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取，移除常见停用词
        stop_words = {'的', '了', '和', '是', '在', '有', '为', '不', '这', '个', '我', '你', '他', '她', '它'}
        words = re.findall(r'\b\w+\b', query.lower())
        return [word for word in words if word not in stop_words and len(word) > 1]

    def _calculate_keyword_score(self, context: Context, keywords: List[str]) -> float:
        """计算关键词匹配分数"""
        score = 0.0
        text_to_search = f"{context.title} {context.content or ''} {context.metadata or ''}".lower()

        for keyword in keywords:
            keyword_count = text_to_search.count(keyword.lower())
            score += keyword_count * 0.1  # 每个关键词匹配增加0.1分

        # 标题匹配权重更高
        for keyword in keywords:
            if keyword.lower() in context.title.lower():
                score += 0.3

        return min(score, 1.0)  # 限制最大分数为1.0

    def _extract_highlights(self, context: Context, keywords: List[str]) -> List[str]:
        """提取高亮文本片段"""
        highlights = []
        content = context.content or ""

        if not content:
            return highlights

        # 查找包含关键词的句子
        sentences = re.split(r'[.!?。！？]', content)
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and any(keyword.lower() in sentence.lower() for keyword in keywords):
                # 截取句子片段（最多100个字符）
                if len(sentence) > 100:
                    start = max(0, sentence.find(' ') if ' ' in sentence[:50] else 0)
                    highlights.append(sentence[start:start+100] + "...")
                else:
                    highlights.append(sentence)

        return highlights[:3]  # 最多返回3个高亮片段

    def _sort_results(self, results: List[SearchResult], sort_by: SortOrder) -> List[SearchResult]:
        """排序搜索结果"""
        if sort_by == SortOrder.RELEVANCE:
            return sorted(results, key=lambda x: x.score, reverse=True)
        elif sort_by == SortOrder.DATE:
            return sorted(results, key=lambda x: x.created_at, reverse=True)
        elif sort_by == SortOrder.TITLE:
            return sorted(results, key=lambda x: x.title.lower())
        return results

    def _apply_pagination(self, results: List[SearchResult], page: int, page_size: int) -> List[SearchResult]:
        """应用分页"""
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        return results[start_idx:end_idx]

    def _merge_results(self, keyword_results: List[SearchResult], semantic_results: List[SearchResult]) -> List[SearchResult]:
        """合并关键词和语义搜索结果"""
        # 简单的合并策略，避免重复
        result_ids = set()
        merged_results = []

        # 先添加关键词搜索结果
        for result in keyword_results:
            if result.id not in result_ids:
                merged_results.append(result)
                result_ids.add(result.id)

        # 添加语义搜索结果
        for result in semantic_results:
            if result.id not in result_ids:
                merged_results.append(result)
                result_ids.add(result.id)

        # 按分数重新排序
        return sorted(merged_results, key=lambda x: x.score, reverse=True)

    async def index_document(self, document: IndexDocument, config: Optional[VectorSearchConfig] = None) -> bool:
        """索引单个文档"""
        try:
            # 这里将在后续集成ChromaDB时实现
            logger.info(f"索引文档: {document.id} - {document.title}")
            return True
        except Exception as e:
            logger.error(f"索引文档失败: {str(e)}")
            return False

    async def batch_index(self, request: BatchIndexRequest) -> IndexResponse:
        """批量索引文档"""
        success_count = 0
        failed_count = 0
        errors = []

        for doc in request.documents:
            try:
                success = await self.index_document(doc, request.config)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                    errors.append(f"文档 {doc.id} 索引失败")
            except Exception as e:
                failed_count += 1
                errors.append(f"文档 {doc.id} 索引异常: {str(e)}")

        return IndexResponse(
            success=failed_count == 0,
            indexed_count=success_count,
            failed_count=failed_count,
            errors=errors
        )

    async def get_search_stats(self) -> Dict[str, Any]:
        """获取搜索统计信息"""
        try:
            total_contexts = self.db.query(func.count(Context.id)).scalar()

            stats = {
                "total_documents": total_contexts,
                "indexed_documents": 0,  # 将在ChromaDB集成后更新
                "search_types": {
                    "keyword": "available",
                    "semantic": "pending",
                    "hybrid": "available"
                },
                "last_updated": time.time()
            }

            return stats
        except Exception as e:
            logger.error(f"获取搜索统计失败: {str(e)}")
            return {}