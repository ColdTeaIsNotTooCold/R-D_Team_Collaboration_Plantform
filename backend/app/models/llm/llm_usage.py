"""
LLM使用情况统计和成本跟踪模型
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, date
from enum import Enum


class UsagePeriod(str, Enum):
    """使用统计周期"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class CostUnit(str, Enum):
    """成本单位"""
    USD = "USD"
    CNY = "CNY"
    EUR = "EUR"


class LLMUsage(BaseModel):
    """LLM使用情况统计模型"""
    id: str = Field(..., description="使用统计ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    model: str = Field(..., description="模型名称")
    provider: str = Field(..., description="服务提供商")
    request_id: str = Field(..., description="请求ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    input_tokens: int = Field(default=0, description="输入令牌数")
    output_tokens: int = Field(default=0, description="输出令牌数")
    total_tokens: int = Field(default=0, description="总令牌数")
    cost: float = Field(default=0.0, description="成本")
    latency: float = Field(default=0.0, description="延迟（秒）")
    status: str = Field(default="success", description="请求状态")
    error_message: Optional[str] = Field(None, description="错误消息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="使用元数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CostTracking(BaseModel):
    """成本跟踪模型"""
    id: str = Field(..., description="成本跟踪ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    period: UsagePeriod = Field(..., description="统计周期")
    date: date = Field(..., description="日期")
    model: Optional[str] = Field(None, description="模型名称")
    provider: Optional[str] = Field(None, description="服务提供商")
    total_cost: float = Field(default=0.0, description="总成本")
    total_tokens: int = Field(default=0, description="总令牌数")
    total_requests: int = Field(default=0, description="总请求数")
    average_latency: float = Field(default=0.0, description="平均延迟")
    success_rate: float = Field(default=1.0, description="成功率")
    currency: CostUnit = Field(default=CostUnit.USD, description="货币单位")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class UsageStatistics(BaseModel):
    """使用情况统计汇总模型"""
    period: UsagePeriod = Field(..., description="统计周期")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    total_requests: int = Field(default=0, description="总请求数")
    total_tokens: int = Field(default=0, description="总令牌数")
    total_cost: float = Field(default=0.0, description="总成本")
    average_tokens_per_request: float = Field(default=0.0, description="平均每请求令牌数")
    average_cost_per_request: float = Field(default=0.0, description="平均每请求成本")
    average_latency: float = Field(default=0.0, description="平均延迟")
    success_rate: float = Field(default=1.0, description="成功率")
    model_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="模型细分")
    provider_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="服务商细分")
    daily_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="每日细分")

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class CostAlert(BaseModel):
    """成本告警模型"""
    id: str = Field(..., description="告警ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    alert_type: str = Field(..., description="告警类型")
    threshold: float = Field(..., description="阈值")
    current_value: float = Field(..., description="当前值")
    message: str = Field(..., description="告警消息")
    severity: str = Field(default="warning", description="严重程度")
    is_resolved: bool = Field(default=False, description="是否已解决")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    resolved_at: Optional[datetime] = Field(None, description="解决时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="告警元数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UsageFilter(BaseModel):
    """使用情况过滤器模型"""
    user_id: Optional[str] = Field(None, description="用户ID")
    model: Optional[str] = Field(None, description="模型名称")
    provider: Optional[str] = Field(None, description="服务提供商")
    period: UsagePeriod = Field(default=UsagePeriod.DAILY, description="统计周期")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    status: Optional[str] = Field(None, description="请求状态")
    limit: int = Field(default=100, description="限制数量")
    offset: int = Field(default=0, description="偏移量")

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class CostLimit(BaseModel):
    """成本限制模型"""
    id: str = Field(..., description="限制ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    model: Optional[str] = Field(None, description="模型名称")
    provider: Optional[str] = Field(None, description="服务提供商")
    period: UsagePeriod = Field(..., description="限制周期")
    limit_type: str = Field(..., description="限制类型")
    limit_value: float = Field(..., description="限制值")
    action: str = Field(default="alert", description="触发动作")
    is_active: bool = Field(default=True, description="是否激活")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }