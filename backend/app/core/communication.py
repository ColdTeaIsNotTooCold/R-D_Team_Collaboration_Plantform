import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..core.redis import get_redis_stream, redis_stream
from ..schemas.message import Message, ConsumerGroup, Consumer

logger = logging.getLogger(__name__)


class CommunicationManager:
    """通信管理器 - 基于Redis Streams的简单消息传递系统"""

    def __init__(self):
        self.redis_stream = redis_stream
        self.active_consumers: Dict[str, asyncio.Task] = {}
        self.consumer_groups: Dict[str, ConsumerGroup] = {}

    async def send_message(self, stream_name: str, message_data: Dict[str, Any]) -> str:
        """发送消息到指定的Stream"""
        try:
            # 添加时间戳和消息ID
            message_data.update({
                "timestamp": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat()
            })

            # 序列化消息内容
            serialized_data = {}
            for key, value in message_data.items():
                if isinstance(value, (dict, list)):
                    serialized_data[key] = json.dumps(value, ensure_ascii=False)
                else:
                    serialized_data[key] = str(value)

            message_id = await asyncio.get_event_loop().run_in_executor(
                None, self.redis_stream.add_message, stream_name, serialized_data
            )

            logger.info(f"消息已发送到Stream {stream_name}, ID: {message_id}")
            return message_id

        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            raise

    async def create_consumer_group(self, stream_name: str, group_name: str, description: str = None) -> bool:
        """创建消费者组"""
        try:
            success = await asyncio.get_event_loop().run_in_executor(
                None, self.redis_stream.create_consumer_group, stream_name, group_name
            )

            if success:
                self.consumer_groups[f"{stream_name}:{group_name}"] = ConsumerGroup(
                    id=len(self.consumer_groups) + 1,
                    group_name=group_name,
                    stream_name=stream_name,
                    description=description,
                    created_at=datetime.utcnow()
                )
                logger.info(f"消费者组创建成功: {group_name} for stream {stream_name}")

            return success

        except Exception as e:
            logger.error(f"创建消费者组失败: {e}")
            return False

    async def consume_messages(self, stream_name: str, group_name: str, consumer_name: str,
                            message_handler=None, batch_size: int = 1) -> List[Dict[str, Any]]:
        """从消费者组消费消息"""
        try:
            messages = await asyncio.get_event_loop().run_in_executor(
                None, self.redis_stream.read_group_messages,
                stream_name, group_name, consumer_name, batch_size
            )

            processed_messages = []
            for message in messages:
                try:
                    # 反序列化消息内容
                    deserialized_data = {}
                    for key, value in message['data'].items():
                        try:
                            deserialized_data[key] = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            deserialized_data[key] = value

                    message_obj = Message(
                        id=message['id'],
                        stream_name=stream_name,
                        message_type=deserialized_data.get('message_type', 'default'),
                        content=deserialized_data.get('content', {}),
                        sender_id=deserialized_data.get('sender_id'),
                        recipient_id=deserialized_data.get('recipient_id'),
                        priority=deserialized_data.get('priority', 0),
                        timestamp=datetime.fromisoformat(deserialized_data.get('timestamp', datetime.utcnow().isoformat()))
                    )

                    processed_messages.append(message_obj)

                    # 如果有消息处理器，则处理消息
                    if message_handler:
                        await message_handler(message_obj)

                    # 确认消息处理完成
                    await self.acknowledge_message(stream_name, group_name, message['id'])

                except Exception as e:
                    logger.error(f"处理消息失败 {message['id']}: {e}")
                    continue

            return processed_messages

        except Exception as e:
            logger.error(f"消费消息失败: {e}")
            return []

    async def acknowledge_message(self, stream_name: str, group_name: str, message_id: str) -> bool:
        """确认消息处理完成"""
        try:
            success = await asyncio.get_event_loop().run_in_executor(
                None, self.redis_stream.ack_message, stream_name, group_name, message_id
            )

            if success:
                logger.info(f"消息已确认: {message_id}")

            return success

        except Exception as e:
            logger.error(f"确认消息失败: {e}")
            return False

    async def start_consumer(self, stream_name: str, group_name: str, consumer_name: str,
                           message_handler=None, poll_interval: float = 1.0):
        """启动消费者任务"""
        consumer_key = f"{stream_name}:{group_name}:{consumer_name}"

        if consumer_key in self.active_consumers:
            logger.warning(f"消费者 {consumer_key} 已在运行")
            return

        async def consumer_task():
            logger.info(f"启动消费者: {consumer_key}")

            while consumer_key in self.active_consumers:
                try:
                    messages = await self.consume_messages(
                        stream_name, group_name, consumer_name,
                        message_handler, batch_size=1
                    )

                    if messages:
                        logger.info(f"消费者 {consumer_key} 处理了 {len(messages)} 条消息")

                    await asyncio.sleep(poll_interval)

                except asyncio.CancelledError:
                    logger.info(f"消费者 {consumer_key} 被取消")
                    break
                except Exception as e:
                    logger.error(f"消费者 {consumer_key} 出错: {e}")
                    await asyncio.sleep(poll_interval)

            logger.info(f"消费者 {consumer_key} 已停止")

        task = asyncio.create_task(consumer_task())
        self.active_consumers[consumer_key] = task

    async def stop_consumer(self, stream_name: str, group_name: str, consumer_name: str):
        """停止消费者任务"""
        consumer_key = f"{stream_name}:{group_name}:{consumer_name}"

        if consumer_key in self.active_consumers:
            task = self.active_consumers[consumer_key]
            task.cancel()
            del self.active_consumers[consumer_key]
            logger.info(f"消费者 {consumer_key} 已停止")

    async def get_stream_info(self, stream_name: str) -> Dict[str, Any]:
        """获取Stream信息"""
        try:
            # 获取Stream的基本信息
            info = {
                "stream_name": stream_name,
                "consumer_groups": [],
                "active_consumers": len(self.active_consumers),
                "pending_messages": 0
            }

            # 获取消费者组信息
            for group_key, group in self.consumer_groups.items():
                if group.stream_name == stream_name:
                    info["consumer_groups"].append({
                        "group_name": group.group_name,
                        "description": group.description,
                        "created_at": group.created_at.isoformat(),
                        "is_active": group.is_active
                    })

            return info

        except Exception as e:
            logger.error(f"获取Stream信息失败: {e}")
            return {"error": str(e)}

    async def list_streams(self) -> List[str]:
        """列出所有活跃的Stream"""
        try:
            streams = set()
            for group_key, group in self.consumer_groups.items():
                streams.add(group.stream_name)
            return list(streams)
        except Exception as e:
            logger.error(f"列出Stream失败: {e}")
            return []

    async def cleanup_inactive_consumers(self):
        """清理不活跃的消费者"""
        try:
            inactive_consumers = []

            for consumer_key, task in self.active_consumers.items():
                if task.done():
                    inactive_consumers.append(consumer_key)

            for consumer_key in inactive_consumers:
                del self.active_consumers[consumer_key]
                logger.info(f"清理不活跃的消费者: {consumer_key}")

        except Exception as e:
            logger.error(f"清理不活跃消费者失败: {e}")


# 全局通信管理器实例
communication_manager = CommunicationManager()


def get_communication_manager():
    """获取通信管理器实例"""
    return communication_manager