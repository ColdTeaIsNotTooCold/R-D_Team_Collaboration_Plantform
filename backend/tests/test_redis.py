import pytest
import json
import time
from unittest.mock import Mock, patch

from app.core.redis import (
    RedisManager,
    RedisCache,
    RedisStream,
    RedisSession,
    redis_manager,
    redis_cache,
    redis_stream,
    redis_session,
    get_redis_cache,
    get_redis_stream,
    get_redis_session
)


class TestRedisManager:
    """Redis管理器测试"""

    def test_get_success(self):
        """测试获取缓存值成功"""
        # 模拟redis客户端
        mock_client = Mock()
        mock_client.get.return_value = '{"key": "value"}'

        # 替换redis客户端
        with patch.object(redis_manager, 'client', mock_client):
            result = redis_manager.get('test_key')
            assert result == {"key": "value"}
            mock_client.get.assert_called_once_with('test_key')

    def test_get_not_found(self):
        """测试获取不存在的缓存值"""
        mock_client = Mock()
        mock_client.get.return_value = None

        with patch.object(redis_manager, 'client', mock_client):
            result = redis_manager.get('nonexistent_key')
            assert result is None

    def test_set_success(self):
        """测试设置缓存值成功"""
        mock_client = Mock()
        mock_client.set.return_value = True

        with patch.object(redis_manager, 'client', mock_client):
            result = redis_manager.set('test_key', {'data': 'value'}, 300)
            assert result is True
            mock_client.set.assert_called_once()

    def test_delete_success(self):
        """测试删除缓存值成功"""
        mock_client = Mock()
        mock_client.delete.return_value = 1

        with patch.object(redis_manager, 'client', mock_client):
            result = redis_manager.delete('test_key')
            assert result is True

    def test_exists_true(self):
        """测试检查键存在"""
        mock_client = Mock()
        mock_client.exists.return_value = 1

        with patch.object(redis_manager, 'client', mock_client):
            result = redis_manager.exists('test_key')
            assert result is True

    def test_exists_false(self):
        """测试检查键不存在"""
        mock_client = Mock()
        mock_client.exists.return_value = 0

        with patch.object(redis_manager, 'client', mock_client):
            result = redis_manager.exists('nonexistent_key')
            assert result is False


class TestRedisCache:
    """Redis缓存测试"""

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        mock_client = Mock()
        cache = RedisCache(mock_client)

        # 测试_make_key方法
        key = cache._make_key('user_data')
        assert key.startswith('tcp:user_data')

    def test_cache_get_with_json(self):
        """测试获取JSON格式的缓存数据"""
        mock_client = Mock()
        mock_client.get.return_value = '{"user_id": 123, "name": "test"}'

        cache = RedisCache(mock_client)
        result = cache.get('user_123')

        assert result == {"user_id": 123, "name": "test"}

    def test_cache_get_with_string(self):
        """测试获取字符串格式的缓存数据"""
        mock_client = Mock()
        mock_client.get.return_value = 'simple_string_value'

        cache = RedisCache(mock_client)
        result = cache.get('simple_key')

        assert result == 'simple_string_value'

    def test_cache_set_with_dict(self):
        """测试设置字典类型的缓存数据"""
        mock_client = Mock()
        mock_client.setex.return_value = True

        cache = RedisCache(mock_client)
        result = cache.set('user_data', {'id': 123, 'name': 'test'})

        assert result is True
        mock_client.setex.assert_called_once()

    def test_cache_set_with_string(self):
        """测试设置字符串类型的缓存数据"""
        mock_client = Mock()
        mock_client.setex.return_value = True

        cache = RedisCache(mock_client)
        result = cache.set('simple_key', 'simple_value')

        assert result is True
        # 字符串值不应该被JSON序列化
        call_args = mock_client.setex.call_args
        assert 'simple_value' in call_args[0]

    def test_cache_clear_pattern(self):
        """测试清除匹配模式的缓存"""
        mock_client = Mock()
        mock_client.keys.return_value = ['tcp:user:1', 'tcp:user:2']
        mock_client.delete.return_value = 2

        cache = RedisCache(mock_client)
        result = cache.clear_pattern('user:*')

        assert result == 2
        mock_client.keys.assert_called_once_with('tcp:user:*')
        mock_client.delete.assert_called_once_with('tcp:user:1', 'tcp:user:2')


