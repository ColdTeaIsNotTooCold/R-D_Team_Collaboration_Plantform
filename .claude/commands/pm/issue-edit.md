---
allowed-tools: Bash, Read, Write, LS
---

# 问题编辑

在本地和 GitHub 上编辑问题详情。

## 使用方法
```
/pm:issue-edit <issue_number>
```

## 指示

### 1. 获取当前问题状态

```bash
# 从 GitHub 获取
gh issue view $ARGUMENTS --json title,body,labels

# 查找本地任务文件
# 搜索包含 github:.*issues/$ARGUMENTS 的文件
```

### 2. 交互式编辑

询问用户要编辑什么：
- 标题
- 描述/正文
- 标签
- 验收标准（仅本地）
- 优先级/规模（仅本地）

### 3. 更新本地文件

获取当前日期时间：`date -u +"%Y-%m-%dT%H:%M:%SZ"`

使用更改更新任务文件：
- 如果标题更改，更新前置元数据 `name`
- 如果描述更改，更新正文内容
- 用当前日期时间更新 `updated` 字段

### 4. 更新 GitHub

如果标题更改：
```bash
gh issue edit $ARGUMENTS --title "{new_title}"
```

如果正文更改：
```bash
gh issue edit $ARGUMENTS --body-file {updated_task_file}
```

如果标签更改：
```bash
gh issue edit $ARGUMENTS --add-label "{new_labels}"
gh issue edit $ARGUMENTS --remove-label "{removed_labels}"
```

### 5. 输出

```
✅ 已更新问题 #$ARGUMENTS
  更改：
    {made_changes_list}
  
已同步到 GitHub：✅
```

## 重要说明

始终先更新本地，然后更新 GitHub。
保留未编辑的前置元数据字段。
遵循 `/rules/frontmatter-operations.md`。