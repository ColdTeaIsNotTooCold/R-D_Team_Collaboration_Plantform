# 日期时间规则

## 获取当前日期和时间

当任何命令需要当前日期/时间（用于前置元数据、时间戳或日志）时，您必须从系统获取真实的当前日期/时间，而不是估算或使用占位符值。

### 如何获取当前日期时间

使用 `date` 命令获取当前 ISO 8601 格式的日期时间：

```bash
# 获取 ISO 8601 格式的当前日期时间（适用于 Linux/Mac）
date -u +"%Y-%m-%dT%H:%M:%SZ"

# 支持此格式的系统的替代方案
date --iso-8601=seconds

# 适用于 Windows（如果使用 PowerShell）
Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
```

### 必需格式

前置元数据中的所有日期必须使用 UTC 时区的 ISO 8601 格式：
- 格式：`YYYY-MM-DDTHH:MM:SSZ`
- 示例：`2024-01-15T14:30:45Z`

### 在前置元数据中的使用

在任何文件（PRD、史诗、任务、进度）中创建或更新前置元数据时，始终使用真实的当前日期时间：

```yaml
---
name: feature-name
created: 2024-01-15T14:30:45Z  # 使用 date 命令的实际输出
updated: 2024-01-15T14:30:45Z  # 使用 date 命令的实际输出
---
```

### 实现说明

1. **在编写任何带有前置元数据的文件之前：**
   - 运行：`date -u +"%Y-%m-%dT%H:%M:%SZ"`
   - 存储输出
   - 在前置元数据中使用这个确切的值

2. **对于创建文件的命令：**
   - PRD 创建：使用真实日期作为 `created` 字段
   - 史诗创建：使用真实日期作为 `created` 字段
   - 任务创建：使用真实日期作为 `created` 和 `updated` 字段
   - 进度跟踪：使用真实日期作为 `started` 和 `last_sync` 字段

3. **对于更新文件的命令：**
   - 始终使用当前真实日期时间更新 `updated` 字段
   - 保留原始的 `created` 字段
   - 对于同步操作，使用真实日期时间更新 `last_sync`

### 示例

**创建新的 PRD：**
```bash
# 首先，获取当前日期时间
CURRENT_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
# 输出：2024-01-15T14:30:45Z

# 然后在前置元数据中使用：
---
name: user-authentication
description: 用户身份验证和授权系统
status: backlog
created: 2024-01-15T14:30:45Z  # 使用实际的 $CURRENT_DATE 值
---
```

**更新现有任务：**
```bash
# 获取更新用的当前日期时间
UPDATE_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 只更新 'updated' 字段：
---
name: implement-login-api
status: in-progress
created: 2024-01-10T09:15:30Z  # 保持原始值
updated: 2024-01-15T14:30:45Z  # 使用新的 $UPDATE_DATE 值
---
```

### 重要说明

- **永远不要使用占位符日期** 如 `[Current ISO date/time]` 或 `YYYY-MM-DD`
- **永远不要估算日期** - 始终获取实际的系统时间
- **始终使用 UTC**（`Z` 后缀）以保持跨时区的一致性
- **保持时区一致性** - 系统中的所有日期都使用 UTC

### 跨平台兼容性

如果您需要确保在不同系统之间的兼容性：

```bash
# 首先尝试主要方法
date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || \
# 没有 -u 标志的系统的备用方案
date +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || \
# 最后的方案：如果可用则使用 Python
python3 -c "from datetime import datetime; print(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))" 2>/dev/null || \
python -c "from datetime import datetime; print(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))" 2>/dev/null
```

## 规则优先级

此规则具有**最高优先级**，必须被所有遵循以下规则的命令所遵守：
- 创建带有前置元数据的新文件
- 更新带有前置元数据的现有文件
- 跟踪时间戳或进度
- 记录任何基于时间的信息

受影响的命令：prd-new、prd-parse、epic-decompose、epic-sync、issue-start、issue-sync 以及任何其他写入时间戳的命令。