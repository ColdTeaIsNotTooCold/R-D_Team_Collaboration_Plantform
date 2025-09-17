"""
Claude API客户端封装
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
import aiohttp
from datetime import datetime

from .base import BaseLLMProvider
from ...models.llm import LLMRequest, LLMResponse, LLMStreamResponse, LLMMessage
from ...core.llm_config import LLMProvider, LLMModelConfig
from .exceptions import (
    LLMException, RateLimitException, AuthenticationException,
    ServiceUnavailableException, TimeoutException, NetworkException
)


class ClaudeProvider(BaseLLMProvider):
    """Claude服务提供商"""

    def __init__(self, provider_config: LLMProvider, model_configs: Dict[str, LLMModelConfig]):
        super().__init__(provider_config, model_configs)
        self.api_key = provider_config.api_key
        self.base_url = provider_config.base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = asyncio.Semaphore(10)  # 并发请求限制

    async def initialize(self) -> bool:
        """初始化Claude客户端"""
        try:
            if not self.api_key:
                raise AuthenticationException("Claude API密钥未配置", self.provider_config.name)

            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)

            # 执行健康检查
            health_ok = await self.health_check()
            if not health_ok:
                raise LLMException("Claude健康检查失败", "INITIALIZATION_FAILED", self.provider_config.name)

            self._is_initialized = True
            self.logger.info("Claude客户端初始化成功")
            return True

        except Exception as e:
            self.logger.error(f"Claude客户端初始化失败: {e}")
            return False

    async def health_check(self) -> bool:
        """健康检查"""
        if not self.session:
            return False

        try:
            # Claude的健康检查可以通过发送一个简单的消息来实现
            test_request = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hello"}]
            }

            async with self.session.post(f"{self.base_url}/messages", json=test_request) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    raise AuthenticationException("Claude API密钥无效", self.provider_config.name)
                else:
                    self.logger.warning(f"Claude健康检查返回状态码: {response.status}")
                    return False
        except Exception as e:
            self.logger.error(f"Claude健康检查失败: {e}")
            return False

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """生成响应"""
        if not self.is_initialized():
            raise LLMException("Claude客户端未初始化", "NOT_INITIALIZED", self.provider_config.name)

        self.validate_request(request)

        start_time = time.time()
        request_id = f"claude_{int(time.time() * 1000)}"

        try:
            async with self.rate_limiter:
                # 构建请求数据
                claude_request = self._build_claude_request(request)

                # 发送请求
                async with self.session.post(
                    f"{self.base_url}/messages",
                    json=claude_request
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        return self._parse_response(data, request, start_time, request_id)

                    elif response.status == 429:
                        retry_after = self._get_retry_after(response)
                        raise RateLimitException(
                            "Claude速率限制",
                            self.provider_config.name,
                            request.model,
                            retry_after
                        )

                    elif response.status == 401:
                        raise AuthenticationException("Claude API密钥无效", self.provider_config.name)

                    elif response.status in [500, 502, 503, 504]:
                        raise ServiceUnavailableException("Claude服务不可用", self.provider_config.name)

                    else:
                        error_data = await response.json()
                        error_message = error_data.get("error", {}).get("message", "未知错误")
                        raise LLMException(
                            f"Claude请求失败: {error_message}",
                            "API_ERROR",
                            self.provider_config.name,
                            request.model
                        )

        except asyncio.TimeoutError:
            raise TimeoutException("Claude请求超时", self.provider_config.name, request.model)

        except aiohttp.ClientError as e:
            raise NetworkException(f"Claude网络错误: {e}", self.provider_config.name, request.model)

    async def generate_stream_response(self, request: LLMRequest) -> AsyncGenerator[LLMStreamResponse, None]:
        """生成流式响应"""
        if not self.is_initialized():
            raise LLMException("Claude客户端未初始化", "NOT_INITIALIZED", self.provider_config.name)

        self.validate_request(request)

        request_id = f"claude_stream_{int(time.time() * 1000)}"

        try:
            async with self.rate_limiter:
                claude_request = self._build_claude_request(request)
                claude_request["stream"] = True

                async with self.session.post(
                    f"{self.base_url}/messages",
                    json=claude_request
                ) as response:

                    if response.status != 200:
                        error_data = await response.json()
                        error_message = error_data.get("error", {}).get("message", "未知错误")
                        raise LLMException(
                            f"Claude流式请求失败: {error_message}",
                            "STREAM_ERROR",
                            self.provider_config.name,
                            request.model
                        )

                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data = line[6:]
                            if data == '[DONE]':
                                break

                            try:
                                chunk = json.loads(data)
                                yield self._parse_stream_chunk(chunk, request, request_id)
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            if isinstance(e, LLMException):
                raise
            else:
                raise LLMException(f"Claude流式响应错误: {e}", "STREAM_ERROR", self.provider_config.name, request.model)

    async def count_tokens(self, text: str, model: str) -> int:
        """计算令牌数"""
        # Claude使用自己的token计算方式
        # 这里使用简单的字符数作为近似值
        # 实际应用中应该使用Claude的token计算器
        return len(text.split())

    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        model_config = self.get_model_config(model)
        if not model_config:
            raise LLMException(f"模型 '{model}' 不存在", "MODEL_NOT_FOUND", self.provider_config.name, model)

        return {
            "id": model,
            "object": "model",
            "created": int(datetime.now().timestamp()),
            "owned_by": "anthropic",
            "max_tokens": model_config.max_tokens,
            "provider": self.provider_config.name,
            "cost_per_1k_input": model_config.cost_per_1k_input,
            "cost_per_1k_output": model_config.cost_per_1k_output
        }

    async def list_models(self) -> List[str]:
        """获取可用模型列表"""
        return list(self.model_configs.keys())

    async def estimate_cost(self, request: LLMRequest) -> float:
        """估算成本"""
        input_tokens = 0
        for message in request.messages:
            input_tokens += await self.count_tokens(message.content, request.model)

        # 估算输出令牌数（通常是输入令牌的2-3倍）
        estimated_output_tokens = input_tokens * 2

        return self.calculate_cost(input_tokens, estimated_output_tokens, request.model)

    def _build_claude_request(self, request: LLMRequest) -> Dict[str, Any]:
        """构建Claude请求数据"""
        # 转换消息格式
        claude_messages = []
        system_message = None

        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                claude_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        claude_request = {
            "model": request.model,
            "max_tokens": request.max_tokens or 4096,
            "messages": claude_messages,
            "temperature": request.temperature,
            "top_p": request.top_p
        }

        # 添加系统消息
        if system_message:
            claude_request["system"] = system_message

        # 可选参数
        if request.stop:
            claude_request["stop_sequences"] = request.stop

        return claude_request

    def _parse_response(self, data: Dict[str, Any], request: LLMRequest, start_time: float, request_id: str) -> LLMResponse:
        """解析Claude响应"""
        content = data.get("content", [{}])[0].get("text", "")
        usage = data.get("usage", {})

        # 计算延迟
        latency = time.time() - start_time

        # 计算成本
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cost = self.calculate_cost(input_tokens, output_tokens, request.model)

        # 映射finish reason
        finish_reason = data.get("stop_reason", "end_turn")
        if finish_reason == "end_turn":
            finish_reason = "stop"
        elif finish_reason == "max_tokens":
            finish_reason = "length"

        return LLMResponse(
            id=data.get("id", request_id),
            model=data.get("model", request.model),
            provider=self.provider_config.name,
            content=content,
            finish_reason=finish_reason,
            usage=usage,
            tokens={
                "input": input_tokens,
                "output": output_tokens,
                "total": usage.get("total_tokens", 0)
            },
            cost=cost,
            latency=latency,
            request_id=request_id,
            user_id=request.user_id,
            session_id=request.session_id
        )

    def _parse_stream_chunk(self, chunk: Dict[str, Any], request: LLMRequest, request_id: str) -> LLMStreamResponse:
        """解析流式响应块"""
        content = ""
        finish_reason = None

        if "delta" in chunk:
            delta = chunk["delta"]
            if "text" in delta:
                content = delta["text"]

        if "stop_reason" in chunk:
            finish_reason = chunk["stop_reason"]
            if finish_reason == "end_turn":
                finish_reason = "stop"
            elif finish_reason == "max_tokens":
                finish_reason = "length"

        return LLMStreamResponse(
            id=chunk.get("id", request_id),
            model=chunk.get("model", request.model),
            provider=self.provider_config.name,
            content=content,
            finish_reason=finish_reason,
            is_final=finish_reason is not None
        )

    def _get_retry_after(self, response: aiohttp.ClientResponse) -> Optional[int]:
        """获取重试时间"""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                return None
        return None

    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()
            self.session = None
        self._is_initialized = False