"""
简单Agent实现
提供基础功能的Agent示例实现
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import redis.asyncio as redis

from .base import BaseAgent, AgentConfig, AgentCapability, AgentMessage, AgentStatus

logger = logging.getLogger(__name__)


class SimpleAgent(BaseAgent):
    """简单Agent实现，提供基础功能"""

    def __init__(self, config: AgentConfig, redis_client: Optional[redis.Redis] = None):
        super().__init__(config, redis_client)
        self.processed_count = 0
        self.error_count = 0

    async def _execute_task_impl(self, task_data: Dict[str, Any]) -> Any:
        """执行具体任务"""
        task_type = task_data.get("type", "echo")

        try:
            if task_type == "echo":
                result = await self._handle_echo_task(task_data)
            elif task_type == "calculate":
                result = await self._handle_calculate_task(task_data)
            elif task_type == "text_process":
                result = await self._handle_text_process_task(task_data)
            elif task_type == "status_check":
                result = await self._handle_status_check_task(task_data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            self.processed_count += 1
            return result

        except Exception as e:
            self.error_count += 1
            logger.error(f"Task execution failed: {e}")
            raise

    async def _handle_message(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        """处理接收到的消息"""
        message_type = message.message_type
        content = message.content

        try:
            if message_type == "ping":
                return await self._handle_ping(content)
            elif message_type == "status_request":
                return await self._handle_status_request(content)
            elif message_type == "capability_request":
                return await self._handle_capability_request(content)
            elif message_type == "task_request":
                return await self._handle_task_request(content)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                return {"status": "error", "message": f"Unknown message type: {message_type}"}

        except Exception as e:
            logger.error(f"Message handling failed: {e}")
            return {"status": "error", "message": str(e)}

    async def _handle_echo_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理echo任务"""
        echo_data = task_data.get("data", "")
        processed_data = f"Echo from {self.config.name}: {echo_data}"

        await asyncio.sleep(0.1)  # 模拟处理时间

        return {
            "type": "echo_response",
            "original_data": echo_data,
            "processed_data": processed_data,
            "timestamp": task_data.get("timestamp"),
            "agent_info": {
                "name": self.config.name,
                "type": self.config.agent_type
            }
        }

    async def _handle_calculate_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理计算任务"""
        operation = task_data.get("operation", "add")
        numbers = task_data.get("numbers", [])

        if not isinstance(numbers, list) or not numbers:
            raise ValueError("Numbers must be a non-empty list")

        if not all(isinstance(n, (int, float)) for n in numbers):
            raise ValueError("All numbers must be numeric")

        if operation == "add":
            result = sum(numbers)
        elif operation == "multiply":
            result = 1
            for num in numbers:
                result *= num
        elif operation == "average":
            result = sum(numbers) / len(numbers)
        elif operation == "max":
            result = max(numbers)
        elif operation == "min":
            result = min(numbers)
        else:
            raise ValueError(f"Unknown operation: {operation}")

        await asyncio.sleep(0.05)  # 模拟计算时间

        return {
            "type": "calculation_result",
            "operation": operation,
            "numbers": numbers,
            "result": result,
            "agent_info": {
                "name": self.config.name,
                "type": self.config.agent_type
            }
        }

    async def _handle_text_process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理文本任务"""
        text = task_data.get("text", "")
        operation = task_data.get("operation", "count")

        if not text:
            raise ValueError("Text cannot be empty")

        if operation == "count":
            result = len(text)
        elif operation == "word_count":
            result = len(text.split())
        elif operation == "uppercase":
            result = text.upper()
        elif operation == "lowercase":
            result = text.lower()
        elif operation == "reverse":
            result = text[::-1]
        else:
            raise ValueError(f"Unknown text operation: {operation}")

        await asyncio.sleep(0.02)  # 模拟处理时间

        return {
            "type": "text_processing_result",
            "operation": operation,
            "original_text": text,
            "result": result,
            "agent_info": {
                "name": self.config.name,
                "type": self.config.agent_type
            }
        }

    async def _handle_status_check_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理状态检查任务"""
        return {
            "type": "status_check_result",
            "agent_id": self.config.agent_id,
            "status": self.status.value,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "active_tasks": len(self.tasks),
            "capabilities": [cap.dict() for cap in self.config.capabilities],
            "agent_info": {
                "name": self.config.name,
                "type": self.config.agent_type,
                "description": self.config.description
            }
        }

    async def _handle_ping(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """处理ping消息"""
        return {
            "type": "pong",
            "agent_id": self.config.agent_id,
            "timestamp": content.get("timestamp"),
            "status": self.status.value,
            "message": f"Pong from {self.config.name}"
        }

    async def _handle_status_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """处理状态请求"""
        return {
            "type": "status_response",
            "agent_id": self.config.agent_id,
            "status": self.status.value,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "active_tasks": len(self.tasks),
            "capabilities": [cap.dict() for cap in self.config.capabilities]
        }

    async def _handle_capability_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """处理能力请求"""
        capability_name = content.get("capability")

        if capability_name:
            # 查找特定能力
            capability = next(
                (cap for cap in self.config.capabilities if cap.name == capability_name),
                None
            )
            return {
                "type": "capability_response",
                "capability": capability.dict() if capability else None,
                "found": capability is not None
            }
        else:
            # 返回所有能力
            return {
                "type": "capability_response",
                "capabilities": [cap.dict() for cap in self.config.capabilities],
                "total": len(self.config.capabilities)
            }

    async def _handle_task_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务请求"""
        task_type = content.get("task_type")
        task_data = content.get("task_data", {})

        if not task_type:
            return {"status": "error", "message": "Task type is required"}

        try:
            # 检查是否支持该任务类型
            supported_tasks = ["echo", "calculate", "text_process", "status_check"]
            if task_type not in supported_tasks:
                return {
                    "status": "error",
                    "message": f"Unsupported task type: {task_type}",
                    "supported_tasks": supported_tasks
                }

            # 执行任务
            result = await self._execute_task_impl({
                "type": task_type,
                **task_data
            })

            return {
                "status": "success",
                "result": result
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    async def _custom_health_check(self) -> None:
        """自定义健康检查"""
        # 检查错误率
        if self.processed_count > 0:
            error_rate = self.error_count / self.processed_count
            if error_rate > 0.1:  # 错误率超过10%
                logger.warning(f"High error rate detected: {error_rate:.2%}")
                if error_rate > 0.2:  # 错误率超过20%
                    self.status = AgentStatus.ERROR

        # 检查队列积压
        queue_size = self.message_queue.qsize()
        if queue_size > 100:
            logger.warning(f"Message queue backlog: {queue_size}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        total_requests = self.processed_count + self.error_count
        success_rate = self.processed_count / total_requests if total_requests > 0 else 0

        return {
            "total_requests": total_requests,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "success_rate": success_rate,
            "queue_size": self.message_queue.qsize(),
            "active_tasks": len(self.tasks)
        }