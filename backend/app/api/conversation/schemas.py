"""
对话管理API模式定义
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# 基础模式
class ConversationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="对话标题")
    description: Optional[str] = Field(None, description="对话描述")
    model: Optional[str] = Field(None, description="使用的模型")
    system_prompt: Optional[str] = Field(None, description="系统提示")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="生成温度")
    max_tokens: int = Field(2000, ge=1, le=8000, description="最大token数")
    top_p: float = Field(1.0, ge=0.0, le=1.0, description="Top-p采样")
    context_length: int = Field(50, ge=1, le=200, description="上下文长度")
    max_context_tokens: int = Field(4000, ge=1000, le=16000, description="最大上下文token数")
    context_compression: str = Field("truncate", description="上下文压缩策略")
    auto_save_context: bool = Field(True, description="自动保存上下文")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class ConversationCreate(ConversationBase):
    session_id: Optional[str] = Field(None, description="会话ID")


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None)
    model: Optional[str] = Field(None)
    system_prompt: Optional[str] = Field(None)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=8000)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    context_length: Optional[int] = Field(None, ge=1, le=200)
    max_context_tokens: Optional[int] = Field(None, ge=1000, le=16000)
    context_compression: Optional[str] = Field(None)
    auto_save_context: Optional[bool] = Field(None)
    is_active: Optional[bool] = Field(None)
    is_pinned: Optional[bool] = Field(None)
    is_archived: Optional[bool] = Field(None)
    tags: Optional[List[str]] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)


class ConversationResponse(ConversationBase):
    id: int
    user_id: int
    session_id: Optional[str]
    is_active: bool
    is_pinned: bool
    is_archived: bool
    message_count: int
    total_tokens: int
    total_cost: float
    average_latency: float
    created_at: datetime
    updated_at: Optional[datetime]
    last_message_at: datetime

    class Config:
        from_attributes = True


# 消息模式
class MessageBase(BaseModel):
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class MessageCreate(MessageBase):
    conversation_id: int
    context_id: Optional[int] = Field(None, description="关联的上下文ID")


class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    user_id: int
    sequence: int
    is_visible: bool
    is_edited: bool
    is_deleted: bool
    model: Optional[str]
    provider: Optional[str]
    tokens: Optional[int]
    cost: float
    latency: float
    finish_reason: Optional[str]
    parent_id: Optional[int]
    batch_id: Optional[str]
    group_id: Optional[str]
    feedback: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# 会话模式
class SessionBase(BaseModel):
    title: Optional[str] = Field(None, description="会话标题")
    model: Optional[str] = Field(None, description="使用的模型")
    system_prompt: Optional[str] = Field(None, description="系统提示")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="生成温度")
    max_tokens: int = Field(2000, ge=1, le=8000, description="最大token数")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class SessionCreate(SessionBase):
    session_id: Optional[str] = Field(None, description="会话ID")
    user_agent: Optional[str] = Field(None, description="用户代理")
    ip_address: Optional[str] = Field(None, description="IP地址")


class SessionUpdate(BaseModel):
    title: Optional[str] = Field(None)
    model: Optional[str] = Field(None)
    system_prompt: Optional[str] = Field(None)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=8000)
    metadata: Optional[Dict[str, Any]] = Field(None)


class SessionResponse(SessionBase):
    id: int
    session_id: str
    user_id: Optional[int]
    conversation_id: Optional[int]
    is_active: bool
    created_at: datetime
    last_activity: datetime
    expires_at: Optional[datetime]
    message_count: int
    total_tokens: int
    total_cost: float
    user_agent: Optional[str]
    ip_address: Optional[str]

    class Config:
        from_attributes = True


# 对话处理模式
class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    conversation_id: int = Field(..., description="对话ID")
    message: str = Field(..., description="用户消息")
    mode: str = Field("hybrid", description="响应模式: chat_only, rag_enhanced, hybrid")
    max_tokens: int = Field(2000, ge=1, le=8000, description="最大token数")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="生成温度")
    enable_context: bool = Field(True, description="启用上下文")
    enable_rag: bool = Field(True, description="启用RAG")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class ChatResponse(BaseModel):
    content: str = Field(..., description="响应内容")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="RAG来源")
    context_messages: List[Dict[str, Any]] = Field(default_factory=list, description="上下文消息")
    usage: Dict[str, Any] = Field(default_factory=dict, description="使用统计")
    cost: float = Field(0.0, description="成本")
    latency: float = Field(0.0, description="延迟")
    mode: str = Field(..., description="响应模式")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


# 上下文管理模式
class ContextOptimizeRequest(BaseModel):
    max_tokens: int = Field(4000, ge=1000, le=16000, description="最大token数")
    compression_strategy: str = Field("truncate", description="压缩策略")
    include_system_prompt: bool = Field(True, description="包含系统提示")
    context_priority_rules: Optional[Dict[str, Any]] = Field(None, description="优先级规则")


class ContextOptimizeResponse(BaseModel):
    conversation_id: int
    messages: List[Dict[str, Any]]
    total_tokens: int
    max_tokens: int
    compression_strategy: str
    optimization_metadata: Dict[str, Any]


class CompressionRequest(BaseModel):
    max_tokens: int = Field(4000, ge=1000, le=16000, description="最大token数")
    compression_type: str = Field("truncate", description="压缩类型")


class CompressionResponse(BaseModel):
    original_token_count: int
    compressed_token_count: int
    compression_ratio: float
    strategy_used: str
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any]


# 搜索和统计模式
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200, description="搜索查询")
    skip: int = Field(0, ge=0, description="跳过数量")
    limit: int = Field(20, ge=1, le=100, description="返回数量")


class SearchResult(BaseModel):
    conversation: ConversationResponse
    relevance_score: float
    matched_messages: List[MessageResponse]


class StatsResponse(BaseModel):
    total_conversations: int
    active_conversations: int
    total_messages: int
    total_cost: float
    total_tokens: int
    average_latency: float
    period_days: int


class HealthCheckResponse(BaseModel):
    conversation_id: int
    health_score: float
    check_time: str
    metrics: Dict[str, Any]
    recommendations: List[str]


# 批量操作模式
class BatchMessageCreate(BaseModel):
    conversation_id: int
    messages: List[MessageBase]
    metadata: Optional[Dict[str, Any]] = Field(None, description="批量元数据")


class BatchMessageResponse(BaseModel):
    success_count: int
    failed_count: int
    messages: List[MessageResponse]
    errors: List[str]


# 导出模式
class ConversationExportRequest(BaseModel):
    format: str = Field("json", description="导出格式: json, txt, markdown")
    include_metadata: bool = Field(True, description="包含元数据")
    include_deleted: bool = Field(False, description="包含已删除消息")
    message_limit: Optional[int] = Field(None, description="消息数量限制")


class ExportResponse(BaseModel):
    content: str
    format: str
    filename: str
    size_bytes: int
    export_time: datetime