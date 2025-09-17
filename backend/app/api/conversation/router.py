"""
对话管理API路由
提供对话创建、管理、消息处理等功能
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
import json
import logging
from datetime import datetime

from ...models.user import User
from ...core.auth import get_current_user
from .schemas import *
from .deps import *

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["对话管理"])


# 对话管理
@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    conversation: ConversationCreate,
    user: User = Depends(get_current_user),
    manager: ConversationHistoryManager = Depends(get_conversation_manager)
):
    """创建新对话"""
    try:
        new_conversation = await manager.create_conversation(
            user_id=user.id,
            title=conversation.title,
            description=conversation.description,
            session_id=conversation.session_id,
            model=conversation.model,
            system_prompt=conversation.system_prompt,
            temperature=conversation.temperature,
            max_tokens=conversation.max_tokens,
            top_p=conversation.top_p,
            context_length=conversation.context_length,
            max_context_tokens=conversation.max_context_tokens,
            context_compression=conversation.context_compression,
            auto_save_context=conversation.auto_save_context,
            tags=conversation.tags,
            metadata=conversation.metadata
        )
        return new_conversation

    except Exception as e:
        logger.error(f"创建对话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建对话失败: {str(e)}"
        )


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_archived: bool = Query(False),
    is_pinned: Optional[bool] = Query(None),
    tags: Optional[List[str]] = Query(None),
    user: User = Depends(get_current_user),
    manager: ConversationHistoryManager = Depends(get_conversation_manager)
):
    """列出用户对话"""
    try:
        conversations = await manager.list_conversations(
            user_id=user.id,
            skip=skip,
            limit=limit,
            is_archived=is_archived,
            is_pinned=is_pinned,
            tags=tags
        )
        return conversations

    except Exception as e:
        logger.error(f"列出对话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话列表失败: {str(e)}"
        )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation: Conversation = Depends(get_conversation_or_404)
):
    """获取对话详情"""
    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_update: ConversationUpdate,
    conversation: Conversation = Depends(get_conversation_or_404),
    manager: ConversationHistoryManager = Depends(get_conversation_manager)
):
    """更新对话信息"""
    try:
        # 过滤None值
        update_data = {k: v for k, v in conversation_update.dict().items() if v is not None}

        updated_conversation = await manager.update_conversation(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            **update_data
        )

        if not updated_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )

        return updated_conversation

    except Exception as e:
        logger.error(f"更新对话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新对话失败: {str(e)}"
        )


@router.delete("/{conversation_id}")
async def delete_conversation(
    soft_delete: bool = Query(True),
    conversation: Conversation = Depends(get_conversation_or_404),
    manager: ConversationHistoryManager = Depends(get_conversation_manager)
):
    """删除对话"""
    try:
        success = await manager.delete_conversation(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            soft_delete=soft_delete
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )

        return {"message": "对话删除成功"}

    except Exception as e:
        logger.error(f"删除对话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除对话失败: {str(e)}"
        )


# 消息管理
@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    limit: Optional[int] = Query(None, ge=1, le=200),
    include_deleted: bool = Query(False),
    include_hidden: bool = Query(False),
    conversation: Conversation = Depends(get_conversation_or_404),
    manager: ConversationHistoryManager = Depends(get_conversation_manager)
):
    """获取对话消息"""
    try:
        messages = await manager.get_conversation_messages(
            conversation_id=conversation_id,
            user_id=conversation.user_id,
            limit=limit,
            include_deleted=include_deleted,
            include_hidden=include_hidden
        )
        return messages

    except Exception as e:
        logger.error(f"获取对话消息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取消息失败: {str(e)}"
        )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    message: MessageCreate,
    conversation: Conversation = Depends(get_conversation_or_404),
    manager: ConversationHistoryManager = Depends(get_conversation_manager)
):
    """添加消息到对话"""
    try:
        new_message = await manager.add_message(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            role=message.role,
            content=message.content,
            context_id=message.context_id,
            metadata=message.metadata
        )
        return new_message

    except Exception as e:
        logger.error(f"添加消息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加消息失败: {str(e)}"
        )


@router.post("/{conversation_id}/chat", response_model=ChatResponse)
async def chat_with_conversation(
    chat_request: ChatRequest,
    background_tasks: BackgroundTasks,
    conversation: Conversation = Depends(get_conversation_or_404),
    rag_integration: RAGLLMIntegration = Depends(get_rag_integration)
):
    """与对话聊天"""
    try:
        from .rag_integration import RAGEnhancedRequest, ResponseMode

        # 构建RAG增强请求
        rag_request = RAGEnhancedRequest(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            message=chat_request.message,
            mode=ResponseMode(chat_request.mode),
            max_tokens=chat_request.max_tokens,
            temperature=chat_request.temperature,
            enable_context=chat_request.enable_context,
            enable_rag=chat_request.enable_rag,
            system_prompt=conversation.system_prompt,
            metadata=chat_request.metadata
        )

        # 处理消息
        response = await rag_integration.process_message(rag_request)

        return ChatResponse(
            content=response.content,
            sources=response.sources,
            context_messages=response.context_messages,
            usage=response.usage,
            cost=response.cost,
            latency=response.latency,
            mode=response.mode,
            metadata=response.metadata
        )

    except Exception as e:
        logger.error(f"聊天处理失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天处理失败: {str(e)}"
        )


# 上下文管理
@router.post("/{conversation_id}/context/optimize", response_model=ContextOptimizeResponse)
async def optimize_context(
    request: ContextOptimizeRequest,
    conversation: Conversation = Depends(get_conversation_or_404),
    context_manager: SmartContextManager = Depends(get_context_manager)
):
    """优化对话上下文"""
    try:
        context_window = await context_manager.build_context_window(
            conversation_id=conversation.id,
            max_tokens=request.max_tokens,
            compression_strategy=request.compression_strategy,
            include_system_prompt=request.include_system_prompt,
            context_priority_rules=request.context_priority_rules
        )

        return ContextOptimizeResponse(
            conversation_id=conversation.id,
            messages=[
                {
                    "role": msg.role,
                    "content": msg.content,
                    "tokens": msg.tokens,
                    "priority": msg.priority.value,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in context_window.messages
            ],
            total_tokens=context_window.total_tokens,
            max_tokens=context_window.max_tokens,
            compression_strategy=context_window.compression_strategy.value,
            optimization_metadata={
                "message_count": len(context_window.messages),
                "usage_ratio": context_window.total_tokens / context_window.max_tokens
            }
        )

    except Exception as e:
        logger.error(f"上下文优化失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上下文优化失败: {str(e)}"
        )


@router.post("/{conversation_id}/context/compress", response_model=CompressionResponse)
async def compress_context(
    request: CompressionRequest,
    conversation: Conversation = Depends(get_conversation_or_404),
    compression_manager: ContextCompressionManager = Depends(get_compression_manager)
):
    """压缩对话上下文"""
    try:
        result = await compression_manager.compress_conversation_context(
            conversation_id=conversation.id,
            max_tokens=request.max_tokens,
            compression_type=request.compression_type
        )

        return CompressionResponse(
            original_token_count=result.original_token_count,
            compressed_token_count=result.compressed_token_count,
            compression_ratio=result.compression_ratio,
            strategy_used=result.strategy_used,
            messages=result.messages,
            metadata=result.metadata
        )

    except Exception as e:
        logger.error(f"上下文压缩失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上下文压缩失败: {str(e)}"
        )


@router.get("/{conversation_id}/context/health", response_model=HealthCheckResponse)
async def check_conversation_health(
    conversation: Conversation = Depends(get_conversation_or_404),
    context_manager: SmartContextManager = Depends(get_context_manager)
):
    """检查对话健康状态"""
    try:
        health_report = await context_manager.maintain_context_health(conversation.id)

        return HealthCheckResponse(
            conversation_id=conversation.id,
            health_score=health_report.get("health_score", 0.0),
            check_time=health_report.get("check_time", ""),
            metrics=health_report.get("metrics", {}),
            recommendations=health_report.get("recommendations", [])
        )

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"健康检查失败: {str(e)}"
        )


# 搜索功能
@router.post("/search", response_model=List[SearchResult])
async def search_conversations(
    search_request: SearchRequest,
    user: User = Depends(get_current_user),
    manager: ConversationHistoryManager = Depends(get_conversation_manager)
):
    """搜索对话"""
    try:
        results = await manager.search_conversations(
            user_id=user.id,
            query=search_request.query,
            skip=search_request.skip,
            limit=search_request.limit
        )

        search_results = []
        for conversation, score in results:
            # 获取匹配的消息
            matched_messages = await manager.get_conversation_messages(
                conversation_id=conversation.id,
                user_id=user.id,
                limit=5  # 最多返回5条匹配消息
            )

            search_results.append(SearchResult(
                conversation=conversation,
                relevance_score=score,
                matched_messages=matched_messages
            ))

        return search_results

    except Exception as e:
        logger.error(f"搜索对话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}"
        )


# 统计功能
@router.get("/stats", response_model=StatsResponse)
async def get_conversation_stats(
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(get_current_user),
    manager: ConversationHistoryManager = Depends(get_conversation_manager)
):
    """获取对话统计"""
    try:
        stats = await manager.get_conversation_stats(user_id=user.id, days=days)
        return StatsResponse(**stats)

    except Exception as e:
        logger.error(f"获取统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计失败: {str(e)}"
        )


# 批量操作
@router.post("/batch/messages", response_model=BatchMessageResponse)
async def batch_add_messages(
    batch_request: BatchMessageCreate,
    user: User = Depends(get_current_user),
    manager: ConversationHistoryManager = Depends(get_conversation_manager)
):
    """批量添加消息"""
    try:
        success_count = 0
        failed_count = 0
        messages = []
        errors = []

        # 验证对话权限
        conversation = await manager.get_conversation(
            batch_request.conversation_id,
            user.id
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )

        # 批量添加消息
        for i, msg_data in enumerate(batch_request.messages):
            try:
                message = await manager.add_message(
                    conversation_id=batch_request.conversation_id,
                    user_id=user.id,
                    role=msg_data.role,
                    content=msg_data.content,
                    metadata={
                        **(msg_data.metadata or {}),
                        "batch_id": batch_request.metadata.get("batch_id", f"batch_{datetime.utcnow().timestamp()}"),
                        "batch_index": i
                    }
                )
                messages.append(message)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"消息 {i+1}: {str(e)}")

        return BatchMessageResponse(
            success_count=success_count,
            failed_count=failed_count,
            messages=messages,
            errors=errors
        )

    except Exception as e:
        logger.error(f"批量添加消息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量操作失败: {str(e)}"
        )


# 导出功能
@router.post("/{conversation_id}/export", response_model=ExportResponse)
async def export_conversation(
    export_request: ConversationExportRequest,
    conversation: Conversation = Depends(get_conversation_or_404),
    manager: ConversationHistoryManager = Depends(get_conversation_manager)
):
    """导出对话"""
    try:
        # 获取消息
        messages = await manager.get_conversation_messages(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            include_deleted=export_request.include_deleted,
            limit=export_request.message_limit
        )

        # 根据格式导出
        if export_request.format == "json":
            content = json.dumps({
                "conversation": {
                    "id": conversation.id,
                    "title": conversation.title,
                    "description": conversation.description,
                    "created_at": conversation.created_at.isoformat(),
                    "metadata": conversation.metadata if export_request.include_metadata else None
                },
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                        "metadata": msg.metadata if export_request.include_metadata else None
                    }
                    for msg in messages
                ]
            }, ensure_ascii=False, indent=2)
        elif export_request.format == "txt":
            content = f"对话: {conversation.title}\n"
            content += f"创建时间: {conversation.created_at}\n"
            if conversation.description:
                content += f"描述: {conversation.description}\n"
            content += "\n" + "="*50 + "\n\n"

            for msg in messages:
                content += f"[{msg.role}] {msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                content += f"{msg.content}\n\n"
        elif export_request.format == "markdown":
            content = f"# {conversation.title}\n\n"
            if conversation.description:
                content += f"**描述**: {conversation.description}\n\n"
            content += f"**创建时间**: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            content += "---\n\n"

            for msg in messages:
                if msg.role == "user":
                    content += f"## 用户 {msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                else:
                    content += f"## 助手 {msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                content += f"{msg.content}\n\n"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不支持的导出格式"
            )

        filename = f"conversation_{conversation.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{export_request.format}"

        return ExportResponse(
            content=content,
            format=export_request.format,
            filename=filename,
            size_bytes=len(content.encode('utf-8')),
            export_time=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"导出对话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出失败: {str(e)}"
        )


# 健康检查和维护
@router.post("/maintenance/cleanup-sessions")
async def cleanup_sessions(
    days: int = Query(7, ge=1, le=30),
    user: User = Depends(get_current_user),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """清理过期会话"""
    try:
        if not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )

        cleaned_count = await session_manager.cleanup_expired_sessions()

        return {
            "message": f"清理完成",
            "cleaned_sessions": cleaned_count
        }

    except Exception as e:
        logger.error(f"清理会话失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理失败: {str(e)}"
        )