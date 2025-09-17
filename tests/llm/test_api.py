"""
LLM API测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend.app.main import app
from backend.app.api.llm.router import router
from backend.app.api.llm.schemas import ChatRequest, ChatMessage
from backend.app.models.llm import LLMResponse, LLMMessage


class TestLLMAPI:
    """LLM API测试"""

    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def mock_llm_manager(self):
        """模拟LLM管理器"""
        manager = Mock()
        manager.generate_response = AsyncMock()
        manager.get_available_models = AsyncMock(return_value=["gpt-3.5-turbo", "gpt-4"])
        manager.get_model_info = AsyncMock(return_value={
            "id": "gpt-3.5-turbo",
            "provider": "openai",
            "max_tokens": 4096,
            "cost_per_1k_input": 0.0015,
            "cost_per_1k_output": 0.002
        })
        manager.estimate_cost = AsyncMock(return_value=0.01)
        manager.get_usage_statistics = AsyncMock(return_value={
            "total_requests": 10,
            "total_tokens": 1000,
            "total_cost": 0.1,
            "average_latency": 0.5,
            "success_rate": 1.0
        })
        manager.get_cost_breakdown = AsyncMock(return_value={})
        manager.get_system_status = AsyncMock(return_value={
            "initialized": True,
            "providers": {},
            "load_balancer": {},
            "cost_monitor": {}
        })
        manager.health_check = AsyncMock(return_value=True)
        manager.create_conversation = AsyncMock()
        return manager

    def test_get_models(self, client, mock_llm_manager):
        """测试获取模型列表"""
        with patch('backend.app.api.llm.router.get_llm_manager', return_value=mock_llm_manager):
            response = client.get("/api/v1/llm/models")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "gpt-3.5-turbo"
            assert data[1]["name"] == "gpt-4"

    def test_get_model_info(self, client, mock_llm_manager):
        """测试获取模型信息"""
        with patch('backend.app.api.llm.router.get_llm_manager', return_value=mock_llm_manager):
            response = client.get("/api/v1/llm/models/gpt-3.5-turbo")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "gpt-3.5-turbo"
            assert data["provider"] == "openai"
            assert data["max_tokens"] == 4096

    def test_chat_success(self, client, mock_llm_manager):
        """测试聊天成功"""
        # 设置模拟响应
        mock_response = LLMResponse(
            id="test_id",
            model="gpt-3.5-turbo",
            provider="openai",
            content="Hello! How can I help you?",
            finish_reason="stop",
            usage={"total_tokens": 10},
            tokens={"input": 5, "output": 5, "total": 10},
            cost=0.001,
            latency=0.5
        )
        mock_llm_manager.generate_response.return_value = mock_response

        with patch('backend.app.api.llm.router.get_llm_manager', return_value=mock_llm_manager):
            request_data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "temperature": 0.7,
                "max_tokens": 100
            }

            response = client.post("/api/v1/llm/chat", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test_id"
            assert data["model"] == "gpt-3.5-turbo"
            assert data["content"] == "Hello! How can I help you?"
            assert data["cost"] == 0.001

    def test_chat_invalid_model(self, client):
        """测试无效模型"""
        request_data = {
            "model": "invalid_model",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }

        response = client.post("/api/v1/llm/chat", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "模型 'invalid_model' 不可用" in data["detail"]

    def test_estimate_cost(self, client, mock_llm_manager):
        """测试估算成本"""
        with patch('backend.app.api.llm.router.get_llm_manager', return_value=mock_llm_manager):
            request_data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            }

            response = client.post("/api/v1/llm/estimate-cost", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["estimated_cost"] == 0.01

    def test_get_usage_stats(self, client, mock_llm_manager):
        """测试获取使用统计"""
        with patch('backend.app.api.llm.router.get_llm_manager', return_value=mock_llm_manager):
            response = client.get("/api/v1/llm/usage")

            assert response.status_code == 200
            data = response.json()
            assert data["total_requests"] == 10
            assert data["total_tokens"] == 1000
            assert data["total_cost"] == 0.1

    def test_get_cost_breakdown(self, client, mock_llm_manager):
        """测试获取成本分解"""
        with patch('backend.app.api.llm.router.get_llm_manager', return_value=mock_llm_manager):
            response = client.get("/api/v1/llm/cost-breakdown")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict)

    def test_get_system_status(self, client, mock_llm_manager):
        """测试获取系统状态"""
        with patch('backend.app.api.llm.router.get_llm_manager', return_value=mock_llm_manager):
            response = client.get("/api/v1/llm/system-status")

            assert response.status_code == 200
            data = response.json()
            assert data["initialized"] is True
            assert "providers" in data
            assert "load_balancer" in data
            assert "cost_monitor" in data

    def test_health_check(self, client, mock_llm_manager):
        """测试健康检查"""
        with patch('backend.app.api.llm.router.get_llm_manager', return_value=mock_llm_manager):
            response = client.get("/api/v1/llm/health")

            assert response.status_code == 200
            data = response.json()
            assert data["healthy"] is True

    def test_create_conversation(self, client, mock_llm_manager):
        """测试创建对话"""
        mock_llm_manager.create_conversation.return_value = Mock(id="test_conv_id")

        with patch('backend.app.api.llm.router.get_llm_manager', return_value=mock_llm_manager):
            request_data = {
                "title": "Test Conversation",
                "model": "gpt-3.5-turbo"
            }

            response = client.post("/api/v1/llm/conversations", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["conversation_id"] == "test_conv_id"
            assert data["status"] == "created"

    def test_chat_stream(self, client, mock_llm_manager):
        """测试流式聊天"""
        # 模拟流式响应
        async def mock_stream():
            chunks = [
                {"id": "test_id", "model": "gpt-3.5-turbo", "provider": "openai", "content": "Hello", "finish_reason": None, "is_final": False},
                {"id": "test_id", "model": "gpt-3.5-turbo", "provider": "openai", "content": "!", "finish_reason": "stop", "is_final": True}
            ]
            for chunk in chunks:
                yield chunk

        mock_llm_manager.generate_stream_response = mock_stream

        with patch('backend.app.api.llm.router.get_llm_manager', return_value=mock_llm_manager):
            request_data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "stream": True
            }

            response = client.post("/api/v1/llm/chat/stream", json=request_data)

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/plain; charset=utf-8"
            assert "Cache-Control" in response.headers

    def test_invalid_chat_request(self, client):
        """测试无效聊天请求"""
        # 缺少必需字段
        request_data = {
            "model": "gpt-3.5-turbo"
            # 缺少messages字段
        }

        response = client.post("/api/v1/llm/chat", json=request_data)

        assert response.status_code == 422  # 验证错误