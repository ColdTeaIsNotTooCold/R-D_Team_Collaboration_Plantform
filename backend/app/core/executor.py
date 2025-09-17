import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..core.database import get_db
from ..core.redis import redis_client
from ..core.messaging import MessagingService
from ..models.executor import TaskExecution, ExecutionLog, ExecutionMetrics, AgentWorkload, ExecutionQueue
from ..schemas.executor import (
    ExecutionStatus, ExecutionRequest, ExecutionResponse, ExecutionResult,
    ExecutionMetrics as ExecutionMetricsSchema, ExecutionQueueStatus as ExecutionQueueStatusSchema,
    AgentExecutionStats as AgentExecutionStatsSchema
)
from ..schemas.task import TaskStatus, TaskPriority, TaskUpdate
from ..schemas.agent import AgentStatus

logger = logging.getLogger(__name__)


class TaskExecutor:
    """任务执行器 - 负责任务的调度、执行和监控"""

    def __init__(self):
        self.messaging_service = MessagingService()
        self.active_executions: Dict[int, Dict[str, Any]] = {}
        self.execution_handlers: Dict[str, Callable] = {}
        self.agent_loads: Dict[int, int] = {}
        self.task_queue = asyncio.Queue()
        self.max_concurrent_executions = 10
        self.default_timeout = 300  # 5分钟
        self.retry_delays = [5, 30, 60, 300]  # 重试延迟（秒）

    async def initialize(self):
        """初始化执行器"""
        logger.info("初始化任务执行器...")

        # 启动任务处理循环
        asyncio.create_task(self._task_processing_loop())

        # 启动监控循环
        asyncio.create_task(self._monitoring_loop())

        # 启动超时检查循环
        asyncio.create_task(self._timeout_check_loop())

        # 恢复未完成的任务
        await self._recover_pending_tasks()

        logger.info("任务执行器初始化完成")

    async def submit_task(self, task_data: Dict[str, Any], db: Session) -> ExecutionResponse:
        """提交任务到执行器"""
        try:
            # 创建执行记录
            execution_create = TaskExecutionCreate(
                task_id=task_data["task_id"],
                agent_id=task_data["agent_id"],
                message_id="",
                status=ExecutionStatus.PENDING,
                metadata=task_data.get("metadata", {})
            )

            # 这里需要数据库模型，暂时使用内存存储
            execution_id = int(time.time() * 1000)  # 临时ID

            # 创建任务请求
            execution_request = ExecutionRequest(
                task_id=task_data["task_id"],
                agent_id=task_data["agent_id"],
                task_type=task_data["task_type"],
                input_data=task_data.get("input_data"),
                timeout=task_data.get("timeout", self.default_timeout),
                priority=task_data.get("priority", TaskPriority.MEDIUM),
                metadata=task_data.get("metadata", {})
            )

            # 将任务加入队列
            await self.task_queue.put({
                "execution_id": execution_id,
                "request": execution_request,
                "created_at": datetime.utcnow()
            })

            logger.info(f"任务已提交到执行器: task_id={task_data['task_id']}, execution_id={execution_id}")

            return ExecutionResponse(
                execution_id=execution_id,
                task_id=task_data["task_id"],
                agent_id=task_data["agent_id"],
                message_id="",
                status=ExecutionStatus.PENDING,
                estimated_duration=task_data.get("estimated_duration"),
                created_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"提交任务失败: {e}")
            raise

    async def _task_processing_loop(self):
        """任务处理循环"""
        logger.info("启动任务处理循环...")

        while True:
            try:
                # 检查并发执行数量
                if len(self.active_executions) >= self.max_concurrent_executions:
                    await asyncio.sleep(1)
                    continue

                # 从队列获取任务
                task_data = await self.task_queue.get()

                # 创建执行任务
                asyncio.create_task(self._execute_task(task_data))

                # 短暂休眠避免CPU过度使用
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"任务处理循环错误: {e}")
                await asyncio.sleep(1)

    async def _execute_task(self, task_data: Dict[str, Any]):
        """执行单个任务"""
        execution_id = task_data["execution_id"]
        request: ExecutionRequest = task_data["request"]

        try:
            # 更新执行状态为运行中
            await self._update_execution_status(execution_id, ExecutionStatus.RUNNING)

            # 更新Agent负载
            self.agent_loads[request.agent_id] = self.agent_loads.get(request.agent_id, 0) + 1

            # 记录执行开始时间
            start_time = time.time()

            # 发送任务到Agent
            message_id = await self._send_task_to_agent(request)

            # 等待Agent响应
            result = await self._wait_for_agent_response(message_id, request.timeout)

            # 计算执行时间
            execution_time = time.time() - start_time

            # 处理执行结果
            if result["success"]:
                await self._handle_successful_execution(execution_id, result, execution_time)
            else:
                await self._handle_failed_execution(execution_id, result["error"], execution_time)

        except asyncio.TimeoutError:
            logger.warning(f"任务执行超时: execution_id={execution_id}")
            await self._handle_timeout_execution(execution_id)

        except Exception as e:
            logger.error(f"任务执行失败: execution_id={execution_id}, error={e}")
            await self._handle_failed_execution(execution_id, str(e), 0)

        finally:
            # 减少Agent负载
            self.agent_loads[request.agent_id] = max(0, self.agent_loads.get(request.agent_id, 1) - 1)

            # 从活跃执行中移除
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]

    async def _send_task_to_agent(self, request: ExecutionRequest) -> str:
        """发送任务到Agent"""
        try:
            task_message = {
                "task_id": request.task_id,
                "task_type": request.task_type,
                "input_data": request.input_data,
                "priority": request.priority,
                "timeout": request.timeout,
                "metadata": request.metadata,
                "timestamp": datetime.utcnow().isoformat()
            }

            message_id = await self.messaging_service.send_agent_task(
                task_type=request.task_type,
                task_data=task_message,
                target_agent_id=str(request.agent_id),
                priority=self._priority_to_int(request.priority)
            )

            logger.info(f"任务已发送到Agent: agent_id={request.agent_id}, message_id={message_id}")
            return message_id

        except Exception as e:
            logger.error(f"发送任务到Agent失败: {e}")
            raise

    async def _wait_for_agent_response(self, message_id: str, timeout: int) -> Dict[str, Any]:
        """等待Agent响应"""
        try:
            # 使用Redis Pub/Sub等待响应
            response_channel = f"agent_response:{message_id}"

            # 订阅响应通道
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(response_channel)

            start_time = time.time()
            while True:
                # 检查超时
                if time.time() - start_time > timeout:
                    await pubsub.unsubscribe(response_channel)
                    raise asyncio.TimeoutError("任务执行超时")

                # 等待消息
                message = await pubsub.get_message(timeout=1)
                if message and message["type"] == "message":
                    response_data = json.loads(message["data"])
                    await pubsub.unsubscribe(response_channel)
                    return response_data

                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"等待Agent响应失败: {e}")
            raise

    async def _handle_successful_execution(self, execution_id: int, result: Dict[str, Any], execution_time: float):
        """处理成功执行"""
        try:
            await self._update_execution_status(
                execution_id,
                ExecutionStatus.COMPLETED,
                output_data=result.get("output_data"),
                execution_time=execution_time
            )

            # 更新任务状态
            await self._update_task_status(result["task_id"], TaskStatus.COMPLETED)

            logger.info(f"任务执行成功: execution_id={execution_id}")

        except Exception as e:
            logger.error(f"处理成功执行失败: {e}")

    async def _handle_failed_execution(self, execution_id: int, error_message: str, execution_time: float):
        """处理失败执行"""
        try:
            # 获取当前重试次数
            current_retries = self.active_executions.get(execution_id, {}).get("retry_count", 0)

            if current_retries < len(self.retry_delays):
                # 重试任务
                retry_delay = self.retry_delays[current_retries]
                logger.info(f"任务执行失败，准备重试: execution_id={execution_id}, retry={current_retries + 1}, delay={retry_delay}s")

                # 更新重试次数
                self.active_executions[execution_id] = self.active_executions.get(execution_id, {})
                self.active_executions[execution_id]["retry_count"] = current_retries + 1

                # 延迟后重试
                await asyncio.sleep(retry_delay)
                await self._retry_execution(execution_id)

            else:
                # 达到最大重试次数，标记为失败
                await self._update_execution_status(
                    execution_id,
                    ExecutionStatus.FAILED,
                    error_message=error_message,
                    execution_time=execution_time
                )

                # 更新任务状态
                task_id = self.active_executions.get(execution_id, {}).get("task_id")
                if task_id:
                    await self._update_task_status(task_id, TaskStatus.FAILED)

                logger.error(f"任务执行失败，达到最大重试次数: execution_id={execution_id}")

        except Exception as e:
            logger.error(f"处理失败执行失败: {e}")

    async def _handle_timeout_execution(self, execution_id: int):
        """处理超时执行"""
        try:
            await self._update_execution_status(
                execution_id,
                ExecutionStatus.TIMEOUT,
                error_message="任务执行超时"
            )

            # 更新任务状态
            task_id = self.active_executions.get(execution_id, {}).get("task_id")
            if task_id:
                await self._update_task_status(task_id, TaskStatus.FAILED)

            logger.warning(f"任务执行超时: execution_id={execution_id}")

        except Exception as e:
            logger.error(f"处理超时执行失败: {e}")

    async def _retry_execution(self, execution_id: int):
        """重试执行"""
        try:
            # 从活跃执行中获取任务数据
            task_data = self.active_executions.get(execution_id)
            if not task_data:
                logger.error(f"找不到要重试的任务: execution_id={execution_id}")
                return

            # 重新提交任务
            request = task_data["request"]
            await self.task_queue.put({
                "execution_id": execution_id,
                "request": request,
                "created_at": datetime.utcnow()
            })

            logger.info(f"任务已重新提交: execution_id={execution_id}")

        except Exception as e:
            logger.error(f"重试执行失败: {e}")

    async def _update_execution_status(self, execution_id: int, status: ExecutionStatus, **kwargs):
        """更新执行状态"""
        # 这里应该更新数据库，暂时使用内存存储
        if execution_id not in self.active_executions:
            self.active_executions[execution_id] = {}

        self.active_executions[execution_id].update({
            "status": status,
            "updated_at": datetime.utcnow()
        })

        for key, value in kwargs.items():
            if value is not None:
                self.active_executions[execution_id][key] = value

    async def _update_task_status(self, task_id: int, status: TaskStatus):
        """更新任务状态"""
        # 这里应该更新数据库，暂时记录日志
        logger.info(f"更新任务状态: task_id={task_id}, status={status}")

    async def _monitoring_loop(self):
        """监控循环"""
        logger.info("启动监控循环...")

        while True:
            try:
                # 监控执行状态
                await self._monitor_executions()

                # 监控Agent状态
                await self._monitor_agents()

                await asyncio.sleep(30)  # 每30秒监控一次

            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(10)

    async def _monitor_executions(self):
        """监控执行状态"""
        try:
            # 检查长时间运行的任务
            current_time = time.time()
            for execution_id, execution_data in self.active_executions.items():
                if execution_data.get("status") == ExecutionStatus.RUNNING:
                    start_time = execution_data.get("started_at")
                    if start_time and (current_time - start_time.timestamp()) > self.default_timeout:
                        logger.warning(f"检测到长时间运行的任务: execution_id={execution_id}")
                        await self._handle_timeout_execution(execution_id)

        except Exception as e:
            logger.error(f"监控执行失败: {e}")

    async def _monitor_agents(self):
        """监控Agent状态"""
        try:
            # 检查Agent负载
            for agent_id, load in self.agent_loads.items():
                if load > 5:  # 假设最大负载为5
                    logger.warning(f"Agent负载过高: agent_id={agent_id}, load={load}")

        except Exception as e:
            logger.error(f"监控Agent失败: {e}")

    async def _timeout_check_loop(self):
        """超时检查循环"""
        logger.info("启动超时检查循环...")

        while True:
            try:
                await self._check_timeouts()
                await asyncio.sleep(60)  # 每分钟检查一次

            except Exception as e:
                logger.error(f"超时检查循环错误: {e}")
                await asyncio.sleep(10)

    async def _check_timeouts(self):
        """检查超时任务"""
        try:
            current_time = time.time()
            for execution_id, execution_data in self.active_executions.items():
                if execution_data.get("status") == ExecutionStatus.RUNNING:
                    start_time = execution_data.get("started_at")
                    if start_time:
                        execution_duration = current_time - start_time.timestamp()
                        if execution_duration > self.default_timeout:
                            logger.warning(f"任务执行超时: execution_id={execution_id}, duration={execution_duration}s")
                            await self._handle_timeout_execution(execution_id)

        except Exception as e:
            logger.error(f"检查超时失败: {e}")

    async def _recover_pending_tasks(self):
        """恢复未完成的任务"""
        logger.info("恢复未完成的任务...")
        # 这里应该从数据库恢复未完成的任务
        # 暂时跳过实现

    def _priority_to_int(self, priority: TaskPriority) -> int:
        """将优先级转换为整数"""
        priority_map = {
            TaskPriority.LOW: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.HIGH: 3,
            TaskPriority.URGENT: 4
        }
        return priority_map.get(priority, 2)

    async def get_execution_status(self, execution_id: int) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        execution_data = self.active_executions.get(execution_id)
        if not execution_data:
            return None

        return {
            "execution_id": execution_id,
            "status": execution_data.get("status"),
            "started_at": execution_data.get("started_at"),
            "completed_at": execution_data.get("completed_at"),
            "execution_time": execution_data.get("execution_time"),
            "output_data": execution_data.get("output_data"),
            "error_message": execution_data.get("error_message"),
            "retry_count": execution_data.get("retry_count", 0)
        }

    async def cancel_execution(self, execution_id: int) -> bool:
        """取消执行"""
        try:
            execution_data = self.active_executions.get(execution_id)
            if not execution_data:
                return False

            if execution_data.get("status") == ExecutionStatus.RUNNING:
                await self._update_execution_status(execution_id, ExecutionStatus.CANCELLED)

                # 更新任务状态
                task_id = execution_data.get("task_id")
                if task_id:
                    await self._update_task_status(task_id, TaskStatus.CANCELLED)

                logger.info(f"任务执行已取消: execution_id={execution_id}")
                return True

        except Exception as e:
            logger.error(f"取消执行失败: {e}")

        return False

    async def get_metrics(self) -> ExecutionMetrics:
        """获取执行指标"""
        try:
            total_executions = len(self.active_executions)
            successful_executions = sum(
                1 for execution in self.active_executions.values()
                if execution.get("status") == ExecutionStatus.COMPLETED
            )
            failed_executions = sum(
                1 for execution in self.active_executions.values()
                if execution.get("status") == ExecutionStatus.FAILED
            )

            # 计算平均执行时间
            completed_executions = [
                execution for execution in self.active_executions.values()
                if execution.get("status") == ExecutionStatus.COMPLETED
            ]

            if completed_executions:
                avg_execution_time = sum(
                    execution.get("execution_time", 0) for execution in completed_executions
                ) / len(completed_executions)
            else:
                avg_execution_time = 0.0

            success_rate = successful_executions / total_executions if total_executions > 0 else 0.0

            # 计算Agent利用率
            agent_utilization = {}
            for agent_id, load in self.agent_loads.items():
                agent_utilization[agent_id] = min(load / 5.0, 1.0)  # 假设最大负载为5

            return ExecutionMetrics(
                total_executions=total_executions,
                successful_executions=successful_executions,
                failed_executions=failed_executions,
                average_execution_time=avg_execution_time,
                success_rate=success_rate,
                agent_utilization=agent_utilization
            )

        except Exception as e:
            logger.error(f"获取执行指标失败: {e}")
            return ExecutionMetrics(
                total_executions=0,
                successful_executions=0,
                failed_executions=0,
                average_execution_time=0.0,
                success_rate=0.0,
                agent_utilization={}
            )

    async def get_queue_status(self) -> ExecutionQueueStatus:
        """获取队列状态"""
        try:
            queue_length = self.task_queue.qsize()
            running_executions = sum(
                1 for execution in self.active_executions.values()
                if execution.get("status") == ExecutionStatus.RUNNING
            )
            completed_executions = sum(
                1 for execution in self.active_executions.values()
                if execution.get("status") == ExecutionStatus.COMPLETED
            )
            failed_executions = sum(
                1 for execution in self.active_executions.values()
                if execution.get("status") == ExecutionStatus.FAILED
            )
            pending_executions = queue_length

            # 简化的吞吐量计算
            throughput = completed_executions / max(1, len(self.active_executions))

            return ExecutionQueueStatus(
                pending_executions=pending_executions,
                running_executions=running_executions,
                completed_executions=completed_executions,
                failed_executions=failed_executions,
                average_wait_time=0.0,  # 简化实现
                queue_length=queue_length,
                throughput=throughput
            )

        except Exception as e:
            logger.error(f"获取队列状态失败: {e}")
            return ExecutionQueueStatus(
                pending_executions=0,
                running_executions=0,
                completed_executions=0,
                failed_executions=0,
                average_wait_time=0.0,
                queue_length=0,
                throughput=0.0
            )


# 全局任务执行器实例
task_executor = TaskExecutor()


async def get_task_executor() -> TaskExecutor:
    """获取任务执行器实例"""
    return task_executor


async def initialize_task_executor():
    """初始化任务执行器"""
    await task_executor.initialize()