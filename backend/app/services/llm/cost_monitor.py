"""
成本监控系统
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from collections import defaultdict
import logging

from ...models.llm import LLMUsage, CostTracking, UsageStatistics, CostAlert, CostLimit
from ...core.llm_config import get_llm_config, CostControl
from ...core.redis import get_redis_client
from .exceptions import CostLimitExceededException


logger = logging.getLogger(__name__)


class CostMonitor:
    """成本监控器"""

    def __init__(self):
        self.redis_client = None
        self.config = get_llm_config()
        self.cost_control = self.config.cost_control
        self.usage_cache = defaultdict(lambda: defaultdict(float))
        self.cost_limits = {}
        self.alerts = []
        self._is_initialized = False

    async def initialize(self) -> bool:
        """初始化成本监控器"""
        try:
            self.redis_client = await get_redis_client()
            await self._load_cost_limits()
            self._is_initialized = True
            logger.info("成本监控器初始化成功")
            return True
        except Exception as e:
            logger.error(f"成本监控器初始化失败: {e}")
            return False

    async def record_usage(self, usage: LLMUsage) -> None:
        """记录使用情况"""
        if not self._is_initialized:
            return

        try:
            # 记录到Redis
            await self._record_usage_to_redis(usage)

            # 检查成本限制
            await self._check_cost_limits(usage)

            # 更新缓存
            self._update_usage_cache(usage)

        except Exception as e:
            logger.error(f"记录使用情况失败: {e}")

    async def get_usage_statistics(self, user_id: Optional[str] = None,
                                 period: str = "daily",
                                 start_date: Optional[date] = None,
                                 end_date: Optional[date] = None) -> UsageStatistics:
        """获取使用统计"""
        if not self._is_initialized:
            return UsageStatistics(period=period, start_date=date.today(), end_date=date.today())

        try:
            # 从Redis获取数据
            usage_data = await self._get_usage_from_redis(user_id, period, start_date, end_date)

            # 计算统计信息
            stats = self._calculate_statistics(usage_data, period, start_date or date.today(), end_date or date.today())

            return stats

        except Exception as e:
            logger.error(f"获取使用统计失败: {e}")
            return UsageStatistics(period=period, start_date=date.today(), end_date=date.today())

    async def get_cost_breakdown(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取成本分解"""
        if not self._is_initialized:
            return {}

        try:
            breakdown = {
                "models": {},
                "providers": {},
                "periods": {
                    "daily": await self._get_period_usage(user_id, "daily"),
                    "weekly": await self._get_period_usage(user_id, "weekly"),
                    "monthly": await self._get_period_usage(user_id, "monthly")
                }
            }

            return breakdown

        except Exception as e:
            logger.error(f"获取成本分解失败: {e}")
            return {}

    async def create_cost_limit(self, user_id: Optional[str], model: Optional[str],
                             provider: Optional[str], period: str,
                             limit_type: str, limit_value: float,
                             action: str = "alert") -> CostLimit:
        """创建成本限制"""
        limit = CostLimit(
            id=f"limit_{int(time.time() * 1000)}",
            user_id=user_id,
            model=model,
            provider=provider,
            period=period,
            limit_type=limit_type,
            limit_value=limit_value,
            action=action
        )

        self.cost_limits[limit.id] = limit
        await self._save_cost_limit(limit)

        return limit

    async def get_active_alerts(self, user_id: Optional[str] = None) -> List[CostAlert]:
        """获取活动告警"""
        active_alerts = [alert for alert in self.alerts
                        if not alert.is_resolved and
                        (user_id is None or alert.user_id == user_id)]
        return active_alerts

    async def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.is_resolved = True
                alert.resolved_at = datetime.now()
                return True
        return False

    async def _record_usage_to_redis(self, usage: LLMUsage) -> None:
        """记录使用情况到Redis"""
        if not self.redis_client:
            return

        try:
            # 记录每日使用
            date_key = usage.timestamp.date().isoformat()
            daily_key = f"usage:daily:{usage.user_id or 'global'}:{date_key}"

            # 记录模型使用
            model_key = f"usage:model:{usage.model}:{date_key}"

            # 记录提供商使用
            provider_key = f"usage:provider:{usage.provider}:{date_key}"

            # 使用Redis管道批量操作
            async with self.redis_client.pipeline() as pipe:
                pipe.hincrby(daily_key, "total_tokens", usage.total_tokens)
                pipe.hincrby(daily_key, "total_cost", int(usage.cost * 100))  # 存储为分
                pipe.hincrby(daily_key, "total_requests", 1)
                pipe.hincrby(daily_key, "total_latency", int(usage.latency * 1000))  # 存储为毫秒

                pipe.hincrby(model_key, "total_tokens", usage.total_tokens)
                pipe.hincrby(model_key, "total_cost", int(usage.cost * 100))
                pipe.hincrby(model_key, "total_requests", 1)

                pipe.hincrby(provider_key, "total_tokens", usage.total_tokens)
                pipe.hincrby(provider_key, "total_cost", int(usage.cost * 100))
                pipe.hincrby(provider_key, "total_requests", 1)

                await pipe.execute()

            # 设置过期时间（30天）
            await self.redis_client.expire(daily_key, 30 * 24 * 3600)
            await self.redis_client.expire(model_key, 30 * 24 * 3600)
            await self.redis_client.expire(provider_key, 30 * 24 * 3600)

        except Exception as e:
            logger.error(f"记录使用情况到Redis失败: {e}")

    async def _check_cost_limits(self, usage: LLMUsage) -> None:
        """检查成本限制"""
        for limit in self.cost_limits.values():
            if not limit.is_active:
                continue

            # 检查用户和模型匹配
            if limit.user_id and limit.user_id != usage.user_id:
                continue
            if limit.model and limit.model != usage.model:
                continue
            if limit.provider and limit.provider != usage.provider:
                continue

            # 获取当前使用情况
            current_usage = await self._get_period_usage(
                usage.user_id,
                limit.period,
                usage.model,
                usage.provider
            )

            # 检查是否超过限制
            if current_usage >= limit.limit_value:
                await self._handle_cost_limit_exceeded(limit, current_usage)

    async def _handle_cost_limit_exceeded(self, limit: CostLimit, current_value: float) -> None:
        """处理成本限制超限"""
        # 创建告警
        alert = CostAlert(
            id=f"alert_{int(time.time() * 1000)}",
            user_id=limit.user_id,
            alert_type="cost_limit_exceeded",
            threshold=limit.limit_value,
            current_value=current_value,
            message=f"成本限制超限: {current_value:.2f} > {limit.limit_value:.2f}",
            severity="critical"
        )

        self.alerts.append(alert)

        # 根据动作处理
        if limit.action == "alert":
            logger.warning(f"成本限制告警: {alert.message}")
        elif limit.action == "block":
            raise CostLimitExceededException(
                f"成本限制超限: {current_value:.2f} > {limit.limit_value:.2f}",
                limit.provider,
                limit.model,
                current_value,
                limit.limit_value
            )

    async def _get_usage_from_redis(self, user_id: Optional[str], period: str,
                                  start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """从Redis获取使用数据"""
        if not self.redis_client:
            return []

        usage_data = []
        current_date = start_date

        while current_date <= end_date:
            date_key = current_date.isoformat()
            daily_key = f"usage:daily:{user_id or 'global'}:{date_key}"

            try:
                data = await self.redis_client.hgetall(daily_key)
                if data:
                    usage_data.append({
                        "date": date_key,
                        "total_tokens": int(data.get("total_tokens", 0)),
                        "total_cost": int(data.get("total_cost", 0)) / 100,  # 转换为元
                        "total_requests": int(data.get("total_requests", 0)),
                        "total_latency": int(data.get("total_latency", 0)) / 1000  # 转换为秒
                    })
            except Exception as e:
                logger.error(f"获取Redis数据失败: {e}")

            current_date += timedelta(days=1)

        return usage_data

    def _calculate_statistics(self, usage_data: List[Dict[str, Any]], period: str,
                            start_date: date, end_date: date) -> UsageStatistics:
        """计算统计信息"""
        total_tokens = sum(item["total_tokens"] for item in usage_data)
        total_cost = sum(item["total_cost"] for item in usage_data)
        total_requests = sum(item["total_requests"] for item in usage_data)

        avg_latency = 0
        if total_requests > 0:
            total_latency = sum(item["total_latency"] for item in usage_data)
            avg_latency = total_latency / total_requests

        avg_tokens_per_request = total_tokens / total_requests if total_requests > 0 else 0
        avg_cost_per_request = total_cost / total_requests if total_requests > 0 else 0

        return UsageStatistics(
            period=period,
            start_date=start_date,
            end_date=end_date,
            total_requests=total_requests,
            total_tokens=total_tokens,
            total_cost=total_cost,
            average_tokens_per_request=avg_tokens_per_request,
            average_cost_per_request=avg_cost_per_request,
            average_latency=avg_latency
        )

    async def _get_period_usage(self, user_id: Optional[str], period: str,
                               model: Optional[str] = None,
                               provider: Optional[str] = None) -> float:
        """获取周期内使用情况"""
        if not self.redis_client:
            return 0.0

        try:
            end_date = date.today()
            if period == "daily":
                start_date = end_date
            elif period == "weekly":
                start_date = end_date - timedelta(days=7)
            elif period == "monthly":
                start_date = end_date - timedelta(days=30)
            else:
                return 0.0

            total_cost = 0.0
            current_date = start_date

            while current_date <= end_date:
                date_key = current_date.isoformat()
                if user_id:
                    daily_key = f"usage:daily:{user_id}:{date_key}"
                else:
                    daily_key = f"usage:daily:global:{date_key}"

                cost_data = await self.redis_client.hget(daily_key, "total_cost")
                if cost_data:
                    total_cost += int(cost_data) / 100

                current_date += timedelta(days=1)

            return total_cost

        except Exception as e:
            logger.error(f"获取周期使用情况失败: {e}")
            return 0.0

    def _update_usage_cache(self, usage: LLMUsage) -> None:
        """更新使用情况缓存"""
        date_key = usage.timestamp.date().isoformat()
        self.usage_cache[date_key][usage.user_id or "global"] += usage.cost

    async def _load_cost_limits(self) -> None:
        """加载成本限制"""
        if not self.redis_client:
            return

        try:
            limits_data = await self.redis_client.get("cost_limits")
            if limits_data:
                limits_dict = json.loads(limits_data)
                for limit_data in limits_dict.values():
                    limit = CostLimit(**limit_data)
                    self.cost_limits[limit.id] = limit
        except Exception as e:
            logger.error(f"加载成本限制失败: {e}")

    async def _save_cost_limit(self, limit: CostLimit) -> None:
        """保存成本限制"""
        if not self.redis_client:
            return

        try:
            limits_data = await self.redis_client.get("cost_limits")
            if limits_data:
                limits_dict = json.loads(limits_data)
            else:
                limits_dict = {}

            limits_dict[limit.id] = limit.dict()

            await self.redis_client.set("cost_limits", json.dumps(limits_dict), ex=30 * 24 * 3600)
        except Exception as e:
            logger.error(f"保存成本限制失败: {e}")


# 全局成本监控器实例
cost_monitor = CostMonitor()


async def get_cost_monitor() -> CostMonitor:
    """获取成本监控器实例"""
    if not cost_monitor._is_initialized:
        await cost_monitor.initialize()
    return cost_monitor