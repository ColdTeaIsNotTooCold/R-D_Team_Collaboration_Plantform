"""
向量数据库相关的Pydantic模型
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentAddRequest(BaseModel):
    """添加文档请求"""
    documents: List[str] = Field(..., description="文档内容列表")
    metadatas: Optional[List[Dict[str, Any]]] = Field(None, description="文档元数据")
    ids: Optional[List[str]] = Field(None, description="文档ID列表")

    class Config:
        schema_extra = {
            "example": {
                "documents": [
                    "这是第一个文档的内容",
                    "这是第二个文档的内容"
                ],
                "metadatas": [
                    {"source": "document1.txt", "type": "text"},
                    {"source": "document2.txt", "type": "text"}
                ],
                "ids": ["doc1", "doc2"]
            }
        }


class DocumentAddResponse(BaseModel):
    """添加文档响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    document_count: int = Field(..., description="添加的文档数量")


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索查询")
    n_results: int = Field(5, description="返回结果数量", ge=1, le=100)
    where: Optional[Dict[str, Any]] = Field(None, description="元数据过滤条件")
    where_document: Optional[Dict[str, Any]] = Field(None, description="文档内容过滤条件")

    class Config:
        schema_extra = {
            "example": {
                "query": "团队协作平台的功能",
                "n_results": 5,
                "where": {"type": "documentation"}
            }
        }


class SearchResult(BaseModel):
    """搜索结果"""
    document: str = Field(..., description="文档内容")
    metadata: Dict[str, Any] = Field(..., description="文档元数据")
    id: str = Field(..., description="文档ID")
    distance: float = Field(..., description="距离分数")


class SearchResponse(BaseModel):
    """搜索响应"""
    success: bool = Field(..., description="是否成功")
    results: List[SearchResult] = Field(..., description="搜索结果")
    query: str = Field(..., description="原始查询")
    result_count: int = Field(..., description="结果数量")


class DocumentDeleteRequest(BaseModel):
    """删除文档请求"""
    ids: List[str] = Field(..., description="要删除的文档ID列表")

    class Config:
        schema_extra = {
            "example": {
                "ids": ["doc1", "doc2"]
            }
        }


class DocumentDeleteResponse(BaseModel):
    """删除文档响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    deleted_count: int = Field(..., description="删除的文档数量")


class DocumentUpdateRequest(BaseModel):
    """更新文档请求"""
    ids: List[str] = Field(..., description="要更新的文档ID列表")
    documents: Optional[List[str]] = Field(None, description="新的文档内容")
    metadatas: Optional[List[Dict[str, Any]]] = Field(None, description="新的元数据")

    class Config:
        schema_extra = {
            "example": {
                "ids": ["doc1"],
                "documents": ["更新后的文档内容"],
                "metadatas": [{"source": "updated.txt", "type": "text"}]
            }
        }


class DocumentUpdateResponse(BaseModel):
    """更新文档响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    updated_count: int = Field(..., description="更新的文档数量")


class CollectionInfo(BaseModel):
    """集合信息"""
    collection_name: str = Field(..., description="集合名称")
    document_count: int = Field(..., description="文档数量")
    initialized: bool = Field(..., description="是否已初始化")


class CollectionInfoResponse(BaseModel):
    """集合信息响应"""
    success: bool = Field(..., description="是否成功")
    collection_info: CollectionInfo = Field(..., description="集合信息")


class ClearCollectionResponse(BaseModel):
    """清空集合响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")


class EmbeddingRequest(BaseModel):
    """嵌入生成请求"""
    texts: List[str] = Field(..., description="要生成嵌入的文本列表")

    class Config:
        schema_extra = {
            "example": {
                "texts": [
                    "这是一个测试句子",
                    "这是另一个测试句子"
                ]
            }
        }


class EmbeddingResponse(BaseModel):
    """嵌入生成响应"""
    success: bool = Field(..., description="是否成功")
    embeddings: List[List[float]] = Field(..., description="生成的嵌入向量")
    dimension: int = Field(..., description="嵌入维度")


class SimilarityRequest(BaseModel):
    """相似度计算请求"""
    text1: str = Field(..., description="第一个文本")
    text2: str = Field(..., description="第二个文本")

    class Config:
        schema_extra = {
            "example": {
                "text1": "团队协作平台",
                "text2": "协作管理系统"
            }
        }


class SimilarityResponse(BaseModel):
    """相似度计算响应"""
    success: bool = Field(..., description="是否成功")
    similarity: float = Field(..., description="相似度分数")
    text1: str = Field(..., description="第一个文本")
    text2: str = Field(..., description="第二个文本")


class TextChunkRequest(BaseModel):
    """文本分块请求"""
    text: str = Field(..., description="要分块的文本")
    chunk_size: int = Field(512, description="块大小", ge=100, le=2000)
    chunk_overlap: int = Field(50, description="重叠大小", ge=0, le=200)

    class Config:
        schema_extra = {
            "example": {
                "text": "这是一个很长的文本内容...",
                "chunk_size": 512,
                "chunk_overlap": 50
            }
        }


class TextChunkResponse(BaseModel):
    """文本分块响应"""
    success: bool = Field(..., description="是否成功")
    chunks: List[str] = Field(..., description="分块结果")
    chunk_count: int = Field(..., description="块数量")
    original_length: int = Field(..., description="原始文本长度")