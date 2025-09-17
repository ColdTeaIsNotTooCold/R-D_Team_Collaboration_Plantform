from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default='pending')  # pending, in_progress, completed, failed
    priority = Column(String(20), default='medium')  # low, medium, high, urgent
    task_type = Column(String(50), nullable=False)  # e.g., 'code', 'analysis', 'test'
    input_data = Column(Text, nullable=True)  # JSON string for task input
    output_data = Column(Text, nullable=True)  # JSON string for task output
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Foreign keys
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    creator_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    assigned_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)

    # Relationships
    creator = relationship("User", back_populates="created_tasks", foreign_keys=[creator_id])
    assignee = relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_id])
    creator_agent = relationship("Agent", back_populates="created_tasks", foreign_keys=[creator_agent_id])
    assigned_agent = relationship("Agent", back_populates="assigned_tasks", foreign_keys=[assigned_agent_id])
    parent_task = relationship("Task", remote_side=[id], back_populates="subtasks")
    subtasks = relationship("Task", back_populates="parent_task")
    contexts = relationship("Context", back_populates="task")
    executions = relationship("TaskExecution", back_populates="task")

    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"