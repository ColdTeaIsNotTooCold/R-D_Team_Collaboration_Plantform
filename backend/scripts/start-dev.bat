@echo off
REM 开发环境快速启动脚本 (Windows)

echo === 团队协作平台开发环境启动 ===

REM 检查Docker是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo 错误: Docker未运行，请先启动Docker
    pause
    exit /b 1
)

REM 创建日志目录
if not exist "logs" mkdir logs

REM 停止现有服务
echo 停止现有服务...
docker-compose down

REM 构建并启动服务
echo 构建并启动服务...
docker-compose up --build -d

REM 等待服务启动
echo 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo 检查服务状态...
docker-compose ps

REM 运行数据库迁移
echo 运行数据库迁移...
docker-compose run --rm alembic

REM 显示访问信息
echo.
echo === 服务访问信息 ===
echo API文档: http://localhost:8000/docs
echo 健康检查: http://localhost:8000/health
echo 详细健康检查: http://localhost:8000/health/detailed
echo 指标: http://localhost:8000/metrics
echo.
echo Redis CLI: docker-compose run --rm redis-cli
echo.
echo 查看日志: docker-compose logs -f [service]
echo 停止服务: docker-compose down
echo.

REM 运行验证脚本
echo 运行部署验证...
python scripts/deployment-verify.py

pause