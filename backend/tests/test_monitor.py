import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from app.core.monitor import (
    TaskMonitor,
    MonitorEventType,
    AlertLevel,
    SystemMetrics,
    TaskPerformanceMetrics,
    MonitorEvent,
    get_task_monitor
)
from app.schemas.monitor import (
    TaskTrackingRequest,
    TaskCompletionRequest,
    SystemMetricsRequest,
    AlertsRequest,
    EventsRequest,
    CleanupRequest,
    TaskTrackingResponse,
    TaskCompletionResponse,
    SystemMetricsResponse,
    AlertsResponse,
    EventsResponse,
    CleanupResponse
)


class TestTaskMonitor:
    """任务监控器测试"""

    @pytest.fixture
    def monitor(self):
        """创建监控器实例"""
        return TaskMonitor()

    @pytest.fixture
    def mock_task_metrics(self):
        """创建模拟任务指标"""
        return TaskPerformanceMetrics(
            task_id="test_task_123",
            task_type="code_review",
            agent_id=1,
            start_time=datetime.now() - timedelta(minutes=5),
            wait_time=2.0,
            status="running"
        )

    @pytest.fixture
    def mock_system_metrics(self):
        """创建模拟系统指标"""
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_usage=45.5,
            memory_usage=60.2,
            disk_usage=75.8,
            network_io={"bytes_sent": 1024, "bytes_recv": 2048},
            active_connections=15,
            redis_connections=5,
            queue_size=3,
            active_agents=2,
            running_tasks=1
        )

    def test_monitor_initialization(self, monitor):
        """测试监控器初始化"""
        assert monitor.task_metrics == {}
        assert monitor.event_log == []
        assert monitor.system_metrics_history == []
        assert monitor.alerts == []
        assert monitor.max_history_size == 1000
        assert monitor.monitoring_interval == 30
        assert monitor._monitoring_task is None

    def test_track_task_start(self, monitor):
        """测试任务开始跟踪"""
        task_id = "test_task_123"
        task_type = "code_review"
        agent_id = 1

        # 测试同步调用
        asyncio.run(monitor.track_task_start(task_id, task_type, agent_id))

        # 验证任务指标被创建
        assert task_id in monitor.task_metrics
        metrics = monitor.task_metrics[task_id]
        assert metrics.task_id == task_id
        assert metrics.task_type == task_type
        assert metrics.agent_id == agent_id
        assert metrics.status == "running"
        assert metrics.start_time is not None

        # 验证事件被记录
        assert len(monitor.event_log) == 1
        event = monitor.event_log[0]
        assert event.event_type == MonitorEventType.TASK_STARTED
        assert event.level == AlertLevel.INFO
        assert event.task_id == task_id
        assert event.agent_id == agent_id

    def test_track_task_completion_success(self, monitor, mock_task_metrics):
        """测试任务成功完成跟踪"""
        task_id = "test_task_123"
        monitor.task_metrics[task_id] = mock_task_metrics

        # 测试同步调用
        asyncio.run(monitor.track_task_completion(task_id, success=True))

        # 验证任务指标被更新
        metrics = monitor.task_metrics[task_id]
        assert metrics.status == "completed"
        assert metrics.end_time is not None
        assert metrics.execution_time is not None
        assert metrics.execution_time > 0

        # 验证事件被记录
        assert len(monitor.event_log) == 1
        event = monitor.event_log[0]
        assert event.event_type == MonitorEventType.TASK_COMPLETED
        assert event.level == AlertLevel.INFO

    def test_track_task_completion_failure(self, monitor, mock_task_metrics):
        """测试任务失败跟踪"""
        task_id = "test_task_123"
        error_message = "Test error message"
        monitor.task_metrics[task_id] = mock_task_metrics

        # 测试同步调用
        asyncio.run(monitor.track_task_completion(task_id, success=False, error_message=error_message))

        # 验证任务指标被更新
        metrics = monitor.task_metrics[task_id]
        assert metrics.status == "failed"
        assert metrics.error_message == error_message

        # 验证事件被记录
        assert len(monitor.event_log) == 1
        event = monitor.event_log[0]
        assert event.event_type == MonitorEventType.TASK_FAILED
        assert event.level == AlertLevel.ERROR

    def test_get_task_metrics(self, monitor, mock_task_metrics):
        """测试获取任务指标"""
        task_id = "test_task_123"
        monitor.task_metrics[task_id] = mock_task_metrics

        # 测试存在的任务
        metrics = monitor.get_task_metrics(task_id)
        assert metrics == mock_task_metrics

        # 测试不存在的任务
        metrics = monitor.get_task_metrics("nonexistent_task")
        assert metrics is None

    def test_get_all_task_metrics(self, monitor, mock_task_metrics):
        """测试获取所有任务指标"""
        task_id = "test_task_123"
        monitor.task_metrics[task_id] = mock_task_metrics

        metrics_list = monitor.get_all_task_metrics()
        assert len(metrics_list) == 1
        assert metrics_list[0] == mock_task_metrics

    def test_get_system_metrics(self, monitor, mock_system_metrics):
        """测试获取系统指标"""
        # 添加模拟指标
        monitor.system_metrics_history.append(mock_system_metrics)

        # 测试获取最近24小时的指标
        metrics = monitor.get_system_metrics(hours=24)
        assert len(metrics) == 1
        assert metrics[0] == mock_system_metrics

        # 测试获取最近1小时的指标（应该为空）
        old_metric = SystemMetrics(
            timestamp=datetime.now() - timedelta(hours=2),
            cpu_usage=30.0,
            memory_usage=50.0,
            disk_usage=70.0,
            network_io={"bytes_sent": 512, "bytes_recv": 1024},
            active_connections=10,
            redis_connections=3,
            queue_size=2,
            active_agents=1,
            running_tasks=0
        )
        monitor.system_metrics_history.append(old_metric)

        metrics = monitor.get_system_metrics(hours=1)
        assert len(metrics) == 1
        assert metrics[0] == mock_system_metrics

    def test_get_alerts(self, monitor):
        """测试获取告警"""
        # 添加模拟告警
        alert_event = MonitorEvent(
            event_type=MonitorEventType.RESOURCE_WARNING,
            timestamp=datetime.now(),
            level=AlertLevel.WARNING,
            message="Test warning",
            details={"test": "data"}
        )
        monitor.alerts.append(alert_event)

        # 测试获取所有告警
        alerts = monitor.get_alerts()
        assert len(alerts) == 1
        assert alerts[0] == alert_event

        # 测试按级别过滤
        alerts = monitor.get_alerts(level=AlertLevel.WARNING)
        assert len(alerts) == 1

        alerts = monitor.get_alerts(level=AlertLevel.ERROR)
        assert len(alerts) == 0

    def test_get_recent_events(self, monitor):
        """测试获取最近事件"""
        # 添加多个事件
        for i in range(5):
            event = MonitorEvent(
                event_type=MonitorEventType.TASK_CREATED,
                timestamp=datetime.now() - timedelta(minutes=i),
                level=AlertLevel.INFO,
                message=f"Event {i}"
            )
            monitor.event_log.append(event)

        # 测试获取最近3个事件
        events = monitor.get_recent_events(count=3)
        assert len(events) == 3
        # 应该是最新的3个事件
        assert events[0].message == "Event 0"

    def test_get_performance_summary(self, monitor, mock_task_metrics):
        """测试获取性能摘要"""
        # 添加不同状态的任务
        completed_task = TaskPerformanceMetrics(
            task_id="completed_task",
            task_type="test",
            agent_id=1,
            start_time=datetime.now() - timedelta(minutes=10),
            end_time=datetime.now() - timedelta(minutes=5),
            execution_time=300.0,
            wait_time=2.0,
            status="completed"
        )
        failed_task = TaskPerformanceMetrics(
            task_id="failed_task",
            task_type="test",
            agent_id=2,
            start_time=datetime.now() - timedelta(minutes=8),
            end_time=datetime.now() - timedelta(minutes=3),
            execution_time=180.0,
            wait_time=1.5,
            status="failed"
        )
        running_task = TaskPerformanceMetrics(
            task_id="running_task",
            task_type="test",
            agent_id=3,
            start_time=datetime.now() - timedelta(minutes=2),
            wait_time=3.0,
            status="running"
        )

        monitor.task_metrics = {
            "completed_task": completed_task,
            "failed_task": failed_task,
            "running_task": running_task
        }

        summary = monitor.get_performance_summary()
        assert summary["total_tasks"] == 3
        assert summary["completed_tasks"] == 1
        assert summary["failed_tasks"] == 1
        assert summary["running_tasks"] == 1
        assert summary["success_rate"] == 0.5  # 1/2 (completed+failed)
        assert summary["average_execution_time"] == 240.0  # (300+180)/2

    def test_get_performance_summary_empty(self, monitor):
        """测试空性能摘要"""
        summary = monitor.get_performance_summary()
        assert summary["total_tasks"] == 0
        assert summary["completed_tasks"] == 0
        assert summary["failed_tasks"] == 0
        assert summary["running_tasks"] == 0
        assert summary["success_rate"] == 0
        assert summary["average_execution_time"] is None

    def test_get_health_status(self, monitor, mock_system_metrics):
        """测试获取健康状态"""
        # 添加系统指标
        monitor.system_metrics_history.append(mock_system_metrics)

        health = monitor.get_health_status()
        assert health["status"] == "healthy"
        assert health["cpu_usage"] == mock_system_metrics.cpu_usage
        assert health["memory_usage"] == mock_system_metrics.memory_usage
        assert health["disk_usage"] == mock_system_metrics.disk_usage
        assert health["active_agents"] == mock_system_metrics.active_agents
        assert health["running_tasks"] == mock_system_metrics.running_tasks

    def test_get_health_status_critical_alert(self, monitor, mock_system_metrics):
        """测试严重告警时的健康状态"""
        # 添加系统指标
        monitor.system_metrics_history.append(mock_system_metrics)

        # 添加严重告警
        critical_alert = MonitorEvent(
            event_type=MonitorEventType.RESOURCE_WARNING,
            timestamp=datetime.now(),
            level=AlertLevel.CRITICAL,
            message="Critical error"
        )
        monitor.alerts.append(critical_alert)

        health = monitor.get_health_status()
        assert health["status"] == "critical"

    def test_get_health_status_high_resource_usage(self, monitor, mock_system_metrics):
        """测试高资源使用率时的健康状态"""
        # 修改系统指标为高使用率
        high_usage_metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_usage=95.0,  # 高CPU使用率
            memory_usage=60.2,
            disk_usage=75.8,
            network_io={"bytes_sent": 1024, "bytes_recv": 2048},
            active_connections=15,
            redis_connections=5,
            queue_size=3,
            active_agents=2,
            running_tasks=1
        )
        monitor.system_metrics_history.append(high_usage_metrics)

        health = monitor.get_health_status()
        assert health["status"] == "warning"

    def test_history_size_limit(self, monitor):
        """测试历史记录大小限制"""
        # 设置较小的历史记录大小
        monitor.max_history_size = 3

        # 添加超过限制的事件
        for i in range(5):
            event = MonitorEvent(
                event_type=MonitorEventType.TASK_CREATED,
                timestamp=datetime.now(),
                level=AlertLevel.INFO,
                message=f"Event {i}"
            )
            monitor.event_log.append(event)

        # 验证历史记录被限制
        assert len(monitor.event_log) == 3
        assert monitor.event_log[0].message == "Event 2"  # 保留最新的3个

    @pytest.mark.asyncio
    async def test_cleanup_old_metrics(self, monitor):
        """测试清理旧的指标数据"""
        # 创建旧的任务指标
        old_task_metrics = TaskPerformanceMetrics(
            task_id="old_task",
            task_type="test",
            agent_id=1,
            start_time=datetime.now() - timedelta(days=10),
            end_time=datetime.now() - timedelta(days=10),
            execution_time=300.0,
            wait_time=2.0,
            status="completed"
        )
        monitor.task_metrics["old_task"] = old_task_metrics

        # 创建新的任务指标
        new_task_metrics = TaskPerformanceMetrics(
            task_id="new_task",
            task_type="test",
            agent_id=2,
            start_time=datetime.now() - timedelta(hours=1),
            wait_time=2.0,
            status="running"
        )
        monitor.task_metrics["new_task"] = new_task_metrics

        # 创建旧的系统指标
        old_system_metrics = SystemMetrics(
            timestamp=datetime.now() - timedelta(days=10),
            cpu_usage=30.0,
            memory_usage=50.0,
            disk_usage=70.0,
            network_io={"bytes_sent": 512, "bytes_recv": 1024},
            active_connections=10,
            redis_connections=3,
            queue_size=2,
            active_agents=1,
            running_tasks=0
        )
        monitor.system_metrics_history.append(old_system_metrics)

        # 执行清理
        await monitor.cleanup_old_metrics(days=7)

        # 验证旧的指标被清理，新的被保留
        assert "old_task" not in monitor.task_metrics
        assert "new_task" in monitor.task_metrics
        assert len(monitor.system_metrics_history) == 0

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitor):
        """测试启动和停止监控"""
        # 测试启动监控
        await monitor.start_monitoring()
        assert monitor._monitoring_task is not None
        assert not monitor._monitoring_task.done()

        # 测试停止监控
        await monitor.stop_monitoring()
        assert monitor._monitoring_task is None

    def test_get_task_monitor_function(self):
        """测试获取监控器函数"""
        monitor = get_task_monitor()
        assert isinstance(monitor, TaskMonitor)
        # 多次调用应该返回同一个实例
        assert get_task_monitor() is monitor


