import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from .communication import communication_manager, get_communication_manager
from ..schemas.message import Message, MessageCreate

logger = logging.getLogger(__name__)


class MessagingService:
    """消息服务 - 提供更高层的消息抽象"""

    def __init__(self):
        self.comm_manager = communication_manager
        self.message_handlers: Dict[str, Callable] = {}
        self.default_streams = {
            'agent_tasks': 'agent_tasks',
            'agent_responses': 'agent_responses',
            'system_events': 'system_events',
            'user_notifications': 'user_notifications'
        }

    async def send_agent_task(self, task_type: str, task_data: Dict[str, Any],
                            target_agent_id: str = None, priority: int = 0) -> str:
        """发送Agent任务"""
        try:
            message_data = {
                'message_type': 'agent_task',
                'content': {
                    'task_type': task_type,
                    'task_data': task_data,
                    'created_at': datetime.utcnow().isoformat()
                },
                'sender_id': 'system',
                'recipient_id': target_agent_id,
                'priority': priority
            }

            return await self.comm_manager.send_message(
                self.default_streams['agent_tasks'], message_data
            )

        except Exception as e:
            logger.error(f"发送Agent任务失败: {e}")
            raise

    async def send_agent_response(self, response_data: Dict[str, Any],
                                original_task_id: str = None,
                                target_agent_id: str = None) -> str:
        """发送Agent响应"""
        try:
            message_data = {
                'message_type': 'agent_response',
                'content': {
                    'response_data': response_data,
                    'original_task_id': original_task_id,
                    'timestamp': datetime.utcnow().isoformat()
                },
                'sender_id': target_agent_id,
                'recipient_id': 'system',
                'priority': 0
            }

            return await self.comm_manager.send_message(
                self.default_streams['agent_responses'], message_data
            )

        except Exception as e:
            logger.error(f"发送Agent响应失败: {e}")
            raise

    async def send_system_event(self, event_type: str, event_data: Dict[str, Any],
                              severity: str = 'info') -> str:
        """发送系统事件"""
        try:
            message_data = {
                'message_type': 'system_event',
                'content': {
                    'event_type': event_type,
                    'event_data': event_data,
                    'severity': severity,
                    'timestamp': datetime.utcnow().isoformat()
                },
                'sender_id': 'system',
                'recipient_id': 'all',
                'priority': 1 if severity == 'error' else 0
            }

            return await self.comm_manager.send_message(
                self.default_streams['system_events'], message_data
            )

        except Exception as e:
            logger.error(f"发送系统事件失败: {e}")
            raise

    async def send_user_notification(self, user_id: str, notification_type: str,
                                  notification_data: Dict[str, Any]) -> str:
        """发送用户通知"""
        try:
            message_data = {
                'message_type': 'user_notification',
                'content': {
                    'notification_type': notification_type,
                    'notification_data': notification_data,
                    'timestamp': datetime.utcnow().isoformat()
                },
                'sender_id': 'system',
                'recipient_id': user_id,
                'priority': 0
            }

            return await self.comm_manager.send_message(
                self.default_streams['user_notifications'], message_data
            )

        except Exception as e:
            logger.error(f"发送用户通知失败: {e}")
            raise

    async def register_message_handler(self, message_type: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        logger.info(f"注册消息处理器: {message_type}")

    async def process_message(self, message: Message):
        """处理接收到的消息"""
        try:
            handler = self.message_handlers.get(message.message_type)
            if handler:
                await handler(message)
            else:
                logger.warning(f"未找到消息处理器: {message.message_type}")

        except Exception as e:
            logger.error(f"处理消息失败: {e}")

    async def create_agent_consumer_group(self, agent_id: str) -> bool:
        """为Agent创建消费者组"""
        try:
            group_name = f"agent_{agent_id}"
            return await self.comm_manager.create_consumer_group(
                self.default_streams['agent_tasks'],
                group_name,
                f"Consumer group for agent {agent_id}"
            )

        except Exception as e:
            logger.error(f"创建Agent消费者组失败: {e}")
            return False

    async def start_agent_consumer(self, agent_id: str, message_handler: Callable = None):
        """启动Agent消费者"""
        try:
            group_name = f"agent_{agent_id}"
            consumer_name = f"agent_{agent_id}_consumer"

            # 如果没有提供消息处理器，使用默认处理器
            if message_handler is None:
                message_handler = self.process_message

            await self.comm_manager.start_consumer(
                self.default_streams['agent_tasks'],
                group_name,
                consumer_name,
                message_handler
            )

            logger.info(f"Agent消费者已启动: {agent_id}")

        except Exception as e:
            logger.error(f"启动Agent消费者失败: {e}")

    async def stop_agent_consumer(self, agent_id: str):
        """停止Agent消费者"""
        try:
            group_name = f"agent_{agent_id}"
            consumer_name = f"agent_{agent_id}_consumer"

            await self.comm_manager.stop_consumer(
                self.default_streams['agent_tasks'],
                group_name,
                consumer_name
            )

            logger.info(f"Agent消费者已停止: {agent_id}")

        except Exception as e:
            logger.error(f"停止Agent消费者失败: {e}")

    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            status = {
                'streams': {},
                'consumer_groups': {},
                'active_consumers': 0,
                'message_handlers': list(self.message_handlers.keys())
            }

            # 获取所有Stream状态
            for stream_name in self.default_streams.values():
                stream_info = await self.comm_manager.get_stream_info(stream_name)
                status['streams'][stream_name] = stream_info

            # 获取消费者组状态
            for group_key, group in self.comm_manager.consumer_groups.items():
                status['consumer_groups'][group_key] = {
                    'group_name': group.group_name,
                    'stream_name': group.stream_name,
                    'created_at': group.created_at.isoformat(),
                    'is_active': group.is_active
                }

            status['active_consumers'] = len(self.comm_manager.active_consumers)

            return status

        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {'error': str(e)}

    async def initialize_default_streams(self):
        """初始化默认Stream和消费者组"""
        try:
            # 为系统事件创建消费者组
            await self.comm_manager.create_consumer_group(
                self.default_streams['system_events'],
                'system_event_consumers',
                'System event consumer group'
            )

            # 为用户通知创建消费者组
            await self.comm_manager.create_consumer_group(
                self.default_streams['user_notifications'],
                'notification_consumers',
                'User notification consumer group'
            )

            logger.info("默认Stream和消费者组初始化完成")

        except Exception as e:
            logger.error(f"初始化默认Stream失败: {e}")


# 全局消息服务实例
messaging_service = MessagingService()


def get_messaging_service():
    """获取消息服务实例"""
    return messaging_service