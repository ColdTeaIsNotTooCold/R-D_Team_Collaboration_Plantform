"""
向量数据库API路由
提供向量数据库管理、搜索优化和批量处理功能
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime

from ...core.vector_db import get_vector_db
from ...services.vectorization import get_vectorization_service, get_batch_processor, get_search_optimizer
from ...api.deps import get_current_active_user
from ...schemas.vector import (
    DocumentAddRequest,
    DocumentAddResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    DocumentDeleteRequest,
    DocumentDeleteResponse,
    DocumentUpdateRequest,
    DocumentUpdateResponse,
    CollectionInfoResponse,
    CollectionInfo,
    ClearCollectionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    SimilarityRequest,
    SimilarityResponse,
    TextChunkRequest,
    TextChunkResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ===== 文档管理API =====

@router.post("/documents/batch-add", response_model=DocumentAddResponse)
async def batch_add_documents(
    request: DocumentAddRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user)
):
    """批量添加文档到向量数据库"""
    try:
        vector_db = await get_vector_db()

        if not request.documents:
            raise HTTPException(
                status_code=400,
                detail="文档列表不能为空"
            )

        # 添加用户信息到元数据
        enhanced_metadatas = []
        if request.metadatas:
            for metadata in request.metadatas:
                enhanced_metadata = metadata.copy()
                enhanced_metadata['created_by'] = current_user.get('username', 'unknown')
                enhanced_metadata['created_at'] = datetime.now().isoformat()
                enhanced_metadata['batch_id'] = f"batch_{int(datetime.now().timestamp())}"
                enhanced_metadatas.append(enhanced_metadata)
        else:
            enhanced_metadatas = None

        # 后台任务处理批量添加
        background_tasks.add_task(
            _background_batch_add_documents,
            vector_db,
            request.documents,
            enhanced_metadatas,
            request.ids
        )

        return DocumentAddResponse(
            success=True,
            message="批量添加文档任务已提交",
            document_count=len(request.documents)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量添加文档失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"批量添加文档失败: {str(e)}"
        )


@router.post("/search/optimized", response_model=SearchResponse)
async def optimized_search(
    request: SearchRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """优化的向量搜索"""
    try:
        search_optimizer = await get_search_optimizer()

        results = await search_optimizer.optimized_search(
            query=request.query,
            n_results=request.n_results,
            where=request.where,
            where_document=request.where_document,
            use_cache=True
        )

        # 格式化结果
        search_results = []
        for result in results:
            search_result = SearchResult(
                document=result['document'],
                metadata=result['metadata'],
                id=result['id'],
                distance=result.get('distance', 0.0)
            )
            search_results.append(search_result)

        return SearchResponse(
            success=True,
            results=search_results,
            query=request.query,
            result_count=len(search_results)
        )

    except Exception as e:
        logger.error(f"优化搜索失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"优化搜索失败: {str(e)}"
        )


@router.post("/search/batch", response_model=List[SearchResponse])
async def batch_search(
    queries: List[str],
    n_results: int = 5,
    where: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """批量向量搜索"""
    try:
        search_optimizer = await get_search_optimizer()

        all_results = await search_optimizer.batch_optimized_search(
            queries=queries,
            n_results=n_results,
            where=where
        )

        # 格式化结果
        responses = []
        for i, results in enumerate(all_results):
            search_results = []
            for result in results:
                search_result = SearchResult(
                    document=result['document'],
                    metadata=result['metadata'],
                    id=result['id'],
                    distance=result.get('distance', 0.0)
                )
                search_results.append(search_result)

            response = SearchResponse(
                success=True,
                results=search_results,
                query=queries[i],
                result_count=len(search_results)
            )
            responses.append(response)

        return responses

    except Exception as e:
        logger.error(f"批量搜索失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"批量搜索失败: {str(e)}"
        )


# ===== 向量化服务API =====

@router.post("/vectorization/generate", response_model=EmbeddingResponse)
async def generate_embeddings(
    request: EmbeddingRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """生成文本嵌入"""
    try:
        vectorization_service = await get_vectorization_service()

        if not request.texts:
            raise HTTPException(
                status_code=400,
                detail="文本列表不能为空"
            )

        embeddings = await vectorization_service.batch_generate_embeddings(
            texts=request.texts,
            use_cache=True
        )

        dimension = len(embeddings[0]) if embeddings else 0

        return EmbeddingResponse(
            success=True,
            embeddings=embeddings,
            dimension=dimension
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成嵌入失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"生成嵌入失败: {str(e)}"
        )


@router.post("/vectorization/document", response_model=Dict[str, Any])
async def vectorize_document(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    current_user: dict = Depends(get_current_active_user)
):
    """文档向量化"""
    try:
        vectorization_service = await get_vectorization_service()

        result = await vectorization_service.generate_document_embeddings(
            documents=[text],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"文档向量化失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"文档向量化失败: {str(e)}"
        )


@router.post("/vectorization/batch", response_model=Dict[str, Any])
async def batch_vectorize(
    texts: List[str],
    batch_size: int = 32,
    current_user: dict = Depends(get_current_active_user)
):
    """批量向量化"""
    try:
        batch_processor = await get_batch_processor()

        result = await batch_processor.process_text_batch(
            texts=texts,
            batch_size=batch_size,
            use_cache=True
        )

        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"批量向量化失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"批量向量化失败: {str(e)}"
        )


# ===== 性能监控API =====

@router.get("/performance/stats")
async def get_performance_stats(
    current_user: dict = Depends(get_current_active_user)
):
    """获取性能统计信息"""
    try:
        search_optimizer = await get_search_optimizer()
        vectorization_service = await get_vectorization_service()
        batch_processor = await get_batch_processor()

        search_stats = await search_optimizer.get_search_performance_stats()
        vectorization_stats = await vectorization_service.get_embedding_stats()
        batch_stats = await batch_processor.get_batch_metrics()

        return {
            "success": True,
            "search_performance": search_stats,
            "vectorization_stats": vectorization_stats,
            "batch_processing_stats": batch_stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取性能统计失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取性能统计失败: {str(e)}"
        )


@router.post("/performance/optimize")
async def optimize_performance(
    current_user: dict = Depends(get_current_active_user)
):
    """优化性能"""
    try:
        search_optimizer = await get_search_optimizer()
        vector_db = await get_vector_db()

        # 优化搜索索引
        search_optimized = await search_optimizer.optimize_search_index()

        # 优化向量数据库
        db_optimized = await vector_db.optimize_collection()

        return {
            "success": True,
            "search_optimized": search_optimized,
            "database_optimized": db_optimized,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"性能优化失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"性能优化失败: {str(e)}"
        )


# ===== 缓存管理API =====

@router.post("/cache/clear")
async def clear_cache(
    current_user: dict = Depends(get_current_active_user)
):
    """清空缓存"""
    try:
        search_optimizer = await get_search_optimizer()
        vectorization_service = await get_vectorization_service()

        # 清空搜索缓存
        search_cleared = await search_optimizer.clear_search_cache()

        # 清空向量化缓存
        vectorization_cleared = await vectorization_service.clear_cache()

        return {
            "success": True,
            "search_cache_cleared": search_cleared,
            "vectorization_cache_cleared": vectorization_cleared,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"清空缓存失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"清空缓存失败: {str(e)}"
        )


@router.get("/cache/info")
async def get_cache_info(
    current_user: dict = Depends(get_current_active_user)
):
    """获取缓存信息"""
    try:
        search_optimizer = await get_search_optimizer()
        vectorization_service = await get_vectorization_service()

        search_cache_info = {
            "cache_size": len(search_optimizer._search_cache),
            "cache_hit_rate": search_optimizer._index_metrics['cache_hits'] / max(1, search_optimizer._index_metrics['cache_hits'] + search_optimizer._index_metrics['cache_misses'])
        }

        vectorization_cache_info = await vectorization_service.get_cache_info()

        return {
            "success": True,
            "search_cache": search_cache_info,
            "vectorization_cache": vectorization_cache_info,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取缓存信息失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取缓存信息失败: {str(e)}"
        )


# ===== 相似度计算API =====

@router.post("/similarity/matrix", response_model=Dict[str, Any])
async def calculate_similarity_matrix(
    texts: List[str],
    current_user: dict = Depends(get_current_active_user)
):
    """计算相似度矩阵"""
    try:
        vectorization_service = await get_vectorization_service()

        similarity_matrix = await vectorization_service.calculate_similarity_matrix(
            texts=texts,
            use_cache=True
        )

        return {
            "success": True,
            "similarity_matrix": similarity_matrix.tolist() if hasattr(similarity_matrix, 'tolist') else similarity_matrix,
            "texts": texts,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"计算相似度矩阵失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"计算相似度矩阵失败: {str(e)}"
        )


@router.post("/similarity/find-similar", response_model=Dict[str, Any])
async def find_similar_texts(
    query_text: str,
    candidate_texts: List[str],
    top_k: int = 5,
    current_user: dict = Depends(get_current_active_user)
):
    """查找相似文本"""
    try:
        vectorization_service = await get_vectorization_service()

        similar_texts = await vectorization_service.find_similar_texts(
            query_text=query_text,
            candidate_texts=candidate_texts,
            top_k=top_k,
            use_cache=True
        )

        return {
            "success": True,
            "similar_texts": similar_texts,
            "query_text": query_text,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"查找相似文本失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"查找相似文本失败: {str(e)}"
        )


# ===== 集合管理API =====

@router.get("/collection/detailed-info", response_model=Dict[str, Any])
async def get_collection_detailed_info(
    current_user: dict = Depends(get_current_active_user)
):
    """获取详细集合信息"""
    try:
        vector_db = await get_vector_db()

        info = await vector_db.get_collection_info()
        performance_metrics = await vector_db.get_performance_metrics()

        return {
            "success": True,
            "collection_info": info,
            "performance_metrics": performance_metrics,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取详细集合信息失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取详细集合信息失败: {str(e)}"
        )


@router.post("/collection/reset-metrics")
async def reset_performance_metrics(
    current_user: dict = Depends(get_current_active_user)
):
    """重置性能指标"""
    try:
        vector_db = await get_vector_db()
        batch_processor = await get_batch_processor()

        # 重置向量数据库指标
        db_metrics_reset = await vector_db.reset_performance_metrics()

        # 重置批量处理指标
        batch_metrics_reset = await batch_processor.reset_batch_metrics()

        return {
            "success": True,
            "db_metrics_reset": db_metrics_reset,
            "batch_metrics_reset": batch_metrics_reset,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"重置性能指标失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"重置性能指标失败: {str(e)}"
        )


# ===== 后台任务 =====

async def _background_batch_add_documents(
    vector_db,
    documents: List[str],
    metadatas: Optional[List[Dict[str, Any]]],
    ids: Optional[List[str]]
):
    """后台批量添加文档"""
    try:
        success = await vector_db.add_documents(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        if success:
            logger.info(f"后台批量添加 {len(documents)} 个文档完成")
        else:
            logger.error("后台批量添加文档失败")

    except Exception as e:
        logger.error(f"后台批量添加文档异常: {str(e)}")


# ===== 健康检查 =====

@router.get("/health")
async def vector_health_check(
    current_user: dict = Depends(get_current_active_user)
):
    """向量服务健康检查"""
    try:
        vector_db = await get_vector_db()
        vectorization_service = await get_vectorization_service()
        search_optimizer = await get_search_optimizer()

        vector_status = {
            "vector_db": {
                "initialized": vector_db.is_initialized(),
                "collection_name": vector_db.collection_name
            },
            "vectorization_service": {
                "initialized": vectorization_service.is_initialized(),
                "model_name": vectorization_service.embedding_generator.model_name
            },
            "search_optimizer": {
                "initialized": search_optimizer.is_initialized(),
                "cache_size": len(search_optimizer._search_cache)
            }
        }

        return {
            "status": "healthy",
            "components": vector_status,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"健康检查失败: {str(e)}"
        )