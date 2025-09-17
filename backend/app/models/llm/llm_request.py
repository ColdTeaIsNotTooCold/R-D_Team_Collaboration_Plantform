"""
LLM请求和响应模型
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class LLMMessage(BaseModel):
    """LLM消息模型"""
    role: Literal["system", "user", "assistant"] = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(None, description="消息发送者名称")
    metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LLMRequest(BaseModel):
    """LLM请求模型"""
    model: str = Field(..., description="模型名称")
    messages: List[LLMMessage] = Field(..., description="消息列表")
    max_tokens: Optional[int] = Field(None, description="最大令牌数")
    temperature: float = Field(0.7, description="温度参数")
    top_p: float = Field(1.0, description="top-p参数")
    frequency_penalty: float = Field(0.0, description="频率惩罚")
    presence_penalty: float = Field(0.0, description="存在惩罚")
    stop: Optional[List[str]] = Field(None, description="停止序列")
    stream: bool = Field(False, description="是否流式输出")
    user_id: Optional[str] = Field(None, description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="请求元数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LLMResponse(BaseModel):
    """LLM响应模型"""
    id: str = Field(..., description="响应ID")
    model: str = Field(..., description="使用的模型")
    provider: str = Field(..., description="服务提供商")
    content: str = Field(..., description="响应内容")
    finish_reason: str = Field(..., description="结束原因")
    usage: Dict[str, int] = Field(..., description="使用情况统计")
    tokens: Dict[str, int] = Field(..., description="令牌使用详情")
    cost: float = Field(0.0, description="成本")
    latency: float = Field(0.0, description="延迟（秒）")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    request_id: Optional[str] = Field(None, description="请求ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="响应元数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LLMStreamResponse(BaseModel):
    """LLM流式响应模型"""
    id: str = Field(..., description="响应ID")
    model: str = Field(..., description="使用的模型")
    provider: str = Field(..., description="服务提供商")
    content: str = Field(..., description="响应内容")
    finish_reason: Optional[str] = Field(None, description="结束原因")
    is_final: bool = Field(False, description="是否最终响应")
    metadata: Optional[Dict[str, Any]] = Field(None, description="响应元数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LLMError(BaseModel):
    """LLM错误模型"""
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    provider: str = Field(..., description="服务提供商")
    model: str = Field(..., description="模型名称")
    request_id: Optional[str] = Field(None, description="请求ID")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }