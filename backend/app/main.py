from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import time
import logging
import asyncio
from datetime import datetime
import psutil

from .core.config import settings
from .core.database import engine, Base, get_db
from sqlalchemy.orm import Session
from .core.redis import get_redis
from .core.vector_db import get_vector_db
from .core.embeddings import get_embedding_generator
from .core.executor_init import initialize_executor_services, shutdown_executor_services, get_executor_status
from .api import users, agents, tasks, context, messages, vector, executor, scheduler

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Team Collaboration Platform API",
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # 记录请求信息
    logger.info(f"Request: {request.method} {request.url}")

    response = await call_next(request)

    # 记录响应信息
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.4f}s")

    return response

# 异常处理
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "status_code": 422}
    )

# 健康检查端点
@app.get("/health")
async def health_check():
    """基础健康检查端点"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat()
    }

# 详细健康检查端点
@app.get("/health/detailed")
async def detailed_health_check():
    """详细健康检查端点，包含数据库和Redis连接状态"""
    health_status = {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": "unknown",
            "redis": "unknown",
            "system": "unknown",
            "executor": "unknown"
        },
        "uptime": "unknown"
    }

    try:
        # 检查数据库连接
        async with get_db() as db:
            await db.execute("SELECT 1")
            health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["components"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    try:
        # 检查Redis连接
        redis_client = get_redis()
        await redis_client.ping()
        health_status["components"]["redis"] = "healthy"
    except Exception as e:
        health_status["components"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    try:
        # 检查系统状态
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        health_status["components"]["system"] = {
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "cpu_percent": psutil.cpu_percent(interval=1),
            "status": "healthy" if memory.percent < 90 and disk.percent < 90 else "warning"
        }

        # 获取应用运行时间（简化版本）
        process = psutil.Process()
        health_status["uptime"] = str(datetime.fromtimestamp(process.create_time()))

    except Exception as e:
        health_status["components"]["system"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    try:
        # 检查任务执行器状态
        executor_status = get_executor_status()
        health_status["components"]["executor"] = executor_status

        # 如果执行器未初始化，标记为降级
        if executor_status.get("task_executor") != "initialized":
            health_status["status"] = "degraded"

    except Exception as e:
        health_status["components"]["executor"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # 如果所有组件都健康，状态为healthy
    if all(component == "healthy" or
           (isinstance(component, dict) and component.get("status") == "healthy")
           for component in health_status["components"].values()):
        health_status["status"] = "healthy"

    return health_status

# 就绪检查端点
@app.get("/health/ready")
async def readiness_check():
    """就绪检查端点"""
    ready = True
    checks = {}

    # 检查数据库是否就绪
    try:
        async with get_db() as db:
            await db.execute("SELECT 1")
        checks["database"] = "ready"
    except Exception as e:
        checks["database"] = f"not_ready: {str(e)}"
        ready = False

    # 检查Redis是否就绪
    try:
        redis_client = get_redis()
        await redis_client.ping()
        checks["redis"] = "ready"
    except Exception as e:
        checks["redis"] = f"not_ready: {str(e)}"
        ready = False

    return {
        "ready": ready,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }

# 存活检查端点
@app.get("/health/live")
async def liveness_check():
    """存活检查端点"""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }

# 指标端点
@app.get("/metrics")
async def metrics():
    """基础指标端点"""
    try:
        process = psutil.Process()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": memory.percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "disk_percent": disk.percent,
                "disk_total": disk.total,
                "disk_free": disk.free
            },
            "process": {
                "memory_percent": process.memory_percent(),
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads(),
                "connections": len(process.connections())
            }
        }
    except Exception as e:
        return {
            "error": f"Failed to collect metrics: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }

# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs"
    }

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化组件"""
    logger.info("应用启动，初始化组件...")

    # 初始化向量数据库
    try:
        vector_db = await get_vector_db()
        success = await vector_db.initialize()
        if success:
            logger.info("向量数据库初始化成功")
        else:
            logger.error("向量数据库初始化失败")
    except Exception as e:
        logger.error(f"向量数据库初始化异常: {str(e)}")

    # 初始化嵌入生成器
    try:
        embedding_generator = await get_embedding_generator()
        success = await embedding_generator.initialize()
        if success:
            logger.info("嵌入生成器初始化成功")
        else:
            logger.error("嵌入生成器初始化失败")
    except Exception as e:
        logger.error(f"嵌入生成器初始化异常: {str(e)}")

    # 初始化任务执行器服务
    try:
        await initialize_executor_services()
        logger.info("任务执行器服务初始化成功")
    except Exception as e:
        logger.error(f"任务执行器服务初始化异常: {str(e)}")

    logger.info("应用启动完成")


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理组件"""
    logger.info("应用关闭，清理组件...")

    try:
        await shutdown_executor_services()
        logger.info("任务执行器服务已关闭")
    except Exception as e:
        logger.error(f"任务执行器服务关闭异常: {str(e)}")

    logger.info("应用关闭完成")


# 包含路由
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(context.router, prefix="/api/v1/contexts", tags=["contexts"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
app.include_router(vector.router, prefix="/api/v1/vector", tags=["vector"])
app.include_router(executor.router, prefix="/api/v1/executor", tags=["executor"])
app.include_router(scheduler.router, prefix="/api/v1/scheduler", tags=["scheduler"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)