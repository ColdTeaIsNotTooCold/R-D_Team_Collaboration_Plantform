---
allowed-tools: Bash, Read, Write, LS
---

# 问题同步

将本地更新作为 GitHub 问题评论推送，实现透明的审计跟踪。

## 使用方法
```
/pm:issue-sync <issue_number>
```

## 必需规则

**重要：** 执行此命令前，请阅读并遵循：
- `.claude/rules/datetime.md` - 用于获取真实当前日期/时间

## 预检查清单

在继续之前，完成这些验证步骤。
不要用预检查进度打扰用户（"我不会..."）。只需执行它们并继续。

0. **仓库保护检查：**
   遵循 `/rules/github-operations.md` - 检查远程源：
   ```bash
   remote_url=$(git remote get-url origin 2>/dev/null || echo "")
   if [[ "$remote_url" == *"automazeio/ccpm"* ]]; then
     echo "❌ 错误：无法同步到 CCPM 模板仓库！"
     echo "更新您的远程：git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
     exit 1
   fi
   ```

1. **GitHub 身份验证：**
   - 运行：`gh auth status`
   - 如果未身份验证，告诉用户："❌ GitHub CLI 未身份验证。运行：gh auth login"

2. **问题验证：**
   - 运行：`gh issue view $ARGUMENTS --json state`
   - 如果问题不存在，告诉用户："❌ 未找到问题 #$ARGUMENTS"
   - 如果问题已关闭且完成度 < 100%，警告："⚠️ 问题已关闭但工作未完成"

3. **本地更新检查：**
   - 检查 `.claude/epics/*/updates/$ARGUMENTS/` 目录是否存在
   - 如果未找到，告诉用户："❌ 未找到问题 #$ARGUMENTS 的本地更新。运行：/pm:issue-start $ARGUMENTS"
   - 检查 progress.md 是否存在
   - 如果不存在，告诉用户："❌ 未找到进度跟踪。使用以下命令初始化：/pm:issue-start $ARGUMENTS"

4. **检查上次同步：**
   - 从 progress.md 前置元数据读取 `last_sync`
   - 如果最近同步过（< 5 分钟），询问："⚠️ 最近已同步。仍要强制同步吗？（是/否）"
   - 计算自上次同步以来的新内容

5. **验证更改：**
   - 检查是否有实际更新需要同步
   - 如果没有更改，告诉用户："ℹ️ 自 {last_sync} 以来没有新更新需要同步"
   - 如果没有要同步的内容，优雅退出

## 指示

您正在将本地开发进度同步到 GitHub 作为问题评论，用于：**问题 #$ARGUMENTS**

### 1. 收集本地更新
收集问题的所有本地更新：
- 从 `.claude/epics/{epic_name}/updates/$ARGUMENTS/` 读取
- 检查新内容：
  - `progress.md` - 开发进度
  - `notes.md` - 技术说明和决策
  - `commits.md` - 最近提交和更改
  - 任何其他更新文件

### 2. 更新进度跟踪前置元数据
获取当前日期时间：`date -u +"%Y-%m-%dT%H:%M:%SZ"`

更新 progress.md 文件前置元数据：
```yaml
---
issue: $ARGUMENTS
started: [保留现有日期]
last_sync: [使用上面命令的真实日期时间]
completion: [计算百分比 0-100%]
---
```

### 3. 确定新内容
与上次同步比较以识别新内容：
- 查找同步时间戳标记
- 识别新部分或更新
- 只收集自上次同步以来的增量更改

### 4. 格式化更新评论
创建全面的更新评论：

```markdown
## 🔄 进度更新 - {current_date}

### ✅ 已完成工作
{list_completed_items}

### 🔄 进行中
{current_work_items}

### 📝 技术说明
{key_technical_decisions}

### 📊 验收标准状态
- ✅ {completed_criterion}
- 🔄 {in_progress_criterion}
- ⏸️ {blocked_criterion}
- □ {pending_criterion}

### 🚀 后续步骤
{planned_next_actions}

### ⚠️ 阻塞项
{any_current_blockers}

### 💻 最近提交
{commit_summaries}

---
*进度：{completion}% | 从本地更新同步于 {timestamp}*
```

### 5. 发布到 GitHub
使用 GitHub CLI 添加评论：
```bash
gh issue comment #$ARGUMENTS --body-file {temp_comment_file}
```

### 6. 更新本地任务文件
获取当前日期时间：`date -u +"%Y-%m-%dT%H:%M:%SZ"`

