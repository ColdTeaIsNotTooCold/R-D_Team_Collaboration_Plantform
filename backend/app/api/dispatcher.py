from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

from ..core.database import get_db
from ..core.dispatcher import get_task_dispatcher, get_agent_lifecycle_manager
from ..api.deps import get_current_active_user
from ..schemas.task import TaskCreate, TaskUpdate, TaskDispatchRequest, TaskDispatchResponse, TaskQueueStatus, AgentWorkload

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentRegistrationRequest(BaseModel):
    """Agent注册请求"""
    agent_id: int
    agent_type: str
    capabilities: List[str]


class AgentStatusResponse(BaseModel):
    """Agent状态响应"""
    agent_id: int
    agent_type: str
    capabilities: List[str]
    status: str
    current_task: Optional[int]
    registered_at: str
    last_heartbeat: str
    error_count: int


class TaskDispatchRequest(BaseModel):
    """任务分发请求"""
    title: str
    description: Optional[str] = None
    task_type: str
    priority: str = "medium"
    input_data: Optional[str] = None
    creator_agent_id: Optional[int] = None


class TaskDispatchResponse(BaseModel):
    """任务分发响应"""
    task_id: str
    agent_id: int
    message_id: str
    status: str
    dispatched_at: str


class TaskCancelRequest(BaseModel):
    """任务取消请求"""
    task_id: str
    reason: Optional[str] = None


class AgentLoadResponse(BaseModel):
    """Agent负载响应"""
    total_agents: int
    idle_agents: int
    running_agents: int
    error_agents: int
    agents: List[Dict[str, Any]]


