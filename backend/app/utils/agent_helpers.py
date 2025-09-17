"""
Agent工具函数
提供Agent管理和辅助功能
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Type, Union
import redis.asyncio as redis
from datetime import datetime, timedelta

from ..agents.base import BaseAgent, AgentConfig, AgentCapability, AgentMessage, AgentStatus

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Agent注册表管理"""

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    async def register_agent(self, agent: BaseAgent) -> bool:
        """注册Agent"""
        try:
            agent_data = {
                "agent_id": agent.config.agent_id,
                "name": agent.config.name,
                "description": agent.config.description,
                "agent_type": agent.config.agent_type,
                "status": agent.status.value,
                "capabilities": json.dumps([cap.dict() for cap in agent.config.capabilities]),
                "max_concurrent_tasks": agent.config.max_concurrent_tasks,
                "last_heartbeat": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }

            # 存储Agent信息
            await self.redis_client.hset(
                f"agent:{agent.config.agent_id}",
                mapping=agent_data
            )

            # 添加到活跃Agent集合
            await self.redis_client.sadd("active_agents", agent.config.agent_id)

            # 按类型索引
            await self.redis_client.sadd(f"agents_by_type:{agent.config.agent_type}", agent.config.agent_id)

            logger.info(f"Agent {agent.config.agent_id} registered successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to register agent {agent.config.agent_id}: {e}")
            return False

    async def unregister_agent(self, agent_id: str) -> bool:
        """注销Agent"""
        try:
            # 获取Agent信息
            agent_info = await self.redis_client.hgetall(f"agent:{agent_id}")
            if not agent_info:
                logger.warning(f"Agent {agent_id} not found for unregistration")
                return False

            agent_type = agent_info.get(b"agent_type", b"").decode()

            # 从集合中移除
            await self.redis_client.srem("active_agents", agent_id)
            await self.redis_client.srem(f"agents_by_type:{agent_type}", agent_id)

            # 删除Agent信息
            await self.redis_client.delete(f"agent:{agent_id}")

            logger.info(f"Agent {agent_id} unregistered successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False

    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取Agent信息"""
        try:
            agent_data = await self.redis_client.hgetall(f"agent:{agent_id}")
            if not agent_data:
                return None

            # 转换字节数据为字符串
            result = {}
            for key, value in agent_data.items():
                key_str = key.decode()
                value_str = value.decode()

                if key_str == "capabilities":
                    result[key_str] = json.loads(value_str)
                else:
                    result[key_str] = value_str

            return result

        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            return None

    async def list_agents(self, agent_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有Agent或指定类型的Agent"""
        try:
            if agent_type:
                agent_ids = await self.redis_client.smembers(f"agents_by_type:{agent_type}")
            else:
                agent_ids = await self.redis_client.smembers("active_agents")

            agents = []
            for agent_id in agent_ids:
                agent_id_str = agent_id.decode()
                agent_info = await self.get_agent(agent_id_str)
                if agent_info:
                    agents.append(agent_info)

            return agents

        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return []

    async def find_agents_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """根据能力查找Agent"""
        try:
            all_agents = await self.list_agents()
            matching_agents = []

            for agent in all_agents:
                capabilities = agent.get("capabilities", [])
                if any(cap.get("name") == capability for cap in capabilities):
                    matching_agents.append(agent)

            return matching_agents

        except Exception as e:
            logger.error(f"Failed to find agents by capability {capability}: {e}")
            return []

    async def update_agent_status(self, agent_id: str, status: AgentStatus) -> bool:
        """更新Agent状态"""
        try:
            await self.redis_client.hset(
                f"agent:{agent_id}",
                "status",
                status.value
            )
            return True

        except Exception as e:
            logger.error(f"Failed to update agent {agent_id} status: {e}")
            return False

    async def check_agent_health(self, agent_id: str) -> bool:
        """检查Agent健康状态"""
        try:
            agent_info = await self.get_agent(agent_id)
            if not agent_info:
                return False

            # 检查最后心跳时间
            last_heartbeat_str = agent_info.get("last_heartbeat")
            if not last_heartbeat_str:
                return False

            last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
            time_diff = datetime.utcnow() - last_heartbeat

            # 如果超过2分钟没有心跳，认为Agent不健康
            return time_diff < timedelta(minutes=2)

        except Exception as e:
            logger.error(f"Failed to check agent {agent_id} health: {e}")
            return False

    async def cleanup_inactive_agents(self, timeout_minutes: int = 5) -> int:
        """清理不活跃的Agent"""
        try:
            all_agents = await self.list_agents()
            cleaned_count = 0

            for agent in all_agents:
                agent_id = agent.get("agent_id")
                if not await self.check_agent_health(agent_id):
                    await self.unregister_agent(agent_id)
                    cleaned_count += 1

            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup inactive agents: {e}")
            return 0


class AgentMessageRouter:
    """Agent消息路由器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.consumer_tasks: Dict[str, asyncio.Task] = {}

    async def start_consuming(self, agent_id: str, callback) -> None:
        """开始为指定Agent消费消息"""
        if agent_id in self.consumer_tasks:
            logger.warning(f"Message consumer for agent {agent_id} already exists")
            return

        stream_name = f"agent_messages:{agent_id}"
        task = asyncio.create_task(self._consume_messages(stream_name, callback))
        self.consumer_tasks[agent_id] = task

        logger.info(f"Started message consumption for agent {agent_id}")

    async def stop_consuming(self, agent_id: str) -> None:
        """停止为指定Agent消费消息"""
        if agent_id in self.consumer_tasks:
            task = self.consumer_tasks[agent_id]
            task.cancel()
            del self.consumer_tasks[agent_id]
            logger.info(f"Stopped message consumption for agent {agent_id}")

    async def _consume_messages(self, stream_name: str, callback) -> None:
        """消费消息的内部实现"""
        last_id = "0"  # 从头开始消费

        while True:
            try:
                # 读取消息
                messages = await self.redis_client.xread(
                    {stream_name: last_id},
                    block=1000,  # 阻塞1秒
                    count=1
                )

                if messages:
                    for stream, message_list in messages:
                        for message_id, fields in message_list:
                            # 处理消息
                            message = self._parse_message(fields)
                            if message:
                                await callback(message)

                            last_id = message_id

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error consuming messages from {stream_name}: {e}")
                await asyncio.sleep(1)  # 错误后等待1秒

    def _parse_message(self, fields: Dict[bytes, bytes]) -> Optional[AgentMessage]:
        """解析Redis消息字段"""
        try:
            # 转换字节数据
            data = {}
            for key, value in fields.items():
                key_str = key.decode()
                value_str = value.decode()

                if key_str == "content":
                    data[key_str] = json.loads(value_str)
                else:
                    data[key_str] = value_str

            return AgentMessage(
                id=data.get("id", ""),
                sender_id=data["sender_id"],
                receiver_id=data["receiver_id"],
                message_type=data["message_type"],
                content=data["content"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                correlation_id=data.get("correlation_id")
            )

        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            return None


class AgentFactory:
    """Agent工厂类"""

    @staticmethod
    def create_agent_config(
        agent_id: str,
        name: str,
        description: str,
        agent_type: str,
        capabilities: List[Dict[str, Any]],
        **kwargs
    ) -> AgentConfig:
        """创建Agent配置"""
        agent_capabilities = []
        for cap_data in capabilities:
            agent_capabilities.append(AgentCapability(**cap_data))

        return AgentConfig(
            agent_id=agent_id,
            name=name,
            description=description,
            agent_type=agent_type,
            capabilities=agent_capabilities,
            **kwargs
        )

    @staticmethod
    def create_simple_agent(config: AgentConfig, redis_client: Optional[redis.Redis] = None) -> "SimpleAgent":
        """创建简单Agent实例"""
        from ..agents.simple import SimpleAgent
        return SimpleAgent(config, redis_client)


async def create_redis_client(host: str = "localhost", port: int = 6379, db: int = 0) -> redis.Redis:
    """创建Redis客户端"""
    return redis.Redis(host=host, port=port, db=db, decode_responses=False)


def create_agent_capabilities(capability_configs: List[Dict[str, Any]]) -> List[AgentCapability]:
    """批量创建Agent能力"""
    capabilities = []
    for config in capability_configs:
        capabilities.append(AgentCapability(**config))
    return capabilities


def validate_agent_config(config: Dict[str, Any]) -> bool:
    """验证Agent配置"""
    required_fields = ["agent_id", "name", "description", "agent_type", "capabilities"]

    for field in required_fields:
        if field not in config:
            logger.error(f"Missing required field: {field}")
            return False

    # 验证能力配置
    capabilities = config.get("capabilities", [])
    for cap in capabilities:
        if not all(key in cap for key in ["name", "description", "input_types", "output_types"]):
            logger.error("Invalid capability configuration")
            return False

    return True


def get_default_capabilities() -> List[AgentCapability]:
    """获取默认的Agent能力"""
    return [
        AgentCapability(
            name="echo",
            description="Echo messages back",
            input_types=["text"],
            output_types=["text"]
        ),
        AgentCapability(
            name="calculate",
            description="Basic mathematical calculations",
            input_types=["numbers"],
            output_types=["number"]
        ),
        AgentCapability(
            name="text_process",
            description="Text processing operations",
            input_types=["text"],
            output_types=["text", "number"]
        ),
        AgentCapability(
            name="status_check",
            description="Check agent status and performance",
            input_types=[""],
            output_types=["dict"]
        )
    ]