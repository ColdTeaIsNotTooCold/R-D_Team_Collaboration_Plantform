# 代理协调

在同一史诗工作树中并行工作的多个代理的规则。

## 并行执行原则

1. **文件级并行** - 处理不同文件的代理不会冲突
2. **显式协调** - 当需要同一文件时，显式协调
3. **快速失败** - 立即暴露冲突，不要尝试智能处理
4. **人工解决** - 冲突由人工解决，而不是代理

## 工作流分配

每个代理从问题分析中分配一个工作流：
```yaml
# 来自 {issue}-analysis.md
流 A: 数据库层
  文件: src/db/*, migrations/*
  代理: backend-specialist

流 B: API 层
  文件: src/api/*
  代理: api-specialist
```

代理只应修改其分配模式中的文件。

## 文件访问协调

### 修改前检查
修改共享文件之前：
```bash
# 检查文件是否正在被修改
git status {file}

# 如果被其他代理修改，等待
if [[ $(git status --porcelain {file}) ]]; then
  echo "等待 {file} 可用..."
  sleep 30
  # 重试
fi
```

### 原子提交
使提交原子化和专注：
```bash
# 好 - 单一目的提交
git add src/api/users.ts src/api/users.test.ts
git commit -m "Issue #1234: 添加用户 CRUD 端点"

# 不好 - 混合关注点
git add src/api/* src/db/* src/ui/*
git commit -m "Issue #1234: 多个更改"
```

## 代理间通信

### 通过提交
代理通过提交查看彼此的工作：
```bash
# 代理检查其他人的工作
git log --oneline -10

# 代理拉取最新更改
git pull origin epic/{name}
```

### 通过进度文件
每个流维护进度：
```markdown
# .claude/epics/{epic}/updates/{issue}/stream-A.md
---
stream: 数据库层
agent: backend-specialist
started: {datetime}
status: in_progress
---

## 已完成
- 创建用户表架构
- 添加迁移文件

## 正在进行
- 添加索引

## 已阻塞
- 无
```

### 通过分析文件
分析文件是契约：
```yaml
# 代理阅读此文件以了解边界
流 A:
  文件: src/db/*  # 代理 A 只处理这些
流 B:
  文件: src/api/* # 代理 B 只处理这些
```

## 处理冲突

### 冲突检测
```bash
# 如果提交因冲突而失败
git commit -m "Issue #1234: 更新"
# 错误: 存在冲突

# 代理应报告并等待
echo "❌ 在 {files} 中检测到冲突"
echo "需要人工干预"
```

### 冲突解决
始终依赖人工：
1. 代理检测冲突
2. 代理报告问题
3. 代理暂停工作
4. 人工解决
5. 代理继续

永远不要尝试自动合并解决。

## 同步点

### 自然同步点
- 每次提交后
- 开始新文件之前
- 切换工作流时
- 每工作 30 分钟

### 显式同步
```bash
# 拉取最新更改
git pull --rebase origin epic/{name}

# 如果有冲突，停止并报告
if [[ $? -ne 0 ]]; then
  echo "❌ 同步失败 - 需要人工帮助"
  exit 1
fi
```

## 代理通信协议

### 状态更新
代理应定期更新状态：
```bash
# 每个重要步骤更新进度文件
echo "✅ 已完成: 数据库架构" >> stream-A.md
git add stream-A.md
git commit -m "进度: 流 A - 架构完成"
```

### 协调请求
当代理需要协调时：
```markdown
# 在 stream-A.md 中
## 需要协调
- 需要更新 src/types/index.ts
- 将在流 B 提交后修改
- 预计时间: 10 分钟
```

## 并行提交策略

### 无可能冲突
处理完全不同的文件时：
```bash
# 这些可以同时进行
代理-A: git commit -m "Issue #1234: 更新数据库"
代理-B: git commit -m "Issue #1235: 更新 UI"
代理-C: git commit -m "Issue #1236: 添加测试"
```

### 需要时序处理
处理共享资源时：
```bash
# 代理 A 先提交
git add src/types/index.ts
git commit -m "Issue #1234: 更新类型定义"

# 代理 B 等待，然后继续
# (在 A 提交后)
git pull
git add src/api/users.ts
git commit -m "Issue #1235: 使用新类型"
```

## 最佳实践

1. **频繁提交** - 较小的提交 = 较少的冲突
2. **坚守自己的领域** - 只修改分配的文件
3. **沟通更改** - 更新进度文件
4. **频繁拉取** - 与其他代理保持同步
5. **大声失败** - 立即报告问题
6. **不要强制** - 永远不要使用 `--force` 标志

## 常见模式

### 开始工作
```bash
1. cd ../epic-{name}
2. git pull
3. 检查 {issue}-analysis.md 以获取分配
4. 用 "started" 更新 stream-{X}.md
5. 开始处理分配的文件
```

### 工作期间
```bash
1. 对分配的文件进行更改
2. 用清晰的消息提交
3. 更新进度文件
4. 检查其他人的新提交
5. 根据需要继续或协调
```

### 完成工作
```bash
1. 流的最终提交
2. 用 "completed" 更新 stream-{X}.md
3. 检查其他流是否需要帮助
4. 报告完成
```
