"""
LLM服务基础抽象类和工厂
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
import logging

from ...models.llm import LLMRequest, LLMResponse, LLMStreamResponse, LLMError
from ...core.llm_config import get_llm_config, LLMProvider, LLMModelConfig
from .exceptions import LLMException, RateLimitException, AuthenticationException, ServiceUnavailableException

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """LLM服务提供商基础抽象类"""

    def __init__(self, provider_config: LLMProvider, model_configs: Dict[str, LLMModelConfig]):
        self.provider_config = provider_config
        self.model_configs = model_configs
        self.logger = logging.getLogger(f"{__name__}.{provider_config.name}")
        self._is_initialized = False

    @abstractmethod
    async def initialize(self) -> bool:
        """初始化服务提供商"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass

    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """生成响应"""
        pass

    @abstractmethod
    async def generate_stream_response(self, request: LLMRequest) -> AsyncGenerator[LLMStreamResponse, None]:
        """生成流式响应"""
        pass

    @abstractmethod
    async def count_tokens(self, text: str, model: str) -> int:
        """计算令牌数"""
        pass

    @abstractmethod
    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """获取可用模型列表"""
        pass

    @abstractmethod
    async def estimate_cost(self, request: LLMRequest) -> float:
        """估算成本"""
        pass

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._is_initialized

    def validate_request(self, request: LLMRequest) -> bool:
        """验证请求"""
        if request.model not in self.model_configs:
            raise LLMException(
                f"模型 '{request.model}' 在提供商 '{self.provider_config.name}' 中不可用",
                "MODEL_NOT_FOUND",
                self.provider_config.name,
                request.model
            )

        model_config = self.model_configs[request.model]
        if not model_config.enabled:
            raise LLMException(
                f"模型 '{request.model}' 已禁用",
                "MODEL_NOT_AVAILABLE",
                self.provider_config.name,
                request.model
            )

        return True

    def get_model_config(self, model: str) -> Optional[LLMModelConfig]:
        """获取模型配置"""
        return self.model_configs.get(model)

    def create_error_response(self, request: LLMRequest, error: Exception) -> LLMError:
        """创建错误响应"""
        error_code = "UNKNOWN_ERROR"
        if isinstance(error, RateLimitException):
            error_code = "RATE_LIMIT"
        elif isinstance(error, AuthenticationException):
            error_code = "AUTHENTICATION_ERROR"
        elif isinstance(error, ServiceUnavailableException):
            error_code = "SERVICE_UNAVAILABLE"

        return LLMError(
            code=error_code,
            message=str(error),
            provider=self.provider_config.name,
            model=request.model,
            details={"exception_type": type(error).__name__}
        )

    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """计算成本"""
        model_config = self.get_model_config(model)
        if not model_config:
            return 0.0

        return (input_tokens * model_config.cost_per_1k_input / 1000 +
                output_tokens * model_config.cost_per_1k_output / 1000)

    async def validate_rate_limits(self, request: LLMRequest) -> bool:
        """验证速率限制"""
        model_config = self.get_model_config(request.model)
        if not model_config:
            return False

        # 这里可以实现更复杂的速率限制逻辑
        # 目前只检查基本配置
        return True


class LLMProviderFactory:
    """LLM服务提供商工厂"""

    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._provider_configs: Dict[str, LLMProvider] = {}
        self._model_configs: Dict[str, LLMModelConfig] = {}
        self.logger = logging.getLogger(__name__)

    def register_provider(self, provider: BaseLLMProvider):
        """注册服务提供商"""
        self._providers[provider.provider_config.name] = provider
        self._provider_configs[provider.provider_config.name] = provider.provider_config
        self._model_configs.update(provider.model_configs)
        self.logger.info(f"注册服务提供商: {provider.provider_config.name}")

    def get_provider(self, provider_name: str) -> Optional[BaseLLMProvider]:
        """获取服务提供商"""
        return self._providers.get(provider_name)

    def get_available_providers(self) -> List[str]:
        """获取可用的服务提供商列表"""
        return [name for name, provider in self._providers.items() if provider.is_initialized()]

    def get_provider_for_model(self, model: str) -> Optional[BaseLLMProvider]:
        """根据模型获取服务提供商"""
        for provider in self._providers.values():
            if model in provider.model_configs:
                return provider
        return None

    async def initialize_all_providers(self) -> Dict[str, bool]:
        """初始化所有服务提供商"""
        results = {}
        for name, provider in self._providers.items():
            try:
                result = await provider.initialize()
                results[name] = result
                if result:
                    self.logger.info(f"服务提供商 '{name}' 初始化成功")
                else:
                    self.logger.error(f"服务提供商 '{name}' 初始化失败")
            except Exception as e:
                self.logger.error(f"服务提供商 '{name}' 初始化异常: {e}")
                results[name] = False
        return results

    async def health_check_all_providers(self) -> Dict[str, bool]:
        """检查所有服务提供商的健康状态"""
        results = {}
        for name, provider in self._providers.items():
            if provider.is_initialized():
                try:
                    result = await provider.health_check()
                    results[name] = result
                    if not result:
                        self.logger.warning(f"服务提供商 '{name}' 健康检查失败")
                except Exception as e:
                    self.logger.error(f"服务提供商 '{name}' 健康检查异常: {e}")
                    results[name] = False
            else:
                results[name] = False
        return results

    def get_model_configs(self) -> Dict[str, LLMModelConfig]:
        """获取所有模型配置"""
        return self._model_configs.copy()

    def get_provider_configs(self) -> Dict[str, LLMProvider]:
        """获取所有服务提供商配置"""
        return self._provider_configs.copy()

    def list_available_models(self) -> List[str]:
        """列出所有可用模型"""
        models = []
        for provider in self._providers.values():
            if provider.is_initialized():
                models.extend(provider.model_configs.keys())
        return models

    def validate_model(self, model: str) -> bool:
        """验证模型是否可用"""
        provider = self.get_provider_for_model(model)
        if not provider or not provider.is_initialized():
            return False

        model_config = provider.get_model_config(model)
        return model_config and model_config.enabled


# 全局工厂实例
llm_provider_factory = LLMProviderFactory()


def get_llm_provider_factory() -> LLMProviderFactory:
    """获取LLM服务提供商工厂实例"""
    return llm_provider_factory


def register_llm_provider(provider: BaseLLMProvider):
    """注册LLM服务提供商"""
    llm_provider_factory.register_provider(provider)