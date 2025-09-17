"""
LLM管理器
提供统一的LLM服务接口
"""
import asyncio
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
import logging

from .base import BaseLLMProvider, get_llm_provider_factory
from ...models.llm import LLMRequest, LLMResponse, LLMStreamResponse, LLMConversation, LLMUsage
from ...core.llm_config import get_llm_config
from .exceptions import LLMException, ProviderUnavailableException
from .cost_monitor import get_cost_monitor
from .load_balancer import get_load_balancer

logger = logging.getLogger(__name__)


class LLMManager:
    """LLM管理器"""

    def __init__(self):
        self.config = get_llm_config()
        self.factory = get_llm_provider_factory()
        self.cost_monitor = None
        self.load_balancer = None
        self._is_initialized = False

    async def initialize(self) -> bool:
        """初始化LLM管理器"""
        try:
            # 初始化成本监控器
            self.cost_monitor = await get_cost_monitor()

            # 初始化负载均衡器
            self.load_balancer = await get_load_balancer()

            # 初始化服务提供商
            await self._initialize_providers()

            self._is_initialized = True
            logger.info("LLM管理器初始化成功")
            return True

        except Exception as e:
            logger.error(f"LLM管理器初始化失败: {e}")
            return False

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """生成响应"""
        if not self._is_initialized:
            raise LLMException("LLM管理器未初始化", "NOT_INITIALIZED")

        start_time = time.time()
        provider = None
        fallback_used = False

        try:
            # 选择提供商
            provider = await self.load_balancer.select_provider(request.model, request.user_id)

            # 生成响应
            response = await provider.generate_response(request)

            # 记录使用情况
            await self._record_usage(request, response, start_time, provider, False)

            # 记录请求结果
            await self.load_balancer.record_request_result(
                provider.provider_config.name, True, response.latency
            )

            return response

        except Exception as e:
            logger.error(f"生成响应失败: {e}")

            # 记录失败
            if provider:
                await self.load_balancer.record_request_result(
                    provider.provider_config.name, False, time.time() - start_time
                )

            # 尝试备用提供商
            if not fallback_used:
                try:
                    fallback_provider = await self.load_balancer.select_fallback_provider(
                        request.model, [provider.provider_config.name] if provider else None
                    )

                    if fallback_provider:
                        logger.info(f"使用备用提供商: {fallback_provider.provider_config.name}")
                        fallback_response = await fallback_provider.generate_response(request)

                        # 记录使用情况
                        await self._record_usage(request, fallback_response, start_time, fallback_provider, True)

                        # 记录请求结果
                        await self.load_balancer.record_request_result(
                            fallback_provider.provider_config.name, True, fallback_response.latency
                        )

                        return fallback_response

                except Exception as fallback_error:
                    logger.error(f"备用提供商也失败: {fallback_error}")

            raise e

    async def generate_stream_response(self, request: LLMRequest) -> AsyncGenerator[LLMStreamResponse, None]:
        """生成流式响应"""
        if not self._is_initialized:
            raise LLMException("LLM管理器未初始化", "NOT_INITIALIZED")

        provider = await self.load_balancer.select_provider(request.model, request.user_id)

        try:
            # 流式响应的负载记录比较复杂，这里简化处理
            async for chunk in provider.generate_stream_response(request):
                yield chunk

        except Exception as e:
            logger.error(f"生成流式响应失败: {e}")
            await self.load_balancer.record_request_result(
                provider.provider_config.name, False, 0
            )
            raise

    async def create_conversation(self, user_id: str, title: str, model: str,
                                system_prompt: Optional[str] = None) -> LLMConversation:
        """创建对话"""
        # 选择提供商
        provider = await self.load_balancer.select_provider(model, user_id)

        conversation = LLMConversation(
            id=f"conv_{int(time.time() * 1000)}",
            user_id=user_id,
            title=title,
            model=model,
            provider=provider.provider_config.name,
            system_prompt=system_prompt
        )

        return conversation

    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return self.factory.list_available_models()

    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        provider = self.factory.get_provider_for_model(model)
        if not provider:
            raise LLMException(f"没有提供商支持模型 '{model}'", "MODEL_NOT_SUPPORTED")

        return await provider.get_model_info(model)

    async def estimate_cost(self, request: LLMRequest) -> float:
        """估算成本"""
        provider = self.factory.get_provider_for_model(request.model)
        if not provider:
            return 0.0

        return await provider.estimate_cost(request)

    async def count_tokens(self, text: str, model: str) -> int:
        """计算令牌数"""
        provider = self.factory.get_provider_for_model(model)
        if not provider:
            return len(text.split())  # 简单估算

        return await provider.count_tokens(text, model)

    async def get_usage_statistics(self, user_id: Optional[str] = None,
                                 period: str = "daily") -> Dict[str, Any]:
        """获取使用统计"""
        if not self.cost_monitor:
            return {}

        stats = await self.cost_monitor.get_usage_statistics(user_id, period)
        return stats.dict()

    async def get_cost_breakdown(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取成本分解"""
        if not self.cost_monitor:
            return {}

        return await self.cost_monitor.get_cost_breakdown(user_id)

    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "initialized": self._is_initialized,
            "providers": {},
            "load_balancer": {},
            "cost_monitor": {}
        }

        # 提供商状态
        for provider_name, provider in self.factory._providers.items():
            health = await self.load_balancer.get_provider_health(provider_name)
            status["providers"][provider_name] = {
                "initialized": provider.is_initialized(),
                "healthy": health.is_healthy,
                "health_score": health.health_score,
                "models": list(provider.model_configs.keys())
            }

        # 负载均衡器状态
        if self.load_balancer:
            status["load_balancer"] = await self.load_balancer.get_load_balancing_stats()

        # 成本监控状态
        if self.cost_monitor:
            alerts = await self.cost_monitor.get_active_alerts()
            status["cost_monitor"] = {
                "active_alerts": len(alerts),
                "alerts": [alert.dict() for alert in alerts]
            }

        return status

    async def health_check(self) -> bool:
        """系统健康检查"""
        if not self._is_initialized:
            return False

        # 检查所有提供商
        health_results = await self.factory.health_check_all_providers()
        healthy_providers = sum(health_results.values())

        # 至少有一个健康的提供商
        return healthy_providers > 0

    async def _initialize_providers(self) -> None:
        """初始化服务提供商"""
        # 导入提供商
        from .openai_provider import OpenAIProvider
        from .claude_provider import ClaudeProvider

        # 注册OpenAI提供商
        if self.config.openai_enabled and self.config.openai_api_key:
            openai_config = self.config.get_provider_config("openai")
            if openai_config:
                openai_provider = OpenAIProvider(
                    openai_config,
                    self.config.model_configs
                )
                self.factory.register_provider(openai_provider)

        # 注册Claude提供商
        if self.config.claude_enabled and self.config.claude_api_key:
            claude_config = self.config.get_provider_config("claude")
            if claude_config:
                claude_provider = ClaudeProvider(
                    claude_config,
                    self.config.model_configs
                )
                self.factory.register_provider(claude_provider)

        # 初始化所有提供商
        await self.factory.initialize_all_providers()

    async def _record_usage(self, request: LLMRequest, response: LLMResponse,
                           start_time: float, provider: BaseLLMProvider,
                           is_fallback: bool) -> None:
        """记录使用情况"""
        if not self.cost_monitor:
            return

        usage = LLMUsage(
            id=f"usage_{int(time.time() * 1000)}",
            user_id=request.user_id,
            model=request.model,
            provider=provider.provider_config.name,
            request_id=response.request_id,
            input_tokens=response.tokens.get("input", 0),
            output_tokens=response.tokens.get("output", 0),
            total_tokens=response.tokens.get("total", 0),
            cost=response.cost,
            latency=response.latency,
            status="success" if response.finish_reason == "stop" else "partial",
            metadata={
                "is_fallback": is_fallback,
                "finish_reason": response.finish_reason
            }
        )

        await self.cost_monitor.record_usage(usage)

    async def close(self):
        """关闭管理器"""
        if self._is_initialized:
            # 关闭所有提供商
            for provider in self.factory._providers.values():
                if hasattr(provider, 'close'):
                    await provider.close()

            self._is_initialized = False
            logger.info("LLM管理器已关闭")


# 全局LLM管理器实例
llm_manager = LLMManager()


async def get_llm_manager() -> LLMManager:
    """获取LLM管理器实例"""
    if not llm_manager._is_initialized:
        await llm_manager.initialize()
    return llm_manager