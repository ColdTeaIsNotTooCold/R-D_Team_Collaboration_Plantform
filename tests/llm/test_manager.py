"""
LLM管理器测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from backend.app.services.llm.manager import LLMManager
from backend.app.services.llm.load_balancer import LoadBalancer
from backend.app.services.llm.cost_monitor import CostMonitor
from backend.app.models.llm import LLMRequest, LLMResponse, LLMMessage
from backend.app.core.llm_config import LLMConfig, LLMProvider, LLMModelConfig


class TestLLMManager:
    """LLM管理器测试"""

    @pytest.fixture
    def mock_config(self):
        """模拟配置"""
        config = Mock(spec=LLMConfig)
        config.providers = {}
        config.model_configs = {}
        config.load_balancing_strategy = "round_robin"
        config.health_check_interval = 60
        return config

    @pytest.fixture
    def mock_factory(self):
        """模拟工厂"""
        from backend.app.services.llm.base import LLMProviderFactory
        factory = Mock(spec=LLMProviderFactory)
        factory._providers = {}
        factory.list_available_models.return_value = []
        return factory

    @pytest.fixture
    def mock_cost_monitor(self):
        """模拟成本监控器"""
        cost_monitor = Mock(spec=CostMonitor)
        cost_monitor._is_initialized = True
        cost_monitor.record_usage = AsyncMock()
        cost_monitor.get_usage_statistics = AsyncMock(return_value={
            "total_requests": 10,
            "total_tokens": 1000,
            "total_cost": 0.1
        })
        return cost_monitor

    @pytest.fixture
    def mock_load_balancer(self):
        """模拟负载均衡器"""
        load_balancer = Mock(spec=LoadBalancer)
        load_balancer._is_initialized = True
        load_balancer.select_provider = AsyncMock()
        load_balancer.record_request_result = AsyncMock()
        load_balancer.get_load_balancing_stats = AsyncMock(return_value={})
        return load_balancer

    @pytest.fixture
    def mock_provider(self):
        """模拟提供商"""
        provider = Mock()
        provider.is_initialized.return_value = True
        provider.generate_response = AsyncMock()
        provider.model_configs = {}
        provider.provider_config = Mock()
        provider.provider_config.name = "test_provider"
        return provider

    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_config, mock_factory, mock_cost_monitor, mock_load_balancer):
        """测试初始化成功"""
        with patch('backend.app.services.llm.manager.get_llm_config', return_value=mock_config), \
             patch('backend.app.services.llm.manager.get_llm_provider_factory', return_value=mock_factory), \
             patch('backend.app.services.llm.manager.get_cost_monitor', return_value=mock_cost_monitor), \
             patch('backend.app.services.llm.manager.get_load_balancer', return_value=mock_load_balancer):

            manager = LLMManager()
            result = await manager.initialize()

            assert result is True
            assert manager._is_initialized is True
            assert manager.config == mock_config
            assert manager.factory == mock_factory
            assert manager.cost_monitor == mock_cost_monitor
            assert manager.load_balancer == mock_load_balancer

    @pytest.mark.asyncio
    async def test_generate_response_success(self, mock_config, mock_factory, mock_cost_monitor, mock_load_balancer, mock_provider):
        """测试生成响应成功"""
        # 设置模拟返回值
        mock_load_balancer.select_provider.return_value = mock_provider
        mock_response = LLMResponse(
            id="test_id",
            model="gpt-3.5-turbo",
            provider="test_provider",
            content="Test response",
            finish_reason="stop",
            usage={"total_tokens": 10},
            tokens={"input": 5, "output": 5, "total": 10},
            cost=0.001,
            latency=0.5
        )
        mock_provider.generate_response.return_value = mock_response

        with patch('backend.app.services.llm.manager.get_llm_config', return_value=mock_config), \
             patch('backend.app.services.llm.manager.get_llm_provider_factory', return_value=mock_factory), \
             patch('backend.app.services.llm.manager.get_cost_monitor', return_value=mock_cost_monitor), \
             patch('backend.app.services.llm.manager.get_load_balancer', return_value=mock_load_balancer):

            manager = LLMManager()
            await manager.initialize()

            request = LLMRequest(
                model="gpt-3.5-turbo",
                messages=[LLMMessage(role="user", content="Hello")]
            )

            response = await manager.generate_response(request)

            assert response == mock_response
            mock_load_balancer.select_provider.assert_called_once_with("gpt-3.5-turbo", None)
            mock_provider.generate_response.assert_called_once()
            mock_load_balancer.record_request_result.assert_called_once_with("test_provider", True, 0.5)

    @pytest.mark.asyncio
    async def test_generate_response_with_fallback(self, mock_config, mock_factory, mock_cost_monitor, mock_load_balancer, mock_provider):
        """测试生成响应失败后使用备用提供商"""
        # 设置主提供商失败
        mock_load_balancer.select_provider.side_effect = [mock_provider, mock_provider]
        mock_provider.generate_response.side_effect = [Exception("Provider failed"), None]

        # 设置备用响应
        fallback_response = LLMResponse(
            id="fallback_id",
            model="gpt-3.5-turbo",
            provider="test_provider",
            content="Fallback response",
            finish_reason="stop",
            usage={"total_tokens": 10},
            tokens={"input": 5, "output": 5, "total": 10},
            cost=0.001,
            latency=0.5
        )
        mock_provider.generate_response.side_effect = [Exception("Provider failed"), fallback_response]

        with patch('backend.app.services.llm.manager.get_llm_config', return_value=mock_config), \
             patch('backend.app.services.llm.manager.get_llm_provider_factory', return_value=mock_factory), \
             patch('backend.app.services.llm.manager.get_cost_monitor', return_value=mock_cost_monitor), \
             patch('backend.app.services.llm.manager.get_load_balancer', return_value=mock_load_balancer):

            manager = LLMManager()
            await manager.initialize()

            request = LLMRequest(
                model="gpt-3.5-turbo",
                messages=[LLMMessage(role="user", content="Hello")]
            )

            response = await manager.generate_response(request)

            assert response == fallback_response
            assert mock_load_balancer.select_provider.call_count == 2

    @pytest.mark.asyncio
    async def test_get_available_models(self, mock_config, mock_factory, mock_cost_monitor, mock_load_balancer):
        """测试获取可用模型列表"""
        mock_factory.list_available_models.return_value = ["gpt-3.5-turbo", "gpt-4"]

        with patch('backend.app.services.llm.manager.get_llm_config', return_value=mock_config), \
             patch('backend.app.services.llm.manager.get_llm_provider_factory', return_value=mock_factory), \
             patch('backend.app.services.llm.manager.get_cost_monitor', return_value=mock_cost_monitor), \
             patch('backend.app.services.llm.manager.get_load_balancer', return_value=mock_load_balancer):

            manager = LLMManager()
            await manager.initialize()

            models = await manager.get_available_models()

            assert models == ["gpt-3.5-turbo", "gpt-4"]
            mock_factory.list_available_models.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self, mock_config, mock_factory, mock_cost_monitor, mock_load_balancer):
        """测试健康检查"""
        mock_factory.health_check_all_providers.return_value = {"test_provider": True}

        with patch('backend.app.services.llm.manager.get_llm_config', return_value=mock_config), \
             patch('backend.app.services.llm.manager.get_llm_provider_factory', return_value=mock_factory), \
             patch('backend.app.services.llm.manager.get_cost_monitor', return_value=mock_cost_monitor), \
             patch('backend.app.services.llm.manager.get_load_balancer', return_value=mock_load_balancer):

            manager = LLMManager()
            await manager.initialize()

            result = await manager.health_check()

            assert result is True
            mock_factory.health_check_all_providers.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, mock_config, mock_factory, mock_cost_monitor, mock_load_balancer, mock_provider):
        """测试关闭管理器"""
        mock_factory._providers = {"test_provider": mock_provider}

        with patch('backend.app.services.llm.manager.get_llm_config', return_value=mock_config), \
             patch('backend.app.services.llm.manager.get_llm_provider_factory', return_value=mock_factory), \
             patch('backend.app.services.llm.manager.get_cost_monitor', return_value=mock_cost_monitor), \
             patch('backend.app.services.llm.manager.get_load_balancer', return_value=mock_load_balancer):

            manager = LLMManager()
            await manager.initialize()
            await manager.close()

            assert manager._is_initialized is False
            # 注意：如果provider有close方法，应该调用它
            # mock_provider.close.assert_called_once()