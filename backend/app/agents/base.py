"""
基础Agent类实现
提供Agent的核心功能和生命周期管理
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import redis.asyncio as redis
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    PAUSED = "paused"
    ACTIVE = "active"
    INACTIVE = "inactive"


class AgentCapability(BaseModel):
    """Agent能力描述"""
    name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AgentMessage(BaseModel):
    """Agent消息结构"""
    id: str
    sender_id: str
    receiver_id: str
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None


class AgentConfig(BaseModel):
    """Agent配置"""
    agent_id: str
    name: str
    description: str
    agent_type: str
    capabilities: List[AgentCapability]
    model_config: Dict[str, Any] = Field(default_factory=dict)
    system_prompt: Optional[str] = None
    max_concurrent_tasks: int = 3
    timeout_seconds: int = 300


class BaseAgent(ABC):
    """Agent基类"""

    def __init__(self, config: AgentConfig, redis_client: Optional[redis.Redis] = None):
        self.config = config
        self.redis_client = redis_client
        self.status = AgentStatus.IDLE
        self.tasks: Dict[str, asyncio.Task] = {}
        self.message_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self._stop_event = asyncio.Event()
        self._health_check_interval = 30
        self._health_check_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """启动Agent"""
        if self.status != AgentStatus.STOPPED and self.status != AgentStatus.IDLE:
            logger.warning(f"Agent {self.config.agent_id} is already running")
            return

        logger.info(f"Starting agent {self.config.agent_id}")
        self.status = AgentStatus.RUNNING
        self._stop_event.clear()

        # 启动消息处理任务
        self.tasks["message_processor"] = asyncio.create_task(self._process_messages())

        # 启动健康检查任务
        self._health_check_task = asyncio.create_task(self._health_check_loop())

        # 注册Agent到Redis
        await self._register_agent()

        logger.info(f"Agent {self.config.agent_id} started successfully")

    async def stop(self) -> None:
        """停止Agent"""
        if self.status == AgentStatus.STOPPED:
            return

        logger.info(f"Stopping agent {self.config.agent_id}")
        self.status = AgentStatus.STOPPED
        self._stop_event.set()

        # 取消所有任务
        for task_id, task in self.tasks.items():
            if not task.done():
                task.cancel()

        # 取消健康检查任务
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()

        # 注销Agent
        await self._unregister_agent()

        logger.info(f"Agent {self.config.agent_id} stopped successfully")

    async def send_message(self, message: AgentMessage) -> None:
        """发送消息到其他Agent"""
        if not self.redis_client:
            raise ValueError("Redis client not configured")

        try:
            # 将消息发送到Redis Stream
            stream_name = f"agent_messages:{message.receiver_id}"
            message_data = {
                "sender_id": message.sender_id,
                "receiver_id": message.receiver_id,
                "message_type": message.message_type,
                "content": json.dumps(message.content),
                "timestamp": message.timestamp.isoformat(),
                "correlation_id": message.correlation_id or ""
            }

            await self.redis_client.xadd(stream_name, message_data)
            logger.debug(f"Message sent from {message.sender_id} to {message.receiver_id}")

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise

    async def receive_message(self, message: AgentMessage) -> None:
        """接收消息并加入队列"""
        await self.message_queue.put(message)
        logger.debug(f"Message received from {message.sender_id}")

    async def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        if self.status != AgentStatus.RUNNING:
            raise RuntimeError(f"Agent {self.config.agent_id} is not running")

        if len(self.tasks) >= self.config.max_concurrent_tasks:
            raise RuntimeError(f"Agent {self.config.agent_id} is at maximum capacity")

        task_id = f"task_{datetime.utcnow().timestamp()}"
        logger.info(f"Executing task {task_id} on agent {self.config.agent_id}")

        try:
            # 创建任务执行协程
            task_coro = self._execute_task_impl(task_data)

            # 设置超时
            result = await asyncio.wait_for(
                task_coro,
                timeout=self.config.timeout_seconds
            )

            logger.info(f"Task {task_id} completed successfully")
            return {
                "task_id": task_id,
                "status": "completed",
                "result": result,
                "agent_id": self.config.agent_id
            }

        except asyncio.TimeoutError:
            logger.error(f"Task {task_id} timed out")
            return {
                "task_id": task_id,
                "status": "timeout",
                "error": "Task execution timed out",
                "agent_id": self.config.agent_id
            }
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            return {
                "task_id": task_id,
                "status": "error",
                "error": str(e),
                "agent_id": self.config.agent_id
            }

    @abstractmethod
    async def _execute_task_impl(self, task_data: Dict[str, Any]) -> Any:
        """子类实现的具体任务执行逻辑"""
        pass

    @abstractmethod
    async def _handle_message(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        """子类实现的消息处理逻辑"""
        pass

    async def _process_messages(self) -> None:
        """处理消息队列"""
        while not self._stop_event.is_set():
            try:
                # 设置超时以避免阻塞
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )

                # 处理消息
                response = await self._handle_message(message)

                # 如果需要回复
                if response and message.correlation_id:
                    reply_message = AgentMessage(
                        id=f"msg_{datetime.utcnow().timestamp()}",
                        sender_id=self.config.agent_id,
                        receiver_id=message.sender_id,
                        message_type="response",
                        content=response,
                        correlation_id=message.correlation_id
                    )
                    await self.send_message(reply_message)

                self.message_queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def _register_agent(self) -> None:
        """注册Agent到Redis"""
        if not self.redis_client:
            return

        try:
            agent_data = {
                "agent_id": self.config.agent_id,
                "name": self.config.name,
                "description": self.config.description,
                "agent_type": self.config.agent_type,
                "status": self.status.value,
                "capabilities": json.dumps([cap.dict() for cap in self.config.capabilities]),
                "last_heartbeat": datetime.utcnow().isoformat()
            }

            # 存储Agent信息
            await self.redis_client.hset(
                f"agent:{self.config.agent_id}",
                mapping=agent_data
            )

            # 添加到活跃Agent集合
            await self.redis_client.sadd("active_agents", self.config.agent_id)

            logger.info(f"Agent {self.config.agent_id} registered")

        except Exception as e:
            logger.error(f"Failed to register agent: {e}")

    async def _unregister_agent(self) -> None:
        """从Redis注销Agent"""
        if not self.redis_client:
            return

        try:
            # 从活跃Agent集合中移除
            await self.redis_client.srem("active_agents", self.config.agent_id)

            # 删除Agent信息
            await self.redis_client.delete(f"agent:{self.config.agent_id}")

            logger.info(f"Agent {self.config.agent_id} unregistered")

        except Exception as e:
            logger.error(f"Failed to unregister agent: {e}")

    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self._health_check_interval)

                # 更新心跳
                if self.redis_client:
                    await self.redis_client.hset(
                        f"agent:{self.config.agent_id}",
                        "last_heartbeat",
                        datetime.utcnow().isoformat()
                    )

                # 执行自定义健康检查
                await self._custom_health_check()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                self.status = AgentStatus.ERROR

    async def _custom_health_check(self) -> None:
        """子类可重写的自定义健康检查"""
        pass

    def get_capabilities(self) -> List[AgentCapability]:
        """获取Agent能力列表"""
        return self.config.capabilities

    def has_capability(self, capability_name: str) -> bool:
        """检查是否具有特定能力"""
        return any(cap.name == capability_name for cap in self.config.capabilities)

    def get_status(self) -> AgentStatus:
        """获取Agent状态"""
        return self.status

    def get_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "agent_id": self.config.agent_id,
            "name": self.config.name,
            "description": self.config.description,
            "agent_type": self.config.agent_type,
            "status": self.status.value,
            "capabilities": [cap.dict() for cap in self.config.capabilities],
            "active_tasks": len(self.tasks),
            "max_concurrent_tasks": self.config.max_concurrent_tasks
        }