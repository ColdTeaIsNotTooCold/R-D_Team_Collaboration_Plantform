from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from .task import TaskStatus, TaskPriority


class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskExecution(BaseModel):
    """任务执行记录"""
    id: int = Field(..., description="执行记录ID")
    task_id: int = Field(..., description="任务ID")
    agent_id: int = Field(..., description="执行Agent ID")
    message_id: str = Field(..., description="消息ID")
    status: ExecutionStatus = Field(..., description="执行状态")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")
    output_data: Optional[str] = Field(None, description="输出数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    retry_count: int = Field(0, description="重试次数")
    metadata: Optional[Dict[str, Any]] = Field(None, description="执行元数据")

    class Config:
        from_attributes = True


class TaskExecutionCreate(BaseModel):
    """创建任务执行记录"""
    task_id: int = Field(..., description="任务ID")
    agent_id: int = Field(..., description="执行Agent ID")
    message_id: str = Field(..., description="消息ID")
    status: ExecutionStatus = Field(ExecutionStatus.PENDING, description="执行状态")
    metadata: Optional[Dict[str, Any]] = Field(None, description="执行元数据")


class TaskExecutionUpdate(BaseModel):
    """更新任务执行记录"""
    status: Optional[ExecutionStatus] = Field(None, description="执行状态")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")
    output_data: Optional[str] = Field(None, description="输出数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    retry_count: Optional[int] = Field(None, description="重试次数")
    metadata: Optional[Dict[str, Any]] = Field(None, description="执行元数据")


class ExecutionRequest(BaseModel):
    """执行请求"""
    task_id: int = Field(..., description="任务ID")
    agent_id: int = Field(..., description="目标Agent ID")
    task_type: str = Field(..., description="任务类型")
    input_data: Optional[str] = Field(None, description="输入数据")
    timeout: Optional[int] = Field(300, description="超时时间（秒）")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="任务优先级")
    metadata: Optional[Dict[str, Any]] = Field(None, description="请求元数据")


class ExecutionResponse(BaseModel):
    """执行响应"""
    execution_id: int = Field(..., description="执行记录ID")
    task_id: int = Field(..., description="任务ID")
    agent_id: int = Field(..., description="Agent ID")
    message_id: str = Field(..., description="消息ID")
    status: ExecutionStatus = Field(..., description="执行状态")
    estimated_duration: Optional[int] = Field(None, description="预估执行时间（秒）")
    created_at: datetime = Field(..., description="创建时间")


class ExecutionResult(BaseModel):
    """执行结果"""
    execution_id: int = Field(..., description="执行记录ID")
    task_id: int = Field(..., description="任务ID")
    agent_id: int = Field(..., description="执行Agent ID")
    status: ExecutionStatus = Field(..., description="执行状态")
    output_data: Optional[str] = Field(None, description="输出数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    execution_time: float = Field(..., description="执行时间（秒）")
    started_at: datetime = Field(..., description="开始时间")
    completed_at: datetime = Field(..., description="完成时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="结果元数据")


class ExecutionMetrics(BaseModel):
    """执行指标"""
    total_executions: int = Field(..., description="总执行次数")
    successful_executions: int = Field(..., description="成功执行次数")
    failed_executions: int = Field(..., description="失败执行次数")
    average_execution_time: float = Field(..., description="平均执行时间（秒）")
    success_rate: float = Field(..., ge=0, le=1, description="成功率")
    agent_utilization: Dict[int, float] = Field(..., description="Agent利用率")


class ExecutionQueueStatus(BaseModel):
    """执行队列状态"""
    pending_executions: int = Field(..., description="待执行任务数")
    running_executions: int = Field(..., description="运行中任务数")
    completed_executions: int = Field(..., description="已完成任务数")
    failed_executions: int = Field(..., description="失败任务数")
    average_wait_time: float = Field(..., description="平均等待时间（秒）")
    queue_length: int = Field(..., description="队列长度")
    throughput: float = Field(..., description="吞吐量（任务/秒）")


class AgentExecutionStats(BaseModel):
    """Agent执行统计"""
    agent_id: int = Field(..., description="Agent ID")
    agent_type: str = Field(..., description="Agent类型")
    total_executions: int = Field(..., description="总执行次数")
    successful_executions: int = Field(..., description="成功执行次数")
    failed_executions: int = Field(..., description="失败执行次数")
    average_execution_time: float = Field(..., description="平均执行时间（秒）")
    success_rate: float = Field(..., ge=0, le=1, description="成功率")
    current_load: int = Field(..., description="当前负载")
    last_execution_time: Optional[datetime] = Field(None, description="最后执行时间")