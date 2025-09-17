"""
ChromaDB向量数据库管理模块
提供向量存储、检索和管理功能
"""
import chromadb
import logging
from typing import List, Dict, Any, Optional, Tuple
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
import asyncio
import time
from datetime import datetime
from ..core.config import settings

logger = logging.getLogger(__name__)


class VectorDBManager:
    """ChromaDB向量数据库管理器"""

    def __init__(self, collection_name: str = None):
        self.collection_name = collection_name or settings.vector_db_collection
        self.client = None
        self.collection = None
        self._initialized = False
        self._connection_pool = {}
        self._last_used = {}
        self._performance_metrics = {
            'total_queries': 0,
            'total_adds': 0,
            'total_searches': 0,
            'average_query_time': 0.0,
            'average_search_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }

    async def initialize(self) -> bool:
        """初始化ChromaDB连接"""
        try:
            start_time = time.time()

            # 配置ChromaDB客户端
            chroma_settings = ChromaSettings(
                chroma_db_impl=settings.vector_db_impl,
                persist_directory=settings.vector_db_path,
                anonymized_telemetry=False
            )

            # 创建客户端
            self.client = chromadb.Client(chroma_settings)

            # 获取或创建集合
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"已存在集合: {self.collection_name}")
            except Exception:
                self.collection = self.client.create_collection(name=self.collection_name)
                logger.info(f"创建新集合: {self.collection_name}")

            self._initialized = True
            init_time = time.time() - start_time
            logger.info(f"ChromaDB初始化成功，耗时: {init_time:.2f}秒")

            # 记录性能指标
            self._performance_metrics['total_queries'] += 1

            return True

        except Exception as e:
            logger.error(f"ChromaDB初始化失败: {str(e)}")
            return False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized and self.collection is not None

    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        batch_size: int = None
    ) -> bool:
        """添加文档到向量数据库"""
        if not self.is_initialized():
            logger.error("向量数据库未初始化")
            return False

        try:
            start_time = time.time()
            batch_size = batch_size or settings.vector_max_batch_size
            total_docs = len(documents)

            # 生成ID（如果未提供）
            if ids is None:
                ids = [f"doc_{int(time.time())}_{i}" for i in range(len(documents))]

            # 批量处理文档
            for i in range(0, len(documents), batch_size):
                batch_end = min(i + batch_size, len(documents))
                batch_documents = documents[i:batch_end]
                batch_metadatas = metadatas[i:batch_end] if metadatas else None
                batch_ids = ids[i:batch_end]

                # 添加文档
                self.collection.add(
                    documents=batch_documents,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )

                # 添加小延迟避免过载
                if batch_end < len(documents):
                    await asyncio.sleep(0.01)

            operation_time = time.time() - start_time

            # 更新性能指标
            self._performance_metrics['total_adds'] += 1
            avg_time = self._performance_metrics['average_query_time']
            self._performance_metrics['average_query_time'] = (avg_time * (self._performance_metrics['total_adds'] - 1) + operation_time) / self._performance_metrics['total_adds']

            logger.info(f"成功添加 {total_docs} 个文档到向量数据库，耗时: {operation_time:.2f}秒")
            return True

        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return False

    async def search(
        self,
        query: str,
        n_results: int = None,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        score_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        if not self.is_initialized():
            logger.error("向量数据库未初始化")
            return []

        try:
            start_time = time.time()
            n_results = n_results or settings.vector_search_top_k
            score_threshold = score_threshold or settings.vector_search_score_threshold

            # 执行搜索
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                where_document=where_document
            )

            # 格式化结果并过滤
            formatted_results = []
            for i in range(len(results['documents'][0])):
                distance = results['distances'][0][i] if 'distances' in results else 0.0
                score = 1.0 - distance  # 转换距离为相似度分数

                # 应用分数阈值过滤
                if score >= score_threshold:
                    result = {
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'id': results['ids'][0][i],
                        'distance': distance,
                        'score': score,
                        'rank': i + 1
                    }
                    formatted_results.append(result)

            operation_time = time.time() - start_time

            # 更新性能指标
            self._performance_metrics['total_searches'] += 1
            avg_time = self._performance_metrics['average_search_time']
            self._performance_metrics['average_search_time'] = (avg_time * (self._performance_metrics['total_searches'] - 1) + operation_time) / self._performance_metrics['total_searches']

            logger.info(f"搜索查询 '{query}' 返回 {len(formatted_results)} 个结果，耗时: {operation_time:.3f}秒")
            return formatted_results

        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return []

    async def delete_documents(self, ids: List[str]) -> bool:
        """删除文档"""
        if not self.is_initialized():
            logger.error("向量数据库未初始化")
            return False

        try:
            self.collection.delete(ids=ids)
            logger.info(f"成功删除 {len(ids)} 个文档")
            return True

        except Exception as e:
            logger.error(f"删除文档失败: {str(e)}")
            return False

    async def update_documents(
        self,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """更新文档"""
        if not self.is_initialized():
            logger.error("向量数据库未初始化")
            return False

        try:
            update_kwargs = {}
            if documents:
                update_kwargs['documents'] = documents
            if metadatas:
                update_kwargs['metadatas'] = metadatas

            self.collection.update(ids=ids, **update_kwargs)
            logger.info(f"成功更新 {len(ids)} 个文档")
            return True

        except Exception as e:
            logger.error(f"更新文档失败: {str(e)}")
            return False

    async def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        if not self.is_initialized():
            return {}

        try:
            count = self.collection.count()
            return {
                'collection_name': self.collection_name,
                'document_count': count,
                'initialized': self._initialized,
                'performance_metrics': self._performance_metrics,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取集合信息失败: {str(e)}")
            return {}

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            'metrics': self._performance_metrics,
            'collection_name': self.collection_name,
            'timestamp': datetime.now().isoformat()
        }

    async def reset_performance_metrics(self) -> bool:
        """重置性能指标"""
        try:
            self._performance_metrics = {
                'total_queries': 0,
                'total_adds': 0,
                'total_searches': 0,
                'average_query_time': 0.0,
                'average_search_time': 0.0,
                'cache_hits': 0,
                'cache_misses': 0
            }
            logger.info("性能指标已重置")
            return True
        except Exception as e:
            logger.error(f"重置性能指标失败: {str(e)}")
            return False

    async def batch_search(
        self,
        queries: List[str],
        n_results: int = None,
        where: Optional[Dict[str, Any]] = None,
        batch_size: int = 10
    ) -> List[List[Dict[str, Any]]]:
        """批量搜索"""
        if not self.is_initialized():
            logger.error("向量数据库未初始化")
            return []

        try:
            start_time = time.time()
            all_results = []

            # 分批处理查询
            for i in range(0, len(queries), batch_size):
                batch_queries = queries[i:i + batch_size]
                batch_results = []

                for query in batch_queries:
                    results = await self.search(
                        query=query,
                        n_results=n_results,
                        where=where
                    )
                    batch_results.append(results)

                all_results.extend(batch_results)

                # 添加小延迟避免过载
                if i + batch_size < len(queries):
                    await asyncio.sleep(0.01)

            operation_time = time.time() - start_time
            logger.info(f"批量搜索 {len(queries)} 个查询完成，耗时: {operation_time:.2f}秒")
            return all_results

        except Exception as e:
            logger.error(f"批量搜索失败: {str(e)}")
            return []

    async def optimize_collection(self) -> bool:
        """优化集合性能"""
        if not self.is_initialized():
            return False

        try:
            # 强制持久化数据
            if hasattr(self.client, 'persist'):
                self.client.persist()

            logger.info("向量数据库集合优化完成")
            return True

        except Exception as e:
            logger.error(f"优化集合失败: {str(e)}")
            return False

    async def clear_collection(self) -> bool:
        """清空集合"""
        if not self.is_initialized():
            return False

        try:
            # 获取所有文档ID
            results = self.collection.get()
            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info("成功清空集合")
            return True

        except Exception as e:
            logger.error(f"清空集合失败: {str(e)}")
            return False


# 全局向量数据库管理器实例
vector_db_manager = VectorDBManager()


async def get_vector_db() -> VectorDBManager:
    """获取向量数据库管理器实例"""
    return vector_db_manager