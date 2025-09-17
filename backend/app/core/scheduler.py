"""
任务调度器核心模块
提供任务队列管理、调度算法、任务优先级和并发控制功能
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import uuid

from .redis import redis_client, redis_cache, redis_stream
from .config import settings

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"           # 待处理
    QUEUED = "queued"            # 已入队
    RUNNING = "running"          # 运行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消
    RETRYING = "retrying"        # 重试中
    TIMEOUT = "timeout"          # 超时


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1      # 低优先级
    NORMAL = 2   # 普通优先级
    HIGH = 3     # 高优先级
    URGENT = 4   # 紧急优先级


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0


@dataclass
class Task:
    """任务数据结构"""
    id: str
    name: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout: Optional[int] = None  # 超时时间（秒）
    max_retries: int = 3
    retry_count: int = 0
    result: Optional[TaskResult] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class TaskQueue:
    """任务队列管理器"""

    def __init__(self, redis_client=None):
        self.client = redis_client or redis_client
        self.queue_prefix = "task_queue:"
        self.task_prefix = "task:"
        self.result_prefix = "task_result:"

    def add_task(self, task: Task) -> bool:
        """添加任务到队列"""
        try:
            # 序列化任务
            task_data = self._serialize_task(task)

            # 添加到优先级队列
            priority_queue = f"{self.queue_prefix}{task.priority.value}"
            self.client.lpush(priority_queue, task.id)

            # 存储任务详情
            task_key = f"{self.task_prefix}{task.id}"
            self.client.hset(task_key, mapping=task_data)

            # 设置任务过期时间（24小时）
            self.client.expire(task_key, 86400)

            logger.info(f"任务 {task.id} 已添加到队列，优先级: {task.priority.name}")
            return True

        except Exception as e:
            logger.error(f"添加任务到队列失败: {e}")
            return False

    def get_next_task(self) -> Optional[Task]:
        """获取下一个待处理任务"""
        try:
            # 按优先级顺序检查队列
            for priority in sorted([p.value for p in TaskPriority], reverse=True):
                queue_name = f"{self.queue_prefix}{priority}"

                # 使用阻塞弹出，避免竞态条件
                result = self.client.brpop(queue_name, timeout=1)
                if result:
                    queue_name, task_id = result
                    task = self._get_task(task_id)
                    if task:
                        # 更新任务状态
                        task.status = TaskStatus.QUEUED
                        task.started_at = datetime.now()
                        self._update_task(task)
                        logger.info(f"获取任务 {task.id}，优先级: {TaskPriority(priority).name}")
                        return task

            return None

        except Exception as e:
            logger.error(f"获取下一个任务失败: {e}")
            return None

    def _get_task(self, task_id: str) -> Optional[Task]:
        """获取任务详情"""
        try:
            task_key = f"{self.task_prefix}{task_id}"
            task_data = self.client.hgetall(task_key)

            if not task_data:
                return None

            return self._deserialize_task(task_data)

        except Exception as e:
            logger.error(f"获取任务详情失败: {e}")
            return None

    def _serialize_task(self, task: Task) -> Dict[str, str]:
        """序列化任务"""
        data = asdict(task)
        # 转换datetime对象
        data['created_at'] = task.created_at.isoformat() if task.created_at else None
        data['started_at'] = task.started_at.isoformat() if task.started_at else None
        data['completed_at'] = task.completed_at.isoformat() if task.completed_at else None
        data['priority'] = task.priority.value
        data['status'] = task.status.value
        # 序列化结果
        if task.result:
            data['result'] = json.dumps(asdict(task.result))
        else:
            data['result'] = None

        return {k: str(v) if v is not None else '' for k, v in data.items()}

    def _deserialize_task(self, data: Dict[str, str]) -> Task:
        """反序列化任务"""
        # 转换datetime对象
        created_at = datetime.fromisoformat(data['created_at']) if data['created_at'] else None
        started_at = datetime.fromisoformat(data['started_at']) if data['started_at'] else None
        completed_at = datetime.fromisoformat(data['completed_at']) if data['completed_at'] else None

        # 解析结果
        result = None
        if data.get('result'):
            result_data = json.loads(data['result'])
            result = TaskResult(**result_data)

        return Task(
            id=data['id'],
            name=data['name'],
            task_type=data['task_type'],
            payload=json.loads(data['payload']),
            priority=TaskPriority(int(data['priority'])),
            status=TaskStatus(data['status']),
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            timeout=int(data['timeout']) if data['timeout'] else None,
            max_retries=int(data['max_retries']),
            retry_count=int(data['retry_count']),
            result=result,
            error=data['error'] if data['error'] else None
        )

    def _update_task(self, task: Task) -> bool:
        """更新任务状态"""
        try:
            task_data = self._serialize_task(task)
            task_key = f"{self.task_prefix}{task.id}"
            self.client.hset(task_key, mapping=task_data)
            return True
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            return False

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        try:
            task = self._get_task(task_id)
            return task.status if task else None
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return None

    def set_task_result(self, task_id: str, result: TaskResult) -> bool:
        """设置任务结果"""
        try:
            task = self._get_task(task_id)
            if not task:
                return False

            task.result = result
            task.completed_at = datetime.now()
            task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED

            # 存储结果到独立缓存
            result_key = f"{self.result_prefix}{task_id}"
            self.client.setex(result_key, 3600, json.dumps(asdict(result)))

            return self._update_task(task)

        except Exception as e:
            logger.error(f"设置任务结果失败: {e}")
            return False

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        try:
            result_key = f"{self.result_prefix}{task_id}"
            result_data = self.client.get(result_key)
            if result_data:
                result_dict = json.loads(result_data)
                return TaskResult(**result_dict)
            return None
        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            return None

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            task = self._get_task(task_id)
            if not task or task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False

            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()

            return self._update_task(task)

        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False

    def get_queue_stats(self) -> Dict[str, int]:
        """获取队列统计信息"""
        try:
            stats = {}
            for priority in TaskPriority:
                queue_name = f"{self.queue_prefix}{priority.value}"
                stats[f"{priority.name.lower()}_count"] = self.client.llen(queue_name)
            return stats
        except Exception as e:
            logger.error(f"获取队列统计失败: {e}")
            return {}


class TaskScheduler:
    """任务调度器"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.active_workers = 0
        self.task_queue = TaskQueue()
        self.task_handlers: Dict[str, Callable] = {}
        self.is_running = False
        self.worker_tasks: List[asyncio.Task] = []

    def register_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self.task_handlers[task_type] = handler
        logger.info(f"注册任务处理器: {task_type}")

    async def start(self):
        """启动调度器"""
        if self.is_running:
            return

        self.is_running = True
        logger.info(f"任务调度器启动，最大工作线程数: {self.max_workers}")

        # 创建工作线程
        for i in range(self.max_workers):
            worker_task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(worker_task)

        # 创建监控任务
        monitor_task = asyncio.create_task(self._monitor())
        self.worker_tasks.append(monitor_task)

    async def stop(self):
        """停止调度器"""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("任务调度器停止中...")

        # 等待所有工作线程完成
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)

        self.worker_tasks = []
        logger.info("任务调度器已停止")

    async def restart(self):
        """重启调度器"""
        logger.info("任务调度器重启中...")

        # 停止当前调度器
        if self.is_running:
            await self.stop()

        # 等待一秒
        await asyncio.sleep(1)

        # 重新启动
        await self.start()
        logger.info("任务调度器重启完成")
    async def _worker(self, worker_name: str):
        """工作线程"""
        logger.info(f"工作线程 {worker_name} 启动")

        while self.is_running:
            try:
                # 获取任务
                task = self.task_queue.get_next_task()
                if not task:
                    await asyncio.sleep(0.1)
                    continue

                self.active_workers += 1
                logger.info(f"工作线程 {worker_name} 开始执行任务 {task.id}")

                # 执行任务
                await self._execute_task(task, worker_name)

            except Exception as e:
                logger.error(f"工作线程 {worker_name} 执行失败: {e}")
                await asyncio.sleep(1)
            finally:
                self.active_workers -= 1

        logger.info(f"工作线程 {worker_name} 停止")

    async def _execute_task(self, task: Task, worker_name: str):
        """执行任务"""
        try:
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            self.task_queue._update_task(task)

            # 获取任务处理器
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"未找到任务处理器: {task.task_type}")

            # 设置超时
            timeout = task.timeout or 300  # 默认5分钟

            # 执行任务
            start_time = time.time()
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await asyncio.wait_for(handler(task.payload), timeout=timeout)
                else:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, handler, task.payload
                    )

                execution_time = time.time() - start_time

                # 创建结果
                task_result = TaskResult(
                    success=True,
                    result=result,
                    execution_time=execution_time,
                    retry_count=task.retry_count
                )

                # 保存结果
                self.task_queue.set_task_result(task.id, task_result)

                logger.info(f"任务 {task.id} 执行完成，耗时: {execution_time:.2f}秒")

            except asyncio.TimeoutError:
                task_result = TaskResult(
                    success=False,
                    error=f"任务超时 ({timeout}秒)",
                    execution_time=time.time() - start_time,
                    retry_count=task.retry_count
                )
                task.status = TaskStatus.TIMEOUT
                self.task_queue._update_task(task)
                self.task_queue.set_task_result(task.id, task_result)
                logger.warning(f"任务 {task.id} 执行超时")

            except Exception as e:
                execution_time = time.time() - start_time

                # 检查是否需要重试
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.RETRYING
                    task.error = str(e)
                    self.task_queue._update_task(task)

                    # 重新加入队列
                    await asyncio.sleep(2 ** task.retry_count)  # 指数退避
                    self.task_queue.add_task(task)

                    logger.warning(f"任务 {task.id} 执行失败，准备重试 ({task.retry_count}/{task.max_retries})")
                else:
                    task_result = TaskResult(
                        success=False,
                        error=str(e),
                        execution_time=execution_time,
                        retry_count=task.retry_count
                    )
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    self.task_queue._update_task(task)
                    self.task_queue.set_task_result(task.id, task_result)
                    logger.error(f"任务 {task.id} 执行失败: {e}")

        except Exception as e:
            logger.error(f"执行任务 {task.id} 时发生错误: {e}")

    async def _monitor(self):
        """监控任务"""
        while self.is_running:
            try:
                # 获取队列统计
                stats = self.task_queue.get_queue_stats()
                total_queued = sum(stats.values())

                logger.info(f"队列状态 - 待处理: {total_queued}, 活跃工作线程: {self.active_workers}")

                # 清理过期任务
                await self._cleanup_expired_tasks()

                await asyncio.sleep(30)  # 30秒监控一次

            except Exception as e:
                logger.error(f"监控任务失败: {e}")
                await asyncio.sleep(5)

    async def _cleanup_expired_tasks(self):
        """清理过期任务"""
        try:
            # 这里可以实现清理逻辑
            pass
        except Exception as e:
            logger.error(f"清理过期任务失败: {e}")

    def create_task(self, name: str, task_type: str, payload: Dict[str, Any],
                   priority: TaskPriority = TaskPriority.NORMAL,
                   timeout: Optional[int] = None,
                   max_retries: int = 3) -> str:
        """创建任务"""
        task = Task(
            id=str(uuid.uuid4()),
            name=name,
            task_type=task_type,
            payload=payload,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries
        )

        success = self.task_queue.add_task(task)
        if success:
            logger.info(f"创建任务 {task.id}: {name}")
            return task.id
        else:
            raise RuntimeError("创建任务失败")

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        return self.task_queue.get_task_status(task_id)

    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        return self.task_queue.get_task_result(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return self.task_queue.cancel_task(task_id)

    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        stats = self.task_queue.get_queue_stats()
        stats.update({
            'active_workers': self.active_workers,
            'max_workers': self.max_workers,
            'is_running': self.is_running
        })
        return stats


# 全局调度器实例
scheduler = TaskScheduler()


def get_scheduler() -> TaskScheduler:
    """获取任务调度器实例"""
    return scheduler