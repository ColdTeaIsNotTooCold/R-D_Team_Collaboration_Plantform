"""
监控API端点

提供监控相关的REST API接口，包括系统指标查询、任务跟踪、告警管理等功能。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime

from ..core.monitor import get_task_monitor
from ..schemas.monitor import (
    BaseResponse, TaskTrackingResponse, TaskCompletionResponse,
    MonitoringStatusResponse, PerformanceSummaryResponse, HealthStatusResponseWrapper,
    TaskMetricsRequest, TaskMetricsResponse, SystemMetricsRequest, SystemMetricsResponse,
    AlertsRequest, AlertsResponse, EventsRequest, EventsResponse,
    TaskTrackingRequest, TaskCompletionRequest, CleanupRequest, CleanupResponse,
    MonitoringStatus, HealthStatusResponse, PerformanceSummary
)
from ..api.deps import get_current_active_user

router = APIRouter()


@router.post("/task/start", response_model=TaskTrackingResponse)
async def start_task_tracking(
    request: TaskTrackingRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """开始跟踪任务"""
    try:
        monitor = get_task_monitor()
        await monitor.track_task_start(
            task_id=request.task_id,
            task_type=request.task_type,
            agent_id=request.agent_id
        )

        return TaskTrackingResponse(
            success=True,
            message=f"Started tracking task {request.task_id}",
            data={
                "task_id": request.task_id,
                "status": "tracking_started",
                "timestamp": datetime.now().isoformat()
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start task tracking: {str(e)}"
        )


@router.post("/task/complete", response_model=TaskCompletionResponse)
async def complete_task_tracking(
    request: TaskCompletionRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """完成任务跟踪"""
    try:
        monitor = get_task_monitor()
        await monitor.track_task_completion(
            task_id=request.task_id,
            success=request.success,
            error_message=request.error_message
        )

        return TaskCompletionResponse(
            success=True,
            message=f"Task {request.task_id} completed",
            data={
                "task_id": request.task_id,
                "status": "completed" if request.success else "failed",
                "timestamp": datetime.now().isoformat()
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete task tracking: {str(e)}"
        )


@router.get("/task/metrics/{task_id}", response_model=TaskMetricsResponse)
async def get_task_metrics(
    task_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """获取任务指标"""
    try:
        monitor = get_task_monitor()
        metrics = monitor.get_task_metrics(task_id)

        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task metrics not found for task {task_id}"
            )

        return TaskMetricsResponse(
            task_id=metrics.task_id,
            task_type=metrics.task_type,
            agent_id=metrics.agent_id,
            start_time=metrics.start_time,
            end_time=metrics.end_time,
            execution_time=metrics.execution_time,
            wait_time=metrics.wait_time,
            status=metrics.status,
            error_message=metrics.error_message
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task metrics: {str(e)}"
        )


@router.get("/task/metrics", response_model=List[TaskMetricsResponse])
async def get_all_task_metrics(
    current_user: dict = Depends(get_current_active_user)
):
    """获取所有任务指标"""
    try:
        monitor = get_task_monitor()
        metrics_list = monitor.get_all_task_metrics()

        return [
            TaskMetricsResponse(
                task_id=metrics.task_id,
                task_type=metrics.task_type,
                agent_id=metrics.agent_id,
                start_time=metrics.start_time,
                end_time=metrics.end_time,
                execution_time=metrics.execution_time,
                wait_time=metrics.wait_time,
                status=metrics.status,
                error_message=metrics.error_message
            )
            for metrics in metrics_list
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all task metrics: {str(e)}"
        )


@router.post("/system/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    request: SystemMetricsRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """获取系统指标"""
    try:
        monitor = get_task_monitor()
        metrics = monitor.get_system_metrics(hours=request.hours)

        return SystemMetricsResponse(
            metrics=metrics,
            total_count=len(metrics)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system metrics: {str(e)}"
        )


@router.post("/alerts", response_model=AlertsResponse)
async def get_alerts(
    request: AlertsRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """获取告警"""
    try:
        monitor = get_task_monitor()
        alerts = monitor.get_alerts(level=request.level, hours=request.hours)

        return AlertsResponse(
            alerts=alerts,
            total_count=len(alerts)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )


@router.post("/events", response_model=EventsResponse)
async def get_events(
    request: EventsRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """获取事件"""
    try:
        monitor = get_task_monitor()
        events = monitor.get_recent_events(count=request.count)

        # 过滤事件类型
        if request.event_type:
            events = [e for e in events if e.event_type == request.event_type]

        return EventsResponse(
            events=events,
            total_count=len(events)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get events: {str(e)}"
        )


@router.get("/performance/summary", response_model=PerformanceSummaryResponse)
async def get_performance_summary(
    current_user: dict = Depends(get_current_active_user)
):
    """获取性能摘要"""
    try:
        monitor = get_task_monitor()
        summary_data = monitor.get_performance_summary()

        summary = PerformanceSummary(
            total_tasks=summary_data.get("total_tasks", 0),
            completed_tasks=summary_data.get("completed_tasks", 0),
            failed_tasks=summary_data.get("failed_tasks", 0),
            running_tasks=summary_data.get("running_tasks", 0),
            success_rate=summary_data.get("success_rate", 0.0),
            average_execution_time=summary_data.get("average_execution_time")
        )

        return PerformanceSummaryResponse(
            success=True,
            message="Performance summary retrieved successfully",
            data=summary
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance summary: {str(e)}"
        )


@router.get("/health", response_model=HealthStatusResponseWrapper)
async def get_health_status(
    current_user: dict = Depends(get_current_active_user)
):
    """获取健康状态"""
    try:
        monitor = get_task_monitor()
        health_data = monitor.get_health_status()

        health_status = HealthStatusResponse(
            status=health_data.get("status", "unknown"),
            timestamp=health_data.get("timestamp", datetime.now().isoformat()),
            cpu_usage=health_data.get("cpu_usage", 0.0),
            memory_usage=health_data.get("memory_usage", 0.0),
            disk_usage=health_data.get("disk_usage", 0.0),
            active_agents=health_data.get("active_agents", 0),
            running_tasks=health_data.get("running_tasks", 0),
            recent_alerts_count=health_data.get("recent_alerts_count", 0)
        )

        return HealthStatusResponseWrapper(
            success=True,
            message="Health status retrieved successfully",
            data=health_status
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get health status: {str(e)}"
        )


@router.get("/status", response_model=MonitoringStatusResponse)
async def get_monitoring_status(
    current_user: dict = Depends(get_current_active_user)
):
    """获取监控状态"""
    try:
        monitor = get_task_monitor()

        # 计算运行时间
        uptime_seconds = None
        if monitor._monitoring_task and not monitor._monitoring_task.done():
            # 这里可以记录启动时间，暂时使用默认值
            uptime_seconds = 0.0

        # 获取最后指标收集时间
        last_metrics_time = None
        if monitor.system_metrics_history:
            last_metrics_time = monitor.system_metrics_history[-1].timestamp

        status = MonitoringStatus(
            is_monitoring=monitor._monitoring_task is not None and not monitor._monitoring_task.done(),
            monitoring_interval=monitor.monitoring_interval,
            total_metrics_collected=len(monitor.system_metrics_history),
            total_events_recorded=len(monitor.event_log),
            total_alerts_created=len(monitor.alerts),
            last_metrics_collection=last_metrics_time,
            uptime_seconds=uptime_seconds
        )

        return MonitoringStatusResponse(
            success=True,
            message="Monitoring status retrieved successfully",
            data=status
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitoring status: {str(e)}"
        )


@router.post("/start", response_model=BaseResponse)
async def start_monitoring(
    current_user: dict = Depends(get_current_active_user)
):
    """启动监控"""
    try:
        monitor = get_task_monitor()
        await monitor.start_monitoring()

        return BaseResponse(
            success=True,
            message="Monitoring started successfully",
            timestamp=datetime.now()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start monitoring: {str(e)}"
        )


@router.post("/stop", response_model=BaseResponse)
async def stop_monitoring(
    current_user: dict = Depends(get_current_active_user)
):
    """停止监控"""
    try:
        monitor = get_task_monitor()
        await monitor.stop_monitoring()

        return BaseResponse(
            success=True,
            message="Monitoring stopped successfully",
            timestamp=datetime.now()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop monitoring: {str(e)}"
        )


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_old_metrics(
    request: CleanupRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """清理旧的指标数据"""
    try:
        monitor = get_task_monitor()

        # 记录清理前的数据量
        old_task_metrics_count = len(monitor.task_metrics)
        old_system_metrics_count = len(monitor.system_metrics_history)
        old_events_count = len(monitor.event_log)
        old_alerts_count = len(monitor.alerts)

        await monitor.cleanup_old_metrics(days=request.days)

        # 计算清理的数据量
        cleaned_task_metrics = old_task_metrics_count - len(monitor.task_metrics)
        cleaned_system_metrics = old_system_metrics_count - len(monitor.system_metrics_history)
        cleaned_events = old_events_count - len(monitor.event_log)
        cleaned_alerts = old_alerts_count - len(monitor.alerts)

        return CleanupResponse(
            success=True,
            cleaned_task_metrics=cleaned_task_metrics,
            cleaned_system_metrics=cleaned_system_metrics,
            cleaned_events=cleaned_events,
            cleaned_alerts=cleaned_alerts
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup old metrics: {str(e)}"
        )


@router.get("/dashboard", response_model=BaseResponse)
async def get_dashboard_data(
    current_user: dict = Depends(get_current_active_user)
):
    """获取仪表板数据"""
    try:
        monitor = get_task_monitor()

        # 获取各种数据
        health_data = monitor.get_health_status()
        performance_data = monitor.get_performance_summary()
        recent_alerts = monitor.get_alerts(hours=24)
        recent_events = monitor.get_recent_events(count=50)

        dashboard_data = {
            "health": health_data,
            "performance": performance_data,
            "recent_alerts_count": len(recent_alerts),
            "recent_events_count": len(recent_events),
            "active_agents": health_data.get("active_agents", 0),
            "running_tasks": health_data.get("running_tasks", 0),
            "system_metrics": {
                "cpu_usage": health_data.get("cpu_usage", 0.0),
                "memory_usage": health_data.get("memory_usage", 0.0),
                "disk_usage": health_data.get("disk_usage", 0.0)
            }
        }

        return BaseResponse(
            success=True,
            message="Dashboard data retrieved successfully",
            data=dashboard_data,
            timestamp=datetime.now()
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard data: {str(e)}"
        )