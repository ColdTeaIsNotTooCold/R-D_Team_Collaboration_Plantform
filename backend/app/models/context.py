from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, LargeBinary
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base


class Context(Base):
    __tablename__ = "contexts"

    id = Column(Integer, primary_key=True, index=True)
    context_type = Column(String(50), nullable=False)  # e.g., 'code', 'conversation', 'file'
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    binary_data = Column(LargeBinary, nullable=True)  # For file attachments
    metadata = Column(Text, nullable=True)  # JSON string for additional metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Foreign keys
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)

    # Relationships
    task = relationship("Task", back_populates="contexts")
    conversation = relationship("Conversation", back_populates="contexts")

    def __repr__(self):
        return f"<Context(id={self.id}, type='{self.context_type}', title='{self.title}')>"