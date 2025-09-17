---
allowed-tools: Bash, Read, Write, LS, Task
---

# 问题启动

基于工作流分析，使用并行代理开始处理 GitHub 问题。

## 使用方法
```
/pm:issue-start <issue_number>
```

## 快速检查

1. **获取问题详情：**
   ```bash
   gh issue view $ARGUMENTS --json state,title,labels,body
   ```
   如果失败："❌ 无法访问问题 #$ARGUMENTS。请检查编号或运行：gh auth login"

2. **查找本地任务文件：**
   - 首先检查 `.claude/epics/*/$ARGUMENTS.md` 是否存在（新命名）
   - 如果未找到，搜索前置元数据中包含 `github:.*issues/$ARGUMENTS` 的文件（旧命名）
   - 如果未找到："❌ 问题 #$ARGUMENTS 没有本地任务。此问题可能是在 PM 系统外创建的。"

3. **检查分析：**
   ```bash
   test -f .claude/epics/*/$ARGUMENTS-analysis.md || echo "❌ 未找到问题 #$ARGUMENTS 的分析
   
   请先运行：/pm:issue-analyze $ARGUMENTS
   或：/pm:issue-start $ARGUMENTS --analyze 同时执行两项操作"
   ```
   如果没有分析且没有 --analyze 标志，停止执行。

## 指示

### 1. 确保工作树存在

检查史诗工作树是否存在：
```bash
# 从任务文件中查找史诗名称
epic_name={extracted_from_path}

# 检查工作树
if ! git worktree list | grep -q "epic-$epic_name"; then
  echo "❌ 史诗没有工作树。运行：/pm:epic-start $epic_name"
  exit 1
fi
```

### 2. 读取分析

读取 `.claude/epics/{epic_name}/$ARGUMENTS-analysis.md`：
- 解析并行流
- 识别哪些可以立即开始
- 记录流之间的依赖关系

### 3. 设置进度跟踪

获取当前日期时间：`date -u +"%Y-%m-%dT%H:%M:%SZ"`

创建工作空间结构：
```bash
mkdir -p .claude/epics/{epic_name}/updates/$ARGUMENTS
```

用当前日期时间更新任务文件前置元数据 `updated` 字段。

### 4. 启动并行代理

对于每个可以立即开始的流：

创建 `.claude/epics/{epic_name}/updates/$ARGUMENTS/stream-{X}.md`：
```markdown
---
issue: $ARGUMENTS
stream: {stream_name}
agent: {agent_type}
started: {current_datetime}
status: in_progress
---

# 流 {X}：{stream_name}

## 范围
{stream_description}

## 文件
{file_patterns}

## 进度
- 开始实现
```

使用 Task 工具启动代理：
```yaml
Task:
  description: "问题 #$ARGUMENTS 流 {X}"
  subagent_type: "{agent_type}"
  prompt: |
    您正在史诗工作树中处理问题 #$ARGUMENTS。
    
    工作树位置：../epic-{epic_name}/
    您的流：{stream_name}
    
    您的范围：
    - 要修改的文件：{file_patterns}
    - 要完成的工作：{stream_description}
    
    要求：
    1. 从以下位置读取完整任务：.claude/epics/{epic_name}/{task_file}
    2. 只在您分配的文件中工作
    3. 频繁提交，格式为："问题 #$ARGUMENTS：{具体更改}"
    4. 在以下位置更新进度：.claude/epics/{epic_name}/updates/$ARGUMENTS/stream-{X}.md
    5. 遵循 /rules/agent-coordination.md 中的协调规则
    
    如果您需要修改范围外的文件：
    - 检查是否有另一个流拥有它们
    - 必要时等待
    - 使用协调说明更新您的进度文件
    
    完成您的工作流的工作，完成后标记为已完成。
```

### 5. GitHub 分配

```bash
# 分配给自己并标记为进行中
gh issue edit $ARGUMENTS --add-assignee @me --add-label "in-progress"
```

### 6. 输出

```
✅ 已开始问题 #$ARGUMENTS 的并行工作

史诗：{epic_name}
工作树：../epic-{epic_name}/

正在启动 {count} 个并行代理：
  流 A：{name}（代理-1）✅ 已启动
  流 B：{name}（代理-2）✅ 已启动
  流 C：{name} - 等待中（依赖 A）

进度跟踪：
  .claude/epics/{epic_name}/updates/$ARGUMENTS/

监控：/pm:epic-status {epic_name}
同步更新：/pm:issue-sync $ARGUMENTS
```

## 错误处理

如果任何步骤失败，明确报告：
- "❌ {失败原因}：{如何修复}"
- 继续可行的操作
- 永远不要留下部分状态

## 重要说明

遵循 `/rules/datetime.md` 进行时间戳。
保持简单 - 相信 GitHub 和文件系统能正常工作。