"""
RAG系统数据模式定义
定义RAG系统的Pydantic模型和数据结构
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class RetrievalStrategy(str, Enum):
    """检索策略枚举"""
    SEMANTIC_SEARCH = "semantic_search"
    HYBRID_SEARCH = "hybrid_search"
    MULTI_QUERY = "multi_query"
    QUERY_REFORMULATION = "query_reformulation"
    RERANKING = "reranking"


class ContextCompressionStrategy(str, Enum):
    """上下文压缩策略枚举"""
    NONE = "none"
    TRUNCATE = "truncate"
    SUMMARIZE = "summarize"
    KEY_EXTRACTION = "key_extraction"
    HIERARCHICAL = "hierarchical"


class ContextOptimization(str, Enum):
    """上下文优化策略枚举"""
    RELEVANCE_BASED = "relevance_based"
    DIVERSITY_BASED = "diversity_based"
    COVERAGE_BASED = "coverage_based"
    QUALITY_BASED = "quality_based"


class ScoringMethod(str, Enum):
    """评分方法枚举"""
    COSINE_SIMILARITY = "cosine_similarity"
    BM25 = "bm25"
    JACCARD = "jaccard"
    EDIT_DISTANCE = "edit_distance"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    HYBRID = "hybrid"


class PipelineStatus(str, Enum):
    """管道状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PromptTemplateType(str, Enum):
    """提示词模板类型枚举"""
    QA = "qa"
    SUMMARY = "summary"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    TRANSLATION = "translation"
    CODE = "code"
    CREATIVE = "creative"


