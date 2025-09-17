---
allowed-tools: Bash, Read, Write, LS
---

# 问题重开

重新打开已关闭的问题。

## 使用方法
```
/pm:issue-reopen <issue_number> [reason]
```

## 指示

### 1. 查找本地任务文件

搜索包含 `github:.*issues/$ARGUMENTS` 前置元数据的任务文件。
如果未找到："❌ 问题 #$ARGUMENTS 没有本地任务"

### 2. 更新本地状态

获取当前日期时间：`date -u +"%Y-%m-%dT%H:%M:%SZ"`

更新任务文件前置元数据：
```yaml
status: open
updated: {current_datetime}
```

### 3. 重置进度

如果进度文件存在：
- 保留原始开始日期
- 重置完成度为前一个值或 0%
- 添加重开原因说明

### 4. 在 GitHub 上重开

```bash
# 添加评论重开
echo "🔄 重开问题

原因：$ARGUMENTS

---
重开时间：{timestamp}" | gh issue comment $ARGUMENTS --body-file -

# 重开问题
gh issue reopen $ARGUMENTS
```

### 5. 更新史诗进度

重新计算史诗进度，此任务现在重新打开。

### 6. 输出

```
🔄 已重开问题 #$ARGUMENTS
  原因：{reason_if_provided}
  史诗进度：{updated_progress}%
  
开始工作：/pm:issue-start $ARGUMENTS
```

## 重要说明

保留进度文件中的工作历史。
不要删除之前的进度，只需重置状态。