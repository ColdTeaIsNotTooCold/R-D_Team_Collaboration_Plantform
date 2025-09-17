"""
文档处理API接口
提供文档上传、处理、搜索等功能
"""

import os
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..core.document_processor import DocumentProcessor
from ..core.security import get_current_active_user
from ..schemas.base import BaseResponse
from ..utils.text_utils import TextUtils

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# 全局文档处理器实例
doc_processor = None


def get_document_processor():
    """获取文档处理器实例"""
    global doc_processor
    if doc_processor is None:
        doc_processor = DocumentProcessor()
    return doc_processor


# 请求/响应模型
class DocumentProcessRequest(BaseModel):
    """文档处理请求"""
    file_path: str = Field(..., description="文件路径")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")


class DocumentSearchRequest(BaseModel):
    """文档搜索请求"""
    query: str = Field(..., description="搜索查询")
    limit: int = Field(10, description="返回结果数量", ge=1, le=100)
    metadata_filter: Optional[Dict[str, Any]] = Field(None, description="元数据过滤条件")


class DocumentResponse(BaseResponse):
    """文档响应"""
    data: Optional[Dict[str, Any]] = None


class DocumentListResponse(BaseResponse):
    """文档列表响应"""
    data: List[Dict[str, Any]] = []


class DocumentSearchResponse(BaseResponse):
    """文档搜索响应"""
    data: List[Dict[str, Any]] = []
    total: int = 0
    query: str = ""


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_active_user),
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    上传并处理文档
    """
    try:
        # 验证文件类型
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in processor.supported_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_extension}"
            )

        # 创建上传目录
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)

        # 保存文件
        file_path = upload_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 解析元数据
        doc_metadata = {}
        if metadata:
            try:
                import json
                doc_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="元数据格式错误，应为有效的JSON"
                )

        # 添加用户信息
        doc_metadata.update({
            "uploaded_by": current_user.get("user_id"),
            "uploaded_at": datetime.now().isoformat(),
            "original_filename": file.filename,
            "content_type": file.content_type
        })

        # 处理文档
        result = processor.process_document(str(file_path), doc_metadata)

        if result["status"] == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"文档处理失败: {result.get('error', '未知错误')}"
            )

        return DocumentResponse(
            success=True,
            message="文档上传和处理成功",
            data=result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档上传失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"文档上传失败: {str(e)}"
        )


@router.post("/process", response_model=DocumentResponse)
async def process_document(
    request: DocumentProcessRequest,
    current_user: dict = Depends(get_current_active_user),
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    处理本地文档
    """
    try:
        # 添加用户信息到元数据
        metadata = request.metadata or {}
        metadata.update({
            "processed_by": current_user.get("user_id"),
            "processed_at": datetime.now().isoformat()
        })

        # 处理文档
        result = processor.process_document(request.file_path, metadata)

        if result["status"] == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"文档处理失败: {result.get('error', '未知错误')}"
            )

        return DocumentResponse(
            success=True,
            message="文档处理成功",
            data=result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档处理失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"文档处理失败: {str(e)}"
        )


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearchRequest,
    current_user: dict = Depends(get_current_active_user),
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    搜索文档
    """
    try:
        # 执行搜索
        results = processor.search_documents(
            query=request.query,
            limit=request.limit,
            metadata_filter=request.metadata_filter
        )

        return DocumentSearchResponse(
            success=True,
            message="搜索完成",
            data=results,
            total=len(results),
            query=request.query
        )

    except Exception as e:
        logger.error(f"文档搜索失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"文档搜索失败: {str(e)}"
        )


@router.get("/search", response_model=DocumentSearchResponse)
async def search_documents_get(
    query: str = Query(..., description="搜索查询"),
    limit: int = Query(10, description="返回结果数量", ge=1, le=100),
    current_user: dict = Depends(get_current_active_user),
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    搜索文档 (GET方法)
    """
    try:
        # 执行搜索
        results = processor.search_documents(query=query, limit=limit)

        return DocumentSearchResponse(
            success=True,
            message="搜索完成",
            data=results,
            total=len(results),
            query=query
        )

    except Exception as e:
        logger.error(f"文档搜索失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"文档搜索失败: {str(e)}"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_active_user),
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    获取文档信息
    """
    try:
        document = processor.get_document_by_id(document_id)

        if not document:
            raise HTTPException(
                status_code=404,
                detail="文档不存在"
            )

        return DocumentResponse(
            success=True,
            message="获取文档信息成功",
            data=document
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取文档信息失败: {str(e)}"
        )


@router.delete("/{document_id}", response_model=DocumentResponse)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_active_user),
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    删除文档
    """
    try:
        success = processor.delete_document(document_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail="文档不存在或删除失败"
            )

        return DocumentResponse(
            success=True,
            message="文档删除成功",
            data={"document_id": document_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"删除文档失败: {str(e)}"
        )


@router.get("/statistics", response_model=DocumentResponse)
async def get_document_statistics(
    current_user: dict = Depends(get_current_active_user),
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    获取文档处理统计信息
    """
    try:
        statistics = processor.get_statistics()

        return DocumentResponse(
            success=True,
            message="获取统计信息成功",
            data=statistics
        )

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}"
        )


@router.post("/text/analyze", response_model=DocumentResponse)
async def analyze_text(
    text: str = Form(..., description="要分析的文本"),
    current_user: dict = Depends(get_current_active_user)
):
    """
    分析文本内容
    """
    try:
        text_utils = TextUtils()

        # 提取元数据
        metadata = text_utils.extract_metadata_from_text(text)

        # 获取统计信息
        statistics = text_utils.get_text_statistics(text)

        # 提取关键词
        keywords = text_utils.extract_keywords(text, max_keywords=20)

        result = {
            "metadata": metadata,
            "statistics": statistics,
            "keywords": keywords,
            "analyzed_at": datetime.now().isoformat(),
            "analyzed_by": current_user.get("user_id")
        }

        return DocumentResponse(
            success=True,
            message="文本分析完成",
            data=result
        )

    except Exception as e:
        logger.error(f"文本分析失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"文本分析失败: {str(e)}"
        )


@router.post("/text/chunk", response_model=DocumentResponse)
async def chunk_text(
    text: str = Form(..., description="要分块的文本"),
    max_chunk_size: int = Form(1000, description="最大块大小"),
    overlap_size: int = Form(200, description="重叠大小"),
    current_user: dict = Depends(get_current_active_user)
):
    """
    文本分块
    """
    try:
        from ..utils.text_utils import ChunkConfig

        # 创建配置
        config = ChunkConfig(
            max_chunk_size=max_chunk_size,
            overlap_size=overlap_size
        )

        # 创建文本工具实例
        text_utils = TextUtils(config)

        # 执行分块
        chunks = text_utils.chunk_text(text)

        result = {
            "chunks": chunks,
            "chunk_count": len(chunks),
            "config": {
                "max_chunk_size": max_chunk_size,
                "overlap_size": overlap_size
            },
            "processed_at": datetime.now().isoformat(),
            "processed_by": current_user.get("user_id")
        }

        return DocumentResponse(
            success=True,
            message="文本分块完成",
            data=result
        )

    except Exception as e:
        logger.error(f"文本分块失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"文本分块失败: {str(e)}"
        )


@router.get("/supported-formats", response_model=DocumentResponse)
async def get_supported_formats(
    processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    获取支持的文件格式
    """
    try:
        formats = {
            "supported_extensions": list(processor.supported_extensions),
            "description": {
                ".txt": "纯文本文件",
                ".md": "Markdown文件",
                ".py": "Python源代码",
                ".js": "JavaScript源代码",
                ".html": "HTML文件",
                ".css": "CSS样式表",
                ".json": "JSON数据",
                ".xml": "XML文件",
                ".csv": "CSV数据",
                ".log": "日志文件",
                ".pdf": "PDF文档",
                ".docx": "Word文档",
                ".xlsx": "Excel表格"
            }
        }

        return DocumentResponse(
            success=True,
            message="获取支持的文件格式成功",
            data=formats
        )

    except Exception as e:
        logger.error(f"获取支持的文件格式失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取支持的文件格式失败: {str(e)}"
        )