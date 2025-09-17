from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ContextBase(BaseModel):
    context_type: str
    title: str
    content: Optional[str] = None
    metadata: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    document_type: Optional[str] = None
    version: Optional[str] = '1.0'
    access_level: Optional[str] = 'private'
    permissions: Optional[Dict[str, Any]] = None
    processing_status: Optional[str] = 'pending'
    chunks_count: Optional[int] = None


class ContextCreate(ContextBase):
    task_id: Optional[int] = None
    conversation_id: Optional[int] = None
    owner_id: Optional[int] = None
    parent_version_id: Optional[int] = None


class ContextUpdate(BaseModel):
    context_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    document_type: Optional[str] = None
    version: Optional[str] = None
    access_level: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
    processing_status: Optional[str] = None
    chunks_count: Optional[int] = None
    is_latest: Optional[bool] = None
    is_embedded: Optional[bool] = None
    vector_id: Optional[str] = None
    embedding_metadata: Optional[Dict[str, Any]] = None


class Context(ContextBase):
    id: int
    task_id: Optional[int] = None
    conversation_id: Optional[int] = None
    owner_id: Optional[int] = None
    parent_version_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_latest: bool
    is_embedded: bool
    vector_id: Optional[str] = None
    embedding_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ContextInDB(ContextBase):
    id: int
    task_id: Optional[int] = None
    conversation_id: Optional[int] = None
    owner_id: Optional[int] = None
    parent_version_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_latest: bool
    is_embedded: bool
    vector_id: Optional[str] = None
    embedding_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ContextVersion(BaseModel):
    id: int
    version: str
    title: str
    created_at: datetime
    is_latest: bool


class ContextSearchResult(BaseModel):
    id: int
    title: str
    context_type: str
    document_type: Optional[str] = None
    version: str
    content_snippet: Optional[str] = None
    similarity_score: Optional[float] = None
    created_at: datetime
    owner_id: Optional[int] = None
    access_level: str