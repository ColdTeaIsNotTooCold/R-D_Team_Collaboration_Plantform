"""
LLM集成测试脚本
测试LLM服务的基本功能
"""
import asyncio
import sys
import os
from unittest.mock import Mock, patch

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.services.llm.manager import get_llm_manager
from backend.app.core.llm_config import get_llm_config
from backend.app.models.llm import LLMRequest, LLMMessage


async def test_config():
    """测试配置"""
    print("测试LLM配置...")
    config = get_llm_config()

    # 测试默认配置
    assert config.app_name == "Team Collaboration Platform"
    assert config.default_model == "gpt-3.5-turbo"
    print("✓ 配置加载成功")

    # 测试模型配置
    model_configs = config.model_configs
    assert len(model_configs) > 0
    print(f"✓ 找到 {len(model_configs)} 个模型配置")

    # 测试成本控制
    cost_control = config.cost_control
    assert cost_control.monthly_limit > 0
    print("✓ 成本控制配置正常")


async def test_manager_initialization():
    """测试管理器初始化"""
    print("测试LLM管理器初始化...")

    try:
        manager = await get_llm_manager()
        assert manager is not None
        print("✓ LLM管理器初始化成功")
        return manager
    except Exception as e:
        print(f"✗ LLM管理器初始化失败: {e}")
        return None


async def test_available_models(manager):
    """测试可用模型"""
    if not manager:
        print("✗ 跳过模型测试（管理器未初始化）")
        return

    print("测试可用模型...")
    try:
        models = await manager.get_available_models()
        print(f"✓ 可用模型: {models}")
    except Exception as e:
        print(f"✗ 获取可用模型失败: {e}")


async def test_cost_estimation(manager):
    """测试成本估算"""
    if not manager:
        print("✗ 跳过成本估算测试（管理器未初始化）")
        return

    print("测试成本估算...")
    try:
        request = LLMRequest(
            model="gpt-3.5-turbo",
            messages=[LLMMessage(role="user", content="Hello, how are you?")]
        )
        cost = await manager.estimate_cost(request)
        print(f"✓ 成本估算: ${cost:.6f}")
    except Exception as e:
        print(f"✗ 成本估算失败: {e}")


async def test_system_status(manager):
    """测试系统状态"""
    if not manager:
        print("✗ 跳过系统状态测试（管理器未初始化）")
        return

    print("测试系统状态...")
    try:
        status = await manager.get_system_status()
        print(f"✓ 系统状态: {status.get('initialized', False)}")
        print(f"  - 提供商数量: {len(status.get('providers', {}))}")
        print(f"  - 负载均衡器: {status.get('load_balancer', {}).get('strategy', 'unknown')}")
    except Exception as e:
        print(f"✗ 获取系统状态失败: {e}")


async def test_health_check(manager):
    """测试健康检查"""
    if not manager:
        print("✗ 跳过健康检查（管理器未初始化）")
        return

    print("测试健康检查...")
    try:
        is_healthy = await manager.health_check()
        print(f"✓ 健康状态: {'健康' if is_healthy else '不健康'}")
    except Exception as e:
        print(f"✗ 健康检查失败: {e}")


async def test_usage_statistics(manager):
    """测试使用统计"""
    if not manager:
        print("✗ 跳过使用统计测试（管理器未初始化）")
        return

    print("测试使用统计...")
    try:
        stats = await manager.get_usage_statistics()
        print(f"✓ 使用统计: {stats}")
    except Exception as e:
        print(f"✗ 获取使用统计失败: {e}")


async def test_token_counting(manager):
    """测试令牌计算"""
    if not manager:
        print("✗ 跳过令牌计算测试（管理器未初始化）")
        return

    print("测试令牌计算...")
    try:
        text = "Hello, how are you today?"
        tokens = await manager.count_tokens(text, "gpt-3.5-turbo")
        print(f"✓ 令牌数量: {tokens}")
    except Exception as e:
        print(f"✗ 令牌计算失败: {e}")


async def test_cost_breakdown(manager):
    """测试成本分解"""
    if not manager:
        print("✗ 跳过成本分解测试（管理器未初始化）")
        return

    print("测试成本分解...")
    try:
        breakdown = await manager.get_cost_breakdown()
        print(f"✓ 成本分解: {breakdown}")
    except Exception as e:
        print(f"✗ 获取成本分解失败: {e}")


async def test_conversation_creation(manager):
    """测试对话创建"""
    if not manager:
        print("✗ 跳过对话创建测试（管理器未初始化）")
        return

    print("测试对话创建...")
    try:
        conversation = await manager.create_conversation(
            user_id="test_user",
            title="Test Conversation",
            model="gpt-3.5-turbo",
            system_prompt="You are a helpful assistant."
        )
        print(f"✓ 对话创建成功: {conversation.id}")
    except Exception as e:
        print(f"✗ 对话创建失败: {e}")


async def main():
    """主测试函数"""
    print("=" * 50)
    print("LLM集成测试")
    print("=" * 50)

    # 测试配置
    await test_config()

    # 测试管理器初始化
    manager = await test_manager_initialization()

    # 测试各项功能
    await test_available_models(manager)
    await test_cost_estimation(manager)
    await test_system_status(manager)
    await test_health_check(manager)
    await test_usage_statistics(manager)
    await test_token_counting(manager)
    await test_cost_breakdown(manager)
    await test_conversation_creation(manager)

    print("=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())