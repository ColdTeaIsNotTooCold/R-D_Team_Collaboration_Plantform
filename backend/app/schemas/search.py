from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime
from enum import Enum


class SearchType(str, Enum):
    """搜索类型"""
    KEYWORD = "keyword"      # 关键词搜索
    SEMANTIC = "semantic"    # 语义搜索
    HYBRID = "hybrid"        # 混合搜索


class SortOrder(str, Enum):
    """排序方式"""
    RELEVANCE = "relevance"  # 相关度
    DATE = "date"          # 时间
    TITLE = "title"        # 标题


class SearchQuery(BaseModel):
    """搜索查询参数"""
    query: str = Field(..., description="搜索查询字符串", min_length=1)
    search_type: SearchType = Field(default=SearchType.HYBRID, description="搜索类型")
    context_types: Optional[List[str]] = Field(default=None, description="限制上下文类型")
    task_id: Optional[int] = Field(default=None, description="限制任务ID")
    conversation_id: Optional[int] = Field(default=None, description="限制对话ID")
    sort_by: SortOrder = Field(default=SortOrder.RELEVANCE, description="排序方式")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页大小")
    min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="最小相关度分数")


class SearchResult(BaseModel):
    """搜索结果项"""
    id: int
    context_type: str
    title: str
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    score: float = Field(ge=0.0, le=1.0, description="相关度分数")
    highlights: List[str] = Field(default_factory=list, description="高亮文本片段")
    created_at: datetime
    task_id: Optional[int] = None
    conversation_id: Optional[int] = None


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[SearchResult]
    total: int
    page: int
    page_size: int
    total_pages: int
    query: str
    search_type: SearchType
    execution_time: float = Field(description="搜索执行时间（秒）")


class VectorSearchConfig(BaseModel):
    """向量搜索配置"""
    collection_name: str = Field(default="contexts", description="向量集合名称")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="嵌入模型")
    chunk_size: int = Field(default=1000, description="文档分块大小")
    chunk_overlap: int = Field(default=200, description="分块重叠大小")


class IndexDocument(BaseModel):
    """索引文档"""
    id: int
    content: str
    metadata: Dict[str, Any]
    context_type: str
    title: str


class BatchIndexRequest(BaseModel):
    """批量索引请求"""
    documents: List[IndexDocument]
    config: Optional[VectorSearchConfig] = None


class IndexResponse(BaseModel):
    """索引响应"""
    success: bool
    indexed_count: int
    failed_count: int
    errors: List[str] = Field(default_factory=list)