"""
LLM API路由
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
import json

from ...models.llm import LLMRequest, LLMResponse, LLMMessage
from ...services.llm.exceptions import LLMException
from ...services.llm.manager import get_llm_manager
from ...services.llm.cost_monitor import get_cost_monitor
from ...models.user import User

from .deps import get_llm_manager, get_current_user, validate_model
from .schemas import (
    ChatRequest, ChatResponse, ModelInfo, UsageStats,
    SystemStatus, CreateConversationRequest, CostLimitRequest
)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    user: Optional[User] = Depends(get_current_user),
    manager=Depends(get_llm_manager),
    model: str = Depends(validate_model)
):
    """聊天接口"""
    try:
        # 转换消息格式
        messages = [
            LLMMessage(role=msg.role, content=msg.content)
            for msg in request.messages
        ]

        # 构建LLM请求
        llm_request = LLMRequest(
            model=request.model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stream=request.stream,
            user_id=user.id if user else None,
            session_id=request.session_id
        )

        # 生成响应
        response = await manager.generate_response(llm_request)

        # 转换响应格式
        return ChatResponse(
            id=response.id,
            model=response.model,
            provider=response.provider,
            content=response.content,
            finish_reason=response.finish_reason,
            usage=response.usage,
            cost=response.cost,
            latency=response.latency
        )

    except LLMException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM服务错误: {e.message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"内部服务器错误: {e}"
        )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    user: Optional[User] = Depends(get_current_user),
    manager=Depends(get_llm_manager),
    model: str = Depends(validate_model)
):
    """流式聊天接口"""
    try:
        # 转换消息格式
        messages = [
            LLMMessage(role=msg.role, content=msg.content)
            for msg in request.messages
        ]

        # 构建LLM请求
        llm_request = LLMRequest(
            model=request.model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stream=True,
            user_id=user.id if user else None,
            session_id=request.session_id
        )

        async def generate_stream():
            try:
                async for chunk in manager.generate_stream_response(llm_request):
                    data = {
                        "id": chunk.id,
                        "model": chunk.model,
                        "provider": chunk.provider,
                        "content": chunk.content,
                        "finish_reason": chunk.finish_reason,
                        "is_final": chunk.is_final
                    }
                    yield f"data: {json.dumps(data)}\n\n"

                yield "data: [DONE]\n\n"
            except Exception as e:
                error_data = {
                    "error": str(e),
                    "type": type(e).__name__
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"流式聊天错误: {e}"
        )


@router.get("/models", response_model=List[ModelInfo])
async def get_models(
    manager=Depends(get_llm_manager)
):
    """获取可用模型列表"""
    try:
        available_models = await manager.get_available_models()
        model_infos = []

        for model in available_models:
            try:
                info = await manager.get_model_info(model)
                model_infos.append(ModelInfo(
                    id=info.get("id", model),
                    name=model,
                    provider=info.get("provider", "unknown"),
                    max_tokens=info.get("max_tokens", 4096),
                    cost_per_1k_input=info.get("cost_per_1k_input", 0.0),
                    cost_per_1k_output=info.get("cost_per_1k_output", 0.0)
                ))
            except Exception as e:
                continue

        return model_infos

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"获取模型列表失败: {e}"
        )


@router.get("/models/{model_id}", response_model=ModelInfo)
async def get_model_info(
    model_id: str,
    manager=Depends(get_llm_manager),
    model: str = Depends(validate_model)
):
    """获取模型信息"""
    try:
        info = await manager.get_model_info(model_id)
        return ModelInfo(
            id=info.get("id", model_id),
            name=model_id,
            provider=info.get("provider", "unknown"),
            max_tokens=info.get("max_tokens", 4096),
            cost_per_1k_input=info.get("cost_per_1k_input", 0.0),
            cost_per_1k_output=info.get("cost_per_1k_output", 0.0)
        )

    except LLMException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模型 '{model_id}' 不存在"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"获取模型信息失败: {e}"
        )


@router.post("/estimate-cost")
async def estimate_cost(
    request: ChatRequest,
    manager=Depends(get_llm_manager),
    model: str = Depends(validate_model)
):
    """估算成本"""
    try:
        messages = [
            LLMMessage(role=msg.role, content=msg.content)
            for msg in request.messages
        ]

        llm_request = LLMRequest(
            model=request.model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p
        )

        cost = await manager.estimate_cost(llm_request)
        return {"estimated_cost": cost}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"成本估算失败: {e}"
        )


@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    period: str = "daily",
    user: Optional[User] = Depends(get_current_user),
    manager=Depends(get_llm_manager)
):
    """获取使用统计"""
    try:
        user_id = user.id if user else None
        stats = await manager.get_usage_statistics(user_id, period)

        return UsageStats(
            total_requests=stats.get("total_requests", 0),
            total_tokens=stats.get("total_tokens", 0),
            total_cost=stats.get("total_cost", 0.0),
            average_latency=stats.get("average_latency", 0.0),
            success_rate=stats.get("success_rate", 1.0)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"获取使用统计失败: {e}"
        )


@router.get("/cost-breakdown")
async def get_cost_breakdown(
    user: Optional[User] = Depends(get_current_user),
    manager=Depends(get_llm_manager)
):
    """获取成本分解"""
    try:
        user_id = user.id if user else None
        breakdown = await manager.get_cost_breakdown(user_id)
        return breakdown

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"获取成本分解失败: {e}"
        )


@router.get("/system-status", response_model=SystemStatus)
async def get_system_status(
    manager=Depends(get_llm_manager)
):
    """获取系统状态"""
    try:
        status = await manager.get_system_status()
        return SystemStatus(**status)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"获取系统状态失败: {e}"
        )


@router.get("/health")
async def health_check(
    manager=Depends(get_llm_manager)
):
    """健康检查"""
    try:
        is_healthy = await manager.health_check()
        return {"healthy": is_healthy}

    except Exception as e:
        return {"healthy": False, "error": str(e)}


@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    user: Optional[User] = Depends(get_current_user),
    manager=Depends(get_llm_manager),
    model: str = Depends(validate_model)
):
    """创建对话"""
    try:
        conversation = await manager.create_conversation(
            user_id=user.id if user else "anonymous",
            title=request.title,
            model=request.model,
            system_prompt=request.system_prompt
        )

        return {"conversation_id": conversation.id, "status": "created"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"创建对话失败: {e}"
        )


@router.post("/cost-limits")
async def create_cost_limit(
    request: CostLimitRequest,
    user: Optional[User] = Depends(get_current_user),
    manager=Depends(get_llm_manager)
):
    """创建成本限制"""
    try:
        cost_monitor = await get_cost_monitor()
        limit = await cost_monitor.create_cost_limit(
            user_id=user.id if user else None,
            model=request.model,
            provider=request.provider,
            period=request.period,
            limit_type=request.limit_type,
            limit_value=request.limit_value,
            action=request.action
        )

        return {"limit_id": limit.id, "status": "created"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"创建成本限制失败: {e}"
        )


@router.get("/cost-limits")
async def get_cost_limits(
    user: Optional[User] = Depends(get_current_user),
    manager=Depends(get_llm_manager)
):
    """获取成本限制"""
    try:
        cost_monitor = await get_cost_monitor()
        alerts = await cost_monitor.get_active_alerts(user.id if user else None)

        return {
            "active_alerts": len(alerts),
            "alerts": [alert.dict() for alert in alerts]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"获取成本限制失败: {e}"
        )