class PromptRole(str, Enum):
    """提示词角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class RetrievedDocument(BaseModel):
    """检索到的文档模型"""
    id: str = Field(..., description="文档ID")
    content: str = Field(..., description="文档内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="文档元数据")
    score: float = Field(..., ge=0.0, le=1.0, description="相似度分数")
    rank: int = Field(..., ge=1, description="排名")
    retrieval_method: str = Field(..., description="检索方法")
    timestamp: datetime = Field(default_factory=datetime.now, description="检索时间")

    @validator('content')
    def validate_content(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("文档内容不能为空")
        return v


class ContextWindow(BaseModel):
    """上下文窗口模型"""
    content: str = Field(..., description="上下文内容")
    documents: List[RetrievedDocument] = Field(..., description="包含的文档")
    total_tokens: int = Field(..., ge=0, description="总token数")
    window_size: int = Field(..., ge=0, description="窗口大小")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    compression_ratio: float = Field(default=1.0, ge=0.0, description="压缩比例")
    optimization_score: float = Field(default=0.0, ge=0.0, le=1.0, description="优化分数")


class RenderedPrompt(BaseModel):
    """渲染后的提示词模型"""
    content: str = Field(..., description="提示词内容")
    role: PromptRole = Field(..., description="角色")
    template_id: str = Field(..., description="模板ID")
    variables: Dict[str, Any] = Field(..., description="变量值")
    tokens: int = Field(..., ge=0, description="token数量")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class LLMResponse(BaseModel):
    """LLM响应模型"""
    content: str = Field(..., description="响应内容")
    model: str = Field(..., description="使用的模型")
    total_tokens: int = Field(..., ge=0, description="总token数")
    prompt_tokens: int = Field(..., ge=0, description="提示词token数")
    completion_tokens: int = Field(..., ge=0, description="补全token数")
    cost: float = Field(default=0.0, ge=0.0, description="成本")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class PipelineMetrics(BaseModel):
    """管道指标模型"""
    total_time: float = Field(default=0.0, ge=0.0, description="总耗时")
    retrieval_time: float = Field(default=0.0, ge=0.0, description="检索耗时")
    context_building_time: float = Field(default=0.0, ge=0.0, description="上下文构建耗时")
    prompt_generation_time: float = Field(default=0.0, ge=0.0, description="提示词生成耗时")
    llm_inference_time: float = Field(default=0.0, ge=0.0, description="LLM推理耗时")
    response_processing_time: float = Field(default=0.0, ge=0.0, description="响应处理耗时")
    documents_retrieved: int = Field(default=0, ge=0, description="检索的文档数")
    tokens_used: int = Field(default=0, ge=0, description="使用的token数")
    cache_hits: int = Field(default=0, ge=0, description="缓存命中次数")
    error_count: int = Field(default=0, ge=0, description="错误次数")
    success_count: int = Field(default=0, ge=0, description="成功次数")


class PipelineResult(BaseModel):
    """管道结果模型"""
    query: str = Field(..., description="查询内容")
    response: str = Field(..., description="响应内容")
    documents: List[RetrievedDocument] = Field(..., description="检索的文档")
    context_window: Optional[ContextWindow] = Field(None, description="上下文窗口")
    prompt: Optional[RenderedPrompt] = Field(None, description="提示词")
    llm_response: Optional[LLMResponse] = Field(None, description="LLM响应")
    metrics: PipelineMetrics = Field(..., description="管道指标")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    status: PipelineStatus = Field(..., description="状态")
    error_message: Optional[str] = Field(None, description="错误信息")


class DocumentScore(BaseModel):
    """文档评分模型"""
    document_id: str = Field(..., description="文档ID")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="总体分数")
    component_scores: Dict[str, float] = Field(..., description="组件分数")
    quality_metrics: Dict[str, float] = Field(..., description="质量指标")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    ranking_factors: Dict[str, Any] = Field(..., description="排序因子")
    timestamp: datetime = Field(default_factory=datetime.now, description="评分时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class ScoringResult(BaseModel):
    """评分结果模型"""
    query: str = Field(..., description="查询内容")
    documents: List[RetrievedDocument] = Field(..., description="文档列表")
    scores: List[DocumentScore] = Field(..., description="评分结果")
    ranking: List[int] = Field(..., description="排序结果")
    performance_metrics: Dict[str, Any] = Field(..., description="性能指标")
    timestamp: datetime = Field(default_factory=datetime.now, description="评分时间")


class PromptTemplate(BaseModel):
    """提示词模板模型"""
    id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    type: PromptTemplateType = Field(..., description="模板类型")
    template: str = Field(..., description="模板内容")
    description: str = Field(default="", description="模板描述")
    variables: List[str] = Field(default_factory=list, description="变量列表")
    version: str = Field(default="1.0", description="版本")
    author: str = Field(default="system", description="作者")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    is_active: bool = Field(default=True, description="是否激活")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    @validator('template')
    def validate_template(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("模板内容不能为空")
        return v


class PromptVariable(BaseModel):
    """提示词变量模型"""
    name: str = Field(..., description="变量名称")
    type: str = Field(..., description="变量类型")
    description: str = Field(default="", description="变量描述")
    required: bool = Field(default=True, description="是否必需")
    default_value: Any = Field(None, description="默认值")
    validation_rules: Dict[str, Any] = Field(default_factory=dict, description="验证规则")


class RetrievalConfig(BaseModel):
    """检索配置模型"""
    strategy: RetrievalStrategy = Field(default=RetrievalStrategy.SEMANTIC_SEARCH, description="检索策略")
    max_results: int = Field(default=10, ge=1, le=100, description="最大结果数")
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="分数阈值")
    diversity_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="多样性阈值")
    reranking_enabled: bool = Field(default=True, description="是否启用重排序")
    context_window_size: int = Field(default=4000, ge=100, description="上下文窗口大小")
    enable_query_expansion: bool = Field(default=True, description="是否启用查询扩展")
    enable_fallback: bool = Field(default=True, description="是否启用回退")


class ContextConfig(BaseModel):
    """上下文配置模型"""
    max_context_length: int = Field(default=4000, ge=100, description="最大上下文长度")
    compression_strategy: ContextCompressionStrategy = Field(default=ContextCompressionStrategy.TRUNCATE, description="压缩策略")
    optimization_strategy: ContextOptimization = Field(default=ContextOptimization.RELEVANCE_BASED, description="优化策略")
    enable_deduplication: bool = Field(default=True, description="是否启用去重")
    enable_context_windowing: bool = Field(default=True, description="是否启用上下文窗口")
    enable_semantic_clustering: bool = Field(default=True, description="是否启用语义聚类")
    min_document_score: float = Field(default=0.5, ge=0.0, le=1.0, description="最小文档分数")
    max_documents: int = Field(default=10, ge=1, le=50, description="最大文档数")
    context_buffer_ratio: float = Field(default=0.1, ge=0.0, le=0.5, description="上下文缓冲比例")


class PipelineConfig(BaseModel):
    """管道配置模型"""
    retrieval_config: RetrievalConfig = Field(default_factory=RetrievalConfig, description="检索配置")
    context_config: ContextConfig = Field(default_factory=ContextConfig, description="上下文配置")
    max_total_tokens: int = Field(default=8000, ge=1000, description="最大总token数")
    enable_caching: bool = Field(default=True, description="是否启用缓存")
    enable_monitoring: bool = Field(default=True, description="是否启用监控")
    timeout: int = Field(default=30, ge=5, le=300, description="超时时间")
    max_retries: int = Field(default=3, ge=0, le=10, description="最大重试次数")
    enable_fallback: bool = Field(default=True, description="是否启用回退")
    enable_parallel_processing: bool = Field(default=True, description="是否启用并行处理")


class ScoringConfig(BaseModel):
    """评分配置模型"""
    primary_method: ScoringMethod = Field(default=ScoringMethod.HYBRID, description="主要评分方法")
    secondary_methods: List[ScoringMethod] = Field(default_factory=list, description="次要评分方法")
    weights: Dict[str, float] = Field(default_factory=dict, description="权重配置")
    enable_quality_metrics: bool = Field(default=True, description="是否启用质量指标")
    enable_temporal_decay: bool = Field(default=True, description="是否启用时间衰减")
    decay_factor: float = Field(default=0.95, ge=0.0, le=1.0, description="衰减因子")
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0, description="最小置信度")
    max_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="最大置信度")


class RAGSystemConfig(BaseModel):
    """RAG系统配置模型"""
    # 检索配置
    retrieval_strategy: str = Field(default="semantic_search", description="检索策略")
    retrieval_max_results: int = Field(default=10, ge=1, le=100, description="检索最大结果数")
    retrieval_score_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="检索分数阈值")
    retrieval_enable_fallback: bool = Field(default=True, description="是否启用检索回退")

    # 上下文配置
    context_max_length: int = Field(default=4000, ge=100, description="上下文最大长度")
    context_compression_strategy: str = Field(default="truncate", description="上下文压缩策略")
    context_optimization_strategy: str = Field(default="relevance_based", description="上下文优化策略")
    context_enable_deduplication: bool = Field(default=True, description="是否启用上下文去重")
    context_enable_semantic_clustering: bool = Field(default=True, description="是否启用语义聚类")

    # 管道配置
    pipeline_max_tokens: int = Field(default=8000, ge=1000, description="管道最大token数")
    pipeline_enable_caching: bool = Field(default=True, description="是否启用管道缓存")
    pipeline_enable_monitoring: bool = Field(default=True, description="是否启用管道监控")
    pipeline_timeout: int = Field(default=30, ge=5, le=300, description="管道超时时间")
    pipeline_max_retries: int = Field(default=3, ge=0, le=10, description="管道最大重试次数")

    # 评分配置
    scoring_primary_method: str = Field(default="hybrid", description="主要评分方法")
    scoring_enable_quality_metrics: bool = Field(default=True, description="是否启用质量指标")
    scoring_enable_temporal_decay: bool = Field(default=True, description="是否启用时间衰减")
    scoring_min_confidence: float = Field(default=0.3, ge=0.0, le=1.0, description="最小置信度")

    # 模型配置
    default_model: str = Field(default="gpt-3.5-turbo", description="默认模型")
    fallback_model: str = Field(default="claude-3-haiku-20240307", description="回退模型")


class SystemInfo(BaseModel):
    """系统信息模型"""
    initialized: bool = Field(..., description="是否已初始化")
    config: Dict[str, Any] = Field(..., description="系统配置")
    performance_metrics: Dict[str, Any] = Field(..., description="性能指标")
    component_status: Dict[str, Any] = Field(..., description="组件状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="信息时间")


class HealthStatus(BaseModel):
    """健康状态模型"""
    status: str = Field(..., description="整体状态")
    components: Dict[str, Any] = Field(..., description="组件状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., min_length=1, max_length=2000, description="用户查询内容")
    model: Optional[str] = Field(None, description="使用的模型")
    pipeline: Optional[str] = Field(None, description="使用的管道名称")
    max_tokens: Optional[int] = Field(2000, ge=1, le=8000, description="最大生成token数")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="生成温度")


class BatchQueryRequest(BaseModel):
    """批量查询请求模型"""
    queries: List[str] = Field(..., min_items=1, max_items=50, description="查询列表")
    model: Optional[str] = Field(None, description="使用的模型")
    pipeline: Optional[str] = Field(None, description="使用的管道名称")
    max_tokens: Optional[int] = Field(2000, ge=1, le=8000, description="最大生成token数")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="生成温度")


class DocumentAddRequest(BaseModel):
    """文档添加请求模型"""
    documents: List[str] = Field(..., min_items=1, max_items=1000, description="文档内容列表")
    metadatas: Optional[List[Dict[str, Any]]] = Field(None, description="文档元数据列表")
    collection_name: Optional[str] = Field(None, description="目标集合名称")

    @validator('documents')
    def validate_documents(cls, v):
        for doc in v:
            if len(doc.strip()) == 0:
                raise ValueError("文档内容不能为空")
        return v

    @validator('metadatas')
    def validate_metadatas(cls, v, values):
        if v is not None and 'documents' in values:
            if len(v) != len(values['documents']):
                raise ValueError("元数据列表长度必须与文档列表长度相同")
        return v


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., min_length=1, max_length=1000, description="搜索查询")
    n_results: int = Field(10, ge=1, le=100, description="返回结果数量")
    score_threshold: float = Field(0.5, ge=0.0, le=1.0, description="分数阈值")
    collection_name: Optional[str] = Field(None, description="搜索集合名称")


class PipelineCreateRequest(BaseModel):
    """管道创建请求模型"""
    name: str = Field(..., min_length=1, max_length=50, description="管道名称")
    retrieval_strategy: str = Field("semantic_search", description="检索策略")
    retrieval_max_results: int = Field(10, ge=1, le=100, description="检索最大结果数")
    retrieval_score_threshold: float = Field(0.7, ge=0.0, le=1.0, description="检索分数阈值")
    context_max_length: int = Field(4000, ge=100, description="上下文最大长度")
    context_compression_strategy: str = Field("truncate", description="上下文压缩策略")
    enable_caching: bool = Field(True, description="启用缓存")
    timeout: int = Field(30, ge=5, le=300, description="超时时间")


class QueryResponse(BaseModel):
    """查询响应模型"""
    query: str = Field(..., description="查询内容")
    response: str = Field(..., description="响应内容")
    documents: List[Dict[str, Any]] = Field(..., description="检索的文档")
    metrics: Dict[str, Any] = Field(..., description="性能指标")
    status: str = Field(..., description="状态")
    processing_time: float = Field(..., ge=0.0, description="处理时间")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")


class BatchQueryResponse(BaseModel):
    """批量查询响应模型"""
    results: List[QueryResponse] = Field(..., description="查询结果列表")
    total_count: int = Field(..., ge=0, description="总查询数")
    processing_time: float = Field(..., ge=0.0, description="总处理时间")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")