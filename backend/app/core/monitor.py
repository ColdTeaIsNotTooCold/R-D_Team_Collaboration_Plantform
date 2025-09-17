"""
执行监控器模块

提供任务状态跟踪、性能监控、资源使用监控和健康检查功能。
基于现有的任务分发器和Agent生命周期管理器。
"""

import asyncio
import json
import logging
import psutil
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict

from ..core.redis import redis_client
from ..core.dispatcher import task_dispatcher, agent_lifecycle_manager, TaskStatus, AgentStatus
from ..schemas.task import TaskQueueStatus, AgentWorkload

logger = logging.getLogger(__name__)


class MonitorEventType(str, Enum):
    """监控事件类型"""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_TIMEOUT = "task_timeout"
    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"
    AGENT_ERROR = "agent_error"
    SYSTEM_HEALTH_CHECK = "system_health_check"
    RESOURCE_WARNING = "resource_warning"
    PERFORMANCE_DEGRADATION = "performance_degradation"


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MonitorEvent:
    """监控事件数据结构"""
    event_type: MonitorEventType
    timestamp: datetime
    level: AlertLevel
    message: str
    details: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[int] = None


@dataclass
class SystemMetrics:
    """系统指标数据结构"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    active_connections: int
    redis_connections: int
    queue_size: int
    active_agents: int
    running_tasks: int


@dataclass
class TaskPerformanceMetrics:
    """任务性能指标数据结构"""
    task_id: str
    task_type: str
    agent_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    wait_time: float
    peak_memory_usage: Optional[float] = None
    peak_cpu_usage: Optional[float] = None
    status: str = "running"
    error_message: Optional[str] = None


class TaskMonitor:
    """任务监控器"""

    def __init__(self):
        self.task_metrics: Dict[str, TaskPerformanceMetrics] = {}
        self.event_log: List[MonitorEvent] = []
        self.system_metrics_history: List[SystemMetrics] = []
        self.alerts: List[MonitorEvent] = []
        self.max_history_size = 1000
        self.monitoring_interval = 30  # 30秒
        self._monitoring_task = None

    async def start_monitoring(self):
        """启动监控"""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Task monitoring started")

    async def stop_monitoring(self):
        """停止监控"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
            logger.info("Task monitoring stopped")

    async def _monitoring_loop(self):
        """监控循环"""
        while True:
            try:
                await self._collect_system_metrics()
                await self._check_task_timeouts()
                await self._check_agent_health()
                await self._check_resource_usage()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)

    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # 获取系统资源使用情况
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()

            # 获取活跃连接数
            connections = len(psutil.net_connections())

            # 获取Redis连接数（估计）
            redis_connections = 0
            try:
                redis_info = redis_client.info()
                redis_connections = redis_info.get('connected_clients', 0)
            except:
                pass

            # 获取任务队列状态
            queue_status = await task_dispatcher.get_task_queue_status()
            active_agents = len(await agent_lifecycle_manager.list_agents())

            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                network_io={
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv
                },
                active_connections=connections,
                redis_connections=redis_connections,
                queue_size=queue_status.get('pending_tasks', 0),
                active_agents=active_agents,
                running_tasks=queue_status.get('running_tasks', 0)
            )

            self.system_metrics_history.append(metrics)

            # 限制历史记录大小
            if len(self.system_metrics_history) > self.max_history_size:
                self.system_metrics_history.pop(0)

        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")

    async def _check_task_timeouts(self):
        """检查任务超时"""
        try:
            for task_id, metrics in list(self.task_metrics.items()):
                if metrics.status == "running":
                    # 检查是否超时（超过1小时）
                    if datetime.now() - metrics.start_time > timedelta(hours=1):
                        await self._handle_task_timeout(task_id)
        except Exception as e:
            logger.error(f"Failed to check task timeouts: {e}")

    async def _check_agent_health(self):
        """检查Agent健康状态"""
        try:
            active_agents = await agent_lifecycle_manager.list_agents()
            for agent in active_agents:
                last_heartbeat = datetime.fromisoformat(agent["last_heartbeat"])
                if datetime.now() - last_heartbeat > timedelta(minutes=10):
                    await self._handle_agent_unresponsive(agent["agent_id"])
        except Exception as e:
            logger.error(f"Failed to check agent health: {e}")

    async def _check_resource_usage(self):
        """检查资源使用情况"""
        try:
            if self.system_metrics_history:
                latest_metrics = self.system_metrics_history[-1]

                # CPU使用率超过90%
                if latest_metrics.cpu_usage > 90:
                    await self._create_alert(
                        MonitorEventType.RESOURCE_WARNING,
                        AlertLevel.WARNING,
                        f"High CPU usage: {latest_metrics.cpu_usage:.1f}%",
                        {"cpu_usage": latest_metrics.cpu_usage}
                    )

                # 内存使用率超过90%
                if latest_metrics.memory_usage > 90:
                    await self._create_alert(
                        MonitorEventType.RESOURCE_WARNING,
                        AlertLevel.WARNING,
                        f"High memory usage: {latest_metrics.memory_usage:.1f}%",
                        {"memory_usage": latest_metrics.memory_usage}
                    )

                # 磁盘使用率超过95%
                if latest_metrics.disk_usage > 95:
                    await self._create_alert(
                        MonitorEventType.RESOURCE_WARNING,
                        AlertLevel.CRITICAL,
                        f"High disk usage: {latest_metrics.disk_usage:.1f}%",
                        {"disk_usage": latest_metrics.disk_usage}
                    )

        except Exception as e:
            logger.error(f"Failed to check resource usage: {e}")

    async def track_task_start(self, task_id: str, task_type: str, agent_id: int):
        """跟踪任务开始"""
        try:
            start_time = datetime.now()

            # 获取任务等待时间
            wait_time = 0.0
            # 这里可以从任务创建时间计算，暂时使用默认值

            metrics = TaskPerformanceMetrics(
                task_id=task_id,
                task_type=task_type,
                agent_id=agent_id,
                start_time=start_time,
                wait_time=wait_time,
                status="running"
            )

            self.task_metrics[task_id] = metrics

            # 记录事件
            await self._record_event(
                MonitorEventType.TASK_STARTED,
                AlertLevel.INFO,
                f"Task {task_id} started on agent {agent_id}",
                {"task_type": task_type, "agent_id": agent_id},
                task_id=task_id,
                agent_id=agent_id
            )

            logger.info(f"Started tracking task {task_id}")

        except Exception as e:
            logger.error(f"Failed to track task start: {e}")

    async def track_task_completion(self, task_id: str, success: bool = True, error_message: Optional[str] = None):
        """跟踪任务完成"""
        try:
            if task_id not in self.task_metrics:
                logger.warning(f"Task {task_id} not found in metrics")
                return

            metrics = self.task_metrics[task_id]
            end_time = datetime.now()
            execution_time = (end_time - metrics.start_time).total_seconds()

            metrics.end_time = end_time
            metrics.execution_time = execution_time
            metrics.status = "completed" if success else "failed"
            metrics.error_message = error_message

            # 记录事件
            event_type = MonitorEventType.TASK_COMPLETED if success else MonitorEventType.TASK_FAILED
            level = AlertLevel.INFO if success else AlertLevel.ERROR
            message = f"Task {task_id} {'completed' if success else 'failed'} in {execution_time:.2f}s"

            await self._record_event(
                event_type,
                level,
                message,
                {
                    "execution_time": execution_time,
                    "task_type": metrics.task_type,
                    "agent_id": metrics.agent_id
                },
                task_id=task_id,
                agent_id=metrics.agent_id
            )

            logger.info(f"Task {task_id} completed: {success}")

        except Exception as e:
            logger.error(f"Failed to track task completion: {e}")

    async def _handle_task_timeout(self, task_id: str):
        """处理任务超时"""
        try:
            if task_id in self.task_metrics:
                metrics = self.task_metrics[task_id]
                metrics.status = "timeout"
                metrics.end_time = datetime.now()
                metrics.execution_time = (metrics.end_time - metrics.start_time).total_seconds()

                # 记录超时事件
                await self._record_event(
                    MonitorEventType.TASK_TIMEOUT,
                    AlertLevel.WARNING,
                    f"Task {task_id} timed out",
                    {
                        "execution_time": metrics.execution_time,
                        "task_type": metrics.task_type,
                        "agent_id": metrics.agent_id
                    },
                    task_id=task_id,
                    agent_id=metrics.agent_id
                )

                # 通知任务分发器
                await task_dispatcher.handle_task_timeout(task_id)

                logger.warning(f"Task {task_id} timed out")

        except Exception as e:
            logger.error(f"Failed to handle task timeout: {e}")

    async def _handle_agent_unresponsive(self, agent_id: int):
        """处理Agent无响应"""
        try:
            # 记录Agent错误事件
            await self._record_event(
                MonitorEventType.AGENT_ERROR,
                AlertLevel.ERROR,
                f"Agent {agent_id} is unresponsive",
                {"agent_id": agent_id, "reason": "no_heartbeat"},
                agent_id=agent_id
            )

            # 重启Agent
            await agent_lifecycle_manager.restart_agent(agent_id)

            logger.warning(f"Agent {agent_id} marked as unresponsive and restarted")

        except Exception as e:
            logger.error(f"Failed to handle agent unresponsive: {e}")

    async def _record_event(self, event_type: MonitorEventType, level: AlertLevel, message: str,
                          details: Optional[Dict[str, Any]] = None, task_id: Optional[str] = None,
                          agent_id: Optional[int] = None):
        """记录监控事件"""
        try:
            event = MonitorEvent(
                event_type=event_type,
                timestamp=datetime.now(),
                level=level,
                message=message,
                details=details or {},
                source="task_monitor",
                task_id=task_id,
                agent_id=agent_id
            )

            self.event_log.append(event)

            # 如果是告警级别，添加到告警列表
            if level != AlertLevel.INFO:
                self.alerts.append(event)

            # 限制历史记录大小
            if len(self.event_log) > self.max_history_size:
                self.event_log.pop(0)

            if len(self.alerts) > 100:  # 告警限制更小
                self.alerts.pop(0)

        except Exception as e:
            logger.error(f"Failed to record event: {e}")

    async def _create_alert(self, event_type: MonitorEventType, level: AlertLevel, message: str,
                           details: Optional[Dict[str, Any]] = None):
        """创建告警"""
        await self._record_event(event_type, level, message, details)

    def get_task_metrics(self, task_id: str) -> Optional[TaskPerformanceMetrics]:
        """获取任务指标"""
        return self.task_metrics.get(task_id)

    def get_all_task_metrics(self) -> List[TaskPerformanceMetrics]:
        """获取所有任务指标"""
        return list(self.task_metrics.values())

    def get_system_metrics(self, hours: int = 24) -> List[SystemMetrics]:
        """获取系统指标"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [m for m in self.system_metrics_history if m.timestamp >= cutoff_time]

    def get_alerts(self, level: Optional[AlertLevel] = None, hours: int = 24) -> List[MonitorEvent]:
        """获取告警"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        alerts = [a for a in self.alerts if a.timestamp >= cutoff_time]

        if level:
            alerts = [a for a in alerts if a.level == level]

        return alerts

    def get_recent_events(self, count: int = 100) -> List[MonitorEvent]:
        """获取最近的事件"""
        return self.event_log[-count:]

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        try:
            if not self.task_metrics:
                return {"total_tasks": 0}

            completed_tasks = [m for m in self.task_metrics.values() if m.status == "completed"]
            failed_tasks = [m for m in self.task_metrics.values() if m.status == "failed"]
            running_tasks = [m for m in self.task_metrics.values() if m.status == "running"]

            avg_execution_time = None
            if completed_tasks:
                avg_execution_time = sum(m.execution_time or 0 for m in completed_tasks) / len(completed_tasks)

            return {
                "total_tasks": len(self.task_metrics),
                "completed_tasks": len(completed_tasks),
                "failed_tasks": len(failed_tasks),
                "running_tasks": len(running_tasks),
                "success_rate": len(completed_tasks) / max(1, len(completed_tasks) + len(failed_tasks)),
                "average_execution_time": avg_execution_time
            }

        except Exception as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {"total_tasks": 0}

    def get_health_status(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            if not self.system_metrics_history:
                return {"status": "unknown", "reason": "No metrics available"}

            latest_metrics = self.system_metrics_history[-1]
            recent_alerts = self.get_alerts(hours=1)

            # 确定健康状态
            if any(alert.level == AlertLevel.CRITICAL for alert in recent_alerts):
                health_status = "critical"
            elif any(alert.level == AlertLevel.ERROR for alert in recent_alerts):
                health_status = "error"
            elif latest_metrics.cpu_usage > 90 or latest_metrics.memory_usage > 90:
                health_status = "warning"
            else:
                health_status = "healthy"

            return {
                "status": health_status,
                "timestamp": latest_metrics.timestamp.isoformat(),
                "cpu_usage": latest_metrics.cpu_usage,
                "memory_usage": latest_metrics.memory_usage,
                "disk_usage": latest_metrics.disk_usage,
                "active_agents": latest_metrics.active_agents,
                "running_tasks": latest_metrics.running_tasks,
                "recent_alerts_count": len(recent_alerts)
            }

        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {"status": "error", "reason": str(e)}

    async def cleanup_old_metrics(self, days: int = 7):
        """清理旧的指标数据"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)

            # 清理任务指标
            old_task_metrics = [
                task_id for task_id, metrics in self.task_metrics.items()
                if metrics.end_time and metrics.end_time < cutoff_time
            ]

            for task_id in old_task_metrics:
                del self.task_metrics[task_id]

            # 清理系统指标
            self.system_metrics_history = [
                m for m in self.system_metrics_history
                if m.timestamp >= cutoff_time
            ]

            # 清理事件日志
            self.event_log = [
                e for e in self.event_log
                if e.timestamp >= cutoff_time
            ]

            # 清理告警
            self.alerts = [
                a for a in self.alerts
                if a.timestamp >= cutoff_time
            ]

            logger.info(f"Cleaned up metrics older than {days} days")

        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")


# 全局实例
task_monitor = TaskMonitor()


def get_task_monitor() -> TaskMonitor:
    """获取任务监控器实例"""
    return task_monitor


async def start_monitoring():
    """启动监控服务"""
    await task_monitor.start_monitoring()


async def stop_monitoring():
    """停止监控服务"""
    await task_monitor.stop_monitoring()