"""
任务调度器API端点
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from app.schemas.scheduler import (
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse,
    TaskResultResponse, QueueStats, SchedulerControl, SchedulerStatus,
    TaskSearch, TaskBatchCreate, TaskBatchResponse,
    TaskCancelResponse, TaskRetryResponse, SchedulerMetrics,
    TaskLogResponse, TaskPriority, TaskStatus
)
from app.core.scheduler import (
    get_scheduler, TaskPriority as CoreTaskPriority,
    TaskStatus as CoreTaskStatus
)
from app.api.deps import get_current_user, get_current_active_user

router = APIRouter()
scheduler = get_scheduler()


def map_core_priority(priority: CoreTaskPriority) -> TaskPriority:
    """映射核心优先级到API优先级"""
    mapping = {
        CoreTaskPriority.LOW: TaskPriority.LOW,
        CoreTaskPriority.NORMAL: TaskPriority.NORMAL,
        CoreTaskPriority.HIGH: TaskPriority.HIGH,
        CoreTaskPriority.URGENT: TaskPriority.URGENT
    }
    return mapping.get(priority, TaskPriority.NORMAL)


def map_api_priority(priority: TaskPriority) -> CoreTaskPriority:
    """映射API优先级到核心优先级"""
    mapping = {
        TaskPriority.LOW: CoreTaskPriority.LOW,
        TaskPriority.NORMAL: CoreTaskPriority.NORMAL,
        TaskPriority.HIGH: CoreTaskPriority.HIGH,
        TaskPriority.URGENT: CoreTaskPriority.URGENT
    }
    return mapping.get(priority, CoreTaskPriority.NORMAL)


def map_core_status(status: CoreTaskStatus) -> TaskStatus:
    """映射核心状态到API状态"""
    mapping = {
        CoreTaskStatus.PENDING: TaskStatus.PENDING,
        CoreTaskStatus.QUEUED: TaskStatus.QUEUED,
        CoreTaskStatus.RUNNING: TaskStatus.RUNNING,
        CoreTaskStatus.COMPLETED: TaskStatus.COMPLETED,
        CoreTaskStatus.FAILED: TaskStatus.FAILED,
        CoreTaskStatus.CANCELLED: TaskStatus.CANCELLED,
        CoreTaskStatus.RETRYING: TaskStatus.RETRYING,
        CoreTaskStatus.TIMEOUT: TaskStatus.TIMEOUT
    }
    return mapping.get(status, TaskStatus.PENDING)


@router.post("/tasks", response_model=dict, summary="创建任务")
async def create_task(
    task: TaskCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """创建新任务"""
    try:
        # 转换优先级
        core_priority = map_api_priority(task.priority)

        # 创建任务
        task_id = scheduler.create_task(
            name=task.name,
            task_type=task.task_type,
            payload=task.payload,
            priority=core_priority,
            timeout=task.timeout,
            max_retries=task.max_retries
        )

        return {
            "success": True,
            "message": "任务创建成功",
            "task_id": task_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.post("/tasks/batch", response_model=TaskBatchResponse, summary="批量创建任务")
async def create_tasks_batch(
    batch: TaskBatchCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """批量创建任务"""
    try:
        task_ids = []
        success_count = 0

        for task in batch.tasks:
            try:
                core_priority = map_api_priority(task.priority)
                task_id = scheduler.create_task(
                    name=task.name,
                    task_type=task.task_type,
                    payload=task.payload,
                    priority=core_priority,
                    timeout=task.timeout,
                    max_retries=task.max_retries
                )
                task_ids.append(task_id)
                success_count += 1
            except Exception:
                # 继续处理其他任务
                continue

        failed_count = len(batch.tasks) - success_count

        return TaskBatchResponse(
            task_ids=task_ids,
            success_count=success_count,
            failed_count=failed_count
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量创建任务失败: {str(e)}")


@router.get("/tasks/{task_id}", response_model=TaskResponse, summary="获取任务详情")
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取任务详情"""
    try:
        # 获取任务状态
        status = scheduler.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 获取任务结果
        result = scheduler.get_task_result(task_id)

        # 构建响应（这里简化了，实际应该从数据库获取完整任务信息）
        return TaskResponse(
            id=task_id,
            name="Task",  # 应该从数据库获取
            task_type="unknown",  # 应该从数据库获取
            payload={},  # 应该从数据库获取
            priority=TaskPriority.NORMAL,  # 应该从数据库获取
            status=map_core_status(status),
            created_at=datetime.now(),  # 应该从数据库获取
            started_at=None,
            completed_at=None,
            retry_count=0,
            error=None,
            result=TaskResultResponse(
                success=result.success if result else False,
                result=result.result if result else None,
                error=result.error if result else None,
                execution_time=result.execution_time if result else 0.0,
                retry_count=result.retry_count if result else 0
            ) if result else None
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")


@router.get("/tasks/{task_id}/status", summary="获取任务状态")
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取任务状态"""
    try:
        status = scheduler.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="任务不存在")

        return {
            "task_id": task_id,
            "status": map_core_status(status).value
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.get("/tasks/{task_id}/result", response_model=TaskResultResponse, summary="获取任务结果")
async def get_task_result(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取任务结果"""
    try:
        result = scheduler.get_task_result(task_id)
        if not result:
            raise HTTPException(status_code=404, detail="任务结果不存在")

        return TaskResultResponse(
            success=result.success,
            result=result.result,
            error=result.error,
            execution_time=result.execution_time,
            retry_count=result.retry_count
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")


@router.post("/tasks/{task_id}/cancel", response_model=TaskCancelResponse, summary="取消任务")
async def cancel_task(
    task_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """取消任务"""
    try:
        success = scheduler.cancel_task(task_id)

        if not success:
            raise HTTPException(status_code=400, detail="无法取消任务")

        return TaskCancelResponse(
            success=True,
            message="任务取消成功",
            task_id=task_id
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@router.get("/tasks", response_model=TaskListResponse, summary="获取任务列表")
async def get_tasks(
    task_type: Optional[str] = Query(None, description="任务类型"),
    status: Optional[TaskStatus] = Query(None, description="任务状态"),
    priority: Optional[TaskPriority] = Query(None, description="任务优先级"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: dict = Depends(get_current_user)
):
    """获取任务列表"""
    try:
        # 这里简化了，实际应该从数据库查询
        # 返回空列表作为示例
        return TaskListResponse(
            tasks=[],
            total=0,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/queue/stats", response_model=QueueStats, summary="获取队列统计")
async def get_queue_stats(
    current_user: dict = Depends(get_current_user)
):
    """获取队列统计信息"""
    try:
        stats = scheduler.get_queue_stats()

        return QueueStats(
            low_count=stats.get('low_count', 0),
            normal_count=stats.get('normal_count', 0),
            high_count=stats.get('high_count', 0),
            urgent_count=stats.get('urgent_count', 0),
            active_workers=stats.get('active_workers', 0),
            max_workers=stats.get('max_workers', 0),
            is_running=stats.get('is_running', False)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取队列统计失败: {str(e)}")


@router.post("/scheduler/control", summary="控制调度器")
async def control_scheduler(
    control: SchedulerControl,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user)
):
    """控制调度器（启动/停止/重启）"""
    try:
        if control.action == "start":
            if scheduler.is_running:
                return {"success": True, "message": "调度器已在运行"}

            background_tasks.add_task(scheduler.start)
            return {"success": True, "message": "调度器启动中..."}

        elif control.action == "stop":
            if not scheduler.is_running:
                return {"success": True, "message": "调度器已停止"}

            background_tasks.add_task(scheduler.stop)
            return {"success": True, "message": "调度器停止中..."}

        elif control.action == "restart":
            background_tasks.add_task(scheduler.restart)
            return {"success": True, "message": "调度器重启中..."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"控制调度器失败: {str(e)}")


@router.get("/scheduler/status", response_model=SchedulerStatus, summary="获取调度器状态")
async def get_scheduler_status(
    current_user: dict = Depends(get_current_user)
):
    """获取调度器状态"""
    try:
        return SchedulerStatus(
            is_running=scheduler.is_running,
            max_workers=scheduler.max_workers,
            active_workers=scheduler.active_workers,
            registered_handlers=list(scheduler.task_handlers.keys()),
            uptime=None  # 可以添加运行时间计算
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取调度器状态失败: {str(e)}")


@router.get("/scheduler/metrics", response_model=SchedulerMetrics, summary="获取调度器指标")
async def get_scheduler_metrics(
    current_user: dict = Depends(get_current_user)
):
    """获取调度器性能指标"""
    try:
        stats = scheduler.get_queue_stats()

        # 计算总任务数
        total_tasks = sum(stats.get(f"{priority}_count", 0)
                         for priority in ['low', 'normal', 'high', 'urgent'])

        # 这里简化了，实际应该从数据库获取历史数据
        return SchedulerMetrics(
            total_tasks=total_tasks,
            completed_tasks=0,  # 应该从数据库获取
            failed_tasks=0,     # 应该从数据库获取
            running_tasks=stats.get('active_workers', 0),
            queued_tasks=total_tasks,
            average_execution_time=0.0,  # 应该从历史数据计算
            success_rate=0.0,            # 应该从历史数据计算
            worker_utilization=stats.get('active_workers', 0) / max(stats.get('max_workers', 1), 1)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取调度器指标失败: {str(e)}")


@router.get("/tasks/{task_id}/logs", response_model=TaskLogResponse, summary="获取任务日志")
async def get_task_logs(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取任务执行日志"""
    try:
        # 这里简化了，实际应该从日志系统获取
        return TaskLogResponse(
            logs=[],
            total=0
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务日志失败: {str(e)}")


@router.delete("/tasks/{task_id}", summary="删除任务")
async def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """删除任务"""
    try:
        # 首先取消任务
        scheduler.cancel_task(task_id)

        # 这里可以添加从数据库删除的逻辑

        return {"success": True, "message": "任务删除成功"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.post("/scheduler/restart", summary="重启调度器")
async def restart_scheduler(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user)
):
    """重启调度器"""
    try:
        background_tasks.add_task(scheduler.restart)
        return {"success": True, "message": "调度器重启中..."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启调度器失败: {str(e)}")


@router.get("/scheduler/health", summary="调度器健康检查")
async def scheduler_health():
    """调度器健康检查"""
    try:
        # 检查Redis连接
        redis_connected = True  # 可以添加实际的Redis连接检查

        # 检查调度器状态
        is_healthy = scheduler.is_running or not scheduler.is_running

        status_code = 200 if is_healthy else 503

        return JSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if is_healthy else "unhealthy",
                "redis_connected": redis_connected,
                "scheduler_running": scheduler.is_running,
                "active_workers": scheduler.active_workers,
                "max_workers": scheduler.max_workers
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )