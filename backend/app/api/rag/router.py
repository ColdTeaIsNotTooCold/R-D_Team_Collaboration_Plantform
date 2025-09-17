"""
RAG API路由
提供RAG系统的REST API接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ...core.rag_pipeline import get_rag_system, RAGSystemConfig
from ...services.rag.pipeline import PipelineResult
from ...core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["RAG"])


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., description="用户查询内容", min_length=1, max_length=2000)
    model: Optional[str] = Field(None, description="使用的模型")
    pipeline: Optional[str] = Field(None, description="使用的管道名称")
    max_tokens: Optional[int] = Field(2000, description="最大生成token数")
    temperature: Optional[float] = Field(0.7, description="生成温度")


class BatchQueryRequest(BaseModel):
    """批量查询请求模型"""
    queries: List[str] = Field(..., description="查询列表", min_items=1, max_items=50)
    model: Optional[str] = Field(None, description="使用的模型")
    pipeline: Optional[str] = Field(None, description="使用的管道名称")
    max_tokens: Optional[int] = Field(2000, description="最大生成token数")
    temperature: Optional[float] = Field(0.7, description="生成温度")


class DocumentAddRequest(BaseModel):
    """文档添加请求模型"""
    documents: List[str] = Field(..., description="文档内容列表")
    metadatas: Optional[List[Dict[str, Any]]] = Field(None, description="文档元数据列表")
    collection_name: Optional[str] = Field(None, description="目标集合名称")


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索查询")
    n_results: int = Field(10, description="返回结果数量", ge=1, le=100)
    score_threshold: float = Field(0.5, description="分数阈值", ge=0.0, le=1.0)
    collection_name: Optional[str] = Field(None, description="搜索集合名称")


class PipelineCreateRequest(BaseModel):
    """管道创建请求模型"""
    name: str = Field(..., description="管道名称")
    retrieval_strategy: str = Field("semantic_search", description="检索策略")
    retrieval_max_results: int = Field(10, description="检索最大结果数")
    retrieval_score_threshold: float = Field(0.7, description="检索分数阈值")
    context_max_length: int = Field(4000, description="上下文最大长度")
    context_compression_strategy: str = Field("truncate", description="上下文压缩策略")
    enable_caching: bool = Field(True, description="启用缓存")
    timeout: int = Field(30, description="超时时间")


class ConfigUpdateRequest(BaseModel):
    """配置更新请求模型"""
    retrieval_strategy: str = Field("semantic_search", description="检索策略")
    retrieval_max_results: int = Field(10, description="检索最大结果数")
    retrieval_score_threshold: float = Field(0.7, description="检索分数阈值")
    context_max_length: int = Field(4000, description="上下文最大长度")
    context_compression_strategy: str = Field("truncate", description="上下文压缩策略")
    pipeline_max_tokens: int = Field(8000, description="管道最大token数")
    pipeline_enable_caching: bool = Field(True, description="启用管道缓存")
    scoring_primary_method: str = Field("hybrid", description="主要评分方法")
    default_model: str = Field("gpt-3.5-turbo", description="默认模型")


class QueryResponse(BaseModel):
    """查询响应模型"""
    query: str
    response: str
    documents: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    status: str
    processing_time: float
    timestamp: datetime


class BatchQueryResponse(BaseModel):
    """批量查询响应模型"""
    results: List[QueryResponse]
    total_count: int
    processing_time: float
    timestamp: datetime


class SystemInfoResponse(BaseModel):
    """系统信息响应模型"""
    initialized: bool
    config: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    component_status: Dict[str, Any]
    timestamp: datetime


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    components: Dict[str, Any]
    timestamp: datetime


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """执行RAG查询"""
    try:
        rag_system = await get_rag_system()

        start_time = datetime.now()
        result = await rag_system.query(
            query=request.query,
            model=request.model,
            pipeline_name=request.pipeline
        )
        processing_time = (datetime.now() - start_time).total_seconds()

        response = QueryResponse(
            query=result.query,
            response=result.response,
            documents=[
                {
                    "id": doc.id,
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "score": doc.score,
                    "rank": doc.rank
                }
                for doc in result.documents
            ],
            metrics={
                "total_time": result.metrics.total_time,
                "retrieval_time": result.metrics.retrieval_time,
                "context_building_time": result.metrics.context_building_time,
                "prompt_generation_time": result.metrics.prompt_generation_time,
                "llm_inference_time": result.metrics.llm_inference_time,
                "response_processing_time": result.metrics.response_processing_time,
                "documents_retrieved": result.metrics.documents_retrieved,
                "tokens_used": result.metrics.tokens_used
            },
            status=result.status.value,
            processing_time=processing_time,
            timestamp=datetime.now()
        )

        logger.info(f"用户 {current_user.get('username')} 执行RAG查询: {request.query[:50]}...")
        return response

    except Exception as e:
        logger.error(f"RAG查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/query/batch", response_model=BatchQueryResponse)
async def batch_query(
    request: BatchQueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """批量执行RAG查询"""
    try:
        rag_system = await get_rag_system()

        start_time = datetime.now()
        results = await rag_system.query_batch(
            queries=request.queries,
            model=request.model,
            pipeline_name=request.pipeline
        )
        processing_time = (datetime.now() - start_time).total_seconds()

        query_responses = []
        for i, result in enumerate(results):
            response = QueryResponse(
                query=result.query,
                response=result.response,
                documents=[
                    {
                        "id": doc.id,
                        "content": doc.content,
                        "metadata": doc.metadata,
                        "score": doc.score,
                        "rank": doc.rank
                    }
                    for doc in result.documents
                ],
                metrics={
                    "total_time": result.metrics.total_time,
                    "retrieval_time": result.metrics.retrieval_time,
                    "context_building_time": result.metrics.context_building_time,
                    "prompt_generation_time": result.metrics.prompt_generation_time,
                    "llm_inference_time": result.metrics.llm_inference_time,
                    "response_processing_time": result.metrics.response_processing_time,
                    "documents_retrieved": result.metrics.documents_retrieved,
                    "tokens_used": result.metrics.tokens_used
                },
                status=result.status.value,
                processing_time=0.0,  # 批量查询不计算单个处理时间
                timestamp=datetime.now()
            )
            query_responses.append(response)

        response = BatchQueryResponse(
            results=query_responses,
            total_count=len(results),
            processing_time=processing_time,
            timestamp=datetime.now()
        )

        logger.info(f"用户 {current_user.get('username')} 执行批量RAG查询，共 {len(request.queries)} 个查询")
        return response

    except Exception as e:
        logger.error(f"批量RAG查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量查询失败: {str(e)}")


@router.post("/documents", response_model=Dict[str, Any])
async def add_documents(
    request: DocumentAddRequest,
    current_user: dict = Depends(get_current_user)
):
    """添加文档到向量数据库"""
    try:
        rag_system = await get_rag_system()

        success = await rag_system.add_documents(
            documents=request.documents,
            metadatas=request.metadatas
        )

        if success:
            logger.info(f"用户 {current_user.get('username')} 添加了 {len(request.documents)} 个文档")
            return {
                "success": True,
                "message": f"成功添加 {len(request.documents)} 个文档",
                "document_count": len(request.documents)
            }
        else:
            raise HTTPException(status_code=500, detail="添加文档失败")

    except Exception as e:
        logger.error(f"添加文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加文档失败: {str(e)}")


@router.post("/search", response_model=List[Dict[str, Any]])
async def search_documents(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """搜索文档"""
    try:
        rag_system = await get_rag_system()

        results = await rag_system.search_documents(
            query=request.query,
            n_results=request.n_results
        )

        logger.info(f"用户 {current_user.get('username')} 搜索文档: {request.query[:50]}...")
        return results

    except Exception as e:
        logger.error(f"文档搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/system/info", response_model=SystemInfoResponse)
async def get_system_info(current_user: dict = Depends(get_current_user)):
    """获取系统信息"""
    try:
        rag_system = await get_rag_system()
        info = await rag_system.get_system_info()

        return SystemInfoResponse(
            initialized=info.get('initialized', False),
            config=info.get('config', {}),
            performance_metrics=info.get('performance_metrics', {}),
            component_status=info.get('component_status', {}),
            timestamp=datetime.now()
        )

    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")


@router.get("/system/metrics", response_model=Dict[str, Any])
async def get_performance_metrics(current_user: dict = Depends(get_current_user)):
    """获取性能指标"""
    try:
        rag_system = await get_rag_system()
        metrics = await rag_system.get_performance_metrics()
        return metrics

    except Exception as e:
        logger.error(f"获取性能指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取性能指标失败: {str(e)}")


@router.get("/system/health", response_model=HealthResponse)
async def health_check(current_user: dict = Depends(get_current_user)):
    """健康检查"""
    try:
        rag_system = await get_rag_system()
        health = await rag_system.health_check()

        return HealthResponse(
            status=health.get('status', 'unknown'),
            components=health.get('components', {}),
            timestamp=datetime.now()
        )

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return HealthResponse(
            status="error",
            components={"error": str(e)},
            timestamp=datetime.now()
        )


@router.post("/system/reset-metrics")
async def reset_metrics(current_user: dict = Depends(get_current_user)):
    """重置性能指标"""
    try:
        rag_system = await get_rag_system()
        await rag_system.reset_metrics()

        logger.info(f"用户 {current_user.get('username')} 重置了RAG系统性能指标")
        return {"success": True, "message": "性能指标已重置"}

    except Exception as e:
        logger.error(f"重置性能指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")


@router.post("/pipelines")
async def create_pipeline(
    request: PipelineCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """创建自定义管道"""
    try:
        rag_system = await get_rag_system()

        # 创建管道配置
        from ...services.rag.pipeline import PipelineConfig
        from ...services.rag.retrieval import RetrievalConfig, RetrievalStrategy
        from ...services.rag.context import ContextConfig, ContextCompressionStrategy

        pipeline_config = PipelineConfig(
            retrieval_config=RetrievalConfig(
                strategy=RetrievalStrategy(request.retrieval_strategy),
                max_results=request.retrieval_max_results,
                score_threshold=request.retrieval_score_threshold
            ),
            context_config=ContextConfig(
                max_context_length=request.context_max_length,
                compression_strategy=ContextCompressionStrategy(request.context_compression_strategy)
            ),
            enable_caching=request.enable_caching,
            timeout=request.timeout
        )

        # 创建管道
        pipeline = rag_system.pipeline_manager.create_pipeline(request.name, pipeline_config)

        logger.info(f"用户 {current_user.get('username')} 创建了RAG管道: {request.name}")
        return {
            "success": True,
            "message": f"管道 '{request.name}' 创建成功",
            "pipeline_name": request.name
        }

    except Exception as e:
        logger.error(f"创建管道失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建管道失败: {str(e)}")


@router.get("/pipelines")
async def list_pipelines(current_user: dict = Depends(get_current_user)):
    """列出所有管道"""
    try:
        rag_system = await get_rag_system()
        pipelines = rag_system.pipeline_manager.list_pipelines()

        return {
            "pipelines": pipelines,
            "count": len(pipelines),
            "default": rag_system.pipeline_manager._default_pipeline
        }

    except Exception as e:
        logger.error(f"获取管道列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取管道列表失败: {str(e)}")


@router.delete("/pipelines/{pipeline_name}")
async def delete_pipeline(
    pipeline_name: str,
    current_user: dict = Depends(get_current_user)
):
    """删除管道"""
    try:
        rag_system = await get_rag_system()

        success = rag_system.pipeline_manager.remove_pipeline(pipeline_name)
        if success:
            logger.info(f"用户 {current_user.get('username')} 删除了RAG管道: {pipeline_name}")
            return {"success": True, "message": f"管道 '{pipeline_name}' 删除成功"}
        else:
            raise HTTPException(status_code=404, detail=f"管道 '{pipeline_name}' 不存在")

    except Exception as e:
        logger.error(f"删除管道失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除管道失败: {str(e)}")


@router.put("/config")
async def update_config(
    request: ConfigUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """更新系统配置"""
    try:
        rag_system = await get_rag_system()

        # 创建新的配置对象
        new_config = RAGSystemConfig(
            retrieval_strategy=request.retrieval_strategy,
            retrieval_max_results=request.retrieval_max_results,
            retrieval_score_threshold=request.retrieval_score_threshold,
            context_max_length=request.context_max_length,
            context_compression_strategy=request.context_compression_strategy,
            pipeline_max_tokens=request.pipeline_max_tokens,
            pipeline_enable_caching=request.pipeline_enable_caching,
            scoring_primary_method=request.scoring_primary_method,
            default_model=request.default_model
        )

        rag_system.update_config(new_config)

        logger.info(f"用户 {current_user.get('username')} 更新了RAG系统配置")
        return {
            "success": True,
            "message": "配置更新成功",
            "config": new_config.get_config()
        }

    except Exception as e:
        logger.error(f"更新配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.get("/config")
async def get_config(current_user: dict = Depends(get_current_user)):
    """获取当前配置"""
    try:
        rag_system = await get_rag_system()
        config = rag_system.get_config()
        return config

    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/system/clear-cache")
async def clear_cache(current_user: dict = Depends(get_current_user)):
    """清理缓存"""
    try:
        rag_system = await get_rag_system()

        if rag_system.pipeline_manager:
            rag_system.pipeline_manager.clear_cache()
        if rag_system.context_manager:
            rag_system.context_manager.clear_cache()
        if rag_system.prompt_system:
            rag_system.prompt_system.renderer.clear_cache()

        logger.info(f"用户 {current_user.get('username')} 清理了RAG系统缓存")
        return {"success": True, "message": "缓存已清理"}

    except Exception as e:
        logger.error(f"清理缓存失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清理缓存失败: {str(e)}")


@router.get("/strategies")
async def get_retrieval_strategies(current_user: dict = Depends(get_current_user)):
    """获取可用的检索策略"""
    try:
        rag_system = await get_rag_system()
        if rag_system.retrieval_manager:
            strategies = await rag_system.retrieval_manager.get_retrieval_strategies()
            return strategies
        else:
            return []

    except Exception as e:
        logger.error(f"获取检索策略失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取检索策略失败: {str(e)}")


@router.get("/templates")
async def get_prompt_templates(
    template_type: Optional[str] = Query(None, description="模板类型"),
    current_user: dict = Depends(get_current_user)
):
    """获取提示词模板"""
    try:
        rag_system = await get_rag_system()
        if rag_system.prompt_system:
            from ...services.rag.prompts import PromptTemplateType
            template_type_enum = None
            if template_type:
                template_type_enum = PromptTemplateType(template_type)

            templates = rag_system.prompt_system.get_template_manager().list_templates(template_type_enum)
            return [
                {
                    "id": template.id,
                    "name": template.name,
                    "type": template.type.value,
                    "description": template.description,
                    "variables": template.variables,
                    "tags": template.tags,
                    "is_active": template.is_active
                }
                for template in templates
            ]
        else:
            return []

    except Exception as e:
        logger.error(f"获取提示词模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取提示词模板失败: {str(e)}")