---
allowed-tools: Bash, Read, Write
---

# 史诗合并

将已完成史诗从工作树合并回主分支。

## 使用方法
```
/pm:epic-merge <epic_name>
```

## 快速检查

1. **验证工作树存在：**
   ```bash
   git worktree list | grep "epic-$ARGUMENTS" || echo "❌ 史诗没有工作树：$ARGUMENTS"
   ```

2. **检查活动代理：**
   读取 `.claude/epics/$ARGUMENTS/execution-status.md`
   如果存在活动代理："⚠️ 检测到活动代理。首先停止它们：/pm:epic-stop $ARGUMENTS"

## 指示

### 1. 合并前验证

导航到工作树并检查状态：
```bash
cd ../epic-$ARGUMENTS

# 检查未提交的更改
if [[ $(git status --porcelain) ]]; then
  echo "⚠️ 工作树中有未提交的更改："
  git status --short
  echo "合并前提交或存储更改"
  exit 1
fi

# 检查分支状态
git fetch origin
git status -sb
```

### 2. 运行测试（可选但推荐）

```bash
# 查找测试命令
if [ -f package.json ]; then
  npm test || echo "⚠️ 测试失败。无论如何继续？(是/否)"
elif [ -f Makefile ]; then
  make test || echo "⚠️ 测试失败。无论如何继续？(是/否)"
fi
```

### 3. 更新史诗文档

获取当前日期时间：`date -u +"%Y-%m-%dT%H:%M:%SZ"`

更新 `.claude/epics/$ARGUMENTS/epic.md`：
- 将状态设置为"completed"
- 更新完成日期
- 添加最终摘要

### 4. 尝试合并

```bash
# 返回主仓库
cd {main-repo-path}

# 确保 main 是最新的
git checkout main
git pull origin main

# 尝试合并
echo "正在将 epic/$ARGUMENTS 合并到 main..."
git merge epic/$ARGUMENTS --no-ff -m "合并史诗：$ARGUMENTS

已完成功能：
$(cd .claude/epics/$ARGUMENTS && ls *.md | grep -E '^[0-9]+' | while read f; do
  echo "- $(grep '^name:' $f | cut -d: -f2)"
done)

关闭史诗 #$(grep 'github:' .claude/epics/$ARGUMENTS/epic.md | grep -oE '#[0-9]+')"
```

### 5. 处理合并冲突

如果合并失败并出现冲突：
```bash
# 检查冲突状态
git status

echo "
❌ 检测到合并冲突！

冲突文件：
$(git diff --name-only --diff-filter=U)

选项：
1. 手动解决：
   - 编辑冲突文件
   - git add {files}
   - git commit
   
2. 中止合并：
   git merge --abort
   
3. 获取帮助：
   /pm:epic-resolve $ARGUMENTS

工作树保留在：../epic-$ARGUMENTS
"
exit 1
```

### 6. 合并后清理

如果合并成功：
```bash
# 推送到远程
git push origin main

# 清理工作树
git worktree remove ../epic-$ARGUMENTS
echo "✅ 工作树已移除：../epic-$ARGUMENTS"

# 删除分支
git branch -d epic/$ARGUMENTS
git push origin --delete epic/$ARGUMENTS 2>/dev/null || true

# 在本地归档史诗
mkdir -p .claude/epics/archived/
mv .claude/epics/$ARGUMENTS .claude/epics/archived/
echo "✅ 史诗已归档：.claude/epics/archived/$ARGUMENTS"
```

### 7. 更新 GitHub 问题

关闭相关问题：
```bash
# 从史诗获取问题编号
epic_issue=$(grep 'github:' .claude/epics/archived/$ARGUMENTS/epic.md | grep -oE '[0-9]+$')

# 关闭史诗问题
gh issue close $epic_issue -c "史诗已完成并合并到 main"

# 关闭任务问题
for task_file in .claude/epics/archived/$ARGUMENTS/[0-9]*.md; do
  issue_num=$(grep 'github:' $task_file | grep -oE '[0-9]+$')
  if [ ! -z "$issue_num" ]; then
    gh issue close $issue_num -c "在史诗合并中完成"
  fi
done
```

### 8. 最终输出

```
✅ 史诗成功合并：$ARGUMENTS

摘要：
  分支：epic/$ARGUMENTS → main
  合并的提交：{count}
  更改的文件：{count}
  关闭的问题：{count}
  
清理完成：
  ✓ 工作树已移除
  ✓ 分支已删除
  ✓ 史诗已归档
  ✓ GitHub 问题已关闭
  
下一步：
  - 如需要则部署更改
  - 开始新史诗：/pm:prd-new {feature}
  - 查看已完成的工作：git log --oneline -20
```

## 冲突解决帮助

如果需要解决冲突：
```
史诗分支与 main 有冲突。

这通常发生在：
- main 自史诗开始以来已更改
- 多个史诗修改了相同文件
- 依赖项已更新

解决方法：
1. 打开冲突文件
2. 查找 <<<<<<< 标记
3. 选择正确版本或合并
4. 删除冲突标记
5. git add {已解决的文件}
6. git commit
7. git push

或中止并稍后重试：
  git merge --abort
```

## 重要说明

- 始终首先检查未提交的更改
- 尽可能在合并前运行测试
- 使用 --no-ff 保留史诗历史
- 归档史诗数据而不是删除
- 关闭 GitHub 问题以保持同步