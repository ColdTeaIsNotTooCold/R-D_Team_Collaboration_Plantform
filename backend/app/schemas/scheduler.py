"""
任务调度器数据结构定义
"""
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class TaskPriority(str, Enum):
    """任务优先级"""
    LOW = "low"      # 低优先级
    NORMAL = "normal"   # 普通优先级
    HIGH = "high"     # 高优先级
    URGENT = "urgent"   # 紧急优先级


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"           # 待处理
    QUEUED = "queued"            # 已入队
    RUNNING = "running"          # 运行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消
    RETRYING = "retrying"        # 重试中
    TIMEOUT = "timeout"          # 超时


class TaskResultBase(BaseModel):
    """任务执行结果基础模型"""
    success: bool = Field(..., description="是否成功")
    result: Optional[Any] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: float = Field(0.0, description="执行时间（秒）")
    retry_count: int = Field(0, description="重试次数")


class TaskResultCreate(TaskResultBase):
    """创建任务结果"""
    pass


class TaskResultResponse(TaskResultBase):
    """任务结果响应"""
    pass


class TaskBase(BaseModel):
    """任务基础模型"""
    name: str = Field(..., description="任务名称", min_length=1, max_length=200)
    task_type: str = Field(..., description="任务类型", min_length=1, max_length=100)
    payload: Dict[str, Any] = Field(..., description="任务载荷")
    priority: TaskPriority = Field(TaskPriority.NORMAL, description="任务优先级")
    timeout: Optional[int] = Field(None, description="超时时间（秒）", ge=1, le=3600)
    max_retries: int = Field(3, description="最大重试次数", ge=0, le=10)


class TaskCreate(TaskBase):
    """创建任务请求"""
    pass


class TaskUpdate(BaseModel):
    """更新任务请求"""
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    priority: Optional[TaskPriority] = Field(None, description="任务优先级")
    timeout: Optional[int] = Field(None, description="超时时间（秒）", ge=1, le=3600)
    max_retries: Optional[int] = Field(None, description="最大重试次数", ge=0, le=10)


class TaskResponse(TaskBase):
    """任务响应"""
    id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    retry_count: int = Field(0, description="重试次数")
    error: Optional[str] = Field(None, description="错误信息")
    result: Optional[TaskResultResponse] = Field(None, description="任务结果")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: list[TaskResponse] = Field(..., description="任务列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")


class QueueStats(BaseModel):
    """队列统计信息"""
    low_count: int = Field(0, description="低优先级任务数量")
    normal_count: int = Field(0, description="普通优先级任务数量")
    high_count: int = Field(0, description="高优先级任务数量")
    urgent_count: int = Field(0, description="紧急优先级任务数量")
    active_workers: int = Field(0, description="活跃工作线程数")
    max_workers: int = Field(0, description="最大工作线程数")
    is_running: bool = Field(False, description="调度器是否运行")


class SchedulerControl(BaseModel):
    """调度器控制请求"""
    action: str = Field(..., description="操作: start/stop/restart", regex="^(start|stop|restart)$")
    max_workers: Optional[int] = Field(None, description="最大工作线程数", ge=1, le=32)


class SchedulerStatus(BaseModel):
    """调度器状态"""
    is_running: bool = Field(..., description="是否运行")
    max_workers: int = Field(..., description="最大工作线程数")
    active_workers: int = Field(..., description="活跃工作线程数")
    registered_handlers: list[str] = Field(..., description="已注册的处理器")
    uptime: Optional[float] = Field(None, description="运行时间（秒）")


class TaskSearch(BaseModel):
    """任务搜索条件"""
    task_type: Optional[str] = Field(None, description="任务类型")
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    priority: Optional[TaskPriority] = Field(None, description="任务优先级")
    created_after: Optional[datetime] = Field(None, description="创建时间之后")
    created_before: Optional[datetime] = Field(None, description="创建时间之前")
    name_contains: Optional[str] = Field(None, description="任务名称包含")
    page: int = Field(1, description="页码", ge=1)
    page_size: int = Field(20, description="每页大小", ge=1, le=100)


class TaskBatchCreate(BaseModel):
    """批量创建任务"""
    tasks: list[TaskCreate] = Field(..., description="任务列表", min_items=1, max_items=100)


class TaskBatchResponse(BaseModel):
    """批量创建任务响应"""
    task_ids: list[str] = Field(..., description="任务ID列表")
    success_count: int = Field(..., description="成功创建数量")
    failed_count: int = Field(..., description="失败数量")


class TaskCancelResponse(BaseModel):
    """取消任务响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    task_id: str = Field(..., description="任务ID")


class TaskRetryResponse(BaseModel):
    """重试任务响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    task_id: str = Field(..., description="任务ID")
    retry_count: int = Field(..., description="当前重试次数")


class SchedulerMetrics(BaseModel):
    """调度器指标"""
    total_tasks: int = Field(0, description="总任务数")
    completed_tasks: int = Field(0, description="已完成任务数")
    failed_tasks: int = Field(0, description="失败任务数")
    running_tasks: int = Field(0, description="运行中任务数")
    queued_tasks: int = Field(0, description="队列中任务数")
    average_execution_time: float = Field(0.0, description="平均执行时间（秒）")
    success_rate: float = Field(0.0, description="成功率（0-1）")
    worker_utilization: float = Field(0.0, description="工作线程利用率（0-1）")


class TaskExecutionLog(BaseModel):
    """任务执行日志"""
    task_id: str = Field(..., description="任务ID")
    timestamp: datetime = Field(..., description="时间戳")
    level: str = Field(..., description="日志级别")
    message: str = Field(..., description="日志消息")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class TaskLogResponse(BaseModel):
    """任务日志响应"""
    logs: list[TaskExecutionLog] = Field(..., description="日志列表")
    total: int = Field(..., description="总数")