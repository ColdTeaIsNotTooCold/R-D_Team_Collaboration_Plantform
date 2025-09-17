---
allowed-tools: Read, LS
---

# 史诗一键处理

将史诗分解为任务并在一次操作中同步到 GitHub。

## 使用方法
```
/pm:epic-oneshot <feature_name>
```

## 指示

### 1. 验证先决条件

检查史诗存在且尚未处理：
```bash
# 史诗必须存在
test -f .claude/epics/$ARGUMENTS/epic.md || echo "❌ 史诗未找到。运行：/pm:prd-parse $ARGUMENTS"

# 检查现有任务
if ls .claude/epics/$ARGUMENTS/[0-9]*.md 2>/dev/null | grep -q .; then
  echo "⚠️ 任务已存在。这将创建重复项。"
  echo "删除现有任务或改用 /pm:epic-sync。"
  exit 1
fi

# 检查是否已同步
if grep -q "github:" .claude/epics/$ARGUMENTS/epic.md; then
  echo "⚠️ 史诗已同步到 GitHub。"
  echo "使用 /pm:epic-sync 进行更新。"
  exit 1
fi
```

### 2. 执行分解

只需运行分解命令：
```
正在运行：/pm:epic-decompose $ARGUMENTS
```

这将：
- 读取史诗
- 创建任务文件（如果合适则使用并行代理）
- 用任务摘要更新史诗

### 3. 执行同步

立即跟进同步：
```
正在运行：/pm:epic-sync $ARGUMENTS
```

这将：
- 在 GitHub 上创建史诗问题
- 创建子问题（如果合适则使用并行代理）
- 将任务文件重命名为问题 ID
- 创建工作树

### 4. 输出

```
🚀 史诗一键处理完成：$ARGUMENTS

步骤 1：分解 ✓
  - 已创建任务：{count}
  
步骤 2：GitHub 同步 ✓
  - 史诗：#{number}
  - 已创建子问题：{count}
  - 工作树：../epic-$ARGUMENTS

准备开发！
  开始工作：/pm:epic-start $ARGUMENTS
  或单个任务：/pm:issue-start {task_number}
```

## 重要说明

这只是一个便利包装器，运行：
1. `/pm:epic-decompose` 
2. `/pm:epic-sync`

两个命令都处理自己的错误检查、并行执行和验证。此命令只是按顺序编排它们。

当您确信史诗已准备好并希望一步从史诗到 GitHub 问题时使用此命令。