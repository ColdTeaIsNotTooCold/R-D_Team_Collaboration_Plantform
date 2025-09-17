---
allowed-tools: Bash, Read, Write, LS
---

# 问题关闭

将问题标记为完成并在 GitHub 上关闭。

## 使用方法
```
/pm:issue-close <issue_number> [完成说明]
```

## 指示

### 1. 查找本地任务文件

首先检查 `.claude/epics/*/$ARGUMENTS.md` 是否存在（新命名）。
如果未找到，搜索前置元数据中包含 `github:.*issues/$ARGUMENTS` 的任务文件（旧命名）。
如果未找到："❌ 问题 #$ARGUMENTS 没有本地任务"

### 2. 更新本地状态

获取当前日期时间：`date -u +"%Y-%m-%dT%H:%M:%SZ"`

更新任务文件前置元数据：
```yaml
status: closed
updated: {current_datetime}
```

### 3. 更新进度文件

如果 `.claude/epics/{epic}/updates/$ARGUMENTS/progress.md` 存在进度文件：
- 设置完成度：100%
- 添加带有时间戳的完成说明
- 用当前日期时间更新 last_sync

### 4. 在 GitHub 上关闭

添加完成说明并关闭：
```bash
# 添加最终说明
echo "✅ 任务已完成

$ARGUMENTS

---
关闭时间：{timestamp}" | gh issue comment $ARGUMENTS --body-file -

# 关闭问题
gh issue close $ARGUMENTS
```

### 5. 更新 GitHub 上的史诗任务列表

勾选史诗问题中的任务复选框：

```bash
# 从本地任务文件路径获取史诗名称
epic_name={extract_from_path}

# 从 epic.md 获取史诗问题编号
epic_issue=$(grep 'github:' .claude/epics/$epic_name/epic.md | grep -oE '[0-9]+$')

if [ ! -z "$epic_issue" ]; then
  # 获取当前史诗正文
  gh issue view $epic_issue --json body -q .body > /tmp/epic-body.md
  
  # 勾选此任务
  sed -i "s/- \[ \] #$ARGUMENTS/- [x] #$ARGUMENTS/" /tmp/epic-body.md
  
  # 更新史诗问题
  gh issue edit $epic_issue --body-file /tmp/epic-body.md
  
  echo "✓ 已在 GitHub 上更新史诗进度"
fi
```

### 6. 更新史诗进度

- 统计史诗中的总任务数
- 统计已关闭任务数
- 计算新进度百分比
- 更新 epic.md 前置元数据进度字段

### 7. 输出

```
✅ 已关闭问题 #$ARGUMENTS
  本地：任务标记为已完成
  GitHub：问题已关闭且史诗已更新
  史诗进度：{new_progress}%（{closed}/{total} 任务已完成）
  
下一步：运行 /pm:next 获取下一个优先任务
```

## 重要说明

遵循 `/rules/frontmatter-operations.md` 进行更新。
遵循 `/rules/github-operations.md` 进行 GitHub 命令。
始终在 GitHub 之前同步本地状态。