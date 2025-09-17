"""
RAG检索策略和算法模块
实现多种检索策略和优化算法
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import time
from datetime import datetime
import numpy as np
from ..core.vector_db import VectorDBManager
from ..services.vectorization.service import VectorizationService
from ..services.vectorization.search_optimizer import VectorSearchOptimizer
from ..services.vectorization.similarity_optimizer import SimilarityOptimizer

logger = logging.getLogger(__name__)


class RetrievalStrategy(Enum):
    """检索策略枚举"""
    SEMANTIC_SEARCH = "semantic_search"
    HYBRID_SEARCH = "hybrid_search"
    MULTI_QUERY = "multi_query"
    QUERY_REFORMULATION = "query_reformulation"
    RERANKING = "reranking"


class RetrievalMethod(Enum):
    """检索方法枚举"""
    VECTOR_ONLY = "vector_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID = "hybrid"
    DIVERSITY = "diversity"


@dataclass
class RetrievalConfig:
    """检索配置"""
    strategy: RetrievalStrategy = RetrievalStrategy.SEMANTIC_SEARCH
    method: RetrievalMethod = RetrievalMethod.VECTOR_ONLY
    max_results: int = 10
    score_threshold: float = 0.7
    diversity_threshold: float = 0.8
    reranking_enabled: bool = True
    context_window_size: int = 4000
    enable_query_expansion: bool = True
    enable_fallback: bool = True


@dataclass
class RetrievedDocument:
    """检索到的文档"""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float
    rank: int
    retrieval_method: str
    timestamp: datetime


class RetrievalStrategyFactory:
    """检索策略工厂类"""

    def __init__(self, vector_db: VectorDBManager, vectorization_service: VectorizationService):
        self.vector_db = vector_db
        self.vectorization_service = vectorization_service
        self.search_optimizer = VectorSearchOptimizer(vector_db)
        self.similarity_optimizer = SimilarityOptimizer()
        self._strategies = {
            RetrievalStrategy.SEMANTIC_SEARCH: self._semantic_search_strategy,
            RetrievalStrategy.HYBRID_SEARCH: self._hybrid_search_strategy,
            RetrievalStrategy.MULTI_QUERY: self._multi_query_strategy,
            RetrievalStrategy.QUERY_REFORMULATION: self._query_reformulation_strategy,
            RetrievalStrategy.RERANKING: self._reranking_strategy
        }

    async def retrieve(self, query: str, config: RetrievalConfig) -> List[RetrievedDocument]:
        """执行检索"""
        try:
            strategy_func = self._strategies.get(config.strategy)
            if not strategy_func:
                logger.warning(f"未知检索策略: {config.strategy}, 使用默认策略")
                strategy_func = self._semantic_search_strategy

            results = await strategy_func(query, config)

            # 后处理：过滤和排序
            filtered_results = self._filter_results(results, config)
            sorted_results = self._sort_results(filtered_results)

            return sorted_results[:config.max_results]

        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            if config.enable_fallback:
                return await self._fallback_retrieval(query, config)
            return []

    async def _semantic_search_strategy(self, query: str, config: RetrievalConfig) -> List[RetrievedDocument]:
        """语义搜索策略"""
        try:
            start_time = time.time()

            # 使用优化的搜索
            results = await self.search_optimizer.optimized_search(
                query=query,
                n_results=config.max_results * 2,  # 获取更多结果用于后续处理
                score_threshold=config.score_threshold
            )

            documents = []
            for i, result in enumerate(results):
                doc = RetrievedDocument(
                    id=result['id'],
                    content=result['document'],
                    metadata=result['metadata'],
                    score=result['score'],
                    rank=i + 1,
                    retrieval_method='semantic_search',
                    timestamp=datetime.now()
                )
                documents.append(doc)

            logger.info(f"语义搜索完成，找到 {len(documents)} 个结果，耗时: {time.time() - start_time:.3f}秒")
            return documents

        except Exception as e:
            logger.error(f"语义搜索失败: {str(e)}")
            return []

    async def _hybrid_search_strategy(self, query: str, config: RetrievalConfig) -> List[RetrievedDocument]:
        """混合搜索策略（向量+关键词）"""
        try:
            start_time = time.time()

            # 并行执行向量搜索和关键词搜索
            vector_task = self._semantic_search_strategy(query, config)
            keyword_task = self._keyword_search_strategy(query, config)

            vector_results, keyword_results = await asyncio.gather(vector_task, keyword_task)

            # 合并结果
            merged_results = self._merge_hybrid_results(vector_results, keyword_results, config)

            logger.info(f"混合搜索完成，合并后 {len(merged_results)} 个结果，耗时: {time.time() - start_time:.3f}秒")
            return merged_results

        except Exception as e:
            logger.error(f"混合搜索失败: {str(e)}")
            return []

    async def _multi_query_strategy(self, query: str, config: RetrievalConfig) -> List[RetrievedDocument]:
        """多查询策略"""
        try:
            start_time = time.time()

            # 生成多个查询变体
            query_variants = await self._generate_query_variants(query)

            # 并行执行多个查询
            search_tasks = []
            for variant in query_variants:
                task = self._semantic_search_strategy(variant, config)
                search_tasks.append(task)

            all_results = await asyncio.gather(*search_tasks)

            # 合并和去重
            merged_results = self._merge_multi_query_results(all_results, config)

            logger.info(f"多查询搜索完成，使用 {len(query_variants)} 个查询变体，找到 {len(merged_results)} 个结果，耗时: {time.time() - start_time:.3f}秒")
            return merged_results

        except Exception as e:
            logger.error(f"多查询搜索失败: {str(e)}")
            return []

    async def _query_reformulation_strategy(self, query: str, config: RetrievalConfig) -> List[RetrievedDocument]:
        """查询重构策略"""
        try:
            start_time = time.time()

            # 重构查询
            reformulated_queries = await self._reformulate_query(query)

            # 执行搜索
            search_tasks = []
            for reformulated_query in reformulated_queries:
                task = self._semantic_search_strategy(reformulated_query, config)
                search_tasks.append(task)

            all_results = await asyncio.gather(*search_tasks)

            # 合并结果
            merged_results = self._merge_reformulated_results(all_results, config)

            logger.info(f"查询重构搜索完成，重构为 {len(reformulated_queries)} 个查询，找到 {len(merged_results)} 个结果，耗时: {time.time() - start_time:.3f}秒")
            return merged_results

        except Exception as e:
            logger.error(f"查询重构搜索失败: {str(e)}")
            return []

    async def _reranking_strategy(self, query: str, config: RetrievalConfig) -> List[RetrievedDocument]:
        """重排序策略"""
        try:
            start_time = time.time()

            # 首先执行基础搜索
            initial_results = await self._semantic_search_strategy(query, config)

            if not initial_results or not config.reranking_enabled:
                return initial_results

            # 执行重排序
            reranked_results = await self._rerank_results(query, initial_results)

            logger.info(f"重排序搜索完成，从 {len(initial_results)} 个结果重排序为 {len(reranked_results)} 个结果，耗时: {time.time() - start_time:.3f}秒")
            return reranked_results

        except Exception as e:
            logger.error(f"重排序搜索失败: {str(e)}")
            return []

    async def _keyword_search_strategy(self, query: str, config: RetrievalConfig) -> List[RetrievedDocument]:
        """关键词搜索策略"""
        try:
            # 提取关键词
            keywords = self._extract_keywords(query)

            # 构建关键词过滤条件
            where_filter = {"keywords": {"$in": keywords}} if keywords else None

            # 执行搜索
            results = await self.vector_db.search(
                query=query,
                n_results=config.max_results,
                where=where_filter,
                score_threshold=config.score_threshold
            )

            documents = []
            for i, result in enumerate(results):
                doc = RetrievedDocument(
                    id=result['id'],
                    content=result['document'],
                    metadata=result['metadata'],
                    score=result['score'] * 0.8,  # 关键词搜索权重略低
                    rank=i + 1,
                    retrieval_method='keyword_search',
                    timestamp=datetime.now()
                )
                documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"关键词搜索失败: {str(e)}")
            return []

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取，可以后续优化
        words = query.lower().split()
        keywords = [word for word in words if len(word) > 2 and word.isalnum()]
        return list(set(keywords))

    async def _generate_query_variants(self, query: str) -> List[str]:
        """生成查询变体"""
        variants = [query]

        # 添加同义词扩展（简化版本）
        words = query.split()
        if len(words) > 1:
            # 重新排列词语顺序
            variants.append(' '.join(reversed(words)))

        # 添加上下文相关词汇
        context_words = ["解释", "说明", "详细", "简单"]
        for word in context_words:
            if word not in query:
                variants.append(f"{word} {query}")

        return variants[:3]  # 限制变体数量

    async def _reformulate_query(self, query: str) -> List[str]:
        """重构查询"""
        reformulations = [query]

        # 添加问题形式变体
        if not query.endswith('?'):
            reformulations.append(f"{query}?")

        # 添加更详细的描述
        if len(query) < 20:
            reformulations.append(f"关于{query}的详细信息")

        return reformulations[:2]  # 限制重构数量

    def _merge_hybrid_results(self, vector_results: List[RetrievedDocument],
                            keyword_results: List[RetrievedDocument],
                            config: RetrievalConfig) -> List[RetrievedDocument]:
        """合并混合搜索结果"""
        merged = {}

        # 合并向量搜索结果
        for doc in vector_results:
            merged[doc.id] = doc

        # 合并关键词搜索结果，如果已存在则取更高分数
        for doc in keyword_results:
            if doc.id in merged:
                # 取更高分数
                if doc.score > merged[doc.id].score:
                    merged[doc.id].score = doc.score
                    merged[doc.id].retrieval_method = 'hybrid_search'
            else:
                merged[doc.id] = doc
                doc.retrieval_method = 'hybrid_search'

        return list(merged.values())

    def _merge_multi_query_results(self, all_results: List[List[RetrievedDocument]],
                                 config: RetrievalConfig) -> List[RetrievedDocument]:
        """合并多查询结果"""
        merged = {}

        for query_results in all_results:
            for doc in query_results:
                if doc.id in merged:
                    # 累积分数
                    merged[doc.id].score += doc.score
                    merged[doc.id].rank = min(merged[doc.id].rank, doc.rank)
                else:
                    merged[doc.id] = doc

        # 重新计算平均分数
        for doc in merged.values():
            doc.score = doc.score / len(all_results)

        return list(merged.values())

    def _merge_reformulated_results(self, all_results: List[List[RetrievedDocument]],
                                   config: RetrievalConfig) -> List[RetrievedDocument]:
        """合并重构查询结果"""
        return self._merge_multi_query_results(all_results, config)

    async def _rerank_results(self, query: str, results: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """重排序结果"""
        try:
            # 使用相似度优化器进行重排序
            contents = [doc.content for doc in results]

            # 计算查询与每个结果的相似度
            similarities = await self.similarity_optimizer.batch_similarity(query, contents)

            # 更新分数和排名
            for i, doc in enumerate(results):
                reranked_score = similarities[i] * 0.7 + doc.score * 0.3  # 综合考虑重排序分数和原始分数
                doc.score = reranked_score
                doc.rank = i + 1
                doc.retrieval_method = 'reranked_search'

            return results

        except Exception as e:
            logger.error(f"重排序失败: {str(e)}")
            return results

    def _filter_results(self, results: List[RetrievedDocument], config: RetrievalConfig) -> List[RetrievedDocument]:
        """过滤结果"""
        filtered = []

        for doc in results:
            # 分数阈值过滤
            if doc.score >= config.score_threshold:
                # 多样性过滤
                if self._is_diverse_enough(doc, filtered, config.diversity_threshold):
                    filtered.append(doc)

        return filtered

    def _is_diverse_enough(self, new_doc: RetrievedDocument, existing_docs: List[RetrievedDocument],
                          threshold: float) -> bool:
        """检查文档多样性"""
        if not existing_docs:
            return True

        # 简单的相似度检查（可以后续优化）
        for existing_doc in existing_docs:
            if self._calculate_similarity(new_doc.content, existing_doc.content) > threshold:
                return False

        return True

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化版本）"""
        # 使用词重叠率作为相似度指标
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def _sort_results(self, results: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """排序结果"""
        return sorted(results, key=lambda x: x.score, reverse=True)

    async def _fallback_retrieval(self, query: str, config: RetrievalConfig) -> List[RetrievedDocument]:
        """回退检索策略"""
        try:
            logger.info("执行回退检索策略")
            return await self._semantic_search_strategy(query, config)
        except Exception as e:
            logger.error(f"回退检索失败: {str(e)}")
            return []


class RetrievalManager:
    """检索管理器"""

    def __init__(self, vector_db: VectorDBManager, vectorization_service: VectorizationService):
        self.vector_db = vector_db
        self.vectorization_service = vectorization_service
        self.strategy_factory = RetrievalStrategyFactory(vector_db, vectorization_service)
        self._performance_metrics = {
            'total_retrievals': 0,
            'successful_retrievals': 0,
            'failed_retrievals': 0,
            'average_retrieval_time': 0.0,
            'strategy_usage': {}
        }

    async def retrieve(self, query: str, config: RetrievalConfig = None) -> List[RetrievedDocument]:
        """执行检索"""
        if config is None:
            config = RetrievalConfig()

        try:
            start_time = time.time()

            # 确保向量数据库已初始化
            if not self.vector_db.is_initialized():
                await self.vector_db.initialize()

            # 执行检索
            results = await self.strategy_factory.retrieve(query, config)

            # 更新性能指标
            retrieval_time = time.time() - start_time
            self._update_performance_metrics(config.strategy, retrieval_time, len(results) > 0)

            logger.info(f"检索完成，找到 {len(results)} 个结果，耗时: {retrieval_time:.3f}秒")
            return results

        except Exception as e:
            logger.error(f"检索失败: {str(e)}")
            self._performance_metrics['failed_retrievals'] += 1
            return []

    def _update_performance_metrics(self, strategy: RetrievalStrategy, retrieval_time: float, success: bool):
        """更新性能指标"""
        self._performance_metrics['total_retrievals'] += 1

        if success:
            self._performance_metrics['successful_retrievals'] += 1
        else:
            self._performance_metrics['failed_retrievals'] += 1

        # 更新平均检索时间
        total_retrievals = self._performance_metrics['total_retrievals']
        current_avg = self._performance_metrics['average_retrieval_time']
        self._performance_metrics['average_retrieval_time'] = (current_avg * (total_retrievals - 1) + retrieval_time) / total_retrievals

        # 更新策略使用统计
        strategy_name = strategy.value
        if strategy_name not in self._performance_metrics['strategy_usage']:
            self._performance_metrics['strategy_usage'][strategy_name] = 0
        self._performance_metrics['strategy_usage'][strategy_name] += 1

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            'metrics': self._performance_metrics,
            'success_rate': self._performance_metrics['successful_retrievals'] / max(self._performance_metrics['total_retrievals'], 1),
            'timestamp': datetime.now().isoformat()
        }

    async def get_retrieval_strategies(self) -> List[Dict[str, Any]]:
        """获取可用检索策略"""
        strategies = []
        for strategy in RetrievalStrategy:
            strategies.append({
                'name': strategy.value,
                'description': self._get_strategy_description(strategy),
                'enabled': True
            })
        return strategies

    def _get_strategy_description(self, strategy: RetrievalStrategy) -> str:
        """获取策略描述"""
        descriptions = {
            RetrievalStrategy.SEMANTIC_SEARCH: "基于语义相似度的向量搜索",
            RetrievalStrategy.HYBRID_SEARCH: "结合向量搜索和关键词搜索的混合策略",
            RetrievalStrategy.MULTI_QUERY: "生成多个查询变体进行搜索",
            RetrievalStrategy.QUERY_REFORMULATION: "重构查询以获得更好的搜索结果",
            RetrievalStrategy.RERANKING: "对搜索结果进行重排序优化"
        }
        return descriptions.get(strategy, "未知策略")