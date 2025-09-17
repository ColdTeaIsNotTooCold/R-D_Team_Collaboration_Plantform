from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class MessageBase(BaseModel):
    stream_name: str
    message_type: str
    content: Dict[str, Any]
    sender_id: Optional[str] = None
    recipient_id: Optional[str] = None
    priority: Optional[int] = 0


class MessageCreate(MessageBase):
    pass


class MessageUpdate(BaseModel):
    message_type: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    sender_id: Optional[str] = None
    recipient_id: Optional[str] = None
    priority: Optional[int] = None


class Message(MessageBase):
    id: str
    timestamp: datetime
    processed: bool = False

    class Config:
        from_attributes = True


class ConsumerGroupBase(BaseModel):
    group_name: str
    stream_name: str
    description: Optional[str] = None


class ConsumerGroupCreate(ConsumerGroupBase):
    pass


class ConsumerGroup(ConsumerGroupBase):
    id: int
    created_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True


class ConsumerBase(BaseModel):
    consumer_name: str
    group_name: str
    stream_name: str


class ConsumerCreate(ConsumerBase):
    pass


class Consumer(ConsumerBase):
    id: int
    created_at: datetime
    last_active: Optional[datetime] = None
    status: str = "idle"

    class Config:
        from_attributes = True


class StreamStats(BaseModel):
    stream_name: str
    message_count: int
    consumer_groups: List[str]
    active_consumers: int
    pending_messages: int