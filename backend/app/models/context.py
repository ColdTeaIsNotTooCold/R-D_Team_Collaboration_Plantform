from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, LargeBinary, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base


class Context(Base):
    __tablename__ = "contexts"

    id = Column(Integer, primary_key=True, index=True)
    context_type = Column(String(50), nullable=False)  # e.g., 'code', 'conversation', 'file', 'document'
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    binary_data = Column(LargeBinary, nullable=True)  # For file attachments
    metadata = Column(Text, nullable=True)  # JSON string for additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Document management fields
    file_name = Column(String(500), nullable=True)  # Original file name
    file_type = Column(String(100), nullable=True)  # MIME type or file extension
    file_size = Column(Integer, nullable=True)  # File size in bytes
    document_type = Column(String(50), nullable=True)  # e.g., 'markdown', 'pdf', 'text', 'code'

    # Version control fields
    version = Column(String(20), nullable=False, server_default='1.0')  # Semantic versioning
    parent_version_id = Column(Integer, ForeignKey("contexts.id"), nullable=True)  # Parent version for version history
    is_latest = Column(Boolean, nullable=False, server_default=True)  # Whether this is the latest version

    # Permission management fields
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Document owner
    access_level = Column(String(20), nullable=False, server_default='private')  # 'private', 'team', 'public'
    permissions = Column(JSON, nullable=True)  # JSON object with granular permissions

    # Vector search support
    vector_id = Column(String(100), nullable=True)  # ChromaDB vector ID
    is_embedded = Column(Boolean, nullable=False, server_default=False)  # Whether content has been embedded
    embedding_metadata = Column(JSON, nullable=True)  # Embedding-related metadata

    # Content processing status
    processing_status = Column(String(20), nullable=False, server_default='pending')  # 'pending', 'processing', 'completed', 'failed'
    chunks_count = Column(Integer, nullable=True)  # Number of chunks for large documents

    # Foreign keys
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)

    # Relationships
    task = relationship("Task", back_populates="contexts")
    conversation = relationship("Conversation", back_populates="contexts")
    owner = relationship("User", foreign_keys=[owner_id])
    parent_version = relationship("Context", remote_side=[id], foreign_keys=[parent_version_id])
    child_versions = relationship("Context", foreign_keys=[parent_version_id])

    def __repr__(self):
        return f"<Context(id={self.id}, type='{self.context_type}', title='{self.title}', version='{self.version}')>"