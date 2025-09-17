"""
向量数据库API路由
提供向量存储、检索和嵌入生成功能
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
import logging

from ..core.vector_db import get_vector_db
from ..core.embeddings import get_embedding_generator, get_text_chunker
from ..api.deps import get_current_active_user
from ..schemas.vector import (
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


@router.post("/documents/add", response_model=DocumentAddResponse)
async def add_documents(
    request: DocumentAddRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """添加文档到向量数据库"""
    try:
        vector_db = await get_vector_db()

        # 验证输入
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
                enhanced_metadata['created_at'] = str(__import__('datetime').datetime.now())
                enhanced_metadatas.append(enhanced_metadata)
        else:
            enhanced_metadatas = None

        # 添加文档
        success = await vector_db.add_documents(
            documents=request.documents,
            metadatas=enhanced_metadatas,
            ids=request.ids
        )

        if success:
            return DocumentAddResponse(
                success=True,
                message="文档添加成功",
                document_count=len(request.documents)
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="添加文档失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加文档失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"添加文档失败: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """搜索相似文档"""
    try:
        vector_db = await get_vector_db()

        # 执行搜索
        results = await vector_db.search(
            query=request.query,
            n_results=request.n_results,
            where=request.where,
            where_document=request.where_document
        )

        # 格式化结果
        search_results = []
        for result in results:
            search_result = SearchResult(
                document=result['document'],
                metadata=result['metadata'],
                id=result['id'],
                distance=result['distance']
            )
            search_results.append(search_result)

        return SearchResponse(
            success=True,
            results=search_results,
            query=request.query,
            result_count=len(search_results)
        )

    except Exception as e:
        logger.error(f"搜索文档失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"搜索文档失败: {str(e)}"
        )


@router.delete("/documents", response_model=DocumentDeleteResponse)
async def delete_documents(
    request: DocumentDeleteRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """删除文档"""
    try:
        vector_db = await get_vector_db()

        if not request.ids:
            raise HTTPException(
                status_code=400,
                detail="文档ID列表不能为空"
            )

        success = await vector_db.delete_documents(request.ids)

        if success:
            return DocumentDeleteResponse(
                success=True,
                message="文档删除成功",
                deleted_count=len(request.ids)
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="删除文档失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"删除文档失败: {str(e)}"
        )


@router.put("/documents", response_model=DocumentUpdateResponse)
async def update_documents(
    request: DocumentUpdateRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """更新文档"""
    try:
        vector_db = await get_vector_db()

        if not request.ids:
            raise HTTPException(
                status_code=400,
                detail="文档ID列表不能为空"
            )

        if not request.documents and not request.metadatas:
            raise HTTPException(
                status_code=400,
                detail="至少需要提供文档内容或元数据"
            )

        # 添加更新信息到元数据
        enhanced_metadatas = None
        if request.metadatas:
            enhanced_metadatas = []
            for metadata in request.metadatas:
                enhanced_metadata = metadata.copy()
                enhanced_metadata['updated_by'] = current_user.get('username', 'unknown')
                enhanced_metadata['updated_at'] = str(__import__('datetime').datetime.now())
                enhanced_metadatas.append(enhanced_metadata)

        success = await vector_db.update_documents(
            ids=request.ids,
            documents=request.documents,
            metadatas=enhanced_metadatas
        )

        if success:
            return DocumentUpdateResponse(
                success=True,
                message="文档更新成功",
                updated_count=len(request.ids)
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="更新文档失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文档失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"更新文档失败: {str(e)}"
        )


@router.get("/collection/info", response_model=CollectionInfoResponse)
async def get_collection_info(
    current_user: dict = Depends(get_current_active_user)
):
    """获取集合信息"""
    try:
        vector_db = await get_vector_db()

        info = await vector_db.get_collection_info()

        collection_info = CollectionInfo(
            collection_name=info.get('collection_name', ''),
            document_count=info.get('document_count', 0),
            initialized=info.get('initialized', False)
        )

        return CollectionInfoResponse(
            success=True,
            collection_info=collection_info
        )

    except Exception as e:
        logger.error(f"获取集合信息失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取集合信息失败: {str(e)}"
        )


@router.delete("/collection/clear", response_model=ClearCollectionResponse)
async def clear_collection(
    current_user: dict = Depends(get_current_active_user)
):
    """清空集合"""
    try:
        vector_db = await get_vector_db()

        success = await vector_db.clear_collection()

        if success:
            return ClearCollectionResponse(
                success=True,
                message="集合清空成功"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="清空集合失败"
            )

    except Exception as e:
        logger.error(f"清空集合失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"清空集合失败: {str(e)}"
        )


@router.post("/embeddings/generate", response_model=EmbeddingResponse)
async def generate_embeddings(
    request: EmbeddingRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """生成文本嵌入"""
    try:
        embedding_generator = await get_embedding_generator()

        if not request.texts:
            raise HTTPException(
                status_code=400,
                detail="文本列表不能为空"
            )

        embeddings = await embedding_generator.generate_embeddings(request.texts)
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


@router.post("/embeddings/similarity", response_model=SimilarityResponse)
async def calculate_similarity(
    request: SimilarityRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """计算文本相似度"""
    try:
        embedding_generator = await get_embedding_generator()

        # 生成嵌入
        embedding1 = await embedding_generator.generate_embedding(request.text1)
        embedding2 = await embedding_generator.generate_embedding(request.text2)

        # 计算相似度
        similarity = await embedding_generator.calculate_similarity(embedding1, embedding2)

        return SimilarityResponse(
            success=True,
            similarity=similarity,
            text1=request.text1,
            text2=request.text2
        )

    except Exception as e:
        logger.error(f"计算相似度失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"计算相似度失败: {str(e)}"
        )


@router.post("/text/chunk", response_model=TextChunkResponse)
async def chunk_text(
    request: TextChunkRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """文本分块"""
    try:
        text_chunker = await get_text_chunker()

        # 更新分块参数
        text_chunker.chunk_size = request.chunk_size
        text_chunker.chunk_overlap = request.chunk_overlap

        # 分块
        chunks = text_chunker.chunk_text(request.text)

        return TextChunkResponse(
            success=True,
            chunks=chunks,
            chunk_count=len(chunks),
            original_length=len(request.text)
        )

    except Exception as e:
        logger.error(f"文本分块失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"文本分块失败: {str(e)}"
        )


@router.get("/health")
async def vector_health_check(
    current_user: dict = Depends(get_current_active_user)
):
    """向量数据库健康检查"""
    try:
        vector_db = await get_vector_db()
        embedding_generator = await get_embedding_generator()

        vector_status = {
            "vector_db": {
                "initialized": vector_db.is_initialized(),
                "collection_name": vector_db.collection_name
            },
            "embedding_generator": {
                "initialized": embedding_generator.is_initialized(),
                "model_name": embedding_generator.model_name
            }
        }

        return {
            "status": "healthy",
            "components": vector_status
        }

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"健康检查失败: {str(e)}"
        )