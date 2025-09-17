from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base
import json
from typing import Dict, List


class AgentStatus:
    """Agent状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    agent_type = Column(String(50), nullable=False)  # e.g., 'code', 'analysis', 'test'
    model_config = Column(Text, nullable=True)  # JSON string for model configuration
    system_prompt = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default=AgentStatus.ACTIVE)  # Agent运行状态

    # 注册中心相关字段
    endpoint = Column(String(500), nullable=True)  # Agent服务端点
    capabilities = Column(JSON, nullable=True)  # Agent能力列表
    metadata = Column(JSON, nullable=True)  # 额外的元数据
    health_check_url = Column(String(500), nullable=True)  # 健康检查URL
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)  # 最后心跳时间
    registered_at = Column(DateTime(timezone=True), nullable=True)  # 注册时间

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="agents")
    created_tasks = relationship("Task", back_populates="creator_agent", foreign_keys="Task.creator_agent_id")
    assigned_tasks = relationship("Task", back_populates="assigned_agent", foreign_keys="Task.assigned_agent_id")

    def __repr__(self):
        return f"<Agent(id={self.id}, name='{self.name}', type='{self.agent_type}', status='{self.status}')>"

    @property
    def capabilities_list(self) -> List[str]:
        """获取能力列表"""
        if self.capabilities:
            return self.capabilities if isinstance(self.capabilities, list) else []
        return []

    @capabilities_list.setter
    def capabilities_list(self, value: List[str]):
        """设置能力列表"""
        self.capabilities = value

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "status": self.status,
            "capabilities": self.capabilities_list,
            "endpoint": self.endpoint,
            "metadata": self.metadata,
            "health_check_url": self.health_check_url,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "owner_id": self.owner_id
        }

    def is_healthy(self) -> bool:
        """检查Agent是否健康"""
        if self.status != AgentStatus.ACTIVE:
            return False

        if not self.last_heartbeat:
            return False

        # 检查最后心跳时间是否在5分钟内
        from datetime import datetime, timedelta
        if datetime.now(self.last_heartbeat.tzinfo) - self.last_heartbeat > timedelta(minutes=5):
            return False

        return True