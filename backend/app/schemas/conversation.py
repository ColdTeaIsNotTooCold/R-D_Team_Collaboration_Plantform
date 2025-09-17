from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ConversationBase(BaseModel):
    title: str
    description: Optional[str] = None
    is_active: bool = True


class ConversationCreate(ConversationBase):
    user_id: int


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class Conversation(ConversationBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConversationInDB(ConversationBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True