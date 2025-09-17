"""
监控数据模式定义

定义监控相关的数据结构，包括系统指标、任务性能、告警事件等。
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MonitorEventType(str, Enum):
    """监控事件类型"""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_TIMEOUT = "task_timeout"
    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"
    AGENT_ERROR = "agent_error"
    SYSTEM_HEALTH_CHECK = "system_health_check"
    RESOURCE_WARNING = "resource_warning"
    PERFORMANCE_DEGRADATION = "performance_degradation"


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class NetworkIO(BaseModel):
    """网络IO数据"""
    bytes_sent: int = Field(..., description="发送字节数")
    bytes_recv: int = Field(..., description="接收字节数")


class SystemMetrics(BaseModel):
    """系统指标"""
    timestamp: datetime = Field(..., description="指标时间戳")
    cpu_usage: float = Field(..., ge=0, le=100, description="CPU使用率(%)")
    memory_usage: float = Field(..., ge=0, le=100, description="内存使用率(%)")
    disk_usage: float = Field(..., ge=0, le=100, description="磁盘使用率(%)")
    network_io: NetworkIO = Field(..., description="网络IO数据")
    active_connections: int = Field(..., ge=0, description="活跃连接数")
    redis_connections: int = Field(..., ge=0, description="Redis连接数")
    queue_size: int = Field(..., ge=0, description="任务队列大小")
    active_agents: int = Field(..., ge=0, description="活跃Agent数量")
    running_tasks: int = Field(..., ge=0, description="运行中任务数")

    class Config:
        from_attributes = True


class TaskPerformanceMetrics(BaseModel):
    """任务性能指标"""
    task_id: str = Field(..., description="任务ID")
    task_type: str = Field(..., description="任务类型")
    agent_id: int = Field(..., description="执行Agent ID")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    execution_time: Optional[float] = Field(None, ge=0, description="执行时间(秒)")
    wait_time: float = Field(..., ge=0, description="等待时间(秒)")
    peak_memory_usage: Optional[float] = Field(None, ge=0, le=100, description="峰值内存使用率(%)")
    peak_cpu_usage: Optional[float] = Field(None, ge=0, le=100, description="峰值CPU使用率(%)")
    status: str = Field(..., description="任务状态")
    error_message: Optional[str] = Field(None, description="错误信息")

    class Config:
        from_attributes = True


class MonitorEvent(BaseModel):
    """监控事件"""
    event_type: MonitorEventType = Field(..., description="事件类型")
    timestamp: datetime = Field(..., description="事件时间戳")
    level: AlertLevel = Field(..., description="告警级别")
    message: str = Field(..., description="事件消息")
    details: Optional[Dict[str, Any]] = Field(None, description="事件详情")
    source: Optional[str] = Field(None, description="事件来源")
    task_id: Optional[str] = Field(None, description="相关任务ID")
    agent_id: Optional[int] = Field(None, description="相关Agent ID")

    class Config:
        from_attributes = True


class PerformanceSummary(BaseModel):
    """性能摘要"""
    total_tasks: int = Field(..., ge=0, description="总任务数")
    completed_tasks: int = Field(..., ge=0, description="完成任务数")
    failed_tasks: int = Field(..., ge=0, description="失败任务数")
    running_tasks: int = Field(..., ge=0, description="运行中任务数")
    success_rate: float = Field(..., ge=0, le=1, description="成功率")
    average_execution_time: Optional[float] = Field(None, ge=0, description="平均执行时间(秒)")


class HealthStatusResponse(BaseModel):
    """健康状态响应"""
    status: HealthStatus = Field(..., description="健康状态")
    timestamp: str = Field(..., description="状态时间戳")
    cpu_usage: float = Field(..., ge=0, le=100, description="CPU使用率(%)")
    memory_usage: float = Field(..., ge=0, le=100, description="内存使用率(%)")
    disk_usage: float = Field(..., ge=0, le=100, description="磁盘使用率(%)")
    active_agents: int = Field(..., ge=0, description="活跃Agent数量")
    running_tasks: int = Field(..., ge=0, description="运行中任务数")
    recent_alerts_count: int = Field(..., ge=0, description="最近告警数量")


class TaskMetricsRequest(BaseModel):
    """任务指标查询请求"""
    task_id: str = Field(..., description="任务ID")


class TaskMetricsResponse(BaseModel):
    """任务指标响应"""
    task_id: str = Field(..., description="任务ID")
    task_type: str = Field(..., description="任务类型")
    agent_id: int = Field(..., description="执行Agent ID")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    execution_time: Optional[float] = Field(None, ge=0, description="执行时间(秒)")
    wait_time: float = Field(..., ge=0, description="等待时间(秒)")
    status: str = Field(..., description="任务状态")
    error_message: Optional[str] = Field(None, description="错误信息")


class SystemMetricsRequest(BaseModel):
    """系统指标查询请求"""
    hours: int = Field(24, ge=1, le=168, description="查询时间范围(小时)")


class SystemMetricsResponse(BaseModel):
    """系统指标响应"""
    metrics: List[SystemMetrics] = Field(..., description="系统指标列表")
    total_count: int = Field(..., description="指标总数")


class AlertsRequest(BaseModel):
    """告警查询请求"""
    level: Optional[AlertLevel] = Field(None, description="告警级别过滤")
    hours: int = Field(24, ge=1, le=168, description="查询时间范围(小时)")


class AlertsResponse(BaseModel):
    """告警响应"""
    alerts: List[MonitorEvent] = Field(..., description="告警列表")
    total_count: int = Field(..., description="告警总数")


class EventsRequest(BaseModel):
    """事件查询请求"""
    count: int = Field(100, ge=1, le=1000, description="返回事件数量")
    event_type: Optional[MonitorEventType] = Field(None, description="事件类型过滤")


class EventsResponse(BaseModel):
    """事件响应"""
    events: List[MonitorEvent] = Field(..., description="事件列表")
    total_count: int = Field(..., description="事件总数")


class TaskTrackingRequest(BaseModel):
    """任务跟踪请求"""
    task_id: str = Field(..., description="任务ID")
    task_type: str = Field(..., description="任务类型")
    agent_id: int = Field(..., description="执行Agent ID")


class TaskCompletionRequest(BaseModel):
    """任务完成请求"""
    task_id: str = Field(..., description="任务ID")
    success: bool = Field(True, description="是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")


class MonitoringStatus(BaseModel):
    """监控状态"""
    is_monitoring: bool = Field(..., description="是否正在监控")
    monitoring_interval: int = Field(..., description="监控间隔(秒)")
    total_metrics_collected: int = Field(..., ge=0, description="收集的指标总数")
    total_events_recorded: int = Field(..., ge=0, description="记录的事件总数")
    total_alerts_created: int = Field(..., ge=0, description="创建的告警总数")
    last_metrics_collection: Optional[datetime] = Field(None, description="最后指标收集时间")
    uptime_seconds: Optional[float] = Field(None, ge=0, description="运行时间(秒)")


class CleanupRequest(BaseModel):
    """清理请求"""
    days: int = Field(7, ge=1, le=30, description="清理多少天前的数据")


class CleanupResponse(BaseModel):
    """清理响应"""
    success: bool = Field(..., description="是否成功")
    cleaned_task_metrics: int = Field(..., ge=0, description="清理的任务指标数量")
    cleaned_system_metrics: int = Field(..., ge=0, description="清理的系统指标数量")
    cleaned_events: int = Field(..., ge=0, description="清理的事件数量")
    cleaned_alerts: int = Field(..., ge=0, description="清理的告警数量")


# 响应包装器
class BaseResponse(BaseModel):
    """基础响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class TaskTrackingResponse(BaseResponse):
    """任务跟踪响应"""
    data: Optional[Dict[str, Any]] = Field(None, description="任务跟踪数据")


class TaskCompletionResponse(BaseResponse):
    """任务完成响应"""
    data: Optional[Dict[str, Any]] = Field(None, description="任务完成数据")


class MonitoringStatusResponse(BaseResponse):
    """监控状态响应"""
    data: Optional[MonitoringStatus] = Field(None, description="监控状态数据")


class PerformanceSummaryResponse(BaseResponse):
    """性能摘要响应"""
    data: Optional[PerformanceSummary] = Field(None, description="性能摘要数据")


class HealthStatusResponseWrapper(BaseResponse):
    """健康状态响应包装器"""
    data: Optional[HealthStatusResponse] = Field(None, description="健康状态数据")