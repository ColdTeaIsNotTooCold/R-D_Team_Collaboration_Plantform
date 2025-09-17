from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    """Agent状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class AgentCapability(BaseModel):
    """Agent能力模型"""
    name: str
    description: Optional[str] = None
    version: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    agent_type: str
    model_config: Optional[str] = None
    system_prompt: Optional[str] = None
    is_active: bool = True


class AgentCreate(AgentBase):
    """创建Agent的请求模型"""
    capabilities: List[str] = []
    endpoint: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agent_type: Optional[str] = None
    model_config: Optional[str] = None
    system_prompt: Optional[str] = None
    is_active: Optional[bool] = None
    capabilities: Optional[List[str]] = None
    endpoint: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Agent(AgentBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentInDB(AgentBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentRegistryRequest(BaseModel):
    """Agent注册请求"""
    name: str = Field(..., description="Agent名称")
    agent_type: str = Field(..., description="Agent类型")
    description: Optional[str] = Field(None, description="Agent描述")
    capabilities: List[str] = Field(..., description="Agent能力列表")
    endpoint: str = Field(..., description="Agent服务端点")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    health_check_url: Optional[str] = Field(None, description="健康检查URL")


class AgentRegistryResponse(BaseModel):
    """Agent注册响应"""
    id: str
    name: str
    agent_type: str
    description: Optional[str] = None
    capabilities: List[str]
    endpoint: str
    status: AgentStatus
    metadata: Optional[Dict[str, Any]] = None
    registered_at: str
    last_heartbeat: Optional[str] = None


class AgentDiscoveryRequest(BaseModel):
    """Agent发现请求"""
    required_capabilities: List[str] = Field([], description="所需能力列表")
    agent_type: Optional[str] = Field(None, description="Agent类型过滤")
    max_results: Optional[int] = Field(10, description="最大返回结果数")


class AgentHealthCheck(BaseModel):
    """Agent健康检查响应"""
    agent_id: str
    status: AgentStatus
    timestamp: str
    uptime: Optional[float] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    error_message: Optional[str] = None


class AgentStatistics(BaseModel):
    """Agent统计信息"""
    total_agents: int
    active_agents: int
    inactive_agents: int
    capability_distribution: Dict[str, int]
    type_distribution: Dict[str, int]