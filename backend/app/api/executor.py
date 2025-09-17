from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import timedelta

from ..core.database import get_db
from ..core.executor import get_task_executor, TaskExecutor
from ..schemas.executor import (
    ExecutionRequest, ExecutionResponse, ExecutionResult,
    ExecutionMetrics, ExecutionQueueStatus, AgentExecutionStats,
    ExecutionStatus
)
from ..schemas.task import TaskPriority
from ..api.deps import get_current_active_user

router = APIRouter()


@router.post("/submit", response_model=ExecutionResponse)
async def submit_task(
    request: ExecutionRequest,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """提交任务到执行器"""
    try:
        executor = await get_task_executor()

        # 构造任务数据
        task_data = {
            "task_id": request.task_id,
            "agent_id": request.agent_id,
            "task_type": request.task_type,
            "input_data": request.input_data,
            "timeout": request.timeout,
            "priority": request.priority,
            "metadata": request.metadata,
            "estimated_duration": request.timeout
        }

        # 提交任务
        response = await executor.submit_task(task_data, db)

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交任务失败: {str(e)}"
        )


@router.get("/executions/{execution_id}/status")
async def get_execution_status(
    execution_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """获取执行状态"""
    try:
        executor = await get_task_executor()
        status = await executor.get_execution_status(execution_id)

        if not status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="执行记录不存在"
            )

        return status

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取执行状态失败: {str(e)}"
        )


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """取消执行"""
    try:
        executor = await get_task_executor()
        success = await executor.cancel_execution(execution_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无法取消执行"
            )

        return {"message": "执行已取消", "execution_id": execution_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消执行失败: {str(e)}"
        )


@router.get("/metrics", response_model=ExecutionMetrics)
async def get_execution_metrics(
    current_user: dict = Depends(get_current_active_user)
):
    """获取执行指标"""
    try:
        executor = await get_task_executor()
        metrics = await executor.get_metrics()
        return metrics

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取执行指标失败: {str(e)}"
        )


@router.get("/queue/status", response_model=ExecutionQueueStatus)
async def get_queue_status(
    current_user: dict = Depends(get_current_active_user)
):
    """获取队列状态"""
    try:
        executor = await get_task_executor()
        status = await executor.get_queue_status()
        return status

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取队列状态失败: {str(e)}"
        )


@router.get("/executions", response_model=List[Dict[str, Any]])
async def list_executions(
    status: Optional[ExecutionStatus] = None,
    agent_id: Optional[int] = None,
    limit: int = 100,
    skip: int = 0,
    current_user: dict = Depends(get_current_active_user)
):
    """获取执行记录列表"""
    try:
        executor = await get_task_executor()

        # 获取活跃执行记录
        executions = []
        for execution_id, execution_data in executor.active_executions.items():
            if status and execution_data.get("status") != status:
                continue
            if agent_id and execution_data.get("agent_id") != agent_id:
                continue

            executions.append({
                "execution_id": execution_id,
                "task_id": execution_data.get("task_id"),
                "agent_id": execution_data.get("agent_id"),
                "status": execution_data.get("status"),
                "started_at": execution_data.get("started_at"),
                "completed_at": execution_data.get("completed_at"),
                "execution_time": execution_data.get("execution_time"),
                "retry_count": execution_data.get("retry_count", 0),
                "created_at": execution_data.get("created_at")
            })

        # 分页处理
        start_idx = skip
        end_idx = start_idx + limit
        return executions[start_idx:end_idx]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取执行记录失败: {str(e)}"
        )


@router.get("/agents/{agent_id}/stats", response_model=AgentExecutionStats)
async def get_agent_execution_stats(
    agent_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """获取Agent执行统计"""
    try:
        executor = await get_task_executor()

        # 计算Agent统计信息
        agent_executions = [
            execution for execution in executor.active_executions.values()
            if execution.get("agent_id") == agent_id
        ]

        total_executions = len(agent_executions)
        successful_executions = sum(
            1 for execution in agent_executions
            if execution.get("status") == ExecutionStatus.COMPLETED
        )
        failed_executions = sum(
            1 for execution in agent_executions
            if execution.get("status") == ExecutionStatus.FAILED
        )

        # 计算平均执行时间
        completed_executions = [
            execution for execution in agent_executions
            if execution.get("status") == ExecutionStatus.COMPLETED
        ]

        if completed_executions:
            avg_execution_time = sum(
                execution.get("execution_time", 0) for execution in completed_executions
            ) / len(completed_executions)
        else:
            avg_execution_time = 0.0

        success_rate = successful_executions / total_executions if total_executions > 0 else 0.0

        # 当前负载
        current_load = executor.agent_loads.get(agent_id, 0)

        # 最后执行时间
        last_execution_time = None
        if agent_executions:
            last_execution = max(
                agent_executions,
                key=lambda x: x.get("completed_at", x.get("started_at"))
            )
            last_execution_time = last_execution.get("completed_at") or last_execution.get("started_at")

        return AgentExecutionStats(
            agent_id=agent_id,
            agent_type="unknown",  # 需要从Agent注册中心获取
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            average_execution_time=avg_execution_time,
            success_rate=success_rate,
            current_load=current_load,
            last_execution_time=last_execution_time
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Agent统计失败: {str(e)}"
        )


@router.post("/batch/submit")
async def batch_submit_tasks(
    requests: List[ExecutionRequest],
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """批量提交任务"""
    try:
        executor = await get_task_executor()
        responses = []

        for request in requests:
            # 构造任务数据
            task_data = {
                "task_id": request.task_id,
                "agent_id": request.agent_id,
                "task_type": request.task_type,
                "input_data": request.input_data,
                "timeout": request.timeout,
                "priority": request.priority,
                "metadata": request.metadata,
                "estimated_duration": request.timeout
            }

            # 提交任务
            response = await executor.submit_task(task_data, db)
            responses.append(response)

        return {
            "message": f"成功提交{len(responses)}个任务",
            "responses": responses
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量提交任务失败: {str(e)}"
        )


@router.get("/health")
async def executor_health_check():
    """执行器健康检查"""
    try:
        executor = await get_task_executor()

        # 检查执行器状态
        is_healthy = True
        active_count = len(executor.active_executions)
        queue_length = executor.task_queue.qsize()

        # 检查是否有过多活跃任务
        if active_count > executor.max_concurrent_executions:
            is_healthy = False

        return {
            "status": "healthy" if is_healthy else "degraded",
            "active_executions": active_count,
            "queue_length": queue_length,
            "max_concurrent": executor.max_concurrent_executions,
            "agent_loads": executor.agent_loads
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"健康检查失败: {str(e)}"
        )


@router.post("/cleanup")
async def cleanup_completed_executions(
    older_than_hours: int = 24,
    current_user: dict = Depends(get_current_active_user)
):
    """清理已完成的执行记录"""
    try:
        executor = await get_task_executor()

        # 计算时间阈值
        threshold = datetime.utcnow() - timedelta(hours=older_than_hours)

        # 清理已完成的执行记录
        cleaned_count = 0
        executions_to_remove = []

        for execution_id, execution_data in executor.active_executions.items():
            completed_at = execution_data.get("completed_at")
            if (completed_at and
                execution_data.get("status") in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED] and
                completed_at < threshold):
                executions_to_remove.append(execution_id)

        # 移除执行记录
        for execution_id in executions_to_remove:
            if execution_id in executor.active_executions:
                del executor.active_executions[execution_id]
                cleaned_count += 1

        return {
            "message": f"清理完成",
            "cleaned_count": cleaned_count,
            "remaining_executions": len(executor.active_executions)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理执行记录失败: {str(e)}"
        )