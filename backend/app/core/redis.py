import redis
import json
import logging
from typing import Optional, Any, Union, Dict, List
from contextlib import contextmanager
from .config import settings

logger = logging.getLogger(__name__)

# Redis连接池
redis_pool = redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)
redis_client = redis.Redis(connection_pool=redis_pool)


class RedisManager:
    """Redis操作管理器"""

    def __init__(self):
        self.client = redis_client

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            json_value = json.dumps(value, ensure_ascii=False)
            return self.client.set(key, json_value, ex=expire)
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            return bool(self.client.delete(key))
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return bool(self.client.exists(key))
        except Exception:
            return False


# 全局Redis管理器实例
redis_manager = RedisManager()


def get_redis():
    """获取Redis连接"""
    return redis_manager


class RedisCache:
    """Redis缓存操作类"""

    def __init__(self, redis_client=None):
        self.client = redis_client or redis_client
        self.default_ttl = getattr(settings, 'cache_ttl', 3600)
        self.prefix = getattr(settings, 'cache_prefix', 'tcp:')

    def _make_key(self, key: str) -> str:
        """生成缓存键"""
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            full_key = self._make_key(key)
            value = self.client.get(full_key)
            if value is not None:
                # 尝试解析JSON
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            full_key = self._make_key(key)
            if ttl is None:
                ttl = self.default_ttl

            # 序列化值
            if not isinstance(value, (str, int, float, bool)):
                value = json.dumps(value, ensure_ascii=False)

            return self.client.setex(full_key, ttl, value)
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            full_key = self._make_key(key)
            return bool(self.client.delete(full_key))
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            full_key = self._make_key(key)
            return bool(self.client.exists(full_key))
        except Exception as e:
            logger.error(f"检查缓存存在失败 {key}: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的缓存"""
        try:
            full_pattern = f"{self.prefix}:{pattern}"
            keys = self.client.keys(full_pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"清除缓存模式失败 {pattern}: {e}")
            return 0


class RedisStream:
    """Redis Streams消息队列操作类"""

    def __init__(self, redis_client=None):
        self.client = redis_client or redis_client

    def add_message(self, stream_name: str, message: dict) -> str:
        """添加消息到Stream"""
        try:
            return self.client.xadd(stream_name, message)
        except Exception as e:
            logger.error(f"添加消息到Stream失败 {stream_name}: {e}")
            raise

    def read_messages(self, stream_name: str, count: int = 1, block: Optional[int] = None) -> list:
        """从Stream读取消息"""
        try:
            result = self.client.xread({stream_name: '$'}, count=count, block=block)
            messages = []
            for stream, msgs in result:
                for msg_id, fields in msgs:
                    messages.append({
                        'id': msg_id,
                        'data': fields
                    })
            return messages
        except Exception as e:
            logger.error(f"从Stream读取消息失败 {stream_name}: {e}")
            return []

    def create_consumer_group(self, stream_name: str, group_name: str) -> bool:
        """创建消费者组"""
        try:
            self.client.xgroup_create(stream_name, group_name, id='0', mkstream=True)
            return True
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                return True  # 组已存在
            logger.error(f"创建消费者组失败 {group_name}: {e}")
            return False

    def read_group_messages(self, stream_name: str, group_name: str, consumer_name: str, count: int = 1) -> list:
        """从消费者组读取消息"""
        try:
            result = self.client.xreadgroup(
                group_name, consumer_name, {stream_name: '>'}, count=count
            )
            messages = []
            for stream, msgs in result:
                for msg_id, fields in msgs:
                    messages.append({
                        'id': msg_id,
                        'data': fields
                    })
            return messages
        except Exception as e:
            logger.error(f"从消费者组读取消息失败 {group_name}: {e}")
            return []

    def ack_message(self, stream_name: str, group_name: str, message_id: str) -> bool:
        """确认消息处理完成"""
        try:
            return bool(self.client.xack(stream_name, group_name, message_id))
        except Exception as e:
            logger.error(f"确认消息失败 {message_id}: {e}")
            return False


class RedisSession:
    """Redis会话管理类"""

    def __init__(self, redis_client=None):
        self.client = redis_client or redis_client
        self.session_prefix = "session:"
        self.session_ttl = getattr(settings, 'access_token_expire_minutes', 30) * 60  # 转换为秒

    def create_session(self, session_id: str, user_data: dict) -> bool:
        """创建会话"""
        try:
            key = f"{self.session_prefix}{session_id}"
            return bool(self.client.setex(key, self.session_ttl, json.dumps(user_data)))
        except Exception as e:
            logger.error(f"创建会话失败 {session_id}: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[dict]:
        """获取会话数据"""
        try:
            key = f"{self.session_prefix}{session_id}"
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"获取会话失败 {session_id}: {e}")
            return None

    def update_session(self, session_id: str, user_data: dict) -> bool:
        """更新会话数据"""
        try:
            key = f"{self.session_prefix}{session_id}"
            return bool(self.client.setex(key, self.session_ttl, json.dumps(user_data)))
        except Exception as e:
            logger.error(f"更新会话失败 {session_id}: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            key = f"{self.session_prefix}{session_id}"
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"删除会话失败 {session_id}: {e}")
            return False

    def refresh_session(self, session_id: str) -> bool:
        """刷新会话过期时间"""
        try:
            key = f"{self.session_prefix}{session_id}"
            return bool(self.client.expire(key, self.session_ttl))
        except Exception as e:
            logger.error(f"刷新会话失败 {session_id}: {e}")
            return False


# 增强功能的全局实例
redis_cache = RedisCache(redis_client)
redis_stream = RedisStream(redis_client)
redis_session = RedisSession(redis_client)


def get_redis_cache():
    """获取Redis缓存实例"""
    return redis_cache


def get_redis_stream():
    """获取Redis Stream实例"""
    return redis_stream


def get_redis_session():
    """获取Redis会话实例"""
    return redis_session