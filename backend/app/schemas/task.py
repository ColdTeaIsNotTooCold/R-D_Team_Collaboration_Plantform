from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    task_type: str
    input_data: Optional[str] = None


class TaskCreate(TaskBase):
    creator_id: Optional[int] = None
    assignee_id: Optional[int] = None
    creator_agent_id: Optional[int] = None
    assigned_agent_id: Optional[int] = None
    parent_task_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    task_type: Optional[str] = None
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    assignee_id: Optional[int] = None
    assigned_agent_id: Optional[int] = None


class Task(TaskBase):
    id: int
    creator_id: Optional[int] = None
    assignee_id: Optional[int] = None
    creator_agent_id: Optional[int] = None
    assigned_agent_id: Optional[int] = None
    parent_task_id: Optional[int] = None
    output_data: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskInDB(TaskBase):
    id: int
    creator_id: Optional[int] = None
    assignee_id: Optional[int] = None
    creator_agent_id: Optional[int] = None
    assigned_agent_id: Optional[int] = None
    parent_task_id: Optional[int] = None
    output_data: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True