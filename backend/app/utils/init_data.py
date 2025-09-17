"""
数据库初始化脚本
创建基础用户、Agent和示例数据
"""
import asyncio
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, create_tables
from app.core.security import get_password_hash
from app.models import User, Agent, Task, Conversation, Context


def create_default_user(db: Session) -> User:
    """创建默认管理员用户"""
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            email="admin@example.com",
            full_name="Administrator",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_superuser=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"✅ 创建默认管理员用户: {admin_user.username}")
    else:
        print(f"✓ 默认管理员用户已存在: {admin_user.username}")

    return admin_user


def create_default_agents(db: Session, admin_user: User) -> list[Agent]:
    """创建默认Agent"""
    agents_data = [
        {
            "name": "代码分析器",
            "description": "专门执行繁重工作并返回简洁摘要以保持上下文的专业代理",
            "agent_type": "code_analyzer",
            "system_prompt": "你是代码分析器代理。跨多个文件查找错误，不污染主上下文。搜索多个文件 → 分析代码 → 返回错误报告。仅包含关键发现的简洁错误报告。",
            "owner_id": admin_user.id
        },
        {
            "name": "文件分析器",
            "description": "读取和总结冗长文件（日志、输出、配置）",
            "agent_type": "file_analyzer",
            "system_prompt": "你是文件分析器代理。读取文件 → 提取洞察 → 返回摘要。需要理解日志文件或分析冗长输出时使用。返回关键发现和可操作的洞察（减少 80-90% 的内容）。",
            "owner_id": admin_user.id
        },
        {
            "name": "测试运行器",
            "description": "执行测试，不向主线程转储输出",
            "agent_type": "test_runner",
            "system_prompt": "你是测试运行器代理。运行测试 → 捕获到日志 → 分析结果 → 返回摘要。需要运行测试并理解失败原因时使用。返回带有失败分析的测试结果摘要。",
            "owner_id": admin_user.id
        },
        {
            "name": "并行工作器",
            "description": "协调一个问题的多个并行工作流",
            "agent_type": "parallel_worker",
            "system_prompt": "你是并行工作器代理。读取分析 → 生成子代理 → 整合结果 → 返回摘要。在工作树中执行并行工作流时使用。返回所有并行工作的整合状态。",
            "owner_id": admin_user.id
        }
    ]

    created_agents = []
    for agent_data in agents_data:
        existing_agent = db.query(Agent).filter(
            Agent.name == agent_data["name"],
            Agent.owner_id == agent_data["owner_id"]
        ).first()

        if not existing_agent:
            agent = Agent(**agent_data)
            db.add(agent)
            db.commit()
            db.refresh(agent)
            created_agents.append(agent)
            print(f"✅ 创建默认Agent: {agent.name} ({agent.agent_type})")
        else:
            created_agents.append(existing_agent)
            print(f"✓ 默认Agent已存在: {existing_agent.name} ({existing_agent.agent_type})")

    return created_agents


def create_example_conversation(db: Session, admin_user: User) -> Conversation:
    """创建示例对话"""
    conversation = db.query(Conversation).filter(
        Conversation.title == "项目初始化对话",
        Conversation.user_id == admin_user.id
    ).first()

    if not conversation:
        conversation = Conversation(
            title="项目初始化对话",
            description="项目MVP核心架构搭建的相关讨论",
            user_id=admin_user.id,
            is_active=True
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        print(f"✅ 创建示例对话: {conversation.title}")
    else:
        print(f"✓ 示例对话已存在: {conversation.title}")

    return conversation


def create_example_context(db: Session, conversation: Conversation) -> Context:
    """创建示例上下文"""
    context = db.query(Context).filter(
        Context.title == "项目架构分析",
        Context.conversation_id == conversation.id
    ).first()

    if not context:
        context_data = {
            "context_type": "analysis",
            "title": "项目架构分析",
            "content": """# Team Collaboration Platform 架构分析

## 技术栈
- **后端**: FastAPI + SQLAlchemy + PostgreSQL
- **缓存**: Redis (缓存 + Streams消息队列)
- **认证**: JWT Token
- **数据库迁移**: Alembic
- **部署**: Docker + Docker Compose

## 核心功能
1. **用户管理**: 认证、授权、权限控制
2. **Agent系统**: AI代理配置和管理
3. **任务管理**: 任务创建、分配、执行、跟踪
4. **上下文管理**: 数据存储、文件管理
5. **对话系统**: 会话管理和历史记录

## 数据模型
- **User**: 用户信息和权限
- **Agent**: AI代理配置
- **Task**: 任务管理
- **Context**: 上下文数据
- **Conversation**: 对话记录""",
            "metadata": """{"analysis_type": "architecture", "version": "1.0", "created_by": "system"}""",
            "conversation_id": conversation.id
        }

        context = Context(**context_data)
        db.add(context)
        db.commit()
        db.refresh(context)
        print(f"✅ 创建示例上下文: {context.title}")
    else:
        print(f"✓ 示例上下文已存在: {context.title}")

    return context


def create_example_task(db: Session, admin_user: User, agents: list[Agent]) -> Task:
    """创建示例任务"""
    task = db.query(Task).filter(
        Task.title == "数据库层实现",
        Task.creator_id == admin_user.id
    ).first()

    if not task:
        task_data = {
            "title": "数据库层实现",
            "description": "实现PostgreSQL数据库模型、SQLAlchemy配置、Alembic迁移",
            "status": "completed",
            "priority": "high",
            "task_type": "implementation",
            "input_data": """{
                "subtasks": [
                    "设计数据库模型（用户、Agent、任务、上下文）",
                    "配置SQLAlchemy和数据库连接",
                    "设置Alembic数据库迁移",
                    "创建基础数据初始化脚本"
                ]
            }""",
            "output_data": """{
                "result": "success",
                "models_created": 5,
                "tables_created": 5,
                "migration_files": 3,
                "sample_data": "initialized"
            }""",
            "creator_id": admin_user.id,
            "assigned_agent_id": agents[0].id if agents else None
        }

        task = Task(**task_data)
        db.add(task)
        db.commit()
        db.refresh(task)
        print(f"✅ 创建示例任务: {task.title}")
    else:
        print(f"✓ 示例任务已存在: {task.title}")

    return task


def init_database():
    """初始化数据库"""
    print("🚀 开始初始化数据库...")

    # 创建表
    print("📊 创建数据库表...")
    create_tables()
    print("✅ 数据库表创建完成")

    db = SessionLocal()
    try:
        # 创建默认用户
        admin_user = create_default_user(db)

        # 创建默认Agent
        agents = create_default_agents(db, admin_user)

        # 创建示例对话
        conversation = create_example_conversation(db, admin_user)

        # 创建示例上下文
        create_example_context(db, conversation)

        # 创建示例任务
        create_example_task(db, admin_user, agents)

        print("\n🎉 数据库初始化完成！")
        print("\n📋 初始化摘要:")
        print(f"   - 管理员用户: {admin_user.username}")
        print(f"   - 默认Agent: {len(agents)} 个")
        print(f"   - 示例对话: {conversation.title}")
        print(f"   - 示例任务: 已创建")

        print("\n🔑 默认登录信息:")
        print(f"   用户名: {admin_user.username}")
        print(f"   邮箱: {admin_user.email}")
        print(f"   密码: admin123 (请及时修改)")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()