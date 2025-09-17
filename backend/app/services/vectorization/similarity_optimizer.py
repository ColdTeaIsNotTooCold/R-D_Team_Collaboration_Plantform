"""
向量相似度计算优化模块
提供高效的相似度计算、索引优化和批量处理功能
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import time
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import heapq
from scipy.spatial.distance import cosine, euclidean
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.metrics.pairwise import cosine_similarity
import hashlib
import json

from ..core.config import settings
from .service import VectorizationService

logger = logging.getLogger(__name__)


class SimilarityOptimizer:
    """相似度计算优化器"""

    def __init__(self):
        self.vectorization_service = VectorizationService()
        self._initialized = False

        # 相似度计算缓存
        self._similarity_cache = {}
        self._cache_metadata = {}

        # 批量计算优化
        self._batch_size = 1000
        self._parallel_workers = 4

        # 索引和预计算
        self._embedding_index = {}
        self._similarity_matrix_cache = {}
        self._cluster_cache = {}

        # 性能监控
        self._performance_metrics = {
            'total_similarities': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'batch_calculations': 0,
            'average_calculation_time': 0.0,
            'matrix_calculations': 0,
            'average_matrix_time': 0.0,
            'cluster_calculations': 0,
            'average_cluster_time': 0.0
        }

    async def initialize(self) -> bool:
        """初始化相似度优化器"""
        try:
            if not await self.vectorization_service.initialize():
                logger.error("向量化服务初始化失败")
                return False

            self._initialized = True
            logger.info("相似度优化器初始化成功")
            return True

        except Exception as e:
            logger.error(f"相似度优化器初始化失败: {str(e)}")
            return False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    def _generate_similarity_key(self, embedding1: List[float], embedding2: List[float]) -> str:
        """生成相似度计算缓存键"""
        # 使用嵌入向量的前几个元素作为键的一部分，避免完整向量的哈希
        key_content = f"{len(embedding1)}_{hash(str(embedding1[:10]))}_{hash(str(embedding2[:10]))}"
        return hashlib.md5(key_content.encode('utf-8')).hexdigest()

    async def calculate_similarity_optimized(
        self,
        embedding1: List[float],
        embedding2: List[float],
        method: str = "cosine",
        use_cache: bool = True
    ) -> float:
        """优化的相似度计算"""
        if not self.is_initialized():
            logger.error("相似度优化器未初始化")
            return 0.0

        start_time = time.time()
        self._performance_metrics['total_similarities'] += 1

        # 检查缓存
        if use_cache:
            cache_key = self._generate_similarity_key(embedding1, embedding2)
            if cache_key in self._similarity_cache:
                self._performance_metrics['cache_hits'] += 1
                # 更新访问时间
                self._cache_metadata[cache_key]['last_accessed'] = datetime.now()
                self._cache_metadata[cache_key]['access_count'] += 1
                return self._similarity_cache[cache_key]

        # 计算相似度
        try:
            if method == "cosine":
                similarity = self._cosine_similarity_numpy(embedding1, embedding2)
            elif method == "euclidean":
                similarity = self._euclidean_similarity(embedding1, embedding2)
            elif method == "dot_product":
                similarity = self._dot_product_similarity(embedding1, embedding2)
            else:
                similarity = self._cosine_similarity_numpy(embedding1, embedding2)

            # 缓存结果
            if use_cache:
                self._similarity_cache[cache_key] = similarity
                self._cache_metadata[cache_key] = {
                    'method': method,
                    'created_at': datetime.now(),
                    'last_accessed': datetime.now(),
                    'access_count': 1,
                    'embedding1_dim': len(embedding1),
                    'embedding2_dim': len(embedding2)
                }

            self._performance_metrics['cache_misses'] += 1

            # 更新性能指标
            operation_time = time.time() - start_time
            self._update_performance_metrics(operation_time, 'similarity')

            return similarity

        except Exception as e:
            logger.error(f"相似度计算失败: {str(e)}")
            return 0.0

    def _cosine_similarity_numpy(self, embedding1: List[float], embedding2: List[float]) -> float:
        """使用NumPy计算余弦相似度"""
        try:
            vec1 = np.array(embedding1, dtype=np.float32)
            vec2 = np.array(embedding2, dtype=np.float32)

            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(np.clip(similarity, -1.0, 1.0))

        except Exception as e:
            logger.error(f"余弦相似度计算失败: {str(e)}")
            return 0.0

    def _euclidean_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算欧几里得相似度"""
        try:
            distance = euclidean(embedding1, embedding2)
            # 转换为相似度分数 (0-1)
            max_distance = np.sqrt(len(embedding1)) * 2  # 理论最大距离
            similarity = 1.0 - (distance / max_distance)
            return float(np.clip(similarity, 0.0, 1.0))

        except Exception as e:
            logger.error(f"欧几里得相似度计算失败: {str(e)}")
            return 0.0

    def _dot_product_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算点积相似度"""
        try:
            vec1 = np.array(embedding1, dtype=np.float32)
            vec2 = np.array(embedding2, dtype=np.float32)

            # 归一化后计算点积
            vec1_norm = vec1 / np.linalg.norm(vec1)
            vec2_norm = vec2 / np.linalg.norm(vec2)

            similarity = np.dot(vec1_norm, vec2_norm)
            return float(np.clip(similarity, -1.0, 1.0))

        except Exception as e:
            logger.error(f"点积相似度计算失败: {str(e)}")
            return 0.0

    async def batch_calculate_similarities(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        method: str = "cosine",
        use_cache: bool = True,
        top_k: Optional[int] = None
    ) -> List[Tuple[int, float]]:
        """批量计算相似度"""
        if not self.is_initialized():
            logger.error("相似度优化器未初始化")
            return []

        start_time = time.time()

        try:
            # 使用NumPy向量化计算
            query_array = np.array(query_embedding, dtype=np.float32)
            candidates_array = np.array(candidate_embeddings, dtype=np.float32)

            if method == "cosine":
                # 向量化余弦相似度计算
                query_norm = query_array / np.linalg.norm(query_array)
                candidates_norm = candidates_array / np.linalg.norm(candidates_array, axis=1, keepdims=True)
                similarities = np.dot(candidates_norm, query_norm)
            else:
                # 其他方法逐个计算
                similarities = []
                for candidate in candidate_embeddings:
                    similarity = await self.calculate_similarity_optimized(
                        query_embedding, candidate, method, use_cache
                    )
                    similarities.append(similarity)
                similarities = np.array(similarities)

            # 创建结果列表
            results = [(i, float(similarity)) for i, similarity in enumerate(similarities)]

            # 如果需要top_k结果
            if top_k:
                results = heapq.nlargest(top_k, results, key=lambda x: x[1])

            self._performance_metrics['batch_calculations'] += 1
            operation_time = time.time() - start_time
            self._update_performance_metrics(operation_time, 'batch')

            return results

        except Exception as e:
            logger.error(f"批量相似度计算失败: {str(e)}")
            return []

    async def calculate_similarity_matrix(
        self,
        embeddings: List[List[float]],
        method: str = "cosine",
        use_cache: bool = True
    ) -> np.ndarray:
        """计算相似度矩阵"""
        if not self.is_initialized():
            logger.error("相似度优化器未初始化")
            return np.array([])

        start_time = time.time()

        try:
            embeddings_array = np.array(embeddings, dtype=np.float32)

            if method == "cosine":
                # 使用scikit-learn的向量化计算
                similarity_matrix = cosine_similarity(embeddings_array)
            else:
                # 逐个计算
                n = len(embeddings)
                similarity_matrix = np.zeros((n, n))

                for i in range(n):
                    for j in range(i, n):
                        similarity = await self.calculate_similarity_optimized(
                            embeddings[i], embeddings[j], method, use_cache
                        )
                        similarity_matrix[i, j] = similarity
                        similarity_matrix[j, i] = similarity

            self._performance_metrics['matrix_calculations'] += 1
            operation_time = time.time() - start_time
            self._update_performance_metrics(operation_time, 'matrix')

            # 缓存矩阵
            matrix_key = hashlib.md5(f"{len(embeddings)}_{method}".encode()).hexdigest()
            self._similarity_matrix_cache[matrix_key] = {
                'matrix': similarity_matrix,
                'created_at': datetime.now(),
                'embeddings_count': len(embeddings),
                'method': method
            }

            return similarity_matrix

        except Exception as e:
            logger.error(f"相似度矩阵计算失败: {str(e)}")
            return np.array([])

    async def find_similar_clusters(
        self,
        embeddings: List[List[float]],
        threshold: float = 0.8,
        method: str = "average"
    ) -> Dict[str, Any]:
        """聚类相似向量"""
        if not self.is_initialized():
            logger.error("相似度优化器未初始化")
            return {}

        start_time = time.time()

        try:
            embeddings_array = np.array(embeddings, dtype=np.float32)

            # 层次聚类
            linkage_matrix = linkage(embeddings_array, method=method)
            clusters = fcluster(linkage_matrix, threshold, criterion='distance')

            # 组织聚类结果
            cluster_results = defaultdict(list)
            for i, cluster_id in enumerate(clusters):
                cluster_results[int(cluster_id)].append({
                    'index': i,
                    'embedding': embeddings[i]
                })

            # 计算聚类统计信息
            cluster_stats = {}
            for cluster_id, items in cluster_results.items():
                if len(items) > 1:
                    cluster_embeddings = [item['embedding'] for item in items]
                    centroid = np.mean(cluster_embeddings, axis=0).tolist()
                    avg_similarity = np.mean([
                        await self.calculate_similarity_optimized(centroid, emb)
                        for emb in cluster_embeddings
                    ])
                else:
                    centroid = items[0]['embedding']
                    avg_similarity = 1.0

                cluster_stats[cluster_id] = {
                    'size': len(items),
                    'centroid': centroid,
                    'average_similarity': avg_similarity,
                    'indices': [item['index'] for item in items]
                }

            result = {
                'clusters': dict(cluster_results),
                'cluster_stats': cluster_stats,
                'total_clusters': len(cluster_results),
                'threshold': threshold,
                'method': method
            }

            self._performance_metrics['cluster_calculations'] += 1
            operation_time = time.time() - start_time
            self._update_performance_metrics(operation_time, 'cluster')

            return result

        except Exception as e:
            logger.error(f"聚类分析失败: {str(e)}")
            return {}

    async def find_top_similar_pairs(
        self,
        embeddings: List[List[float]],
        top_k: int = 10,
        min_similarity: float = 0.5
    ) -> List[Tuple[int, int, float]]:
        """找到最相似的向量对"""
        if not self.is_initialized():
            logger.error("相似度优化器未初始化")
            return []

        try:
            similar_pairs = []

            # 计算相似度矩阵的上三角部分
            n = len(embeddings)
            for i in range(n):
                for j in range(i + 1, n):
                    similarity = await self.calculate_similarity_optimized(
                        embeddings[i], embeddings[j], use_cache=True
                    )

                    if similarity >= min_similarity:
                        similar_pairs.append((i, j, similarity))

            # 排序并取前top_k个
            similar_pairs.sort(key=lambda x: x[2], reverse=True)
            return similar_pairs[:top_k]

        except Exception as e:
            logger.error(f"查找相似对失败: {str(e)}")
            return []

    def _update_performance_metrics(self, operation_time: float, operation_type: str) -> None:
        """更新性能指标"""
        if operation_type == 'similarity':
            avg_time = self._performance_metrics['average_calculation_time']
            self._performance_metrics['average_calculation_time'] = (avg_time * (self._performance_metrics['total_similarities'] - 1) + operation_time) / self._performance_metrics['total_similarities']
        elif operation_type == 'batch':
            avg_time = self._performance_metrics['average_calculation_time']
            self._performance_metrics['average_calculation_time'] = (avg_time * (self._performance_metrics['batch_calculations'] - 1) + operation_time) / self._performance_metrics['batch_calculations']
        elif operation_type == 'matrix':
            avg_time = self._performance_metrics['average_matrix_time']
            self._performance_metrics['average_matrix_time'] = (avg_time * (self._performance_metrics['matrix_calculations'] - 1) + operation_time) / self._performance_metrics['matrix_calculations']
        elif operation_type == 'cluster':
            avg_time = self._performance_metrics['average_cluster_time']
            self._performance_metrics['average_cluster_time'] = (avg_time * (self._performance_metrics['cluster_calculations'] - 1) + operation_time) / self._performance_metrics['cluster_calculations']

    async def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        cache_hit_rate = self._performance_metrics['cache_hits'] / max(1, self._performance_metrics['cache_hits'] + self._performance_metrics['cache_misses'])

        return {
            'performance_metrics': self._performance_metrics,
            'cache_stats': {
                'cache_size': len(self._similarity_cache),
                'cache_hit_rate': cache_hit_rate,
                'matrix_cache_size': len(self._similarity_matrix_cache)
            },
            'config': {
                'batch_size': self._batch_size,
                'parallel_workers': self._parallel_workers
            },
            'timestamp': datetime.now().isoformat()
        }

    async def clear_cache(self) -> bool:
        """清空缓存"""
        try:
            self._similarity_cache.clear()
            self._cache_metadata.clear()
            self._similarity_matrix_cache.clear()

            # 重置缓存相关指标
            self._performance_metrics['cache_hits'] = 0
            self._performance_metrics['cache_misses'] = 0

            logger.info("相似度计算缓存已清空")
            return True

        except Exception as e:
            logger.error(f"清空缓存失败: {str(e)}")
            return False


# 全局相似度优化器实例
similarity_optimizer = SimilarityOptimizer()


async def get_similarity_optimizer() -> SimilarityOptimizer:
    """获取相似度优化器实例"""
    return similarity_optimizer