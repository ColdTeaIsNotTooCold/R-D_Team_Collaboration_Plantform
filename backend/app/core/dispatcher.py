import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from ..models.agent import Agent as AgentModel
from ..models.task import Task as TaskModel
from ..schemas.task import TaskCreate, TaskUpdate, TaskDispatchRequest, TaskDispatchResponse, TaskStatus
from ..core.redis import get_redis_stream, redis_client
from ..core.database import get_db

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentLifecycleManager:
    """Agent生命周期管理器"""

    def __init__(self):
        self.agents: Dict[int, Dict[str, Any]] = {}
        self.redis_stream = get_redis_stream()
        self.agent_streams = "agent_tasks"
        self.agent_status_prefix = "agent_status:"

    async def register_agent(self, agent_id: int, agent_type: str, capabilities: List[str]) -> bool:
        """注册Agent"""
        try:
            # 创建Agent状态记录
            agent_info = {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "capabilities": capabilities,
                "status": AgentStatus.IDLE.value,
                "current_task": None,
                "registered_at": datetime.now().isoformat(),
                "last_heartbeat": datetime.now().isoformat(),
                "error_count": 0
            }

            self.agents[agent_id] = agent_info

            # 在Redis中存储Agent状态
            redis_client.set(
                f"{self.agent_status_prefix}{agent_id}",
                json.dumps(agent_info),
                ex=300  # 5分钟过期
            )

            # 创建Agent专用的任务流
            agent_stream_name = f"{self.agent_streams}:{agent_id}"
            self.redis_stream.create_consumer_group(agent_stream_name, f"agent_{agent_id}")

            logger.info(f"Agent {agent_id} registered successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    async def unregister_agent(self, agent_id: int) -> bool:
        """注销Agent"""
        try:
            if agent_id in self.agents:
                # 清理Agent状态
                del self.agents[agent_id]

                # 从Redis中删除状态
                redis_client.delete(f"{self.agent_status_prefix}{agent_id}")

                logger.info(f"Agent {agent_id} unregistered successfully")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False

    async def update_agent_status(self, agent_id: int, status: AgentStatus,
                                 current_task: Optional[int] = None) -> bool:
        """更新Agent状态"""
        try:
            if agent_id not in self.agents:
                return False

            self.agents[agent_id]["status"] = status.value
            self.agents[agent_id]["last_heartbeat"] = datetime.now().isoformat()

            if current_task is not None:
                self.agents[agent_id]["current_task"] = current_task

            # 更新Redis中的状态
            redis_client.set(
                f"{self.agent_status_prefix}{agent_id}",
                json.dumps(self.agents[agent_id]),
                ex=300
            )

            return True

        except Exception as e:
            logger.error(f"Failed to update agent {agent_id} status: {e}")
            return False

    async def get_agent_status(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """获取Agent状态"""
        try:
            # 先从内存中获取
            if agent_id in self.agents:
                return self.agents[agent_id]

            # 尝试从Redis中获取
            agent_data = redis_client.get(f"{self.agent_status_prefix}{agent_id}")
            if agent_data:
                return json.loads(agent_data)

            return None

        except Exception as e:
            logger.error(f"Failed to get agent {agent_id} status: {e}")
            return None

    async def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有活跃的Agent"""
        try:
            active_agents = []
            for agent_id, agent_info in self.agents.items():
                # 检查心跳是否超时
                last_heartbeat = datetime.fromisoformat(agent_info["last_heartbeat"])
                if datetime.now() - last_heartbeat < timedelta(minutes=5):
                    active_agents.append(agent_info)

            return active_agents

        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return []

    async def send_heartbeat(self, agent_id: int) -> bool:
        """Agent心跳检测"""
        try:
            if agent_id in self.agents:
                self.agents[agent_id]["last_heartbeat"] = datetime.now().isoformat()

                # 更新Redis中的状态
                redis_client.set(
                    f"{self.agent_status_prefix}{agent_id}",
                    json.dumps(self.agents[agent_id]),
                    ex=300
                )

                return True

            return False

        except Exception as e:
            logger.error(f"Failed to send heartbeat for agent {agent_id}: {e}")
            return False


class TaskDispatcher:
    """任务分发器"""

    def __init__(self):
        self.agent_manager = AgentLifecycleManager()
        self.redis_stream = get_redis_stream()
        self.task_queue = "task_queue"
        self.task_results = "task_results"

        # 创建任务队列的消费者组
        self.redis_stream.create_consumer_group(self.task_queue, "dispatcher")

    async def dispatch_task(self, task: TaskCreate, db: Session) -> Optional[TaskDispatchResponse]:
        """分发任务到合适的Agent"""
        try:
            # 1. 查找合适的Agent
            suitable_agents = await self._find_suitable_agents(task.task_type, db)

            if not suitable_agents:
                logger.warning(f"No suitable agent found for task type: {task.task_type}")
                return None

            # 2. 选择最优的Agent（负载均衡）
            selected_agent = await self._select_best_agent(suitable_agents)

            if not selected_agent:
                logger.warning("No agent available for task assignment")
                return None

            # 3. 创建任务记录
            task_data = task.dict()
            task_data["status"] = TaskStatus.ASSIGNED.value
            task_data["assigned_agent_id"] = selected_agent["agent_id"]
            task_data["assigned_at"] = datetime.now().isoformat()

            # 4. 发送任务到Agent
            agent_stream_name = f"{self.agent_manager.agent_streams}:{selected_agent['agent_id']}"
            task_message = {
                "task_id": str(uuid.uuid4()),
                "task_data": task_data,
                "created_at": datetime.now().isoformat(),
                "priority": task.priority.value if hasattr(task.priority, 'value') else task.priority
            }

            message_id = self.redis_stream.add_message(agent_stream_name, task_message)

            # 5. 更新Agent状态
            await self.agent_manager.update_agent_status(
                selected_agent["agent_id"],
                AgentStatus.RUNNING,
                current_task=int(task_message["task_id"])
            )

            logger.info(f"Task dispatched to agent {selected_agent['agent_id']}")

            return TaskDispatchResponse(
                task_id=task_message["task_id"],
                agent_id=selected_agent["agent_id"],
                message_id=message_id,
                status=TaskStatus.ASSIGNED,
                dispatched_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Failed to dispatch task: {e}")
            return None

    async def _find_suitable_agents(self, task_type: str, db: Session) -> List[Dict[str, Any]]:
        """查找适合处理任务的Agent"""
        try:
            suitable_agents = []
            active_agents = await self.agent_manager.list_agents()

            # 查询数据库中符合类型的Agent
            db_agents = db.query(AgentModel).filter(
                AgentModel.agent_type == task_type,
                AgentModel.is_active == True
            ).all()

            # 匹配活跃的数据库Agent
            for db_agent in db_agents:
                for active_agent in active_agents:
                    if active_agent["agent_id"] == db_agent.id:
                        suitable_agents.append(active_agent)
                        break

            return suitable_agents

        except Exception as e:
            logger.error(f"Failed to find suitable agents: {e}")
            return []

    async def _select_best_agent(self, agents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """选择最优的Agent（基于负载均衡）"""
        try:
            if not agents:
                return None

            # 简单的负载均衡：选择状态为idle的agent
            idle_agents = [agent for agent in agents if agent["status"] == AgentStatus.IDLE.value]

            if idle_agents:
                # 选择错误计数最少的idle agent
                return min(idle_agents, key=lambda x: x["error_count"])

            # 如果没有idle agent，选择所有agent中错误计数最少的
            return min(agents, key=lambda x: x["error_count"])

        except Exception as e:
            logger.error(f"Failed to select best agent: {e}")
            return None

    async def dispatch_task_with_capabilities(self, task_request: TaskDispatchRequest, db: Session) -> Optional[TaskDispatchResponse]:
        """根据能力需求分发任务"""
        try:
            # 1. 查找具有所需能力的Agent
            suitable_agents = await self._find_agents_by_capabilities(task_request.required_capabilities, db)

            if not suitable_agents:
                logger.warning(f"No suitable agent found for capabilities: {task_request.required_capabilities}")
                return None

            # 2. 如果指定了任务类型，进一步过滤
            if task_request.task_type:
                suitable_agents = [agent for agent in suitable_agents if agent.get("agent_type") == task_request.task_type]

            if not suitable_agents:
                logger.warning(f"No suitable agent found for task type: {task_request.task_type}")
                return None

            # 3. 选择最优的Agent（负载均衡）
            selected_agent = await self._select_best_agent(suitable_agents)

            if not selected_agent:
                logger.warning("No agent available for task assignment")
                return None

            # 4. 创建任务数据
            task_data = {
                "title": task_request.title,
                "description": task_request.description,
                "task_type": task_request.task_type,
                "priority": task_request.priority.value if hasattr(task_request.priority, 'value') else task_request.priority,
                "input_data": task_request.input_data,
                "metadata": task_request.metadata,
                "status": TaskStatus.ASSIGNED.value,
                "assigned_agent_id": selected_agent["agent_id"],
                "assigned_at": datetime.now().isoformat()
            }

            # 5. 发送任务到Agent
            agent_stream_name = f"{self.agent_manager.agent_streams}:{selected_agent['agent_id']}"
            task_message = {
                "task_id": str(task_request.task_id) if task_request.task_id else str(uuid.uuid4()),
                "task_data": task_data,
                "created_at": datetime.now().isoformat(),
                "priority": task_request.priority.value if hasattr(task_request.priority, 'value') else task_request.priority,
                "timeout": task_request.timeout,
                "required_capabilities": task_request.required_capabilities
            }

            message_id = self.redis_stream.add_message(agent_stream_name, task_message)

            # 6. 更新Agent状态
            await self.agent_manager.update_agent_status(
                selected_agent["agent_id"],
                AgentStatus.RUNNING,
                current_task=int(task_message["task_id"])
            )

            logger.info(f"Task with capabilities dispatched to agent {selected_agent['agent_id']}")

            return TaskDispatchResponse(
                task_id=task_message["task_id"],
                agent_id=selected_agent["agent_id"],
                message_id=message_id,
                status=TaskStatus.ASSIGNED,
                dispatched_at=datetime.now().isoformat()
            )

        except Exception as e:
            logger.error(f"Failed to dispatch task with capabilities: {e}")
            return None

    async def _find_agents_by_capabilities(self, required_capabilities: List[str], db: Session) -> List[Dict[str, Any]]:
        """根据能力需求查找Agent"""
        try:
            if not required_capabilities:
                return await self._find_suitable_agents("general", db)

            # 获取所有活跃的Agent
            active_agents = await self.agent_manager.list_agents()

            # 过滤具有所需能力的Agent
            capable_agents = []
            for agent in active_agents:
                agent_capabilities = agent.get("capabilities", [])
                if all(cap in agent_capabilities for cap in required_capabilities):
                    capable_agents.append(agent)

            return capable_agents

        except Exception as e:
            logger.error(f"Failed to find agents by capabilities: {e}")
            return []

    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        try:
            results = self.redis_stream.read_messages(self.task_results, count=1)

            for result in results:
                if result["data"].get("task_id") == task_id:
                    return result["data"]

            return None

        except Exception as e:
            logger.error(f"Failed to get task result {task_id}: {e}")
            return None

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            # 发送取消消息到所有Agent流
            active_agents = await self.agent_manager.list_agents()

            for agent in active_agents:
                agent_stream_name = f"{self.agent_manager.agent_streams}:{agent['agent_id']}"
                cancel_message = {
                    "type": "cancel",
                    "task_id": task_id,
                    "cancelled_at": datetime.now().isoformat()
                }

                self.redis_stream.add_message(agent_stream_name, cancel_message)

            logger.info(f"Cancel message sent for task {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False

    async def get_agent_load(self) -> Dict[str, Any]:
        """获取Agent负载情况"""
        try:
            active_agents = await self.agent_manager.list_agents()

            load_stats = {
                "total_agents": len(active_agents),
                "idle_agents": 0,
                "running_agents": 0,
                "error_agents": 0,
                "agents": []
            }

            for agent in active_agents:
                status = agent["status"]
                if status == AgentStatus.IDLE.value:
                    load_stats["idle_agents"] += 1
                elif status == AgentStatus.RUNNING.value:
                    load_stats["running_agents"] += 1
                elif status == AgentStatus.ERROR.value:
                    load_stats["error_agents"] += 1

                load_stats["agents"].append({
                    "agent_id": agent["agent_id"],
                    "agent_type": agent["agent_type"],
                    "status": status,
                    "current_task": agent["current_task"],
                    "error_count": agent["error_count"]
                })

            return load_stats

        except Exception as e:
            logger.error(f"Failed to get agent load: {e}")
            return {"total_agents": 0, "idle_agents": 0, "running_agents": 0, "error_agents": 0, "agents": []}

    async def get_task_queue_status(self) -> Dict[str, Any]:
        """获取任务队列状态"""
        try:
            # 从Redis获取任务统计信息
            queue_stats = {
                "pending_tasks": 0,
                "running_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "avg_wait_time": None,
                "avg_execution_time": None
            }

            # 统计各状态的任务数量
            active_agents = await self.agent_manager.list_agents()
            for agent in active_agents:
                if agent["status"] == AgentStatus.RUNNING.value:
                    queue_stats["running_tasks"] += 1

            # 这里可以添加更详细的队列统计逻辑
            # 例如从Redis的特定键中读取统计信息

            return queue_stats

        except Exception as e:
            logger.error(f"Failed to get task queue status: {e}")
            return {"pending_tasks": 0, "running_tasks": 0, "completed_tasks": 0, "failed_tasks": 0}

    async def get_agent_workload_details(self) -> List[Dict[str, Any]]:
        """获取详细的Agent工作负载信息"""
        try:
            active_agents = await self.agent_manager.list_agents()
            workload_details = []

            for agent in active_agents:
                agent_workload = {
                    "agent_id": agent["agent_id"],
                    "agent_type": agent["agent_type"],
                    "status": agent["status"],
                    "current_tasks": 1 if agent["current_task"] else 0,
                    "total_tasks_completed": 0,  # 需要从数据库统计
                    "avg_execution_time": None,
                    "error_rate": agent.get("error_count", 0) / max(1, agent.get("error_count", 0) + 1),
                    "last_heartbeat": agent["last_heartbeat"]
                }
                workload_details.append(agent_workload)

            return workload_details

        except Exception as e:
            logger.error(f"Failed to get agent workload details: {e}")
            return []

    async def submit_task_result(self, task_id: str, result_data: Dict[str, Any]) -> bool:
        """提交任务结果"""
        try:
            result_message = {
                "task_id": task_id,
                "result_data": result_data,
                "submitted_at": datetime.now().isoformat()
            }

            self.redis_stream.add_message(self.task_results, result_message)

            # 更新对应的Agent状态
            agent_id = result_data.get("agent_id")
            if agent_id:
                await self.agent_manager.update_agent_status(
                    agent_id,
                    AgentStatus.IDLE,
                    current_task=None
                )

            logger.info(f"Task result submitted for task {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to submit task result {task_id}: {e}")
            return False

    async def handle_task_timeout(self, task_id: str) -> bool:
        """处理任务超时"""
        try:
            # 查找执行该任务的Agent
            active_agents = await self.agent_manager.list_agents()
            for agent in active_agents:
                if agent.get("current_task") == int(task_id):
                    # 更新Agent状态为错误
                    await self.agent_manager.update_agent_status(
                        agent["agent_id"],
                        AgentStatus.ERROR,
                        current_task=None
                    )

                    # 增加错误计数
                    agent["error_count"] = agent.get("error_count", 0) + 1

                    logger.warning(f"Task {task_id} timed out, agent {agent['agent_id']} marked as error")
                    break

            return True

        except Exception as e:
            logger.error(f"Failed to handle task timeout {task_id}: {e}")
            return False

    async def restart_agent(self, agent_id: int) -> bool:
        """重启Agent"""
        try:
            # 重置Agent状态
            success = await self.agent_manager.update_agent_status(
                agent_id,
                AgentStatus.IDLE,
                current_task=None
            )

            if success:
                # 重置错误计数
                if agent_id in self.agent_manager.agents:
                    self.agent_manager.agents[agent_id]["error_count"] = 0

                logger.info(f"Agent {agent_id} restarted successfully")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to restart agent {agent_id}: {e}")
            return False


# 全局实例
task_dispatcher = TaskDispatcher()
agent_lifecycle_manager = AgentLifecycleManager()


def get_task_dispatcher() -> TaskDispatcher:
    """获取任务分发器实例"""
    return task_dispatcher


def get_agent_lifecycle_manager() -> AgentLifecycleManager:
    """获取Agent生命周期管理器实例"""
    return agent_lifecycle_manager