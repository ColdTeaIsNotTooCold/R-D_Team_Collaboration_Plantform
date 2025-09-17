from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime

from ..core.database import get_db
from ..api.deps import get_current_active_user
from ..agents.registry import get_agent_registry
from ..schemas.agent import (
    AgentRegistryRequest,
    AgentRegistryResponse,
    AgentDiscoveryRequest,
    AgentHealthCheck,
    AgentStatistics
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[dict])
async def read_agents(
    skip: int = 0,
    limit: int = 100,
    agent_type: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取Agent列表"""
    try:
        registry = await get_agent_registry()
        agents = await registry.list_agents(agent_type=agent_type)

        # 分页处理
        start_idx = skip
        end_idx = start_idx + limit
        paginated_agents = agents[start_idx:end_idx]

        return paginated_agents
    except Exception as e:
        logger.error(f"获取Agent列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取Agent列表失败")


@router.get("/{agent_id}", response_model=dict)
async def read_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取指定Agent信息"""
    try:
        registry = await get_agent_registry()
        agent_info = await registry.get_agent(agent_id)

        if not agent_info:
            raise HTTPException(status_code=404, detail="Agent not found")

        return agent_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Agent信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取Agent信息失败")


@router.post("/register", response_model=AgentRegistryResponse)
async def register_agent(
    agent_data: AgentRegistryRequest,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """注册新的Agent"""
    try:
        registry = await get_agent_registry()

        # 准备注册数据
        agent_dict = agent_data.dict()
        agent_dict["owner_id"] = current_user.get("id")

        # 注册Agent
        agent_id = await registry.register_agent(agent_dict)

        # 获取注册后的Agent信息
        agent_info = await registry.get_agent(agent_id)

        return AgentRegistryResponse(**agent_info)
    except ValueError as e:
        logger.error(f"Agent注册失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Agent注册失败: {e}")
        raise HTTPException(status_code=500, detail="Agent注册失败")


@router.delete("/{agent_id}")
async def unregister_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """注销Agent"""
    try:
        registry = await get_agent_registry()
        await registry.unregister_agent(agent_id)

        return {"message": f"Agent {agent_id} 注销成功"}
    except ValueError as e:
        logger.error(f"Agent注销失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Agent注销失败: {e}")
        raise HTTPException(status_code=500, detail="Agent注销失败")


@router.post("/{agent_id}/heartbeat")
async def agent_heartbeat(
    agent_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Agent心跳更新"""
    try:
        registry = await get_agent_registry()
        await registry.update_heartbeat(agent_id)

        return {"message": "心跳更新成功", "timestamp": "success"}
    except Exception as e:
        logger.error(f"心跳更新失败: {e}")
        raise HTTPException(status_code=500, detail="心跳更新失败")


@router.get("/{agent_id}/health", response_model=AgentHealthCheck)
async def check_agent_health(
    agent_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """检查Agent健康状态"""
    try:
        registry = await get_agent_registry()
        is_healthy = await registry.health_check(agent_id)

        if not is_healthy:
            raise HTTPException(status_code=404, detail="Agent不存在或不活跃")

        return AgentHealthCheck(
            agent_id=agent_id,
            status="active" if is_healthy else "inactive",
            timestamp="now"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail="健康检查失败")


@router.post("/discover", response_model=List[dict])
async def discover_agents(
    discovery_request: AgentDiscoveryRequest,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """发现具有特定能力的Agent"""
    try:
        registry = await get_agent_registry()
        agents = await registry.discover_agents(discovery_request.required_capabilities)

        # 按类型过滤
        if discovery_request.agent_type:
            agents = [agent for agent in agents if agent.get("agent_type") == discovery_request.agent_type]

        # 限制结果数量
        if discovery_request.max_results:
            agents = agents[:discovery_request.max_results]

        return agents
    except Exception as e:
        logger.error(f"Agent发现失败: {e}")
        raise HTTPException(status_code=500, detail="Agent发现失败")


@router.put("/{agent_id}/capabilities")
async def update_agent_capabilities(
    agent_id: str,
    capabilities: List[str],
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新Agent能力"""
    try:
        registry = await get_agent_registry()
        await registry.update_agent_capabilities(agent_id, capabilities)

        return {"message": f"Agent {agent_id} 能力更新成功"}
    except ValueError as e:
        logger.error(f"能力更新失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"能力更新失败: {e}")
        raise HTTPException(status_code=500, detail="能力更新失败")


@router.get("/statistics/summary", response_model=AgentStatistics)
async def get_agent_statistics(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取Agent统计信息"""
    try:
        registry = await get_agent_registry()
        stats = await registry.get_agent_statistics()

        return AgentStatistics(**stats)
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")


@router.post("/cleanup/inactive")
async def cleanup_inactive_agents(
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """清理不活跃的Agent"""
    try:
        registry = await get_agent_registry()
        cleaned_count = await registry.cleanup_inactive_agents()

        return {"message": f"清理了 {cleaned_count} 个不活跃的Agent"}
    except Exception as e:
        logger.error(f"清理失败: {e}")
        raise HTTPException(status_code=500, detail="清理失败")


@router.post("/{agent_id}/execute", response_model=dict)
async def execute_agent(
    agent_id: str,
    task_data: dict,
    current_user: dict = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """执行Agent任务"""
    try:
        # 验证Agent存在且活跃
        registry = await get_agent_registry()
        agent_info = await registry.get_agent(agent_id)

        if not agent_info:
            raise HTTPException(status_code=404, detail="Agent not found")

        if agent_info.get("status") != "active":
            raise HTTPException(status_code=400, detail="Agent not active")

        # TODO: 实现Agent执行逻辑
        return {
            "task_id": f"task_{agent_id}_{datetime.now().timestamp()}",
            "agent_id": agent_id,
            "status": "started",
            "message": "Agent execution started",
            "estimated_time": "30s"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent执行失败: {e}")
        raise HTTPException(status_code=500, detail="Agent执行失败")