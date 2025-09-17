"""
LLM API数据模型
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="角色")
    content: str = Field(..., description="内容")


class ChatRequest(BaseModel):
    """聊天请求"""
    model: str = Field(..., description="模型名称")
    messages: List[ChatMessage] = Field(..., description="消息列表")
    max_tokens: Optional[int] = Field(None, description="最大令牌数")
    temperature: float = Field(0.7, description="温度")
    top_p: float = Field(1.0, description="Top P")
    stream: bool = Field(False, description="是否流式输出")
    session_id: Optional[str] = Field(None, description="会话ID")


class ChatResponse(BaseModel):
    """聊天响应"""
    id: str = Field(..., description="响应ID")
    model: str = Field(..., description="模型")
    provider: str = Field(..., description="提供商")
    content: str = Field(..., description="内容")
    finish_reason: str = Field(..., description="结束原因")
    usage: Dict[str, Any] = Field(..., description="使用情况")
    cost: float = Field(..., description="成本")
    latency: float = Field(..., description="延迟")


class ModelInfo(BaseModel):
    """模型信息"""
    id: str = Field(..., description="模型ID")
    name: str = Field(..., description="模型名称")
    provider: str = Field(..., description="提供商")
    max_tokens: int = Field(..., description="最大令牌数")
    cost_per_1k_input: float = Field(..., description="每千输入令牌成本")
    cost_per_1k_output: float = Field(..., description="每千输出令牌成本")


class UsageStats(BaseModel):
    """使用统计"""
    total_requests: int = Field(..., description="总请求数")
    total_tokens: int = Field(..., description="总令牌数")
    total_cost: float = Field(..., description="总成本")
    average_latency: float = Field(..., description="平均延迟")
    success_rate: float = Field(..., description="成功率")


class SystemStatus(BaseModel):
    """系统状态"""
    initialized: bool = Field(..., description="是否初始化")
    providers: Dict[str, Any] = Field(..., description="提供商状态")
    load_balancer: Dict[str, Any] = Field(..., description="负载均衡器状态")
    cost_monitor: Dict[str, Any] = Field(..., description="成本监控状态")


class CreateConversationRequest(BaseModel):
    """创建对话请求"""
    title: str = Field(..., description="对话标题")
    model: str = Field(..., description="模型名称")
    system_prompt: Optional[str] = Field(None, description="系统提示")


class CostLimitRequest(BaseModel):
    """成本限制请求"""
    model: Optional[str] = Field(None, description="模型名称")
    provider: Optional[str] = Field(None, description="提供商")
    period: str = Field(..., description="周期")
    limit_type: str = Field(..., description="限制类型")
    limit_value: float = Field(..., description="限制值")
    action: str = Field("alert", description="动作")