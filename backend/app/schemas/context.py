from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ContextBase(BaseModel):
    context_type: str
    title: str
    content: Optional[str] = None
    metadata: Optional[str] = None


class ContextCreate(ContextBase):
    task_id: Optional[int] = None
    conversation_id: Optional[int] = None


class ContextUpdate(BaseModel):
    context_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[str] = None


class Context(ContextBase):
    id: int
    task_id: Optional[int] = None
    conversation_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ContextInDB(ContextBase):
    id: int
    task_id: Optional[int] = None
    conversation_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True