"""
任务调度器测试
"""
import asyncio
import pytest
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.core.scheduler import (
    TaskScheduler, Task, TaskStatus, TaskPriority, TaskResult,
    TaskQueue, get_scheduler
)
from app.schemas.scheduler import (
    TaskCreate, TaskPriority as SchemaTaskPriority,
    TaskStatus as SchemaTaskStatus
)


class TestTask:
    """任务类测试"""

    def test_task_creation(self):
        """测试任务创建"""
        task = Task(
            id="test-id",
            name="测试任务",
            task_type="test_type",
            payload={"key": "value"},
            priority=TaskPriority.HIGH
        )

        assert task.id == "test-id"
        assert task.name == "测试任务"
        assert task.task_type == "test_type"
        assert task.payload == {"key": "value"}
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.created_at is not None
        assert task.started_at is None
        assert task.completed_at is None
        assert task.retry_count == 0
        assert task.max_retries == 3

    def test_task_result_creation(self):
        """测试任务结果创建"""
        result = TaskResult(
            success=True,
            result="test_result",
            execution_time=1.5,
            retry_count=1
        )

        assert result.success is True
        assert result.result == "test_result"
        assert result.execution_time == 1.5
        assert result.retry_count == 1


class TestTaskQueue:
    """任务队列测试"""

    @pytest.fixture
    def task_queue(self):
        """创建测试任务队列"""
        return TaskQueue()

    @pytest.fixture
    def sample_task(self):
        """创建示例任务"""
        return Task(
            id="test-task-id",
            name="测试任务",
            task_type="test_type",
            payload={"key": "value"},
            priority=TaskPriority.NORMAL
        )

    def test_add_task(self, task_queue, sample_task):
        """测试添加任务"""
        # 模拟Redis操作
        task_queue.client = MagicMock()
        task_queue.client.lpush.return_value = 1
        task_queue.client.hset.return_value = 1
        task_queue.client.expire.return_value = 1

        result = task_queue.add_task(sample_task)
        assert result is True

        # 验证Redis调用
        task_queue.client.lpush.assert_called_once()
        task_queue.client.hset.assert_called_once()
        task_queue.client.expire.assert_called_once()

    def test_get_next_task(self, task_queue):
        """测试获取下一个任务"""
        # 模拟Redis操作
        task_queue.client = MagicMock()
        task_queue.client.brpop.return_value = (None, "test-task-id")

        # 模拟任务数据
        task_data = {
            'id': 'test-task-id',
            'name': '测试任务',
            'task_type': 'test_type',
            'payload': '{"key": "value"}',
            'priority': '2',
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'timeout': '',
            'max_retries': '3',
            'retry_count': '0',
            'result': None,
            'error': ''
        }
        task_queue.client.hgetall.return_value = task_data

        task = task_queue.get_next_task()

        assert task is not None
        assert task.id == "test-task-id"
        assert task.status == TaskStatus.QUEUED

    def test_get_queue_stats(self, task_queue):
        """测试获取队列统计"""
        task_queue.client = MagicMock()
        task_queue.client.llen.side_effect = [5, 3, 2, 1]  # 不同优先级的队列长度

        stats = task_queue.get_queue_stats()

        assert stats['urgent_count'] == 1
        assert stats['high_count'] == 2
        assert stats['normal_count'] == 3
        assert stats['low_count'] == 5


