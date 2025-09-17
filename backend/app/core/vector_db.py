"""
ChromaDB向量数据库管理模块
提供向量存储、检索和管理功能
"""
import chromadb
import logging
from typing import List, Dict, Any, Optional, Tuple
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from ..core.config import settings

logger = logging.getLogger(__name__)


class VectorDBManager:
    """ChromaDB向量数据库管理器"""

    def __init__(self, collection_name: str = "team_collaboration"):
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化ChromaDB连接"""
        try:
            # 配置ChromaDB客户端
            chroma_settings = ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory="./chroma_db"
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
            logger.info("ChromaDB初始化成功")
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
        ids: Optional[List[str]] = None
    ) -> bool:
        """添加文档到向量数据库"""
        if not self.is_initialized():
            logger.error("向量数据库未初始化")
            return False

        try:
            # 生成ID（如果未提供）
            if ids is None:
                ids = [f"doc_{i}" for i in range(len(documents))]

            # 添加文档
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"成功添加 {len(documents)} 个文档到向量数据库")
            return True

        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return False

    async def search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        if not self.is_initialized():
            logger.error("向量数据库未初始化")
            return []

        try:
            # 执行搜索
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                where_document=where_document
            )

            # 格式化结果
            formatted_results = []
            for i in range(len(results['documents'][0])):
                result = {
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'id': results['ids'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else 0.0
                }
                formatted_results.append(result)

            logger.info(f"搜索查询 '{query}' 返回 {len(formatted_results)} 个结果")
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
                'initialized': self._initialized
            }
        except Exception as e:
            logger.error(f"获取集合信息失败: {str(e)}")
            return {}

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