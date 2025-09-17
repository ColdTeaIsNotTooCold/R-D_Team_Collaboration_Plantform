---
allowed-tools: Bash, Read, Write, LS
---

# 史诗关闭

当所有任务完成时，将史诗标记为完成。

## 使用方法
```
/pm:epic-close <epic_name>
```

## 指示

### 1. 验证所有任务完成

检查 `.claude/epics/$ARGUMENTS/` 中的所有任务文件：
- 验证所有文件的前置元数据中都有 `status: closed`
- 如果发现任何开放任务："❌ 无法关闭史诗。仍有开放任务：{list}"

### 2. 更新史诗状态

获取当前日期时间：`date -u +"%Y-%m-%dT%H:%M:%SZ"`

更新 epic.md 前置元数据：
```yaml
status: completed
progress: 100%
updated: {current_datetime}
completed: {current_datetime}
```

### 3. 更新 PRD 状态

如果史诗引用了 PRD，将其状态更新为 "complete"。

### 4. 在 GitHub 上关闭史诗

如果史诗有 GitHub 问题：
```bash
gh issue close {epic_issue_number} --comment "✅ 史诗已完成 - 所有任务完成"
```

### 5. 归档选项

询问用户："归档已完成的史诗？(是/否)"

如果是：
- 将史诗目录移动到 `.claude/epics/.archived/{epic_name}/`
- 创建包含完成日期的归档摘要

### 6. 输出

```
✅ 史诗已关闭：$ARGUMENTS
  已完成任务：{count}
  持续时间：{days_from_created_to_completed}
  
{如果已归档}：已归档到 .claude/epics/.archived/

下一个史诗：运行 /pm:next 查看优先级工作
```

## 重要说明

只关闭所有任务都完成的史诗。
归档时保留所有数据。
更新相关的 PRD 状态。