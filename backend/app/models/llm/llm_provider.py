"""
LLM服务提供商状态和健康检查模型
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ProviderStatus(str, Enum):
    """服务提供商状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class HealthStatus(str, Enum):
    """健康状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class LLMProviderStats(BaseModel):
    """LLM服务提供商统计模型"""
    provider: str = Field(..., description="服务提供商名称")
    total_requests: int = Field(default=0, description="总请求数")
    successful_requests: int = Field(default=0, description="成功请求数")
    failed_requests: int = Field(default=0, description="失败请求数")
    total_tokens: int = Field(default=0, description="总令牌数")
    total_cost: float = Field(default=0.0, description="总成本")
    average_latency: float = Field(default=0.0, description="平均延迟")
    success_rate: float = Field(default=1.0, description="成功率")
    uptime_percentage: float = Field(default=100.0, description="正常运行时间百分比")
    last_request_time: Optional[datetime] = Field(None, description="最后请求时间")
    last_error_time: Optional[datetime] = Field(None, description="最后错误时间")
    last_error_message: Optional[str] = Field(None, description="最后错误消息")
    model_stats: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="模型统计")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def update_request_stats(self, success: bool, tokens: int, cost: float, latency: float) -> None:
        """更新请求统计"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        self.total_tokens += tokens
        self.total_cost += cost

        # 更新平均延迟
        if self.total_requests == 1:
            self.average_latency = latency
        else:
            self.average_latency = (self.average_latency * (self.total_requests - 1) + latency) / self.total_requests

        # 更新成功率
        self.success_rate = self.successful_requests / self.total_requests if self.total_requests > 0 else 1.0

        # 更新时间戳
        current_time = datetime.now()
        self.updated_at = current_time
        if success:
            self.last_request_time = current_time
        else:
            self.last_error_time = current_time


class LLMProviderHealth(BaseModel):
    """LLM服务提供商健康检查模型"""
    provider: str = Field(..., description="服务提供商名称")
    status: ProviderStatus = Field(default=ProviderStatus.UNKNOWN, description="服务状态")
    health_status: HealthStatus = Field(default=HealthStatus.UNKNOWN, description="健康状态")
    response_time: float = Field(default=0.0, description="响应时间（秒）")
    error_rate: float = Field(default=0.0, description="错误率")
    last_check_time: datetime = Field(default_factory=datetime.now, description="最后检查时间")
    is_healthy: bool = Field(default=False, description="是否健康")
    health_score: float = Field(default=0.0, description="健康评分（0-100）")
    issues: List[str] = Field(default_factory=list, description="问题列表")
    recommendations: List[str] = Field(default_factory=list, description="建议列表")
    metadata: Optional[Dict[str, Any]] = Field(None, description="健康检查元数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def update_health(self, response_time: float, is_healthy: bool, issues: List[str] = None) -> None:
        """更新健康状态"""
        self.response_time = response_time
        self.is_healthy = is_healthy
        self.last_check_time = datetime.now()

        if issues:
            self.issues = issues

        # 计算健康评分
        if is_healthy:
            self.health_score = max(0, 100 - response_time * 10)  # 响应时间越低，评分越高
            self.health_status = HealthStatus.HEALTHY if self.health_score >= 80 else HealthStatus.WARNING
            self.status = ProviderStatus.ONLINE
        else:
            self.health_score = 0
            self.health_status = HealthStatus.CRITICAL
            self.status = ProviderStatus.OFFLINE

        # 生成建议
        self.recommendations = self._generate_recommendations()

    def _generate_recommendations(self) -> List[str]:
        """生成建议"""
        recommendations = []

        if not self.is_healthy:
            recommendations.append("检查网络连接和API密钥")
            recommendations.append("确认服务提供商状态")
        elif self.response_time > 5:
            recommendations.append("响应时间较长，考虑切换到其他提供商")
        elif self.health_score < 80:
            recommendations.append("服务性能一般，监控服务状态")

        return recommendations


class ProviderLoadBalancer(BaseModel):
    """服务提供商负载均衡模型"""
    provider: str = Field(..., description="服务提供商名称")
    weight: int = Field(default=1, description="权重")
    current_load: int = Field(default=0, description="当前负载")
    max_load: int = Field(default=100, description="最大负载")
    is_available: bool = Field(default=True, description="是否可用")
    last_used: Optional[datetime] = Field(None, description="最后使用时间")
    request_count: int = Field(default=0, description="请求数量")
    error_count: int = Field(default=0, description="错误数量")
    average_response_time: float = Field(default=0.0, description="平均响应时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def get_load_percentage(self) -> float:
        """获取负载百分比"""
        return (self.current_load / self.max_load) * 100 if self.max_load > 0 else 0

    def get_success_rate(self) -> float:
        """获取成功率"""
        return (self.request_count - self.error_count) / self.request_count if self.request_count > 0 else 1.0

    def can_handle_request(self) -> bool:
        """判断是否可以处理请求"""
        return self.is_available and self.current_load < self.max_load

    def record_request(self, success: bool, response_time: float) -> None:
        """记录请求"""
        self.request_count += 1
        self.last_used = datetime.now()

        if not success:
            self.error_count += 1

        # 更新平均响应时间
        if self.request_count == 1:
            self.average_response_time = response_time
        else:
            self.average_response_time = (self.average_response_time * (self.request_count - 1) + response_time) / self.request_count


class LoadBalancingStrategy(str, Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    FASTEST_RESPONSE = "fastest_response"
    RANDOM = "random"


class LoadBalancerConfig(BaseModel):
    """负载均衡配置模型"""
    strategy: LoadBalancingStrategy = Field(default=LoadBalancingStrategy.ROUND_ROBIN, description="负载均衡策略")
    health_check_interval: int = Field(default=60, description="健康检查间隔（秒）")
    timeout_threshold: int = Field(default=30, description="超时阈值（秒）")
    max_retries: int = Field(default=3, description="最大重试次数")
    failover_enabled: bool = Field(default=True, description="是否启用故障转移")
    provider_configs: List[ProviderLoadBalancer] = Field(default_factory=list, description="提供商配置")
    metadata: Optional[Dict[str, Any]] = Field(None, description="负载均衡元数据")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }