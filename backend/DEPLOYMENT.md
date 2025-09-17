# 部署配置说明

## 概述

本文档描述了团队协作平台的部署配置，包括Docker容器化、服务编排和环境管理。

## 快速开始

### 前置条件
- Docker >= 20.10
- Docker Compose >= 1.29
- Python 3.11 (用于运行验证脚本)

### 开发环境启动

#### Linux/macOS
```bash
# 在backend目录下
chmod +x scripts/start-dev.sh
./scripts/start-dev.sh
```

#### Windows
```cmd
# 在backend目录下
scripts\start-dev.bat
```

### 手动启动
```bash
# 1. 停止现有服务
docker-compose down

# 2. 构建并启动服务
docker-compose up --build -d

# 3. 运行数据库迁移
docker-compose run --rm alembic

# 4. 验证部署
python scripts/deployment-verify.py
```

## 服务架构

### 核心服务
- **app**: FastAPI应用 (端口8000)
- **postgres**: PostgreSQL数据库 (端口5432)
- **redis**: Redis缓存和消息队列 (端口6379)

### 辅助服务
- **alembic**: 数据库迁移工具
- **redis-cli**: Redis调试工具

## 配置文件

### 环境变量
- `.env`: 开发环境配置
- `.env.production`: 生产环境配置
- `.env.example`: 配置模板

### 配置文件
- `docker-compose.yml`: 服务编排配置
- `redis.conf`: Redis配置
- `init.sql`: 数据库初始化脚本

## 健康检查

### 检查端点
- `/health`: 基础健康检查
- `/health/detailed`: 详细健康检查（数据库、Redis、系统状态）
- `/health/ready`: 就绪检查
- `/health/live`: 存活检查
- `/metrics`: 系统指标

### 验证脚本
```bash
# 运行完整验证
python scripts/deployment-verify.py

# 检查单个端点
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed
```

## 服务管理

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f app
docker-compose logs -f postgres
docker-compose logs -f redis
```

### 重启服务
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart app
```

### 停止服务
```bash
# 停止并删除容器
docker-compose down

# 停止并删除容器和数据卷
docker-compose down -v
```

## 数据库管理

### 运行迁移
```bash
# 升级到最新版本
docker-compose run --rm alembic upgrade head

# 回滚到上一个版本
docker-compose run --rm alembic downgrade -1

# 查看迁移历史
docker-compose run --rm alembic history

# 创建迁移
docker-compose run --rm alembic revision --autogenerate -m "描述"
```

### 数据库访问
```bash
# 连接到PostgreSQL
docker-compose exec postgres psql -U ccpm_user -d ccpm_db

# 使用psql命令
docker-compose run --rm postgres psql -h postgres -U ccpm_user -d ccpm_db
```

## Redis管理

### Redis CLI访问
```bash
# 连接到Redis
docker-compose run --rm redis-cli

# 执行Redis命令
docker-compose run --rm redis-cli ping
docker-compose run --rm redis-cli info
```

### 常用Redis命令
```bash
# 查看所有键
docker-compose run --rm redis-cli KEYS "*"

# 查看内存使用
docker-compose run --rm redis-cli info memory

# 查看连接信息
docker-compose run --rm redis-cli info clients
```

## 生产环境部署

### 环境准备
```bash
# 1. 复制生产环境配置
cp .env.example .env.production

# 2. 编辑生产环境配置
vim .env.production

# 3. 设置必要的环境变量
export SECRET_KEY="your-production-secret-key"
export DATABASE_URL="your-production-database-url"
export REDIS_URL="your-production-redis-url"
```

### 生产环境启动
```bash
# 使用生产环境配置
export ENVIRONMENT=production

# 启动服务
docker-compose -f docker-compose.yml up -d

# 运行迁移
docker-compose run --rm alembic

# 验证部署
python scripts/deployment-verify.py
```

### 安全配置
1. **更改默认密码**
   - 数据库密码
   - Redis密码
   - JWT密钥

2. **网络安全**
   - 配置防火墙
   - 使用HTTPS
   - 限制数据库访问

3. **监控**
   - 设置日志监控
   - 配置告警
   - 定期备份

## 故障排除

### 常见问题

#### 服务启动失败
```bash
# 检查Docker状态
docker info

# 检查端口占用
netstat -tulpn | grep 8000
netstat -tulpn | grep 5432
netstat -tulpn | grep 6379

# 查看详细错误日志
docker-compose logs app
```

#### 数据库连接失败
```bash
# 检查数据库状态
docker-compose exec postgres pg_isready

# 检查数据库日志
docker-compose logs postgres

# 测试数据库连接
docker-compose run --rm postgres psql -h postgres -U ccpm_user -d ccpm_db -c "SELECT 1"
```

#### Redis连接失败
```bash
# 检查Redis状态
docker-compose exec redis redis-cli ping

# 检查Redis日志
docker-compose logs redis

# 测试Redis连接
docker-compose run --rm redis-cli -h redis ping
```

### 性能优化

### 资源限制
```yaml
# 在docker-compose.yml中添加
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### 数据库优化
```sql
-- 分析查询性能
EXPLAIN ANALYZE SELECT * FROM users;

-- 创建索引
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

### Redis优化
```bash
# 调整内存配置
CONFIG SET maxmemory 512mb
CONFIG SET maxmemory-policy allkeys-lru
```

## 备份和恢复

### 数据库备份
```bash
# 创建备份
docker-compose exec postgres pg_dump -U ccpm_user -d ccpm_db > backup.sql

# 恢复备份
docker-compose exec -T postgres psql -U ccp_user -d ccpm_db < backup.sql
```

### Redis备份
```bash
# 创建备份
docker-compose exec redis redis-cli BGSAVE

# 查看备份文件
docker-compose exec redis ls -la /data/
```

## 监控和日志

### 日志配置
- 应用日志: `/app/logs/app.log`
- Docker日志: `docker-compose logs`
- 系统日志: 通过健康检查端点查看

### 监控指标
- 系统指标: `/metrics` 端点
- 健康状态: `/health/detailed` 端点
- 应用性能: 通过中间件记录

## 联系信息

如有问题，请查看：
- 项目文档: `README.md`
- 问题跟踪: GitHub Issues
- 技术支持: 项目维护者