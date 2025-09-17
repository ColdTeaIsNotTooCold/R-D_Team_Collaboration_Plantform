from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from . import Base


class TaskExecution(Base):
    """任务执行记录表"""
    __tablename__ = "task_executions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    message_id = Column(String(255), nullable=False)  # 消息ID，用于追踪任务消息

    # 执行状态
    status = Column(String(50), default='pending')  # pending, running, completed, failed, cancelled, timeout

    # 时间相关
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time = Column(Float, nullable=True)  # 执行时间（秒）

    # 结果相关
    output_data = Column(Text, nullable=True)  # JSON字符串
    error_message = Column(Text, nullable=True)

    # 重试相关
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # 元数据
    metadata = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    task = relationship("Task", back_populates="executions")
    agent = relationship("Agent", back_populates="executions")
    logs = relationship("ExecutionLog", back_populates="execution")
    queue = relationship("ExecutionQueue", back_populates="execution", uselist=False)

    def __repr__(self):
        return f"<TaskExecution(id={self.id}, task_id={self.task_id}, agent_id={self.agent_id}, status='{self.status}')>"


class ExecutionLog(Base):
    """执行日志表"""
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("task_executions.id"), nullable=False)

    # 日志级别
    level = Column(String(20), default='info')  # debug, info, warning, error, critical

    # 日志内容
    message = Column(Text, nullable=False)

    # 上下文信息
    context = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    execution = relationship("TaskExecution", back_populates="logs")

    def __repr__(self):
        return f"<ExecutionLog(id={self.id}, execution_id={self.execution_id}, level='{self.level}')>"


class ExecutionMetrics(Base):
    """执行指标表"""
    __tablename__ = "execution_metrics"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)

    # 指标数据
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    timeout_executions = Column(Integer, default=0)
    cancelled_executions = Column(Integer, default=0)

    # 时间相关指标
    average_execution_time = Column(Float, default=0.0)
    max_execution_time = Column(Float, default=0.0)
    min_execution_time = Column(Float, default=0.0)

    # 错误率
    error_rate = Column(Float, default=0.0)

    # 统计时间范围
    metric_date = Column(DateTime(timezone=True), nullable=False)
    metric_hour = Column(Integer, nullable=True)  # 小时粒度统计

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    agent = relationship("Agent", back_populates="metrics")

    def __repr__(self):
        return f"<ExecutionMetrics(id={self.id}, agent_id={self.agent_id}, metric_date='{self.metric_date}')>"


class AgentWorkload(Base):
    """Agent工作负载表"""
    __tablename__ = "agent_workloads"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)

    # 负载指标
    current_tasks = Column(Integer, default=0)
    max_concurrent_tasks = Column(Integer, default=5)

    # 性能指标
    avg_task_completion_time = Column(Float, default=0.0)
    tasks_per_hour = Column(Float, default=0.0)

    # 状态
    is_overloaded = Column(String(10), default='false')  # true, false

    # 记录时间
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    agent = relationship("Agent", back_populates="workloads")

    def __repr__(self):
        return f"<AgentWorkload(id={self.id}, agent_id={self.agent_id}, current_tasks={self.current_tasks})>"


class ExecutionQueue(Base):
    """执行队列表"""
    __tablename__ = "execution_queues"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("task_executions.id"), nullable=False)

    # 队列状态
    queue_status = Column(String(50), default='pending')  # pending, queued, processing, completed, failed

    # 优先级
    priority = Column(String(20), default='medium')  # low, medium, high, urgent

    # 队列位置
    queue_position = Column(Integer, nullable=True)

    # 预估时间
    estimated_start_time = Column(DateTime(timezone=True), nullable=True)
    estimated_completion_time = Column(DateTime(timezone=True), nullable=True)

    # 实际时间
    actual_start_time = Column(DateTime(timezone=True), nullable=True)
    actual_completion_time = Column(DateTime(timezone=True), nullable=True)

    # 等待时间
    wait_time = Column(Float, default=0.0)  # 等待时间（秒）

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    execution = relationship("TaskExecution", back_populates="queue")

    def __repr__(self):
        return f"<ExecutionQueue(id={self.id}, execution_id={self.execution_id}, queue_status='{self.queue_status}')>"