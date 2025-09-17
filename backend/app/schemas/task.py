from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """任务优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskBase(BaseModel):
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    status: TaskStatus = Field(TaskStatus.PENDING, description="任务状态")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="任务优先级")
    task_type: str = Field(..., description="任务类型")
    input_data: Optional[str] = Field(None, description="输入数据")
    metadata: Optional[Dict[str, Any]] = Field(None, description="任务元数据")


class TaskCreate(TaskBase):
    creator_id: Optional[int] = Field(None, description="创建者ID")
    assignee_id: Optional[int] = Field(None, description="分配用户ID")
    creator_agent_id: Optional[int] = Field(None, description="创建Agent ID")
    assigned_agent_id: Optional[int] = Field(None, description="分配Agent ID")
    parent_task_id: Optional[int] = Field(None, description="父任务ID")
    tags: Optional[List[str]] = Field([], description="任务标签")
    estimated_duration: Optional[int] = Field(None, description="预估执行时间（秒）")
    retry_count: int = Field(0, description="重试次数")
    max_retries: int = Field(3, description="最大重试次数")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    priority: Optional[TaskPriority] = Field(None, description="任务优先级")
    task_type: Optional[str] = Field(None, description="任务类型")
    input_data: Optional[str] = Field(None, description="输入数据")
    output_data: Optional[str] = Field(None, description="输出数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    assignee_id: Optional[int] = Field(None, description="分配用户ID")
    assigned_agent_id: Optional[int] = Field(None, description="分配Agent ID")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    progress: Optional[float] = Field(None, ge=0, le=100, description="任务进度百分比")
    retry_count: Optional[int] = Field(None, description="重试次数")
    metadata: Optional[Dict[str, Any]] = Field(None, description="任务元数据")


class Task(TaskBase):
    id: int = Field(..., description="任务ID")
    creator_id: Optional[int] = Field(None, description="创建者ID")
    assignee_id: Optional[int] = Field(None, description="分配用户ID")
    creator_agent_id: Optional[int] = Field(None, description="创建Agent ID")
    assigned_agent_id: Optional[int] = Field(None, description="分配Agent ID")
    parent_task_id: Optional[int] = Field(None, description="父任务ID")
    output_data: Optional[str] = Field(None, description="输出数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    tags: Optional[List[str]] = Field([], description="任务标签")
    estimated_duration: Optional[int] = Field(None, description="预估执行时间（秒）")
    retry_count: int = Field(0, description="重试次数")
    max_retries: int = Field(3, description="最大重试次数")
    progress: Optional[float] = Field(None, ge=0, le=100, description="任务进度百分比")

    class Config:
        from_attributes = True


class TaskInDB(TaskBase):
    id: int = Field(..., description="任务ID")
    creator_id: Optional[int] = Field(None, description="创建者ID")
    assignee_id: Optional[int] = Field(None, description="分配用户ID")
    creator_agent_id: Optional[int] = Field(None, description="创建Agent ID")
    assigned_agent_id: Optional[int] = Field(None, description="分配Agent ID")
    parent_task_id: Optional[int] = Field(None, description="父任务ID")
    output_data: Optional[str] = Field(None, description="输出数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    tags: Optional[List[str]] = Field([], description="任务标签")
    estimated_duration: Optional[int] = Field(None, description="预估执行时间（秒）")
    retry_count: int = Field(0, description="重试次数")
    max_retries: int = Field(3, description="最大重试次数")
    progress: Optional[float] = Field(None, ge=0, le=100, description="任务进度百分比")

    class Config:
        from_attributes = True


# 任务分发相关模型
class TaskDispatchRequest(BaseModel):
    """任务分发请求"""
    task_id: Optional[int] = Field(None, description="任务ID")
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    task_type: str = Field(..., description="任务类型")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="任务优先级")
    input_data: Optional[str] = Field(None, description="输入数据")
    metadata: Optional[Dict[str, Any]] = Field(None, description="任务元数据")
    required_capabilities: Optional[List[str]] = Field([], description="需要的Agent能力")
    timeout: Optional[int] = Field(300, description="超时时间（秒）")


class TaskDispatchResponse(BaseModel):
    """任务分发响应"""
    task_id: str = Field(..., description="任务ID")
    agent_id: int = Field(..., description="分配的Agent ID")
    message_id: str = Field(..., description="消息ID")
    status: TaskStatus = Field(..., description="任务状态")
    dispatched_at: str = Field(..., description="分发时间")
    estimated_completion: Optional[str] = Field(None, description="预估完成时间")


class TaskResult(BaseModel):
    """任务结果"""
    task_id: str = Field(..., description="任务ID")
    agent_id: int = Field(..., description="执行Agent ID")
    status: TaskStatus = Field(..., description="任务状态")
    output_data: Optional[str] = Field(None, description="输出数据")
    error_message: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")
    completed_at: str = Field(..., description="完成时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="结果元数据")


class TaskQueueStatus(BaseModel):
    """任务队列状态"""
    pending_tasks: int = Field(..., description="待处理任务数")
    running_tasks: int = Field(..., description="运行中任务数")
    completed_tasks: int = Field(..., description="已完成任务数")
    failed_tasks: int = Field(..., description="失败任务数")
    avg_wait_time: Optional[float] = Field(None, description="平均等待时间（秒）")
    avg_execution_time: Optional[float] = Field(None, description="平均执行时间（秒）")


class AgentWorkload(BaseModel):
    """Agent工作负载"""
    agent_id: int = Field(..., description="Agent ID")
    agent_type: str = Field(..., description="Agent类型")
    status: str = Field(..., description="Agent状态")
    current_tasks: int = Field(..., description="当前任务数")
    total_tasks_completed: int = Field(..., description="总完成任务数")
    avg_execution_time: Optional[float] = Field(None, description="平均执行时间（秒）")
    error_rate: float = Field(0.0, ge=0, le=1, description="错误率")
    last_heartbeat: str = Field(..., description="最后心跳时间")