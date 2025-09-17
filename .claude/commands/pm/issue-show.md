---
allowed-tools: Bash, Read, LS
---

# 问题显示

显示问题和子问题的详细信息。

## 使用方法
```
/pm:issue-show <issue_number>
```

## 指示

您正在显示 GitHub 问题及相关子问题的综合信息：**问题 #$ARGUMENTS**

### 1. 获取问题数据
- 使用 `gh issue view #$ARGUMENTS` 获取 GitHub 问题详情
- 查找本地任务文件：首先检查 `.claude/epics/*/$ARGUMENTS.md`（新命名）
- 如果未找到，搜索前置元数据中包含 `github:.*issues/$ARGUMENTS` 的文件（旧命名）
- 检查相关问题和子任务

### 2. 问题概览
显示问题标题：
```
🎫 问题 #$ARGUMENTS：{Issue Title}
   状态：{open/closed}
   标签：{labels}
   负责人：{assignee}
   创建时间：{creation_date}
   更新时间：{last_update}
   
📝 描述：
{issue_description}
```

### 3. 本地文件映射
如果本地任务文件存在：
```
📁 本地文件：
   任务文件：.claude/epics/{epic_name}/{task_file}
   更新：.claude/epics/{epic_name}/updates/$ARGUMENTS/
   最后本地更新：{timestamp}
```

### 4. 子问题和依赖关系
显示相关问题：
```
🔗 相关问题：
   父级史诗：#{epic_issue_number}
   依赖项：#{dep1}，#{dep2}
   阻塞项：#{blocked1}，#{blocked2}
   子任务：#{sub1}，#{sub2}
```

### 5. 最近活动
显示最近评论和更新：
```
💬 最近活动：
   {timestamp} - {author}：{comment_preview}
   {timestamp} - {author}：{comment_preview}
   
   查看完整对话：gh issue view #$ARGUMENTS --comments
```

### 6. 进度跟踪
如果任务文件存在，显示进度：
```
✅ 验收标准：
   ✅ 标准 1（已完成）
   🔄 标准 2（进行中）
   ⏸️ 标准 3（已阻塞）
   □ 标准 4（未开始）
```

### 7. 快速操作
```
🚀 快速操作：
   开始工作：/pm:issue-start $ARGUMENTS
   同步更新：/pm:issue-sync $ARGUMENTS
   添加评论：gh issue comment #$ARGUMENTS --body "您的评论"
   在浏览器中查看：gh issue view #$ARGUMENTS --web
```

### 8. 错误处理
- 优雅处理无效的问题编号
- 检查网络/身份验证问题
- 提供有用的错误消息和替代方案

为问题 #$ARGUMENTS 提供全面的问题信息，帮助开发人员理解上下文和当前状态。