class TestTaskScheduler:
    """任务调度器测试"""

    @pytest.fixture
    def scheduler(self):
        """创建测试调度器"""
        return TaskScheduler(max_workers=2)

    def test_scheduler_creation(self, scheduler):
        """测试调度器创建"""
        assert scheduler.max_workers == 2
        assert scheduler.active_workers == 0
        assert scheduler.is_running is False
        assert len(scheduler.worker_tasks) == 0
        assert len(scheduler.task_handlers) == 0

    def test_register_handler(self, scheduler):
        """测试注册处理器"""
        def dummy_handler(payload):
            return "dummy_result"

        scheduler.register_handler("test_type", dummy_handler)

        assert "test_type" in scheduler.task_handlers
        assert scheduler.task_handlers["test_type"] == dummy_handler

    def test_create_task(self, scheduler):
        """测试创建任务"""
        # 模拟任务队列
        scheduler.task_queue = MagicMock()
        scheduler.task_queue.add_task.return_value = True

        task_id = scheduler.create_task(
            name="测试任务",
            task_type="test_type",
            payload={"key": "value"},
            priority=TaskPriority.HIGH,
            timeout=60,
            max_retries=2
        )

        assert task_id is not None
        assert isinstance(task_id, str)

        # 验证任务队列调用
        scheduler.task_queue.add_task.assert_called_once()

    def test_get_task_status(self, scheduler):
        """测试获取任务状态"""
        scheduler.task_queue = MagicMock()
        scheduler.task_queue.get_task_status.return_value = TaskStatus.RUNNING

        status = scheduler.get_task_status("test-task-id")

        assert status == TaskStatus.RUNNING
        scheduler.task_queue.get_task_status.assert_called_once_with("test-task-id")

    def test_get_task_result(self, scheduler):
        """测试获取任务结果"""
        expected_result = TaskResult(
            success=True,
            result="test_result",
            execution_time=1.0
        )

        scheduler.task_queue = MagicMock()
        scheduler.task_queue.get_task_result.return_value = expected_result

        result = scheduler.get_task_result("test-task-id")

        assert result == expected_result
        scheduler.task_queue.get_task_result.assert_called_once_with("test-task-id")

    def test_cancel_task(self, scheduler):
        """测试取消任务"""
        scheduler.task_queue = MagicMock()
        scheduler.task_queue.cancel_task.return_value = True

        result = scheduler.cancel_task("test-task-id")

        assert result is True
        scheduler.task_queue.cancel_task.assert_called_once_with("test-task-id")

    def test_get_queue_stats(self, scheduler):
        """测试获取队列统计"""
        expected_stats = {
            'low_count': 1,
            'normal_count': 2,
            'high_count': 3,
            'urgent_count': 4
        }

        scheduler.task_queue = MagicMock()
        scheduler.task_queue.get_queue_stats.return_value = expected_stats

        stats = scheduler.get_queue_stats()

        assert stats['low_count'] == 1
        assert stats['active_workers'] == 0
        assert stats['max_workers'] == 2
        assert stats['is_running'] is False

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, scheduler):
        """测试调度器启动和停止"""
        # 模拟任务队列
        scheduler.task_queue = MagicMock()
        scheduler.task_queue.get_next_task.return_value = None

        # 启动调度器
        await scheduler.start()
        assert scheduler.is_running is True
        assert len(scheduler.worker_tasks) == scheduler.max_workers + 1  # workers + monitor

        # 停止调度器
        await scheduler.stop()
        assert scheduler.is_running is False
        assert len(scheduler.worker_tasks) == 0

    @pytest.mark.asyncio
    async def test_scheduler_restart(self, scheduler):
        """测试调度器重启"""
        # 模拟任务队列
        scheduler.task_queue = MagicMock()
        scheduler.task_queue.get_next_task.return_value = None

        # 启动调度器
        await scheduler.start()
        assert scheduler.is_running is True

        # 重启调度器
        await scheduler.restart()
        assert scheduler.is_running is True

        # 停止调度器
        await scheduler.stop()


