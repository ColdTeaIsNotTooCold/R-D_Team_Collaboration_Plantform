"""
负载均衡器
"""
import asyncio
import random
import time
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging

from .base import BaseLLMProvider, get_llm_provider_factory
from ...models.llm import LLMProviderHealth, ProviderLoadBalancer, LoadBalancingStrategy, LoadBalancerConfig
from ...core.llm_config import get_llm_config

logger = logging.getLogger(__name__)


class LoadBalancer:
    """负载均衡器"""

    def __init__(self):
        self.config = get_llm_config()
        self.factory = get_llm_provider_factory()
        self.provider_configs: Dict[str, ProviderLoadBalancer] = {}
        self.health_cache: Dict[str, LLMProviderHealth] = {}
        self.request_history = defaultdict(lambda: deque(maxlen=1000))
        self.strategy = LoadBalancingStrategy(self.config.load_balancing_strategy)
        self._is_initialized = False

    async def initialize(self) -> bool:
        """初始化负载均衡器"""
        try:
            # 初始化提供商配置
            await self._initialize_provider_configs()

            # 启动健康检查任务
            asyncio.create_task(self._health_check_loop())

            self._is_initialized = True
            logger.info("负载均衡器初始化成功")
            return True

        except Exception as e:
            logger.error(f"负载均衡器初始化失败: {e}")
            return False

    async def select_provider(self, model: str, user_id: Optional[str] = None) -> BaseLLMProvider:
        """选择服务提供商"""
        if not self._is_initialized:
            raise Exception("负载均衡器未初始化")

        # 获取支持该模型的提供商
        available_providers = self._get_providers_for_model(model)
        if not available_providers:
            raise Exception(f"没有可用的提供商支持模型 '{model}'")

        # 根据策略选择提供商
        selected_provider = await self._select_by_strategy(available_providers, user_id)

        # 更新负载统计
        await self._update_load_stats(selected_provider)

        return selected_provider

    async def select_fallback_provider(self, model: str, exclude_providers: List[str] = None) -> Optional[BaseLLMProvider]:
        """选择备用提供商"""
        if not self._is_initialized:
            return None

        exclude_providers = exclude_providers or []
        available_providers = self._get_providers_for_model(model)

        # 过滤掉排除的提供商
        available_providers = [p for p in available_providers if p not in exclude_providers]

        if not available_providers:
            return None

        # 选择负载最低的提供商
        return min(available_providers, key=lambda p: self._get_provider_load(p))

    async def get_provider_health(self, provider_name: str) -> LLMProviderHealth:
        """获取提供商健康状态"""
        return self.health_cache.get(provider_name, LLMProviderHealth(
            provider=provider_name,
            status="unknown",
            health_status="unknown"
        ))

    async def get_load_balancing_stats(self) -> Dict[str, Any]:
        """获取负载均衡统计"""
        stats = {
            "strategy": self.strategy.value,
            "providers": {},
            "total_requests": sum(len(history) for history in self.request_history.values()),
            "health_cache": {k: v.dict() for k, v in self.health_cache.items()}
        }

        for provider_name, config in self.provider_configs.items():
            stats["providers"][provider_name] = {
                "load_percentage": config.get_load_percentage(),
                "success_rate": config.get_success_rate(),
                "average_response_time": config.average_response_time,
                "request_count": config.request_count,
                "error_count": config.error_count,
                "is_available": config.is_available
            }

        return stats

    async def _initialize_provider_configs(self) -> None:
        """初始化提供商配置"""
        for provider_name, provider_config in self.config.providers.items():
            if provider_config.enabled:
                self.provider_configs[provider_name] = ProviderLoadBalancer(
                    provider=provider_name,
                    weight=provider_config.priority,
                    max_load=1000  # 默认最大负载
                )

    def _get_providers_for_model(self, model: str) -> List[BaseLLMProvider]:
        """获取支持指定模型的提供商"""
        providers = []
        for provider_name, config in self.provider_configs.items():
            provider = self.factory.get_provider(provider_name)
            if provider and provider.is_initialized() and config.can_handle_request():
                # 检查是否支持该模型
                if model in provider.model_configs:
                    providers.append(provider)

        return providers

    async def _select_by_strategy(self, providers: List[BaseLLMProvider], user_id: Optional[str] = None) -> BaseLLMProvider:
        """根据策略选择提供商"""
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return await self._select_round_robin(providers)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return await self._select_weighted_round_robin(providers)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return await self._select_least_connections(providers)
        elif self.strategy == LoadBalancingStrategy.FASTEST_RESPONSE:
            return await self._select_fastest_response(providers)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return await self._select_random(providers)
        else:
            # 默认使用轮询
            return await self._select_round_robin(providers)

    async def _select_round_robin(self, providers: List[BaseLLMProvider]) -> BaseLLMProvider:
        """轮询选择"""
        if not hasattr(self, '_round_robin_index'):
            self._round_robin_index = 0

        provider = providers[self._round_robin_index % len(providers)]
        self._round_robin_index += 1

        return provider

    async def _select_weighted_round_robin(self, providers: List[BaseLLMProvider]) -> BaseLLMProvider:
        """加权轮询选择"""
        weights = []
        for provider in providers:
            config = self.provider_configs.get(provider.provider_config.name)
            if config:
                weights.append(config.weight)
            else:
                weights.append(1)

        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(providers)

        # 加权随机选择
        rand_val = random.randint(1, total_weight)
        current_weight = 0

        for provider, weight in zip(providers, weights):
            current_weight += weight
            if rand_val <= current_weight:
                return provider

        return providers[-1]

    async def _select_least_connections(self, providers: List[BaseLLMProvider]) -> BaseLLMProvider:
        """最少连接数选择"""
        return min(providers, key=lambda p: self._get_provider_load(p))

    async def _select_fastest_response(self, providers: List[BaseLLMProvider]) -> BaseLLMProvider:
        """最快响应时间选择"""
        def get_response_time(provider):
            health = self.health_cache.get(provider.provider_config.name)
            return health.response_time if health else float('inf')

        return min(providers, key=get_response_time)

    async def _select_random(self, providers: List[BaseLLMProvider]) -> BaseLLMProvider:
        """随机选择"""
        return random.choice(providers)

    def _get_provider_load(self, provider: BaseLLMProvider) -> int:
        """获取提供商负载"""
        config = self.provider_configs.get(provider.provider_config.name)
        return config.current_load if config else 0

    async def _update_load_stats(self, provider: BaseLLMProvider) -> None:
        """更新负载统计"""
        config = self.provider_configs.get(provider.provider_config.name)
        if config:
            config.current_load += 1
            config.last_used = datetime.now()

    async def record_request_result(self, provider_name: str, success: bool, response_time: float) -> None:
        """记录请求结果"""
        config = self.provider_configs.get(provider_name)
        if config:
            config.record_request(success, response_time)

            # 减少负载
            config.current_load = max(0, config.current_load - 1)

    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self._is_initialized:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
            except Exception as e:
                logger.error(f"健康检查失败: {e}")
                await asyncio.sleep(5)

    async def _perform_health_checks(self) -> None:
        """执行健康检查"""
        for provider_name, provider in self.factory._providers.items():
            if provider.is_initialized():
                try:
                    start_time = time.time()
                    is_healthy = await provider.health_check()
                    response_time = time.time() - start_time

                    # 更新健康缓存
                    health = self.health_cache.get(provider_name, LLMProviderHealth(provider=provider_name))
                    health.update_health(response_time, is_healthy)
                    self.health_cache[provider_name] = health

                    # 更新提供商可用性
                    config = self.provider_configs.get(provider_name)
                    if config:
                        config.is_available = is_healthy

                except Exception as e:
                    logger.error(f"提供商 '{provider_name}' 健康检查失败: {e}")
                    health = self.health_cache.get(provider_name, LLMProviderHealth(provider=provider_name))
                    health.update_health(0, False, [str(e)])
                    self.health_cache[provider_name] = health

    async def update_strategy(self, strategy: LoadBalancingStrategy) -> None:
        """更新负载均衡策略"""
        self.strategy = strategy
        logger.info(f"负载均衡策略已更新为: {strategy.value}")

    async def add_provider_config(self, config: ProviderLoadBalancer) -> None:
        """添加提供商配置"""
        self.provider_configs[config.provider] = config
        logger.info(f"添加提供商配置: {config.provider}")

    async def remove_provider_config(self, provider_name: str) -> None:
        """移除提供商配置"""
        if provider_name in self.provider_configs:
            del self.provider_configs[provider_name]
            logger.info(f"移除提供商配置: {provider_name}")

    async def get_provider_config(self, provider_name: str) -> Optional[ProviderLoadBalancer]:
        """获取提供商配置"""
        return self.provider_configs.get(provider_name)


# 全局负载均衡器实例
load_balancer = LoadBalancer()


async def get_load_balancer() -> LoadBalancer:
    """获取负载均衡器实例"""
    if not load_balancer._is_initialized:
        await load_balancer.initialize()
    return load_balancer