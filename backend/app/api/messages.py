from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..core.database import get_db
from ..core.messaging import messaging_service, get_messaging_service
from ..core.communication import communication_manager, get_communication_manager
from ..schemas.message import MessageCreate, ConsumerGroupCreate, ConsumerCreate, StreamStats
from ..api.deps import get_current_active_user

router = APIRouter()


@router.post("/send")
async def send_message(
    message: MessageCreate,
    current_user: dict = Depends(get_current_active_user),
    messaging: messaging_service = Depends(get_messaging_service)
):
    """发送消息"""
    try:
        message_data = {
            'message_type': message.message_type,
            'content': message.content,
            'sender_id': message.sender_id or str(current_user['id']),
            'recipient_id': message.recipient_id,
            'priority': message.priority
        }

        message_id = await messaging.comm_manager.send_message(
            message.stream_name, message_data
        )

        return {
            "message_id": message_id,
            "status": "sent",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送消息失败: {str(e)}"
        )


@router.post("/streams/{stream_name}/groups")
async def create_consumer_group(
    stream_name: str,
    group: ConsumerGroupCreate,
    current_user: dict = Depends(get_current_active_user),
    comm_manager: communication_manager = Depends(get_communication_manager)
):
    """创建消费者组"""
    try:
        success = await comm_manager.create_consumer_group(
            stream_name, group.group_name, group.description
        )

        if success:
            return {
                "message": "消费者组创建成功",
                "stream_name": stream_name,
                "group_name": group.group_name
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="消费者组创建失败"
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建消费者组失败: {str(e)}"
        )


@router.post("/streams/{stream_name}/groups/{group_name}/consume")
async def consume_messages(
    stream_name: str,
    group_name: str,
    consumer_name: str,
    count: int = 1,
    current_user: dict = Depends(get_current_active_user),
    comm_manager: communication_manager = Depends(get_communication_manager)
):
    """消费消息"""
    try:
        messages = await comm_manager.consume_messages(
            stream_name, group_name, consumer_name, batch_size=count
        )

        return {
            "messages": [
                {
                    "id": msg.id,
                    "stream_name": msg.stream_name,
                    "message_type": msg.message_type,
                    "content": msg.content,
                    "sender_id": msg.sender_id,
                    "recipient_id": msg.recipient_id,
                    "priority": msg.priority,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ],
            "count": len(messages)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"消费消息失败: {str(e)}"
        )


@router.post("/streams/{stream_name}/groups/{group_name}/messages/{message_id}/ack")
async def acknowledge_message(
    stream_name: str,
    group_name: str,
    message_id: str,
    current_user: dict = Depends(get_current_active_user),
    comm_manager: communication_manager = Depends(get_communication_manager)
):
    """确认消息处理完成"""
    try:
        success = await comm_manager.acknowledge_message(
            stream_name, group_name, message_id
        )

        if success:
            return {
                "message": "消息确认成功",
                "message_id": message_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="消息确认失败"
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"确认消息失败: {str(e)}"
        )


@router.get("/streams")
async def list_streams(
    current_user: dict = Depends(get_current_active_user),
    comm_manager: communication_manager = Depends(get_communication_manager)
):
    """列出所有Stream"""
    try:
        streams = await comm_manager.list_streams()
        return {"streams": streams}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Stream列表失败: {str(e)}"
        )


@router.get("/streams/{stream_name}")
async def get_stream_info(
    stream_name: str,
    current_user: dict = Depends(get_current_active_user),
    comm_manager: communication_manager = Depends(get_communication_manager)
):
    """获取Stream信息"""
    try:
        info = await comm_manager.get_stream_info(stream_name)
        return info

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Stream信息失败: {str(e)}"
        )


@router.post("/agent/tasks")
async def send_agent_task(
    task_type: str,
    task_data: Dict[str, Any],
    target_agent_id: Optional[str] = None,
    priority: int = 0,
    current_user: dict = Depends(get_current_active_user),
    messaging: messaging_service = Depends(get_messaging_service)
):
    """发送Agent任务"""
    try:
        message_id = await messaging.send_agent_task(
            task_type, task_data, target_agent_id, priority
        )

        return {
            "task_id": message_id,
            "status": "queued",
            "message": "Agent任务已发送"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送Agent任务失败: {str(e)}"
        )


@router.post("/agent/responses")
async def send_agent_response(
    response_data: Dict[str, Any],
    original_task_id: Optional[str] = None,
    target_agent_id: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
    messaging: messaging_service = Depends(get_messaging_service)
):
    """发送Agent响应"""
    try:
        message_id = await messaging.send_agent_response(
            response_data, original_task_id, target_agent_id
        )

        return {
            "response_id": message_id,
            "status": "sent",
            "message": "Agent响应已发送"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送Agent响应失败: {str(e)}"
        )


@router.post("/agent/{agent_id}/consumer/start")
async def start_agent_consumer(
    agent_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user),
    messaging: messaging_service = Depends(get_messaging_service)
):
    """启动Agent消费者"""
    try:
        # 首先创建消费者组
        await messaging.create_agent_consumer_group(agent_id)

        # 启动消费者
        background_tasks.add_task(messaging.start_agent_consumer, agent_id)

        return {
            "message": f"Agent {agent_id} 消费者已启动",
            "agent_id": agent_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"启动Agent消费者失败: {str(e)}"
        )


@router.post("/agent/{agent_id}/consumer/stop")
async def stop_agent_consumer(
    agent_id: str,
    current_user: dict = Depends(get_current_active_user),
    messaging: messaging_service = Depends(get_messaging_service)
):
    """停止Agent消费者"""
    try:
        await messaging.stop_agent_consumer(agent_id)

        return {
            "message": f"Agent {agent_id} 消费者已停止",
            "agent_id": agent_id
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止Agent消费者失败: {str(e)}"
        )


@router.get("/system/status")
async def get_system_status(
    current_user: dict = Depends(get_current_active_user),
    messaging: messaging_service = Depends(get_messaging_service)
):
    """获取消息系统状态"""
    try:
        status = await messaging.get_system_status()
        return status

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统状态失败: {str(e)}"
        )


@router.post("/system/initialize")
async def initialize_system(
    current_user: dict = Depends(get_current_active_user),
    messaging: messaging_service = Depends(get_messaging_service)
):
    """初始化消息系统"""
    try:
        await messaging.initialize_default_streams()

        return {
            "message": "消息系统初始化完成",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"初始化消息系统失败: {str(e)}"
        )


@router.post("/system/events")
async def send_system_event(
    event_type: str,
    event_data: Dict[str, Any],
    severity: str = "info",
    current_user: dict = Depends(get_current_active_user),
    messaging: messaging_service = Depends(get_messaging_service)
):
    """发送系统事件"""
    try:
        message_id = await messaging.send_system_event(
            event_type, event_data, severity
        )

        return {
            "event_id": message_id,
            "status": "sent",
            "message": "系统事件已发送"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送系统事件失败: {str(e)}"
        )


@router.post("/user/{user_id}/notifications")
async def send_user_notification(
    user_id: str,
    notification_type: str,
    notification_data: Dict[str, Any],
    current_user: dict = Depends(get_current_active_user),
    messaging: messaging_service = Depends(get_messaging_service)
):
    """发送用户通知"""
    try:
        message_id = await messaging.send_user_notification(
            user_id, notification_type, notification_data
        )

        return {
            "notification_id": message_id,
            "status": "sent",
            "message": "用户通知已发送"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送用户通知失败: {str(e)}"
        )