class TestTaskExecution:
    """任务执行测试"""

    @pytest.mark.asyncio
    async def test_sync_task_execution(self):
        """测试同步任务执行"""
        scheduler = TaskScheduler(max_workers=1)

        def sync_handler(payload):
            time.sleep(0.1)  # 模拟耗时操作
            return f"processed: {payload['data']}"

        scheduler.register_handler("sync_task", sync_handler)

        # 创建测试任务
        scheduler.task_queue = MagicMock()
        test_task = Task(
            id="sync-test",
            name="同步测试任务",
            task_type="sync_task",
            payload={"data": "test"},
            priority=TaskPriority.NORMAL
        )

        # 模拟任务队列操作
        scheduler.task_queue.get_next_task.return_value = test_task
        scheduler.task_queue._update_task.return_value = True
        scheduler.task_queue.set_task_result.return_value = True

        # 执行任务
        await scheduler._execute_task(test_task, "test-worker")

        # 验证任务状态更新
        assert scheduler.task_queue._update_task.called
        assert scheduler.task_queue.set_task_result.called

    @pytest.mark.asyncio
    async def test_async_task_execution(self):
        """测试异步任务执行"""
        scheduler = TaskScheduler(max_workers=1)

        async def async_handler(payload):
            await asyncio.sleep(0.1)  # 模拟异步耗时操作
            return f"async processed: {payload['data']}"

        scheduler.register_handler("async_task", async_handler)

        # 创建测试任务
        scheduler.task_queue = MagicMock()
        test_task = Task(
            id="async-test",
            name="异步测试任务",
            task_type="async_task",
            payload={"data": "test"},
            priority=TaskPriority.NORMAL
        )

        # 模拟任务队列操作
        scheduler.task_queue.get_next_task.return_value = test_task
        scheduler.task_queue._update_task.return_value = True
        scheduler.task_queue.set_task_result.return_value = True

        # 执行任务
        await scheduler._execute_task(test_task, "test-worker")

        # 验证任务状态更新
        assert scheduler.task_queue._update_task.called
        assert scheduler.task_queue.set_task_result.called

    @pytest.mark.asyncio
    async def test_task_timeout(self):
        """测试任务超时"""
        scheduler = TaskScheduler(max_workers=1)

        def slow_handler(payload):
            time.sleep(2)  # 模拟耗时操作
            return "should_timeout"

        scheduler.register_handler("slow_task", slow_handler)

        # 创建测试任务（设置1秒超时）
        scheduler.task_queue = MagicMock()
        test_task = Task(
            id="timeout-test",
            name="超时测试任务",
            task_type="slow_task",
            payload={"data": "test"},
            priority=TaskPriority.NORMAL,
            timeout=1  # 1秒超时
        )

        # 模拟任务队列操作
        scheduler.task_queue.get_next_task.return_value = test_task
        scheduler.task_queue._update_task.return_value = True
        scheduler.task_queue.set_task_result.return_value = True

        # 执行任务
        await scheduler._execute_task(test_task, "test-worker")

        # 验证任务状态更新为超时
        assert scheduler.task_queue._update_task.called
        assert scheduler.task_queue.set_task_result.called

    @pytest.mark.asyncio
    async def test_task_retry(self):
        """测试任务重试"""
        scheduler = TaskScheduler(max_workers=1)

        def failing_handler(payload):
            raise Exception("任务执行失败")

        scheduler.register_handler("failing_task", failing_handler)

        # 创建测试任务
        scheduler.task_queue = MagicMock()
        test_task = Task(
            id="retry-test",
            name="重试测试任务",
            task_type="failing_task",
            payload={"data": "test"},
            priority=TaskPriority.NORMAL,
            max_retries=2
        )

        # 模拟任务队列操作
        scheduler.task_queue.get_next_task.return_value = test_task
        scheduler.task_queue._update_task.return_value = True
        scheduler.task_queue.set_task_result.return_value = True
        scheduler.task_queue.add_task.return_value = True

        # 执行任务
        await scheduler._execute_task(test_task, "test-worker")

        # 验证重试逻辑
        assert test_task.retry_count > 0


def test_get_scheduler():
    """测试获取全局调度器实例"""
    scheduler1 = get_scheduler()
    scheduler2 = get_scheduler()

    assert scheduler1 is scheduler2  # 应该是同一个实例
    assert isinstance(scheduler1, TaskScheduler)


@pytest.mark.integration
class TestSchedulerIntegration:
    """调度器集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """测试完整工作流程"""
        scheduler = TaskScheduler(max_workers=1)

        # 定义处理器
        async def test_handler(payload):
            await asyncio.sleep(0.1)
            return {"result": payload["input"] * 2}

        # 注册处理器
        scheduler.register_handler("test_workflow", test_handler)

        # 模拟任务队列
        scheduler.task_queue = MagicMock()

        # 创建任务
        task_id = scheduler.create_task(
            name="集成测试任务",
            task_type="test_workflow",
            payload={"input": 5},
            priority=TaskPriority.HIGH
        )

        # 获取任务状态
        status = scheduler.get_task_status(task_id)

        # 获取队列统计
        stats = scheduler.get_queue_stats()

        # 验证基本功能
        assert task_id is not None
        assert stats is not None
        assert stats['max_workers'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])