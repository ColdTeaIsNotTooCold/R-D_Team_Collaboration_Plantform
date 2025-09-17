"""
向量搜索性能优化模块
提供高效的向量搜索、索引优化和查询加速功能
"""
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
import asyncio
import time
import numpy as np
import re
import hashlib
import json
from datetime import datetime, timedelta
from collections import defaultdict, deque
import heapq
from ..core.config import settings
from .service import VectorizationService

logger = logging.getLogger(__name__)


class VectorSearchOptimizer:
    """向量搜索性能优化器"""

    def __init__(self, cache_size: int = 1000, index_refresh_interval: int = 300):
        self.vectorization_service = VectorizationService()
        self.cache_size = cache_size
        self.index_refresh_interval = index_refresh_interval
        self._initialized = False

        # 搜索缓存
        self._search_cache = {}
        self._search_cache_timestamps = {}
        self._search_stats = defaultdict(int)

        # 索引优化
        self._index_last_refresh = None
        self._index_metrics = {
            'total_searches': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_search_time': 0.0,
            'index_refresh_count': 0,
            'average_index_refresh_time': 0.0
        }

        # 查询优化
        self._query_preprocessing_cache = {}
        self._similarity_cache = {}

        # 性能监控
        self._performance_history = deque(maxlen=1000)
        self._slow_queries = deque(maxlen=100)

    async def initialize(self) -> bool:
        """初始化搜索优化器"""
        try:
            if not await self.vectorization_service.initialize():
                logger.error("向量化服务初始化失败")
                return False

            self._initialized = True
            self._index_last_refresh = datetime.now()
            logger.info("向量搜索优化器初始化成功")
            return True

        except Exception as e:
            logger.error(f"向量搜索优化器初始化失败: {str(e)}")
            return False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    def _generate_search_cache_key(self, query: str, n_results: int, filters: Dict[str, Any]) -> str:
        """生成搜索缓存键"""
        filter_str = json.dumps(filters, sort_keys=True) if filters else "none"
        content = f"{query}:{n_results}:{filter_str}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _is_search_cache_valid(self, cache_key: str) -> bool:
        """检查搜索缓存是否有效"""
        if cache_key not in self._search_cache_timestamps:
            return False

        cache_time = self._search_cache_timestamps[cache_key]
        # 搜索缓存有效期较短（5分钟）
        expiry_time = cache_time + timedelta(seconds=300)
        return datetime.now() < expiry_time

    def _get_from_search_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """从搜索缓存获取结果"""
        if self._is_search_cache_valid(cache_key):
            self._index_metrics['cache_hits'] += 1
            self._search_stats['cache_hits'] += 1
            return self._search_cache[cache_key]
        return None

    def _set_search_cache(self, cache_key: str, results: List[Dict[str, Any]]) -> None:
        """设置搜索缓存"""
        # 使用LRU策略管理缓存
        if len(self._search_cache) >= self.cache_size:
            # 移除最旧的缓存项
            oldest_key = min(self._search_cache_timestamps.keys(),
                           key=lambda k: self._search_cache_timestamps[k])
            del self._search_cache[oldest_key]
            del self._search_cache_timestamps[oldest_key]

        self._search_cache[cache_key] = results
        self._search_cache_timestamps[cache_key] = datetime.now()
        self._index_metrics['cache_misses'] += 1
        self._search_stats['cache_misses'] += 1

    def _preprocess_query(self, query: str) -> str:
        """预处理查询文本"""
        # 检查预处理缓存
        if query in self._query_preprocessing_cache:
            return self._query_preprocessing_cache[query]

        # 预处理逻辑
        processed = query.lower().strip()
        processed = re.sub(r'\s+', ' ', processed)
        processed = re.sub(r'[^\w\s\u4e00-\u9fff]', '', processed)

        # 缓存结果
        self._query_preprocessing_cache[query] = processed
        return processed

    async def optimized_search(
        self,
        query: str,
        n_results: int = None,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        score_threshold: float = None,
        use_cache: bool = True,
        enable_ranking: bool = True
    ) -> List[Dict[str, Any]]:
        """优化的向量搜索"""
        if not self.is_initialized():
            logger.error("向量搜索优化器未初始化")
            return []

        try:
            start_time = time.time()
            n_results = n_results or settings.vector_search_top_k
            score_threshold = score_threshold or settings.vector_search_score_threshold

            # 检查索引是否需要刷新
            await self._check_index_refresh()

            # 预处理查询
            processed_query = self._preprocess_query(query)

            # 检查搜索缓存
            if use_cache:
                cache_key = self._generate_search_cache_key(
                    processed_query, n_results,
                    {'where': where, 'where_document': where_document}
                )
                cached_results = self._get_from_search_cache(cache_key)
                if cached_results:
                    return cached_results

            # 执行搜索
            results = await self._perform_optimized_search(
                processed_query,
                n_results,
                where,
                where_document,
                score_threshold,
                enable_ranking
            )

            # 缓存结果
            if use_cache and results:
                self._set_search_cache(cache_key, results)

            # 记录性能
            operation_time = time.time() - start_time
            await self._record_search_performance(operation_time, len(results))

            # 更新指标
            self._index_metrics['total_searches'] += 1
            avg_time = self._index_metrics['average_search_time']
            self._index_metrics['average_search_time'] = (avg_time * (self._index_metrics['total_searches'] - 1) + operation_time) / self._index_metrics['total_searches']

            return results

        except Exception as e:
            logger.error(f"优化搜索失败: {str(e)}")
            return []

    async def _perform_optimized_search(
        self,
        query: str,
        n_results: int,
        where: Optional[Dict[str, Any]],
        where_document: Optional[Dict[str, Any]],
        score_threshold: float,
        enable_ranking: bool
    ) -> List[Dict[str, Any]]:
        """执行优化的搜索操作"""
        # 这里需要与实际的向量数据库集成
        # 临时使用向量化服务的相似度计算
        try:
            # 生成查询嵌入
            query_embedding = await self.vectorization_service.generate_embedding(query)
            if not query_embedding:
                return []

            # 获取候选文档（这里需要与实际数据库集成）
            candidate_docs = await self._get_candidate_documents(where, where_document)
            if not candidate_docs:
                return []

            # 计算相似度
            similarity_results = []
            for doc in candidate_docs:
                doc_embedding = doc.get('embedding')
                if doc_embedding:
                    similarity = await self._calculate_cached_similarity(
                        query_embedding, doc_embedding
                    )
                    if similarity >= score_threshold:
                        similarity_results.append({
                            'document': doc.get('content', ''),
                            'metadata': doc.get('metadata', {}),
                            'id': doc.get('id', ''),
                            'score': similarity,
                            'distance': 1.0 - similarity
                        })

            # 排序和筛选
            if enable_ranking:
                similarity_results.sort(key=lambda x: x['score'], reverse=True)
                similarity_results = similarity_results[:n_results]

            # 添加排名
            for i, result in enumerate(similarity_results):
                result['rank'] = i + 1

            return similarity_results

        except Exception as e:
            logger.error(f"执行优化搜索失败: {str(e)}")
            return []

    async def _get_candidate_documents(
        self,
        where: Optional[Dict[str, Any]],
        where_document: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """获取候选文档（需要与实际数据库集成）"""
        # 这里应该从向量数据库获取候选文档
        # 临时返回空列表，需要根据实际数据库调整
        return []

    async def _calculate_cached_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """计算缓存的相似度"""
        cache_key = f"{len(embedding1)}_{hash(str(embedding1[:10]))}_{hash(str(embedding2[:10]))}"

        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]

        similarity = await self.vectorization_service.embedding_generator.calculate_similarity(
            embedding1, embedding2
        )

        # 缓存结果
        self._similarity_cache[cache_key] = similarity

        # 限制缓存大小
        if len(self._similarity_cache) > 10000:
            oldest_keys = sorted(self._similarity_cache.keys())[:1000]
            for key in oldest_keys:
                del self._similarity_cache[key]

        return similarity

    async def _check_index_refresh(self) -> None:
        """检查是否需要刷新索引"""
        if not self._index_last_refresh:
            return

        time_since_refresh = (datetime.now() - self._index_last_refresh).total_seconds()
        if time_since_refresh >= self.index_refresh_interval:
            await self._refresh_index()

    async def _refresh_index(self) -> None:
        """刷新索引"""
        try:
            start_time = time.time()

            # 这里应该实现索引刷新逻辑
            # 例如重建索引、更新统计信息等

            refresh_time = time.time() - start_time

            self._index_last_refresh = datetime.now()
            self._index_metrics['index_refresh_count'] += 1

            avg_time = self._index_metrics['average_index_refresh_time']
            self._index_metrics['average_index_refresh_time'] = (avg_time * (self._index_metrics['index_refresh_count'] - 1) + refresh_time) / self._index_metrics['index_refresh_count']

            logger.info(f"索引刷新完成，耗时: {refresh_time:.2f}秒")

        except Exception as e:
            logger.error(f"索引刷新失败: {str(e)}")

    async def _record_search_performance(self, operation_time: float, result_count: int) -> None:
        """记录搜索性能"""
        performance_record = {
            'timestamp': datetime.now(),
            'operation_time': operation_time,
            'result_count': result_count,
            'is_slow_query': operation_time > 1.0  # 超过1秒为慢查询
        }

        self._performance_history.append(performance_record)

        if performance_record['is_slow_query']:
            self._slow_queries.append(performance_record)

    async def batch_optimized_search(
        self,
        queries: List[str],
        n_results: int = None,
        batch_size: int = 10,
        use_cache: bool = True
    ) -> List[List[Dict[str, Any]]]:
        """批量优化搜索"""
        if not self.is_initialized():
            logger.error("向量搜索优化器未初始化")
            return []

        try:
            start_time = time.time()
            all_results = []

            # 分批处理
            for i in range(0, len(queries), batch_size):
                batch_queries = queries[i:i + batch_size]
                batch_results = []

                # 并行处理批次
                tasks = [
                    self.optimized_search(query, n_results, use_cache=use_cache)
                    for query in batch_queries
                ]

                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理异常
                processed_results = []
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"批量搜索中的查询失败: {str(result)}")
                        processed_results.append([])
                    else:
                        processed_results.append(result)

                all_results.extend(processed_results)

                # 批次间延迟
                if i + batch_size < len(queries):
                    await asyncio.sleep(0.001)

            operation_time = time.time() - start_time
            logger.info(f"批量优化搜索完成，处理 {len(queries)} 个查询，耗时: {operation_time:.2f}秒")
            return all_results

        except Exception as e:
            logger.error(f"批量优化搜索失败: {str(e)}")
            return []

    async def get_search_performance_stats(self) -> Dict[str, Any]:
        """获取搜索性能统计"""
        if not self._performance_history:
            return {'message': 'No performance data available'}

        recent_performance = list(self._performance_history)[-100:]  # 最近100次搜索

        return {
            'total_searches': self._index_metrics['total_searches'],
            'cache_hit_rate': self._index_metrics['cache_hits'] / max(1, self._index_metrics['cache_hits'] + self._index_metrics['cache_misses']),
            'average_search_time': self._index_metrics['average_search_time'],
            'slow_query_count': len(self._slow_queries),
            'slow_query_rate': len(self._slow_queries) / len(self._performance_history) if self._performance_history else 0,
            'recent_average_time': sum(p['operation_time'] for p in recent_performance) / len(recent_performance) if recent_performance else 0,
            'index_metrics': self._index_metrics,
            'cache_size': len(self._search_cache),
            'timestamp': datetime.now().isoformat()
        }

    async def clear_search_cache(self) -> bool:
        """清空搜索缓存"""
        try:
            self._search_cache.clear()
            self._search_cache_timestamps.clear()
            self._query_preprocessing_cache.clear()
            self._similarity_cache.clear()
            self._index_metrics['cache_hits'] = 0
            self._index_metrics['cache_misses'] = 0
            logger.info("搜索缓存已清空")
            return True
        except Exception as e:
            logger.error(f"清空搜索缓存失败: {str(e)}")
            return False

    async def optimize_search_index(self) -> bool:
        """优化搜索索引"""
        try:
            start_time = time.time()

            # 强制刷新索引
            await self._refresh_index()

            # 清理过期缓存
            await self._cleanup_expired_cache()

            # 重建相似度缓存
            self._similarity_cache.clear()

            operation_time = time.time() - start_time
            logger.info(f"搜索索引优化完成，耗时: {operation_time:.2f}秒")
            return True

        except Exception as e:
            logger.error(f"优化搜索索引失败: {str(e)}")
            return False

    async def _cleanup_expired_cache(self) -> None:
        """清理过期缓存"""
        current_time = datetime.now()
        expiry_time = current_time - timedelta(seconds=300)  # 5分钟过期

        expired_search_keys = [
            key for key, timestamp in self._search_cache_timestamps.items()
            if timestamp < expiry_time
        ]

        for key in expired_search_keys:
            del self._search_cache[key]
            del self._search_cache_timestamps[key]


# 全局向量搜索优化器实例
search_optimizer = VectorSearchOptimizer()


async def get_search_optimizer() -> VectorSearchOptimizer:
    """获取向量搜索优化器实例"""
    return search_optimizer