---
allowed-tools: Bash, Read, Write, LS, Task
---

# 史诗启动（工作树）

启动并行代理在共享工作树中处理史诗任务。

## 使用方法
```
/pm:epic-start <epic_name>
```

## 快速检查

1. **验证史诗存在：**
   ```bash
   test -f .claude/epics/$ARGUMENTS/epic.md || echo "❌ 史诗未找到。运行：/pm:prd-parse $ARGUMENTS"
   ```

2. **检查 GitHub 同步：**
   查找史诗前置元数据中的 `github:` 字段。
   如果缺失："❌ 史诗未同步。首先运行：/pm:epic-sync $ARGUMENTS"

3. **检查工作树：**
   ```bash
   git worktree list | grep "epic-$ARGUMENTS"
   ```

## 指示

### 1. 创建或进入工作树

遵循 `/rules/worktree-operations.md`：

```bash
# 如果工作树不存在，创建它
if ! git worktree list | grep -q "epic-$ARGUMENTS"; then
  git checkout main
  git pull origin main
  git worktree add ../epic-$ARGUMENTS -b epic/$ARGUMENTS
  echo "✅ 已创建工作树：../epic-$ARGUMENTS"
else
  echo "✅ 使用现有工作树：../epic-$ARGUMENTS"
fi
```

### 2. 识别就绪问题

读取 `.claude/epics/$ARGUMENTS/` 中的所有任务文件：
- 解析前置元数据中的 `status`、`depends_on`、`parallel` 字段
- 如果需要检查 GitHub 问题状态
- 构建依赖图

分类问题：
- **就绪**：无未满足依赖，未开始
- **阻塞**：有未满足依赖
- **进行中**：正在进行中
- **完成**：已完成

### 3. 分析就绪问题

对于每个没有分析的就绪问题：
```bash
# 检查分析
if ! test -f .claude/epics/$ARGUMENTS/{issue}-analysis.md; then
  echo "正在分析问题 #{issue}..."
  # 运行分析（内联或通过任务工具）
fi
```

### 4. 启动并行代理

对于每个有分析的就绪问题：

```markdown
## 开始问题 #{issue}：{title}

正在读取分析...
发现 {count} 个并行流：
  - 流 A：{description} (Agent-{id})
  - 流 B：{description} (Agent-{id})

在工作树中启动代理：../epic-$ARGUMENTS/
```

使用任务工具启动每个流：
```yaml
Task:
  description: "问题 #{issue} 流 {X}"
  subagent_type: "{agent_type}"
  prompt: |
    在工作树中工作：../epic-$ARGUMENTS/
    问题：#{issue} - {title}
    流：{stream_name}

    您的范围：
    - 文件：{file_patterns}
    - 工作：{stream_description}

    从以下读取完整要求：
    - .claude/epics/$ARGUMENTS/{task_file}
    - .claude/epics/$ARGUMENTS/{issue}-analysis.md

    遵循 /rules/agent-coordination.md 中的协调规则

    使用消息格式频繁提交：
    "问题 #{issue}：{specific change}"

    在以下位置更新进度：
    .claude/epics/$ARGUMENTS/updates/{issue}/stream-{X}.md
```

### 5. 跟踪活动代理

创建/更新 `.claude/epics/$ARGUMENTS/execution-status.md`：

```markdown
---
started: {datetime}
worktree: ../epic-$ARGUMENTS
branch: epic/$ARGUMENTS
---

# 执行状态

## 活动代理
- Agent-1: 问题 #1234 流 A (数据库) - {time} 开始
- Agent-2: 问题 #1234 流 B (API) - {time} 开始
- Agent-3: 问题 #1235 流 A (UI) - {time} 开始

## 排队问题
- 问题 #1236 - 等待 #1234
- 问题 #1237 - 等待 #1235

## 已完成
- {尚未}
```

### 6. 监控和协调

设置监控：
```bash
echo "
代理启动成功！

监控进度：
  /pm:epic-status $ARGUMENTS

查看工作树更改：
  cd ../epic-$ARGUMENTS && git status

停止所有代理：
  /pm:epic-stop $ARGUMENTS

完成后合并：
  /pm:epic-merge $ARGUMENTS
"
```

### 7. 处理依赖关系

当代理完成流时：
- 检查是否有任何阻塞问题现在就绪
- 为新就绪的工作启动新代理
- 更新 execution-status.md

## 输出格式

```
🚀 史诗执行已开始：$ARGUMENTS

工作树：../epic-$ARGUMENTS
分支：epic/$ARGUMENTS

在 {issue_count} 个问题上启动 {total} 个代理：

问题 #1234：数据库架构
  ├─ 流 A：架构创建 (Agent-1) ✓ 已开始
  └─ 流 B：迁移 (Agent-2) ✓ 已开始

问题 #1235：API 端点
  ├─ 流 A：用户端点 (Agent-3) ✓ 已开始
  ├─ 流 B：帖子端点 (Agent-4) ✓ 已开始
  └─ 流 C：测试 (Agent-5) ⏸ 等待 A & B

阻塞问题 (2)：
  - #1236：UI 组件（依赖 #1234）
  - #1237：集成（依赖 #1235、#1236）

使用以下监控：/pm:epic-status $ARGUMENTS
```

## 错误处理

如果代理启动失败：
```
❌ 启动 Agent-{id} 失败
  问题：#{issue}
  流：{stream}
  错误：{reason}

继续其他代理？(是/否)
```

如果工作树创建失败：
```
❌ 无法创建工作树
  {git 错误消息}

尝试：git worktree prune
或：使用以下检查现有工作树：git worktree list
```

## 重要说明

- 遵循 `/rules/worktree-operations.md` 进行 git 操作
- 遵循 `/rules/agent-coordination.md` 进行并行工作
- 代理在同一工作树中工作（不是单独的）
- 最大并行代理应该合理（例如 5-10）
- 如果启动许多代理，监控系统资源