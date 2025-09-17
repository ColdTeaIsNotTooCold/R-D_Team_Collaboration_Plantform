"""
Agent注册中心服务
提供Agent的注册、发现、健康检查和能力管理功能
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import redis.asyncio as redis
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.agent import Agent
from ..core.database import get_db
from ..schemas.agent import AgentCreate, AgentUpdate, AgentStatus, AgentCapability

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Agent注册中心"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.agents: Dict[str, Dict] = {}
        self.capabilities: Dict[str, List[str]] = {}
        self.health_checks: Dict[str, datetime] = {}
        self.heartbeat_interval = 30  # 秒
        self.health_check_timeout = 60  # 秒

    async def initialize(self):
        """初始化注册中心"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Agent注册中心初始化成功")
        except Exception as e:
            logger.error(f"Agent注册中心初始化失败: {e}")
            raise

    async def register_agent(self, agent_data: Dict[str, Any]) -> str:
        """注册Agent"""
        agent_id = agent_data.get("id") or f"agent_{datetime.now().timestamp()}"

        # 验证必要字段
        required_fields = ["name", "agent_type", "capabilities", "endpoint"]
        for field in required_fields:
            if field not in agent_data:
                raise ValueError(f"缺少必要字段: {field}")

        # 构建Agent信息
        agent_info = {
            "id": agent_id,
            "name": agent_data["name"],
            "agent_type": agent_data["agent_type"],
            "description": agent_data.get("description", ""),
            "capabilities": agent_data["capabilities"],
            "endpoint": agent_data["endpoint"],
            "status": "active",
            "metadata": agent_data.get("metadata", {}),
            "registered_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat()
        }

        # 存储到Redis
        await self.redis_client.hset(
            f"agent:{agent_id}",
            mapping=agent_info
        )

        # 添加到能力索引
        for capability in agent_data["capabilities"]:
            await self.redis_client.sadd(f"capability:{capability}", agent_id)

        # 设置心跳
        await self.redis_client.setex(
            f"heartbeat:{agent_id}",
            self.health_check_timeout * 2,
            datetime.now().isoformat()
        )

        logger.info(f"Agent {agent_id} 注册成功")
        return agent_id

    async def unregister_agent(self, agent_id: str):
        """注销Agent"""
        # 获取Agent信息
        agent_info = await self.redis_client.hgetall(f"agent:{agent_id}")
        if not agent_info:
            raise ValueError(f"Agent {agent_id} 不存在")

        # 从Redis删除
        await self.redis_client.delete(f"agent:{agent_id}")
        await self.redis_client.delete(f"heartbeat:{agent_id}")

        # 从能力索引中移除
        capabilities = agent_info.get("capabilities", "[]")
        try:
            caps = json.loads(capabilities)
            for capability in caps:
                await self.redis_client.srem(f"capability:{capability}", agent_id)
        except:
            pass

        logger.info(f"Agent {agent_id} 注销成功")

    async def update_heartbeat(self, agent_id: str):
        """更新Agent心跳"""
        await self.redis_client.setex(
            f"heartbeat:{agent_id}",
            self.health_check_timeout * 2,
            datetime.now().isoformat()
        )

        # 更新Agent信息中的最后心跳时间
        await self.redis_client.hset(
            f"agent:{agent_id}",
            "last_heartbeat",
            datetime.now().isoformat()
        )

    async def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取Agent信息"""
        agent_info = await self.redis_client.hgetall(f"agent:{agent_id}")
        if not agent_info:
            return None

        # 检查心跳状态
        last_heartbeat = await self.redis_client.get(f"heartbeat:{agent_id}")
        if last_heartbeat:
            heartbeat_time = datetime.fromisoformat(last_heartbeat)
            if datetime.now() - heartbeat_time > timedelta(seconds=self.health_check_timeout):
                agent_info["status"] = "inactive"
            else:
                agent_info["status"] = "active"

        return agent_info

    async def list_agents(self, agent_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有Agent"""
        agent_keys = await self.redis_client.keys("agent:*")
        agents = []

        for key in agent_keys:
            agent_id = key.split(":")[1]
            agent_info = await self.get_agent(agent_id)
            if agent_info:
                if agent_type is None or agent_info.get("agent_type") == agent_type:
                    agents.append(agent_info)

        return agents

    async def discover_agents(self, required_capabilities: List[str]) -> List[Dict[str, Any]]:
        """发现具有特定能力的Agent"""
        if not required_capabilities:
            return await self.list_agents()

        # 查找具有所有必要能力的Agent
        candidate_agents = None
        for capability in required_capabilities:
            agent_ids = await self.redis_client.smembers(f"capability:{capability}")
            if candidate_agents is None:
                candidate_agents = set(agent_ids)
            else:
                candidate_agents = candidate_agents.intersection(set(agent_ids))

        if not candidate_agents:
            return []

        # 获取Agent详细信息
        agents = []
        for agent_id in candidate_agents:
            agent_info = await self.get_agent(agent_id)
            if agent_info and agent_info.get("status") == "active":
                agents.append(agent_info)

        return agents

    async def health_check(self, agent_id: str) -> bool:
        """检查Agent健康状态"""
        agent_info = await self.get_agent(agent_id)
        if not agent_info:
            return False

        # 检查心跳
        last_heartbeat = await self.redis_client.get(f"heartbeat:{agent_id}")
        if not last_heartbeat:
            return False

        heartbeat_time = datetime.fromisoformat(last_heartbeat)
        if datetime.now() - heartbeat_time > timedelta(seconds=self.health_check_timeout):
            return False

        return True

    async def update_agent_capabilities(self, agent_id: str, capabilities: List[str]):
        """更新Agent能力"""
        agent_info = await self.redis_client.hgetall(f"agent:{agent_id}")
        if not agent_info:
            raise ValueError(f"Agent {agent_id} 不存在")

        # 获取旧能力
        old_capabilities = json.loads(agent_info.get("capabilities", "[]"))

        # 更新能力
        await self.redis_client.hset(
            f"agent:{agent_id}",
            "capabilities",
            json.dumps(capabilities)
        )

        # 更新能力索引
        # 移除旧能力
        for capability in old_capabilities:
            await self.redis_client.srem(f"capability:{capability}", agent_id)

        # 添加新能力
        for capability in capabilities:
            await self.redis_client.sadd(f"capability:{capability}", agent_id)

        logger.info(f"Agent {agent_id} 能力更新成功")

    async def get_agent_statistics(self) -> Dict[str, Any]:
        """获取注册中心统计信息"""
        agent_keys = await self.redis_client.keys("agent:*")
        total_agents = len(agent_keys)

        active_agents = 0
        inactive_agents = 0
        capability_counts = {}
        type_counts = {}

        for key in agent_keys:
            agent_id = key.split(":")[1]
            agent_info = await self.get_agent(agent_id)
            if agent_info:
                if agent_info.get("status") == "active":
                    active_agents += 1
                else:
                    inactive_agents += 1

                # 统计能力
                capabilities = json.loads(agent_info.get("capabilities", "[]"))
                for capability in capabilities:
                    capability_counts[capability] = capability_counts.get(capability, 0) + 1

                # 统计类型
                agent_type = agent_info.get("agent_type", "unknown")
                type_counts[agent_type] = type_counts.get(agent_type, 0) + 1

        return {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "inactive_agents": inactive_agents,
            "capability_distribution": capability_counts,
            "type_distribution": type_counts
        }

    async def cleanup_inactive_agents(self):
        """清理不活跃的Agent"""
        agent_keys = await self.redis_client.keys("agent:*")
        cleaned_count = 0

        for key in agent_keys:
            agent_id = key.split(":")[1]
            if not await self.health_check(agent_id):
                await self.unregister_agent(agent_id)
                cleaned_count += 1

        logger.info(f"清理了 {cleaned_count} 个不活跃的Agent")
        return cleaned_count


# 全局注册中心实例
agent_registry = AgentRegistry()


async def get_agent_registry() -> AgentRegistry:
    """获取Agent注册中心实例"""
    if agent_registry.redis_client is None:
        await agent_registry.initialize()
    return agent_registry