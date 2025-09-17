"""
OpenAI API客户端封装
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
import aiohttp
import tiktoken
from datetime import datetime

from .base import BaseLLMProvider
from ...models.llm import LLMRequest, LLMResponse, LLMStreamResponse, LLMMessage
from ...core.llm_config import LLMProvider, LLMModelConfig
from .exceptions import (
    LLMException, RateLimitException, AuthenticationException,
    ServiceUnavailableException, TimeoutException, NetworkException
)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI服务提供商"""

    def __init__(self, provider_config: LLMProvider, model_configs: Dict[str, LLMModelConfig]):
        super().__init__(provider_config, model_configs)
        self.api_key = provider_config.api_key
        self.base_url = provider_config.base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = asyncio.Semaphore(10)  # 并发请求限制
        self.encoding = None

    async def initialize(self) -> bool:
        """初始化OpenAI客户端"""
        try:
            if not self.api_key:
                raise AuthenticationException("OpenAI API密钥未配置", self.provider_config.name)

            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)

            # 初始化tokenizer
            try:
                self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            except Exception:
                self.encoding = tiktoken.get_encoding("cl100k_base")

            # 执行健康检查
            health_ok = await self.health_check()
            if not health_ok:
                raise LLMException("OpenAI健康检查失败", "INITIALIZATION_FAILED", self.provider_config.name)

            self._is_initialized = True
            self.logger.info("OpenAI客户端初始化成功")
            return True

        except Exception as e:
            self.logger.error(f"OpenAI客户端初始化失败: {e}")
            return False

    async def health_check(self) -> bool:
        """健康检查"""
        if not self.session:
            return False

        try:
            async with self.session.get(f"{self.base_url}/models") as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    raise AuthenticationException("OpenAI API密钥无效", self.provider_config.name)
                else:
                    self.logger.warning(f"OpenAI健康检查返回状态码: {response.status}")
                    return False
        except Exception as e:
            self.logger.error(f"OpenAI健康检查失败: {e}")
            return False

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """生成响应"""
        if not self.is_initialized():
            raise LLMException("OpenAI客户端未初始化", "NOT_INITIALIZED", self.provider_config.name)

        self.validate_request(request)

        start_time = time.time()
        request_id = f"openai_{int(time.time() * 1000)}"

        try:
            async with self.rate_limiter:
                # 构建请求数据
                openai_request = self._build_openai_request(request)

                # 发送请求
                async with self.session.post(
                    f"{self.base_url}/chat/completions",
                    json=openai_request
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        return self._parse_response(data, request, start_time, request_id)

                    elif response.status == 429:
                        retry_after = self._get_retry_after(response)
                        raise RateLimitException(
                            "OpenAI速率限制",
                            self.provider_config.name,
                            request.model,
                            retry_after
                        )

                    elif response.status == 401:
                        raise AuthenticationException("OpenAI API密钥无效", self.provider_config.name)

                    elif response.status == 429:
                        raise ServiceUnavailableException("OpenAI服务不可用", self.provider_config.name)

                    else:
                        error_data = await response.json()
                        raise LLMException(
                            f"OpenAI请求失败: {error_data.get('error', {}).get('message', '未知错误')}",
                            "API_ERROR",
                            self.provider_config.name,
                            request.model
                        )

        except asyncio.TimeoutError:
            raise TimeoutException("OpenAI请求超时", self.provider_config.name, request.model)

        except aiohttp.ClientError as e:
            raise NetworkException(f"OpenAI网络错误: {e}", self.provider_config.name, request.model)

    async def generate_stream_response(self, request: LLMRequest) -> AsyncGenerator[LLMStreamResponse, None]:
        """生成流式响应"""
        if not self.is_initialized():
            raise LLMException("OpenAI客户端未初始化", "NOT_INITIALIZED", self.provider_config.name)

        self.validate_request(request)

        request_id = f"openai_stream_{int(time.time() * 1000)}"

        try:
            async with self.rate_limiter:
                openai_request = self._build_openai_request(request)
                openai_request["stream"] = True

                async with self.session.post(
                    f"{self.base_url}/chat/completions",
                    json=openai_request
                ) as response:

                    if response.status != 200:
                        error_data = await response.json()
                        raise LLMException(
                            f"OpenAI流式请求失败: {error_data.get('error', {}).get('message', '未知错误')}",
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
                raise LLMException(f"OpenAI流式响应错误: {e}", "STREAM_ERROR", self.provider_config.name, request.model)

    async def count_tokens(self, text: str, model: str) -> int:
        """计算令牌数"""
        if not self.encoding:
            return len(text.split())  # 简单估算

        try:
            return len(self.encoding.encode(text))
        except Exception:
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
            "owned_by": "openai",
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

    def _build_openai_request(self, request: LLMRequest) -> Dict[str, Any]:
        """构建OpenAI请求数据"""
        openai_request = {
            "model": request.model,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content
                }
                for msg in request.messages
            ],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty
        }

        # 可选参数
        if request.max_tokens:
            openai_request["max_tokens"] = request.max_tokens
        if request.stop:
            openai_request["stop"] = request.stop
        if request.stream:
            openai_request["stream"] = True

        return openai_request

    def _parse_response(self, data: Dict[str, Any], request: LLMRequest, start_time: float, request_id: str) -> LLMResponse:
        """解析OpenAI响应"""
        choice = data["choices"][0]
        message = choice["message"]
        usage = data.get("usage", {})

        # 计算延迟
        latency = time.time() - start_time

        # 计算成本
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = self.calculate_cost(input_tokens, output_tokens, request.model)

        return LLMResponse(
            id=data["id"],
            model=data["model"],
            provider=self.provider_config.name,
            content=message["content"],
            finish_reason=choice["finish_reason"],
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
        choice = chunk["choices"][0]
        delta = choice.get("delta", {})
        content = delta.get("content", "")

        return LLMStreamResponse(
            id=chunk.get("id", request_id),
            model=chunk.get("model", request.model),
            provider=self.provider_config.name,
            content=content,
            finish_reason=choice.get("finish_reason"),
            is_final=choice.get("finish_reason") is not None
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