使用同步信息更新任务文件前置元数据：
```yaml
---
name: [任务标题]
status: open
created: [保留现有日期]
updated: [使用上面命令的真实日期时间]
github: https://github.com/{org}/{repo}/issues/$ARGUMENTS
---
```

### 7. 处理完成
如果任务完成，更新所有相关前置元数据：

**任务文件前置元数据**：
```yaml
---
name: [任务标题]
status: closed
created: [现有日期]
updated: [当前日期时间]
github: https://github.com/{org}/{repo}/issues/$ARGUMENTS
---
```

**进度文件前置元数据**：
```yaml
---
issue: $ARGUMENTS
started: [现有日期]
last_sync: [当前日期时间]
completion: 100%
---
```

**史诗进度更新**：根据已完成任务重新计算史诗进度并更新史诗前置元数据：
```yaml
---
name: [史诗名称]
status: in-progress
created: [现有日期]
progress: [基于已完成任务计算的百分比]%
prd: [现有路径]
github: [现有 URL]
---
```

### 8. 完成评论
如果任务完成：
```markdown
## ✅ 任务已完成 - {current_date}

### 🎯 所有验收标准已满足
- ✅ {criterion_1}
- ✅ {criterion_2}
- ✅ {criterion_3}

### 📦 交付物
- {deliverable_1}
- {deliverable_2}

### 🧪 测试
- 单元测试：✅ 通过
- 集成测试：✅ 通过
- 手动测试：✅ 完成

### 📚 文档
- 代码文档：✅ 已更新
- README 更新：✅ 完成

此任务已准备好审查，可以关闭。

---
*任务完成：100% | 同步于 {timestamp}*
```

### 9. 输出摘要
```
☁️ 已将更新同步到 GitHub 问题 #$ARGUMENTS

📝 更新摘要：
   进度项目：{progress_count}
   技术说明：{notes_count}
   引用的提交：{commit_count}

📊 当前状态：
   任务完成度：{task_completion}%
   史诗进度：{epic_progress}%
   已完成标准：{completed}/{total}

🔗 查看更新：gh issue view #$ARGUMENTS --comments
```

### 10. 前置元数据维护
- 始终使用当前时间戳更新任务文件前置元数据
- 在进度文件中跟踪完成百分比
- 任务完成时更新史诗进度
- 维护同步时间戳以进行审计跟踪

### 11. 增量同步检测

**防止重复评论：**
1. 每次同步后在本地文件中添加同步标记：
   ```markdown
   <!-- 已同步：2024-01-15T10:30:00Z -->
   ```
2. 只同步最后标记后添加的内容
3. 如果没有新内容，跳过同步并显示消息："自上次同步以来没有更新"

### 12. 评论大小管理

**处理 GitHub 的评论限制：**
- 最大评论大小：65,536 字符
- 如果更新超过限制：
  1. 分割为多个评论
  2. 或使用完整详细信息链接进行总结
  3. 警告用户："⚠️ 由于大小限制更新被截断。完整详细信息在本地文件中。"

### 13. 错误处理

**常见问题和恢复：**

1. **网络错误：**
   - 消息："❌ 发布评论失败：网络错误"
   - 解决方案："检查互联网连接并重试"
   - 保持本地更新完整以供重试

2. **速率限制：**
   - 消息："❌ GitHub 速率限制超出"
   - 解决方案："等待 {minutes} 分钟或使用不同的令牌"
   - 保存评论到本地以供以后同步

3. **权限被拒绝：**
   - 消息："❌ 无法评论问题（权限被拒绝）"
   - 解决方案："检查仓库访问权限"

4. **问题已锁定：**
   - 消息："⚠️ 问题评论已锁定"
   - 解决方案："联系仓库管理员解锁"

### 14. 史诗进度计算

更新史诗进度时：
1. 计算史诗目录中的总任务数
2. 计算前置元数据中 `status: closed` 的任务数
3. 计算：`progress = (closed_tasks / total_tasks) * 100`
4. 四舍五入到最接近的整数
5. 仅在百分比更改时更新史诗前置元数据

### 15. 同步后验证

成功同步后：
- [ ] 验证评论已发布到 GitHub
- [ ] 确认前置元数据已使用同步时间戳更新
- [ ] 如果任务完成，检查史诗进度已更新
- [ ] 验证本地文件中没有数据损坏

这为问题 #$ARGUMENTS 创建了开发进度的透明审计跟踪，利益相关者可以实时跟踪，同时在所有项目文件中保持准确的前置元数据。
