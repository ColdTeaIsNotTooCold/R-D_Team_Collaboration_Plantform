"""
文本向量化服务
提供高效的文本嵌入生成、缓存和批量处理功能
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import time
import hashlib
import json
from datetime import datetime, timedelta
import numpy as np
from sentence_transformers import SentenceTransformer
import re
from ..core.config import settings
from ..core.embeddings import EmbeddingGenerator, TextChunker

logger = logging.getLogger(__name__)


class VectorizationService:
    """高效的文本向量化服务"""

    def __init__(self):
        self.embedding_generator = EmbeddingGenerator(settings.embedding_model)
        self.text_chunker = TextChunker()
        self._cache = {}
        self._cache_timestamps = {}
        self._initialized = False
        self._performance_metrics = {
            'total_embeddings': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_embedding_time': 0.0,
            'batch_processing_time': 0.0,
            'total_batches': 0
        }

    async def initialize(self) -> bool:
        """初始化向量化服务"""
        try:
            start_time = time.time()

            # 初始化嵌入生成器
            if not await self.embedding_generator.initialize():
                logger.error("嵌入生成器初始化失败")
                return False

            self._initialized = True
            init_time = time.time() - start_time
            logger.info(f"向量化服务初始化成功，耗时: {init_time:.2f}秒")
            return True

        except Exception as e:
            logger.error(f"向量化服务初始化失败: {str(e)}")
            return False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    def _generate_cache_key(self, text: str, model_name: str) -> str:
        """生成缓存键"""
        # 使用文本内容和模型名称生成唯一键
        content = f"{text}:{model_name}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._cache_timestamps:
            return False

        cache_time = self._cache_timestamps[cache_key]
        expiry_time = cache_time + timedelta(seconds=settings.embedding_cache_ttl)
        return datetime.now() < expiry_time

    def _get_from_cache(self, cache_key: str) -> Optional[List[float]]:
        """从缓存获取嵌入"""
        if self._is_cache_valid(cache_key):
            self._performance_metrics['cache_hits'] += 1
            return self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, embedding: List[float]) -> None:
        """设置缓存"""
        self._cache[cache_key] = embedding
        self._cache_timestamps[cache_key] = datetime.now()
        self._performance_metrics['cache_misses'] += 1

        # 清理过期缓存
        self._cleanup_expired_cache()

    def _cleanup_expired_cache(self) -> None:
        """清理过期缓存"""
        current_time = datetime.now()
        expiry_time = current_time - timedelta(seconds=settings.embedding_cache_ttl)

        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if timestamp < expiry_time
        ]

        for key in expired_keys:
            del self._cache[key]
            del self._cache_timestamps[key]

    async def generate_embedding(
        self,
        text: str,
        use_cache: bool = True,
        preprocess: bool = True
    ) -> List[float]:
        """生成单个文本的嵌入向量"""
        if not self.is_initialized():
            logger.error("向量化服务未初始化")
            return []

        try:
            start_time = time.time()

            # 检查缓存
            if use_cache:
                cache_key = self._generate_cache_key(text, self.embedding_generator.model_name)
                cached_embedding = self._get_from_cache(cache_key)
                if cached_embedding:
                    return cached_embedding

            # 预处理文本
            if preprocess:
                text = self.embedding_generator._preprocess_text(text)

            # 生成嵌入
            embedding = await self.embedding_generator.generate_embedding(text)

            # 缓存结果
            if use_cache and embedding:
                self._set_cache(cache_key, embedding)

            # 更新性能指标
            operation_time = time.time() - start_time
            self._performance_metrics['total_embeddings'] += 1
            avg_time = self._performance_metrics['average_embedding_time']
            self._performance_metrics['average_embedding_time'] = (avg_time * (self._performance_metrics['total_embeddings'] - 1) + operation_time) / self._performance_metrics['total_embeddings']

            return embedding

        except Exception as e:
            logger.error(f"生成嵌入失败: {str(e)}")
            return []

    async def batch_generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = None,
        use_cache: bool = True,
        preprocess: bool = True
    ) -> List[List[float]]:
        """批量生成嵌入向量"""
        if not self.is_initialized():
            logger.error("向量化服务未初始化")
            return []

        try:
            start_time = time.time()
            batch_size = batch_size or settings.embedding_batch_size
            total_texts = len(texts)

            # 预处理所有文本
            if preprocess:
                texts = [self.embedding_generator._preprocess_text(text) for text in texts]

            all_embeddings = []
            cache_hits = 0

            # 分批处理
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = []

                for text in batch_texts:
                    # 检查缓存
                    if use_cache:
                        cache_key = self._generate_cache_key(text, self.embedding_generator.model_name)
                        cached_embedding = self._get_from_cache(cache_key)
                        if cached_embedding:
                            batch_embeddings.append(cached_embedding)
                            cache_hits += 1
                            continue

                    # 生成嵌入
                    embedding = await self.embedding_generator.generate_embedding(text)
                    if embedding:
                        batch_embeddings.append(embedding)

                        # 缓存结果
                        if use_cache:
                            self._set_cache(cache_key, embedding)

                all_embeddings.extend(batch_embeddings)

                # 添加小延迟避免过载
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.01)

            operation_time = time.time() - start_time

            # 更新性能指标
            self._performance_metrics['total_batches'] += 1
            self._performance_metrics['batch_processing_time'] = (self._performance_metrics['batch_processing_time'] * (self._performance_metrics['total_batches'] - 1) + operation_time) / self._performance_metrics['total_batches']

            logger.info(f"批量生成 {len(all_embeddings)} 个嵌入完成，缓存命中: {cache_hits}，耗时: {operation_time:.2f}秒")
            return all_embeddings

        except Exception as e:
            logger.error(f"批量生成嵌入失败: {str(e)}")
            return []

    async def generate_document_embeddings(
        self,
        documents: List[str],
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """为文档生成嵌入向量（支持分块）"""
        if not self.is_initialized():
            logger.error("向量化服务未初始化")
            return {}

        try:
            start_time = time.time()
            all_chunks = []
            all_embeddings = []
            chunk_metadata = []

            # 配置分块器
            self.text_chunker.chunk_size = chunk_size
            self.text_chunker.chunk_overlap = chunk_overlap

            # 处理每个文档
            for doc_idx, document in enumerate(documents):
                # 分块处理
                chunks = self.text_chunker.chunk_text(document)

                for chunk_idx, chunk in enumerate(chunks):
                    all_chunks.append(chunk)
                    chunk_metadata.append({
                        'document_index': doc_idx,
                        'chunk_index': chunk_idx,
                        'document_length': len(document),
                        'chunk_length': len(chunk)
                    })

            # 批量生成嵌入
            if all_chunks:
                all_embeddings = await self.batch_generate_embeddings(
                    all_chunks,
                    use_cache=use_cache
                )

            operation_time = time.time() - start_time

            result = {
                'chunks': all_chunks,
                'embeddings': all_embeddings,
                'metadata': chunk_metadata,
                'total_chunks': len(all_chunks),
                'total_documents': len(documents),
                'processing_time': operation_time,
                'average_chunk_length': sum(len(chunk) for chunk in all_chunks) / len(all_chunks) if all_chunks else 0
            }

            logger.info(f"文档向量化完成，生成 {len(all_chunks)} 个块，耗时: {operation_time:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"文档向量化失败: {str(e)}")
            return {}

    async def calculate_similarity_matrix(
        self,
        texts: List[str],
        use_cache: bool = True
    ) -> np.ndarray:
        """计算文本相似度矩阵"""
        if not self.is_initialized():
            logger.error("向量化服务未初始化")
            return np.array([])

        try:
            # 生成所有文本的嵌入
            embeddings = await self.batch_generate_embeddings(texts, use_cache=use_cache)

            if not embeddings:
                return np.array([])

            # 转换为numpy数组
            embeddings_array = np.array(embeddings)

            # 计算相似度矩阵
            similarity_matrix = np.dot(embeddings_array, embeddings_array.T)

            # 归一化
            norms = np.linalg.norm(embeddings_array, axis=1)
            similarity_matrix = similarity_matrix / np.outer(norms, norms)

            return similarity_matrix

        except Exception as e:
            logger.error(f"计算相似度矩阵失败: {str(e)}")
            return np.array([])

    async def find_similar_texts(
        self,
        query_text: str,
        candidate_texts: List[str],
        top_k: int = 5,
        use_cache: bool = True
    ) -> List[Tuple[int, float, str]]:
        """找到与查询文本最相似的候选文本"""
        if not self.is_initialized():
            logger.error("向量化服务未初始化")
            return []

        try:
            # 生成查询嵌入
            query_embedding = await self.generate_embedding(query_text, use_cache=use_cache)

            if not query_embedding:
                return []

            # 生成候选文本嵌入
            candidate_embeddings = await self.batch_generate_embeddings(
                candidate_texts,
                use_cache=use_cache
            )

            if not candidate_embeddings:
                return []

            # 计算相似度
            similarities = []
            for i, candidate_embedding in enumerate(candidate_embeddings):
                similarity = await self.embedding_generator.calculate_similarity(
                    query_embedding, candidate_embedding
                )
                similarities.append((i, similarity, candidate_texts[i]))

            # 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)

            # 返回前top_k个结果
            return similarities[:top_k]

        except Exception as e:
            logger.error(f"查找相似文本失败: {str(e)}")
            return []

    async def get_embedding_stats(self) -> Dict[str, Any]:
        """获取嵌入统计信息"""
        return {
            'cache_size': len(self._cache),
            'cache_hit_rate': self._performance_metrics['cache_hits'] / max(1, self._performance_metrics['cache_hits'] + self._performance_metrics['cache_misses']),
            'total_embeddings_generated': self._performance_metrics['total_embeddings'],
            'average_embedding_time': self._performance_metrics['average_embedding_time'],
            'model_name': self.embedding_generator.model_name,
            'embedding_dimension': await self.embedding_generator.get_embedding_dimension(),
            'performance_metrics': self._performance_metrics,
            'timestamp': datetime.now().isoformat()
        }

    async def clear_cache(self) -> bool:
        """清空缓存"""
        try:
            self._cache.clear()
            self._cache_timestamps.clear()
            self._performance_metrics['cache_hits'] = 0
            self._performance_metrics['cache_misses'] = 0
            logger.info("向量化缓存已清空")
            return True
        except Exception as e:
            logger.error(f"清空缓存失败: {str(e)}")
            return False

    async def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            'cache_size': len(self._cache),
            'cache_hit_rate': self._performance_metrics['cache_hits'] / max(1, self._performance_metrics['cache_hits'] + self._performance_metrics['cache_misses']),
            'cache_ttl_seconds': settings.embedding_cache_ttl,
            'oldest_cache_entry': min(self._cache_timestamps.values()) if self._cache_timestamps else None,
            'newest_cache_entry': max(self._cache_timestamps.values()) if self._cache_timestamps else None,
            'timestamp': datetime.now().isoformat()
        }


# 全局向量化服务实例
vectorization_service = VectorizationService()


async def get_vectorization_service() -> VectorizationService:
    """获取向量化服务实例"""
    return vectorization_service