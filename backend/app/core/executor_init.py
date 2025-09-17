import asyncio
import logging
from typing import Optional

from .executor import TaskExecutor, initialize_task_executor
from .messaging import MessagingService

logger = logging.getLogger(__name__)

# 全局任务执行器实例
_task_executor: Optional[TaskExecutor] = None
_messaging_service: Optional[MessagingService] = None


async def get_task_executor() -> TaskExecutor:
    """获取任务执行器实例"""
    global _task_executor
    if _task_executor is None:
        _task_executor = TaskExecutor()
        await _task_executor.initialize()
    return _task_executor


async def get_messaging_service() -> MessagingService:
    """获取消息服务实例"""
    global _messaging_service
    if _messaging_service is None:
        _messaging_service = MessagingService()
    return _messaging_service


async def initialize_executor_services():
    """初始化执行器相关服务"""
    try:
        logger.info("初始化执行器服务...")

        # 初始化消息服务
        messaging_service = await get_messaging_service()

        # 初始化任务执行器
        task_executor = await get_task_executor()

        logger.info("执行器服务初始化完成")

    except Exception as e:
        logger.error(f"初始化执行器服务失败: {e}")
        raise


async def shutdown_executor_services():
    """关闭执行器服务"""
    try:
        logger.info("关闭执行器服务...")

        global _task_executor, _messaging_service

        # 清理任务执行器
        if _task_executor:
            # 取消所有活跃任务
            for execution_id in list(_task_executor.active_executions.keys()):
                await _task_executor.cancel_execution(execution_id)

            # 清理队列
            while not _task_executor.task_queue.empty():
                _task_executor.task_queue.get_nowait()

            _task_executor = None

        # 清理消息服务
        if _messaging_service:
            _messaging_service = None

        logger.info("执行器服务已关闭")

    except Exception as e:
        logger.error(f"关闭执行器服务失败: {e}")


def get_executor_status() -> dict:
    """获取执行器状态"""
    global _task_executor, _messaging_service

    status = {
        "task_executor": "initialized" if _task_executor else "not_initialized",
        "messaging_service": "initialized" if _messaging_service else "not_initialized",
        "active_executions": 0,
        "queue_length": 0
    }

    if _task_executor:
        status["active_executions"] = len(_task_executor.active_executions)
        status["queue_length"] = _task_executor.task_queue.qsize()

    return status