"""
LLM服务异常类
"""
from typing import Optional, Dict, Any
from datetime import datetime


class LLMException(Exception):
    """LLM服务基础异常"""

    def __init__(self, message: str, code: str = "LLM_ERROR",
                 provider: Optional[str] = None, model: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.provider = provider
        self.model = model
        self.details = details or {}
        self.timestamp = datetime.now()
        super().__init__(self.message)


class RateLimitException(LLMException):
    """速率限制异常"""

    def __init__(self, message: str, provider: Optional[str] = None,
                 model: Optional[str] = None, retry_after: Optional[int] = None,
                 requests_remaining: Optional[int] = None):
        super().__init__(message, "RATE_LIMIT", provider, model, {
            "retry_after": retry_after,
            "requests_remaining": requests_remaining
        })
        self.retry_after = retry_after
        self.requests_remaining = requests_remaining


class AuthenticationException(LLMException):
    """认证异常"""

    def __init__(self, message: str, provider: Optional[str] = None,
                 model: Optional[str] = None):
        super().__init__(message, "AUTHENTICATION_ERROR", provider, model)


class ServiceUnavailableException(LLMException):
    """服务不可用异常"""

    def __init__(self, message: str, provider: Optional[str] = None,
                 model: Optional[str] = None, retry_after: Optional[int] = None):
        super().__init__(message, "SERVICE_UNAVAILABLE", provider, model, {
            "retry_after": retry_after
        })
        self.retry_after = retry_after


class TimeoutException(LLMException):
    """超时异常"""

    def __init__(self, message: str, provider: Optional[str] = None,
                 model: Optional[str] = None, timeout_seconds: Optional[int] = None):
        super().__init__(message, "TIMEOUT", provider, model, {
            "timeout_seconds": timeout_seconds
        })
        self.timeout_seconds = timeout_seconds


class ContentFilteredException(LLMException):
    """内容过滤异常"""

    def __init__(self, message: str, provider: Optional[str] = None,
                 model: Optional[str] = None, content_type: Optional[str] = None):
        super().__init__(message, "CONTENT_FILTERED", provider, model, {
            "content_type": content_type
        })
        self.content_type = content_type


class QuotaExceededException(LLMException):
    """配额超限异常"""

    def __init__(self, message: str, provider: Optional[str] = None,
                 model: Optional[str] = None, quota_type: Optional[str] = None):
        super().__init__(message, "QUOTA_EXCEEDED", provider, model, {
            "quota_type": quota_type
        })
        self.quota_type = quota_type


class ModelNotFoundException(LLMException):
    """模型未找到异常"""

    def __init__(self, message: str, provider: Optional[str] = None,
                 model: Optional[str] = None):
        super().__init__(message, "MODEL_NOT_FOUND", provider, model)


class InvalidRequestException(LLMException):
    """无效请求异常"""

    def __init__(self, message: str, provider: Optional[str] = None,
                 model: Optional[str] = None, validation_errors: Optional[Dict[str, Any]] = None):
        super().__init__(message, "INVALID_REQUEST", provider, model, {
            "validation_errors": validation_errors
        })
        self.validation_errors = validation_errors


class CostLimitExceededException(LLMException):
    """成本限制异常"""

    def __init__(self, message: str, provider: Optional[str] = None,
                 model: Optional[str] = None, current_cost: Optional[float] = None,
                 limit: Optional[float] = None):
        super().__init__(message, "COST_LIMIT_EXCEEDED", provider, model, {
            "current_cost": current_cost,
            "limit": limit
        })
        self.current_cost = current_cost
        self.limit = limit


class NetworkException(LLMException):
    """网络异常"""

    def __init__(self, message: str, provider: Optional[str] = None,
                 model: Optional[str] = None, network_error: Optional[str] = None):
        super().__init__(message, "NETWORK_ERROR", provider, model, {
            "network_error": network_error
        })
        self.network_error = network_error


class ProviderUnavailableException(LLMException):
    """提供商不可用异常"""

    def __init__(self, message: str, provider: Optional[str] = None,
                 health_check_failed: bool = False):
        super().__init__(message, "PROVIDER_UNAVAILABLE", provider, None, {
            "health_check_failed": health_check_failed
        })
        self.health_check_failed = health_check_failed


def create_llm_exception(error_type: str, message: str, **kwargs) -> LLMException:
    """创建LLM异常的工厂函数"""
    exception_classes = {
        "rate_limit": RateLimitException,
        "authentication": AuthenticationException,
        "service_unavailable": ServiceUnavailableException,
        "timeout": TimeoutException,
        "content_filtered": ContentFilteredException,
        "quota_exceeded": QuotaExceededException,
        "model_not_found": ModelNotFoundException,
        "invalid_request": InvalidRequestException,
        "cost_limit_exceeded": CostLimitExceededException,
        "network": NetworkException,
        "provider_unavailable": ProviderUnavailableException,
    }

    exception_class = exception_classes.get(error_type, LLMException)
    return exception_class(message, **kwargs)