class TestMonitorSchemas:
    """监控数据模式测试"""

    def test_task_tracking_request(self):
        """测试任务跟踪请求"""
        request = TaskTrackingRequest(
            task_id="test_task_123",
            task_type="code_review",
            agent_id=1
        )
        assert request.task_id == "test_task_123"
        assert request.task_type == "code_review"
        assert request.agent_id == 1

    def test_task_completion_request(self):
        """测试任务完成请求"""
        request = TaskCompletionRequest(
            task_id="test_task_123",
            success=False,
            error_message="Test error"
        )
        assert request.task_id == "test_task_123"
        assert request.success is False
        assert request.error_message == "Test error"

    def test_system_metrics_request(self):
        """测试系统指标请求"""
        request = SystemMetricsRequest(hours=24)
        assert request.hours == 24

    def test_alerts_request(self):
        """测试告警请求"""
        request = AlertsRequest(level="warning", hours=12)
        assert request.level == "warning"
        assert request.hours == 12

    def test_events_request(self):
        """测试事件请求"""
        request = EventsRequest(count=50, event_type="task_created")
        assert request.count == 50
        assert request.event_type == "task_created"

    def test_cleanup_request(self):
        """测试清理请求"""
        request = CleanupRequest(days=7)
        assert request.days == 7

    def test_task_tracking_response(self):
        """测试任务跟踪响应"""
        response = TaskTrackingResponse(
            success=True,
            message="Tracking started",
            data={"task_id": "test_task_123"}
        )
        assert response.success is True
        assert response.message == "Tracking started"
        assert response.data["task_id"] == "test_task_123"

    def test_cleanup_response(self):
        """测试清理响应"""
        response = CleanupResponse(
            success=True,
            cleaned_task_metrics=5,
            cleaned_system_metrics=10,
            cleaned_events=20,
            cleaned_alerts=3
        )
        assert response.success is True
        assert response.cleaned_task_metrics == 5
        assert response.cleaned_system_metrics == 10
        assert response.cleaned_events == 20
        assert response.cleaned_alerts == 3


class TestMonitorIntegration:
    """监控集成测试"""

    @pytest.mark.asyncio
    async def test_full_task_lifecycle(self):
        """测试完整的任务生命周期监控"""
        monitor = TaskMonitor()

        # 开始任务
        task_id = "integration_test_task"
        await monitor.track_task_start(task_id, "test_type", 1)

        # 验证任务开始
        metrics = monitor.get_task_metrics(task_id)
        assert metrics is not None
        assert metrics.status == "running"

        # 完成任务
        await monitor.track_task_completion(task_id, success=True)

        # 验证任务完成
        metrics = monitor.get_task_metrics(task_id)
        assert metrics.status == "completed"
        assert metrics.execution_time is not None

        # 验证性能摘要
        summary = monitor.get_performance_summary()
        assert summary["total_tasks"] == 1
        assert summary["completed_tasks"] == 1
        assert summary["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_monitoring_with_mock_system_metrics(self):
        """测试带模拟系统指标的监控"""
        monitor = TaskMonitor()

        # 模拟系统指标收集
        with patch('psutil.cpu_percent', return_value=45.5), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.net_io_counters') as mock_network, \
             patch('psutil.net_connections', return_value=[]), \
             patch('app.core.monitor.task_dispatcher.get_task_queue_status', return_value={"pending_tasks": 2, "running_tasks": 1}), \
             patch('app.core.monitor.agent_lifecycle_manager.list_agents', return_value=[]):

            # 配置模拟对象
            mock_memory.return_value.percent = 60.2
            mock_disk.return_value.percent = 75.8
            mock_network.return_value.bytes_sent = 1024
            mock_network.return_value.bytes_recv = 2048

            # 执行系统指标收集
            await monitor._collect_system_metrics()

            # 验证指标被收集
            assert len(monitor.system_metrics_history) == 1
            metrics = monitor.system_metrics_history[0]
            assert metrics.cpu_usage == 45.5
            assert metrics.memory_usage == 60.2
            assert metrics.disk_usage == 75.8

    @pytest.mark.asyncio
    async def test_alert_creation_for_high_resource_usage(self):
        """测试高资源使用率告警创建"""
        monitor = TaskMonitor()

        # 创建高CPU使用率的系统指标
        high_cpu_metrics = SystemMetrics(
            timestamp=datetime.now(),
            cpu_usage=95.0,  # 超过90%阈值
            memory_usage=60.2,
            disk_usage=75.8,
            network_io={"bytes_sent": 1024, "bytes_recv": 2048},
            active_connections=15,
            redis_connections=5,
            queue_size=3,
            active_agents=2,
            running_tasks=1
        )
        monitor.system_metrics_history.append(high_cpu_metrics)

        # 执行资源使用检查
        await monitor._check_resource_usage()

        # 验证告警被创建
        assert len(monitor.alerts) == 1
        alert = monitor.alerts[0]
        assert alert.event_type == MonitorEventType.RESOURCE_WARNING
        assert alert.level == AlertLevel.WARNING
        assert "95.0%" in alert.message


if __name__ == '__main__':
    pytest.main([__file__, '-v'])