class TestRedisStream:
    """Redis Stream测试"""

    def test_add_message(self):
        """测试添加消息到Stream"""
        mock_client = Mock()
        mock_client.xadd.return_value = '1672531200000-0'

        stream = RedisStream(mock_client)
        result = stream.add_message('test_stream', {'type': 'message', 'data': 'test'})

        assert result == '1672531200000-0'
        mock_client.xadd.assert_called_once_with('test_stream', {'type': 'message', 'data': 'test'})

    def test_read_messages(self):
        """测试从Stream读取消息"""
        mock_client = Mock()
        mock_client.xread.return_value = [
            ('test_stream', [
                ('1672531200000-0', {'type': 'message', 'data': 'test'})
            ])
        ]

        stream = RedisStream(mock_client)
        result = stream.read_messages('test_stream')

        assert len(result) == 1
        assert result[0]['id'] == '1672531200000-0'
        assert result[0]['data']['type'] == 'message'

    def test_create_consumer_group(self):
        """测试创建消费者组"""
        mock_client = Mock()
        mock_client.xgroup_create.return_value = True

        stream = RedisStream(mock_client)
        result = stream.create_consumer_group('test_stream', 'test_group')

        assert result is True
        mock_client.xgroup_create.assert_called_once_with('test_stream', 'test_group', id='0', mkstream=True)

    def test_create_consumer_group_already_exists(self):
        """测试创建已存在的消费者组"""
        mock_client = Mock()
        from redis import ResponseError
        mock_client.xgroup_create.side_effect = ResponseError("BUSYGROUP Consumer Group name already exists")

        stream = RedisStream(mock_client)
        result = stream.create_consumer_group('test_stream', 'existing_group')

        assert result is True  # 应该返回True，因为组已存在

    def test_read_group_messages(self):
        """测试从消费者组读取消息"""
        mock_client = Mock()
        mock_client.xreadgroup.return_value = [
            ('test_stream', [
                ('1672531200000-0', {'type': 'message', 'data': 'test'})
            ])
        ]

        stream = RedisStream(mock_client)
        result = stream.read_group_messages('test_stream', 'test_group', 'consumer1')

        assert len(result) == 1
        assert result[0]['id'] == '1672531200000-0'

    def test_ack_message(self):
        """测试确认消息处理完成"""
        mock_client = Mock()
        mock_client.xack.return_value = 1

        stream = RedisStream(mock_client)
        result = stream.ack_message('test_stream', 'test_group', '1672531200000-0')

        assert result is True
        mock_client.xack.assert_called_once_with('test_stream', 'test_group', '1672531200000-0')


class TestRedisSession:
    """Redis会话测试"""

    def test_create_session(self):
        """测试创建会话"""
        mock_client = Mock()
        mock_client.setex.return_value = True

        session = RedisSession(mock_client)
        user_data = {'user_id': 123, 'username': 'testuser'}
        result = session.create_session('session_token_123', user_data)

        assert result is True
        mock_client.setex.assert_called_once()

    def test_get_session(self):
        """测试获取会话数据"""
        mock_client = Mock()
        mock_client.get.return_value = '{"user_id": 123, "username": "testuser"}'

        session = RedisSession(mock_client)
        result = session.get_session('session_token_123')

        assert result == {'user_id': 123, 'username': 'testuser'}

    def test_get_session_not_found(self):
        """测试获取不存在的会话"""
        mock_client = Mock()
        mock_client.get.return_value = None

        session = RedisSession(mock_client)
        result = session.get_session('nonexistent_session')

        assert result is None

    def test_update_session(self):
        """测试更新会话数据"""
        mock_client = Mock()
        mock_client.setex.return_value = True

        session = RedisSession(mock_client)
        user_data = {'user_id': 123, 'username': 'updated_user'}
        result = session.update_session('session_token_123', user_data)

        assert result is True

    def test_delete_session(self):
        """测试删除会话"""
        mock_client = Mock()
        mock_client.delete.return_value = 1

        session = RedisSession(mock_client)
        result = session.delete_session('session_token_123')

        assert result is True

    def test_refresh_session(self):
        """测试刷新会话过期时间"""
        mock_client = Mock()
        mock_client.expire.return_value = True

        session = RedisSession(mock_client)
        result = session.refresh_session('session_token_123')

        assert result is True


class TestRedisDependencyInjection:
    """Redis依赖注入测试"""

    def test_get_redis_cache(self):
        """测试获取Redis缓存依赖"""
        cache = get_redis_cache()
        assert isinstance(cache, RedisCache)

    def test_get_redis_stream(self):
        """测试获取Redis Stream依赖"""
        stream = get_redis_stream()
        assert isinstance(stream, RedisStream)

    def test_get_redis_session(self):
        """测试获取Redis会话依赖"""
        session = get_redis_session()
        assert isinstance(session, RedisSession)


@pytest.mark.integration
class TestRedisIntegration:
    """Redis集成测试（需要真实的Redis服务）"""

    @pytest.fixture
    def real_redis_client(self):
        """获取真实的Redis客户端"""
        import redis
        client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
        try:
            client.ping()
            yield client
        finally:
            # 清理测试数据
            client.flushdb()
            client.close()

    def test_real_redis_connection(self, real_redis_client):
        """测试真实Redis连接"""
        assert real_redis_client.ping() is True

    def test_real_cache_operations(self, real_redis_client):
        """测试真实缓存操作"""
        cache = RedisCache(real_redis_client)

        # 测试设置和获取
        assert cache.set('test_key', {'data': 'test'}) is True
        result = cache.get('test_key')
        assert result == {'data': 'test'}

        # 测试删除
        assert cache.delete('test_key') is True
        assert cache.get('test_key') is None

    def test_real_session_operations(self, real_redis_client):
        """测试真实会话操作"""
        session = RedisSession(real_redis_client)

        # 测试创建会话
        user_data = {'user_id': 123, 'username': 'testuser'}
        assert session.create_session('test_session', user_data) is True

        # 测试获取会话
        result = session.get_session('test_session')
        assert result == user_data

        # 测试删除会话
        assert session.delete_session('test_session') is True
        assert session.get_session('test_session') is None

    def test_real_stream_operations(self, real_redis_client):
        """测试真实Stream操作"""
        stream = RedisStream(real_redis_client)

        # 测试创建消费者组
        assert stream.create_consumer_group('test_stream', 'test_group') is True

        # 测试添加消息
        message_id = stream.add_message('test_stream', {'type': 'test', 'data': 'hello'})
        assert message_id is not None

        # 测试读取消息
        messages = stream.read_messages('test_stream', count=1)
        assert len(messages) > 0
        assert messages[0]['data']['type'] == 'test'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])