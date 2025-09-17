"""
LLM配置测试
"""
import pytest
from unittest.mock import Mock, patch
from backend.app.core.llm_config import LLMConfig, LLMProvider, LLMModelConfig


class TestLLMConfig:
    """LLM配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = LLMConfig()

        assert config.app_name == "Team Collaboration Platform"
        assert config.app_version == "1.0.0"
        assert config.default_model == "gpt-3.5-turbo"
        assert config.request_timeout == 30
        assert config.max_retries == 3

    def test_providers_config(self):
        """测试提供商配置"""
        config = LLMConfig()

        # 测试无API密钥时的提供商
        providers = config.providers
        assert len(providers) == 0

        # 测试有OpenAI密钥时的提供商
        with patch.object(config, 'openai_api_key', 'test-key'):
            with patch.object(config, 'openai_enabled', True):
                providers = config.providers
                assert len(providers) == 1
                assert "openai" in providers
                assert providers["openai"].api_key == "test-key"

    def test_model_configs(self):
        """测试模型配置"""
        config = LLMConfig()

        # 测试默认模型配置
        model_configs = config.model_configs
        assert "gpt-4" in model_configs
        assert "gpt-3.5-turbo" in model_configs
        assert "claude-3-haiku-20240307" in model_configs

        # 测试GPT-4配置
        gpt4_config = model_configs["gpt-4"]
        assert gpt4_config.provider == "openai"
        assert gpt4_config.max_tokens == 8192
        assert gpt4_config.cost_per_1k_input == 0.03

    def test_cost_control(self):
        """测试成本控制配置"""
        config = LLMConfig()

        cost_control = config.cost_control
        assert cost_control.monthly_limit == 1000.0
        assert cost_control.daily_limit == 100.0
        assert cost_control.alert_threshold == 0.8
        assert cost_control.enable_monitoring == True

    def test_get_provider_config(self):
        """测试获取提供商配置"""
        config = LLMConfig()

        # 测试不存在的提供商
        provider = config.get_provider_config("nonexistent")
        assert provider is None

    def test_get_model_config(self):
        """测试获取模型配置"""
        config = LLMConfig()

        # 测试存在的模型
        model_config = config.get_model_config("gpt-4")
        assert model_config is not None
        assert model_config.provider == "openai"

        # 测试不存在的模型
        model_config = config.get_model_config("nonexistent")
        assert model_config is None

    def test_validate_model(self):
        """测试模型验证"""
        config = LLMConfig()

        # 测试模型验证（无API密钥时应该失败）
        assert config.validate_model("gpt-4") == False