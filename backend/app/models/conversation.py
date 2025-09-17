from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_pinned = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True), server_default=func.now())

    # 对话配置
    session_id = Column(String(100), nullable=True, index=True)
    model = Column(String(100), nullable=True)
    system_prompt = Column(Text, nullable=True)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)
    top_p = Column(Float, default=1.0)

    # 上下文管理
    context_length = Column(Integer, default=50)  # 保留的消息数量
    max_context_tokens = Column(Integer, default=4000)  # 最大上下文token数
    context_compression = Column(String(50), default="truncate")  # truncate, summarize, semantic
    auto_save_context = Column(Boolean, default=True)

    # 统计信息
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    average_latency = Column(Float, default=0.0)

    # 元数据
    tags = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="conversations")
    contexts = relationship("Context", back_populates="conversation")
    messages = relationship("ConversationMessage", back_populates="conversation", order_by="ConversationMessage.sequence")

    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}', messages={self.message_count})>"


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    sequence = Column(Integer, nullable=False)  # 消息序列号
    is_visible = Column(Boolean, default=True)  # 是否在对话中显示
    is_edited = Column(Boolean, default=False)  # 是否被编辑过
    is_deleted = Column(Boolean, default=False)  # 是否被删除

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # AI相关
    model = Column(String(100), nullable=True)  # 生成回复的模型
    provider = Column(String(50), nullable=True)  # AI提供商
    tokens = Column(Integer, nullable=True)  # 消息token数
    cost = Column(Float, default=0.0)  # 消息成本
    latency = Column(Float, default=0.0)  # 响应延迟
    finish_reason = Column(String(50), nullable=True)  # 完成原因

    # 父消息（用于回复和编辑）
    parent_id = Column(Integer, ForeignKey("conversation_messages.id"), nullable=True)

    # 批次和分组
    batch_id = Column(String(100), nullable=True)  # 批处理ID
    group_id = Column(String(100), nullable=True)  # 消息组ID

    # 元数据
    metadata = Column(JSON, nullable=True)
    feedback = Column(JSON, nullable=True)  # 用户反馈（点赞/点踩等）

    # Foreign keys
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    context_id = Column(Integer, ForeignKey("contexts.id"), nullable=True)  # 关联的上下文

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User")
    context = relationship("Context")
    parent = relationship("ConversationMessage", remote_side=[id])
    children = relationship("ConversationMessage")

    def __repr__(self):
        return f"<ConversationMessage(id={self.id}, role='{self.role}', sequence={self.sequence})>"


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # 会话统计
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)

    # 会话配置
    model = Column(String(100), nullable=True)
    system_prompt = Column(Text, nullable=True)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)

    # 元数据
    metadata = Column(JSON, nullable=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 可为空（匿名用户）
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)

    # Relationships
    user = relationship("User")
    conversation = relationship("Conversation")

    def __repr__(self):
        return f"<ConversationSession(id={self.id}, session_id='{self.session_id}', active={self.is_active})>"