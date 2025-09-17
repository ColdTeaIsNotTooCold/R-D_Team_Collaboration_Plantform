"""
Agent客户端
提供Agent注册、发现和通信的客户端功能
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp
from pydantic import BaseModel

from ..schemas.agent import AgentRegistryRequest, AgentDiscoveryRequest
from .registry import get_agent_registry

logger = logging.getLogger(__name__)


class AgentClient:
    """Agent客户端"""

    def __init__(self, registry_url: str = "http://localhost:8000"):
        self.registry_url = registry_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.agent_id: Optional[str] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.is_running = False

    async def start(self):
        """启动客户端"""
        if self.is_running:
            return

        self.session = aiohttp.ClientSession()
        self.is_running = True
        logger.info("Agent客户端启动成功")

    async def stop(self):
        """停止客户端"""
        if not self.is_running:
            return

        self.is_running = False

        # 停止心跳任务
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        # 关闭会话
        if self.session:
            await self.session.close()

        logger.info("Agent客户端停止成功")

    async def register_agent(self, agent_data: Dict[str, Any]) -> str:
        """注册Agent"""
        if not self.session:
            raise RuntimeError("客户端未启动")

        try:
            async with self.session.post(
                f"{self.registry_url}/api/v1/agents/register",
                json=agent_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.agent_id = result["id"]

                    # 启动心跳任务
                    self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                    logger.info(f"Agent注册成功: {self.agent_id}")
                    return self.agent_id
                else:
                    error_text = await response.text()
                    raise RuntimeError(f"注册失败: {error_text}")
        except Exception as e:
            logger.error(f"Agent注册失败: {e}")
            raise

    async def unregister_agent(self):
        """注销Agent"""
        if not self.session or not self.agent_id:
            return

        try:
            async with self.session.delete(
                f"{self.registry_url}/api/v1/agents/{self.agent_id}"
            ) as response:
                if response.status == 200:
                    logger.info(f"Agent注销成功: {self.agent_id}")
                    self.agent_id = None
                else:
                    logger.error(f"Agent注销失败: {response.status}")
        except Exception as e:
            logger.error(f"Agent注销失败: {e}")

    async def discover_agents(self, required_capabilities: List[str] = None) -> List[Dict[str, Any]]:
        """发现Agent"""
        if not self.session:
            raise RuntimeError("客户端未启动")

        try:
            discovery_data = {
                "required_capabilities": required_capabilities or []
            }

            async with self.session.post(
                f"{self.registry_url}/api/v1/agents/discover",
                json=discovery_data
            ) as response:
                if response.status == 200:
                    agents = await response.json()
                    logger.info(f"发现 {len(agents)} 个Agent")
                    return agents
                else:
                    error_text = await response.text()
                    raise RuntimeError(f"发现失败: {error_text}")
        except Exception as e:
            logger.error(f"Agent发现失败: {e}")
            raise

    async def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """获取Agent信息"""
        if not self.session:
            raise RuntimeError("客户端未启动")

        try:
            async with self.session.get(
                f"{self.registry_url}/api/v1/agents/{agent_id}"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise RuntimeError(f"获取Agent信息失败: {response.status}")
        except Exception as e:
            logger.error(f"获取Agent信息失败: {e}")
            raise

    async def execute_task(self, agent_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        if not self.session:
            raise RuntimeError("客户端未启动")

        try:
            async with self.session.post(
                f"{self.registry_url}/api/v1/agents/{agent_id}/execute",
                json=task_data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise RuntimeError(f"任务执行失败: {error_text}")
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            raise

    async def update_capabilities(self, new_capabilities: List[str]):
        """更新Agent能力"""
        if not self.session or not self.agent_id:
            return

        try:
            async with self.session.put(
                f"{self.registry_url}/api/v1/agents/{self.agent_id}/capabilities",
                json=new_capabilities
            ) as response:
                if response.status == 200:
                    logger.info(f"Agent能力更新成功: {self.agent_id}")
                else:
                    error_text = await response.text()
                    raise RuntimeError(f"能力更新失败: {error_text}")
        except Exception as e:
            logger.error(f"Agent能力更新失败: {e}")
            raise

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.is_running and self.agent_id:
            try:
                await self._send_heartbeat()
                await asyncio.sleep(30)  # 30秒心跳间隔
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳发送失败: {e}")
                await asyncio.sleep(5)  # 错误后短暂等待

    async def _send_heartbeat(self):
        """发送心跳"""
        if not self.session or not self.agent_id:
            return

        try:
            async with self.session.post(
                f"{self.registry_url}/api/v1/agents/{self.agent_id}/heartbeat"
            ) as response:
                if response.status == 200:
                    logger.debug(f"心跳发送成功: {self.agent_id}")
                else:
                    logger.warning(f"心跳发送失败: {response.status}")
        except Exception as e:
            logger.error(f"心跳发送异常: {e}")

    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.session:
            raise RuntimeError("客户端未启动")

        try:
            async with self.session.get(
                f"{self.registry_url}/api/v1/agents/statistics/summary"
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise RuntimeError(f"获取统计信息失败: {error_text}")
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise


class SimpleAgentClient:
    """简化的Agent客户端"""

    def __init__(self):
        self.registry = None

    async def initialize(self):
        """初始化客户端"""
        self.registry = await get_agent_registry()

    async def register(self, name: str, agent_type: str, capabilities: List[str], endpoint: str) -> str:
        """注册Agent"""
        if not self.registry:
            await self.initialize()

        agent_data = {
            "name": name,
            "agent_type": agent_type,
            "capabilities": capabilities,
            "endpoint": endpoint,
            "description": f"{name} - {agent_type}"
        }

        return await self.registry.register_agent(agent_data)

    async def discover(self, capabilities: List[str] = None) -> List[Dict[str, Any]]:
        """发现Agent"""
        if not self.registry:
            await self.initialize()

        return await self.registry.discover_agents(capabilities or [])

    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """获取Agent信息"""
        if not self.registry:
            await self.initialize()

        return await self.registry.get_agent(agent_id)

    async def list_agents(self, agent_type: str = None) -> List[Dict[str, Any]]:
        """列出Agent"""
        if not self.registry:
            await self.initialize()

        return await self.registry.list_agents(agent_type)


# 使用示例
async def example_usage():
    """使用示例"""
    # 创建客户端
    client = AgentClient()

    try:
        # 启动客户端
        await client.start()

        # 注册Agent
        agent_id = await client.register_agent({
            "name": "Code Review Agent",
            "agent_type": "code_review",
            "description": "专门进行代码审查的AI Agent",
            "capabilities": ["python", "javascript", "code_analysis"],
            "endpoint": "http://localhost:8001",
            "health_check_url": "http://localhost:8001/health"
        })

        print(f"Agent注册成功: {agent_id}")

        # 发现Agent
        agents = await client.discover_agents(["python", "code_analysis"])
        print(f"发现 {len(agents)} 个相关Agent")

        # 执行任务
        task_result = await client.execute_task(agent_id, {
            "type": "code_review",
            "code": "print('Hello, World!')",
            "language": "python"
        })
        print(f"任务执行结果: {task_result}")

    finally:
        # 停止客户端
        await client.stop()


if __name__ == "__main__":
    asyncio.run(example_usage())