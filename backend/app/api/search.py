from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

from ..core.database import get_db
from ..core.search import SearchEngine
from ..api.deps import get_current_active_user
from ..schemas.search import (
    SearchQuery, SearchResponse, SearchType, SortOrder,
    VectorSearchConfig, IndexDocument, BatchIndexRequest, IndexResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_contexts(
    search_query: SearchQuery,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """搜索上下文内容"""
    try:
        search_engine = SearchEngine(db)
        return await search_engine.search(search_query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索执行失败: {str(e)}"
        )


@router.get("/search")
async def search_contexts_get(
    q: str = Query(..., description="搜索查询字符串", min_length=1),
    search_type: SearchType = Query(default=SearchType.HYBRID, description="搜索类型"),
    context_types: Optional[str] = Query(default=None, description="上下文类型，用逗号分隔"),
    task_id: Optional[int] = Query(default=None, description="任务ID过滤"),
    conversation_id: Optional[int] = Query(default=None, description="对话ID过滤"),
    sort_by: SortOrder = Query(default=SortOrder.RELEVANCE, description="排序方式"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=10, ge=1, le=100, description="每页大小"),
    min_score: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="最小相关度分数"),
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """GET方式搜索上下文内容"""
    try:
        # 解析上下文类型
        types = None
        if context_types:
            types = [t.strip() for t in context_types.split(',') if t.strip()]

        search_query = SearchQuery(
            query=q,
            search_type=search_type,
            context_types=types,
            task_id=task_id,
            conversation_id=conversation_id,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
            min_score=min_score
        )

        search_engine = SearchEngine(db)
        return await search_engine.search(search_query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索执行失败: {str(e)}"
        )


@router.post("/index", response_model=IndexResponse)
async def index_document(
    document: IndexDocument,
    config: Optional[VectorSearchConfig] = None,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """索引单个文档"""
    try:
        search_engine = SearchEngine(db)
        success = await search_engine.index_document(document, config)

        if success:
            return IndexResponse(
                success=True,
                indexed_count=1,
                failed_count=0,
                errors=[]
            )
        else:
            return IndexResponse(
                success=False,
                indexed_count=0,
                failed_count=1,
                errors=["文档索引失败"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文档索引失败: {str(e)}"
        )


@router.post("/index/batch", response_model=IndexResponse)
async def batch_index_documents(
    request: BatchIndexRequest,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """批量索引文档"""
    try:
        search_engine = SearchEngine(db)
        return await search_engine.batch_index(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量索引失败: {str(e)}"
        )


@router.get("/stats")
async def get_search_stats(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取搜索统计信息"""
    try:
        search_engine = SearchEngine(db)
        stats = await search_engine.get_search_stats()
        return {
            "success": True,
            "data": stats,
            "message": "获取搜索统计信息成功"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取搜索统计失败: {str(e)}"
        )


@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., description="搜索前缀", min_length=1),
    limit: int = Query(default=5, ge=1, le=20, description="建议数量"),
    context_types: Optional[str] = Query(default=None, description="上下文类型，用逗号分隔"),
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取搜索建议"""
    try:
        search_engine = SearchEngine(db)

        # 构建搜索查询
        types = None
        if context_types:
            types = [t.strip() for t in context_types.split(',') if t.strip()]

        search_query = SearchQuery(
            query=q,
            search_type=SearchType.KEYWORD,
            context_types=types,
            page=1,
            page_size=limit
        )

        results = await search_engine._keyword_search(search_query)

        # 提取建议
        suggestions = []
        for result in results:
            if result.title and q.lower() in result.title.lower():
                suggestions.append({
                    "text": result.title,
                    "type": result.context_type,
                    "id": result.id
                })

        return {
            "success": True,
            "suggestions": suggestions[:limit],
            "query": q
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取搜索建议失败: {str(e)}"
        )


@router.get("/types")
async def get_available_context_types(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取可用的上下文类型"""
    try:
        from ..models.context import Context
        from sqlalchemy import distinct

        # 查询所有不同的上下文类型
        types = db.query(distinct(Context.context_type)).all()
        type_list = [t[0] for t in types if t[0]]

        return {
            "success": True,
            "types": sorted(type_list),
            "message": "获取上下文类型成功"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取上下文类型失败: {str(e)}"
        )


@router.delete("/index/{document_id}")
async def remove_document_from_index(
    document_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """从索引中移除文档"""
    try:
        search_engine = SearchEngine(db)

        if search_engine.chroma_client:
            try:
                collection = search_engine.chroma_client.get_collection(name="contexts")
                collection.delete(ids=[f"context_{document_id}"])

                return {
                    "success": True,
                    "message": f"文档 {document_id} 已从索引中移除"
                }
            except Exception as e:
                logger.error(f"从向量数据库移除文档失败: {str(e)}")
                return {
                    "success": False,
                    "message": f"移除文档索引失败: {str(e)}"
                }
        else:
            return {
                "success": False,
                "message": "向量数据库未连接"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移除文档索引失败: {str(e)}"
        )