@router.post("/agents/register", response_model=Dict[str, Any])
async def register_agent(
    request: AgentRegistrationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """注册Agent"""
    try:
        agent_manager = get_agent_lifecycle_manager()

        success = await agent_manager.register_agent(
            request.agent_id,
            request.agent_type,
            request.capabilities
        )

        if success:
            logger.info(f"Agent {request.agent_id} registered by user {current_user.get('id')}")
            return {
                "success": True,
                "message": f"Agent {request.agent_id} registered successfully",
                "agent_id": request.agent_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register agent"
            )

    except Exception as e:
        logger.error(f"Error registering agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/agents/{agent_id}", response_model=Dict[str, Any])
async def unregister_agent(
    agent_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """注销Agent"""
    try:
        agent_manager = get_agent_lifecycle_manager()

        success = await agent_manager.unregister_agent(agent_id)

        if success:
            logger.info(f"Agent {agent_id} unregistered by user {current_user.get('id')}")
            return {
                "success": True,
                "message": f"Agent {agent_id} unregistered successfully",
                "agent_id": agent_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

    except Exception as e:
        logger.error(f"Error unregistering agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/agents/{agent_id}/status", response_model=AgentStatusResponse)
async def get_agent_status(
    agent_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取Agent状态"""
    try:
        agent_manager = get_agent_lifecycle_manager()

        agent_status = await agent_manager.get_agent_status(agent_id)

        if agent_status:
            return AgentStatusResponse(**agent_status)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent {agent_id} status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/agents", response_model=List[AgentStatusResponse])
async def list_agents(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """列出所有Agent"""
    try:
        agent_manager = get_agent_lifecycle_manager()

        agents = await agent_manager.list_agents()

        return [AgentStatusResponse(**agent) for agent in agents]

    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/agents/{agent_id}/heartbeat", response_model=Dict[str, Any])
async def send_agent_heartbeat(
    agent_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """发送Agent心跳"""
    try:
        agent_manager = get_agent_lifecycle_manager()

        success = await agent_manager.send_heartbeat(agent_id)

        if success:
            return {
                "success": True,
                "message": f"Heartbeat received for agent {agent_id}",
                "timestamp": "2025-09-17T00:00:00Z"  # 实际应该使用当前时间
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending heartbeat for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tasks/dispatch", response_model=TaskDispatchResponse)
async def dispatch_task(
    request: TaskDispatchRequest,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """分发任务"""
    try:
        dispatcher = get_task_dispatcher()

        # 分发任务
        result = await dispatcher.dispatch_task_with_capabilities(request, db)

        if result:
            logger.info(f"Task {result.task_id} dispatched to agent {result.agent_id}")
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No suitable agent available for task dispatch"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dispatching task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tasks/{task_id}/result", response_model=Dict[str, Any])
async def get_task_result(
    task_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取任务结果"""
    try:
        dispatcher = get_task_dispatcher()

        result = await dispatcher.get_task_result(task_id)

        if result:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task result for {task_id} not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task result {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tasks/cancel", response_model=Dict[str, Any])
async def cancel_task(
    request: TaskCancelRequest,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """取消任务"""
    try:
        dispatcher = get_task_dispatcher()

        success = await dispatcher.cancel_task(request.task_id)

        if success:
            logger.info(f"Task {request.task_id} cancelled by user {current_user.get('id')}")
            return {
                "success": True,
                "message": f"Task {request.task_id} cancelled successfully",
                "task_id": request.task_id,
                "reason": request.reason
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel task"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {request.task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/agents/load", response_model=AgentLoadResponse)
async def get_agent_load(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取Agent负载情况"""
    try:
        dispatcher = get_task_dispatcher()

        load_info = await dispatcher.get_agent_load()

        return AgentLoadResponse(**load_info)

    except Exception as e:
        logger.error(f"Error getting agent load: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/status", response_model=Dict[str, Any])
async def get_dispatcher_status(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取分发器状态"""
    try:
        dispatcher = get_task_dispatcher()
        agent_manager = get_agent_lifecycle_manager()

        active_agents = await agent_manager.list_agents()
        agent_load = await dispatcher.get_agent_load()

        return {
            "status": "running",
            "active_agents": len(active_agents),
            "dispatcher_info": {
                "task_queue": "task_queue",
                "task_results": "task_results",
                "agent_streams": "agent_tasks"
            },
            "agent_load": agent_load,
            "timestamp": "2025-09-17T00:00:00Z"  # 实际应该使用当前时间
        }

    except Exception as e:
        logger.error(f"Error getting dispatcher status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tasks/{task_id}/result", response_model=Dict[str, Any])
async def submit_task_result(
    task_id: str,
    result_data: Dict[str, Any],
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """提交任务结果"""
    try:
        dispatcher = get_task_dispatcher()

        success = await dispatcher.submit_task_result(task_id, result_data)

        if success:
            logger.info(f"Task result submitted for task {task_id}")
            return {
                "success": True,
                "message": f"Task result for {task_id} submitted successfully",
                "task_id": task_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit task result"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting task result: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tasks/queue/status", response_model=Dict[str, Any])
async def get_task_queue_status(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取任务队列状态"""
    try:
        dispatcher = get_task_dispatcher()

        status = await dispatcher.get_task_queue_status()

        return status

    except Exception as e:
        logger.error(f"Error getting task queue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/agents/workload", response_model=List[AgentWorkload])
async def get_agent_workload(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取Agent工作负载详情"""
    try:
        dispatcher = get_task_dispatcher()

        workload = await dispatcher.get_agent_workload_details()

        return [AgentWorkload(**agent) for agent in workload]

    except Exception as e:
        logger.error(f"Error getting agent workload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/agents/{agent_id}/restart", response_model=Dict[str, Any])
async def restart_agent(
    agent_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """重启Agent"""
    try:
        dispatcher = get_task_dispatcher()

        success = await dispatcher.restart_agent(agent_id)

        if success:
            logger.info(f"Agent {agent_id} restarted by user {current_user.get('id')}")
            return {
                "success": True,
                "message": f"Agent {agent_id} restarted successfully",
                "agent_id": agent_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restart agent"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/tasks/{task_id}/timeout", response_model=Dict[str, Any])
async def handle_task_timeout(
    task_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """处理任务超时"""
    try:
        dispatcher = get_task_dispatcher()

        success = await dispatcher.handle_task_timeout(task_id)

        if success:
            logger.info(f"Task timeout handled for task {task_id}")
            return {
                "success": True,
                "message": f"Task timeout handled for {task_id}",
                "task_id": task_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to handle task timeout"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling task timeout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )