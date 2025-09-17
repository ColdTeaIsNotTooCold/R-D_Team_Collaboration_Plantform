"""
LLM对话模型
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ConversationStatus(str, Enum):
    """对话状态枚举"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class LLMConversationMessage(BaseModel):
    """对话消息模型"""
    id: str = Field(..., description="消息ID")
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")
    tokens: Optional[int] = Field(None, description="令牌数")
    cost: Optional[float] = Field(None, description="成本")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LLMConversation(BaseModel):
    """对话模型"""
    id: str = Field(..., description="对话ID")
    user_id: str = Field(..., description="用户ID")
    title: str = Field(..., description="对话标题")
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE, description="对话状态")
    model: str = Field(..., description="使用的模型")
    provider: str = Field(..., description="服务提供商")
    messages: List[LLMConversationMessage] = Field(default_factory=list, description="消息列表")
    system_prompt: Optional[str] = Field(None, description="系统提示")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="对话元数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def add_message(self, message: LLMConversationMessage) -> None:
        """添加消息到对话"""
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_last_message(self) -> Optional[LLMConversationMessage]:
        """获取最后一条消息"""
        return self.messages[-1] if self.messages else None

    def get_messages_count(self) -> int:
        """获取消息数量"""
        return len(self.messages)

    def calculate_total_tokens(self) -> int:
        """计算总令牌数"""
        return sum(msg.tokens for msg in self.messages if msg.tokens)

    def calculate_total_cost(self) -> float:
        """计算总成本"""
        return sum(msg.cost for msg in self.messages if msg.cost)


class ConversationSummary(BaseModel):
    """对话摘要模型"""
    conversation_id: str = Field(..., description="对话ID")
    title: str = Field(..., description="对话标题")
    status: ConversationStatus = Field(..., description="对话状态")
    message_count: int = Field(..., description="消息数量")
    last_message: Optional[str] = Field(None, description="最后一条消息")
    last_updated: datetime = Field(..., description="最后更新时间")
    total_tokens: int = Field(default=0, description="总令牌数")
    total_cost: float = Field(default=0.0, description="总成本")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConversationFilter(BaseModel):
    """对话过滤器模型"""
    user_id: Optional[str] = Field(None, description="用户ID")
    status: Optional[ConversationStatus] = Field(None, description="对话状态")
    model: Optional[str] = Field(None, description="模型名称")
    provider: Optional[str] = Field(None, description="服务提供商")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    limit: int = Field(default=50, description="限制数量")
    offset: int = Field(default=0, description="偏移量")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }