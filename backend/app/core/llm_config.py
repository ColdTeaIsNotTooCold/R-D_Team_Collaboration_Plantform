"""
LLM配置模块
管理AI服务提供商的配置信息
"""
import logging
from typing import Dict, List, Optional
from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class LLMProvider(BaseModel):
    """LLM服务提供商配置"""
    name: str
    base_url: str
    api_key: Optional[str] = None
    enabled: bool = True
    models: List[str] = []
    priority: int = 0

    class Config:
        extra = "allow"


class LLMModelConfig(BaseModel):
    """LLM模型配置"""
    name: str
    provider: str
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 60000
    enabled: bool = True

    class Config:
        extra = "allow"


class CostControl(BaseModel):
    """成本控制配置"""
    monthly_limit: float = 1000.0
    daily_limit: float = 100.0
    alert_threshold: float = 0.8
    enable_monitoring: bool = True

    class Config:
        extra = "allow"


class LLMConfig(BaseSettings):
    """LLM配置类"""

    # OpenAI配置
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")
    openai_enabled: bool = Field(default=True, env="OPENAI_ENABLED")

    # Claude配置
    claude_api_key: Optional[str] = Field(default=None, env="CLAUDE_API_KEY")
    claude_base_url: str = Field(default="https://api.anthropic.com", env="CLAUDE_BASE_URL")
    claude_enabled: bool = Field(default=True, env="CLAUDE_ENABLED")

    # 模型配置
    default_model: str = Field(default="gpt-3.5-turbo", env="DEFAULT_MODEL")
    fallback_model: str = Field(default="claude-3-haiku-20240307", env="FALLBACK_MODEL")

    # 请求配置
    request_timeout: int = Field(default=30, env="LLM_REQUEST_TIMEOUT")
    max_retries: int = Field(default=3, env="LLM_MAX_RETRIES")
    retry_delay: float = Field(default=1.0, env="LLM_RETRY_DELAY")

    # 成本控制
    cost_monthly_limit: float = Field(default=1000.0, env="COST_MONTHLY_LIMIT")
    cost_daily_limit: float = Field(default=100.0, env="COST_DAILY_LIMIT")
    cost_alert_threshold: float = Field(default=0.8, env="COST_ALERT_THRESHOLD")

    # 负载均衡
    load_balancing_strategy: str = Field(default="round_robin", env="LOAD_BALANCING_STRATEGY")
    health_check_interval: int = Field(default=60, env="HEALTH_CHECK_INTERVAL")

    # 缓存配置
    enable_response_cache: bool = Field(default=True, env="ENABLE_RESPONSE_CACHE")
    cache_ttl: int = Field(default=3600, env="LLM_CACHE_TTL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"

    @property
    def providers(self) -> Dict[str, LLMProvider]:
        """获取所有服务提供商"""
        providers = {}

        if self.openai_enabled and self.openai_api_key:
            providers["openai"] = LLMProvider(
                name="openai",
                base_url=self.openai_base_url,
                api_key=self.openai_api_key,
                enabled=True,
                models=[
                    "gpt-4",
                    "gpt-4-turbo",
                    "gpt-3.5-turbo",
                    "gpt-3.5-turbo-16k"
                ],
                priority=1
            )

        if self.claude_enabled and self.claude_api_key:
            providers["claude"] = LLMProvider(
                name="claude",
                base_url=self.claude_base_url,
                api_key=self.claude_api_key,
                enabled=True,
                models=[
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307"
                ],
                priority=2
            )

        return providers

    @property
    def model_configs(self) -> Dict[str, LLMModelConfig]:
        """获取模型配置"""
        configs = {
            "gpt-4": LLMModelConfig(
                name="gpt-4",
                provider="openai",
                max_tokens=8192,
                cost_per_1k_input=0.03,
                cost_per_1k_output=0.06,
                rate_limit_rpm=200,
                rate_limit_tpm=80000
            ),
            "gpt-4-turbo": LLMModelConfig(
                name="gpt-4-turbo",
                provider="openai",
                max_tokens=128000,
                cost_per_1k_input=0.01,
                cost_per_1k_output=0.03,
                rate_limit_rpm=500,
                rate_limit_tpm=400000
            ),
            "gpt-3.5-turbo": LLMModelConfig(
                name="gpt-3.5-turbo",
                provider="openai",
                max_tokens=4096,
                cost_per_1k_input=0.0015,
                cost_per_1k_output=0.002,
                rate_limit_rpm=3500,
                rate_limit_tpm=200000
            ),
            "claude-3-opus-20240229": LLMModelConfig(
                name="claude-3-opus-20240229",
                provider="claude",
                max_tokens=200000,
                cost_per_1k_input=0.015,
                cost_per_1k_output=0.075,
                rate_limit_rpm=1000,
                rate_limit_tpm=80000
            ),
            "claude-3-sonnet-20240229": LLMModelConfig(
                name="claude-3-sonnet-20240229",
                provider="claude",
                max_tokens=200000,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                rate_limit_rpm=5000,
                rate_limit_tpm=320000
            ),
            "claude-3-haiku-20240307": LLMModelConfig(
                name="claude-3-haiku-20240307",
                provider="claude",
                max_tokens=200000,
                cost_per_1k_input=0.00025,
                cost_per_1k_output=0.00125,
                rate_limit_rpm=10000,
                rate_limit_tpm=400000
            )
        }

        # 只返回启用且配置了API密钥的模型
        enabled_configs = {}
        for model_name, config in configs.items():
            provider = self.providers.get(config.provider)
            if provider and provider.enabled and provider.api_key:
                enabled_configs[model_name] = config

        return enabled_configs

    @property
    def cost_control(self) -> CostControl:
        """获取成本控制配置"""
        return CostControl(
            monthly_limit=self.cost_monthly_limit,
            daily_limit=self.cost_daily_limit,
            alert_threshold=self.cost_alert_threshold,
            enable_monitoring=True
        )

    def get_provider_config(self, provider_name: str) -> Optional[LLMProvider]:
        """获取指定服务提供商的配置"""
        return self.providers.get(provider_name)

    def get_model_config(self, model_name: str) -> Optional[LLMModelConfig]:
        """获取指定模型的配置"""
        return self.model_configs.get(model_name)

    def get_enabled_providers(self) -> List[LLMProvider]:
        """获取启用的服务提供商列表"""
        return [p for p in self.providers.values() if p.enabled]

    def get_enabled_models(self) -> List[LLMModelConfig]:
        """获取启用的模型列表"""
        return [m for m in self.model_configs.values() if m.enabled]

    def validate_model(self, model_name: str) -> bool:
        """验证模型是否可用"""
        model_config = self.get_model_config(model_name)
        if not model_config:
            return False

        provider_config = self.get_provider_config(model_config.provider)
        if not provider_config or not provider_config.enabled:
            return False

        return True


# 全局配置实例
llm_config = LLMConfig()


def get_llm_config() -> LLMConfig:
    """获取LLM配置实例"""
    return llm_config


def get_provider_config(provider_name: str) -> Optional[LLMProvider]:
    """获取指定服务提供商的配置"""
    return llm_config.get_provider_config(provider_name)


def get_model_config(model_name: str) -> Optional[LLMModelConfig]:
    """获取指定模型的配置"""
    return llm_config.get_model_config(model_name)


def get_enabled_providers() -> List[LLMProvider]:
    """获取启用的服务提供商列表"""
    return llm_config.get_enabled_providers()


def get_enabled_models() -> List[LLMModelConfig]:
    """获取启用的模型列表"""
    return llm_config.get_enabled_models()


def validate_model(model_name: str) -> bool:
    """验证模型是否可用"""
    return llm_config.validate_model(model_name)