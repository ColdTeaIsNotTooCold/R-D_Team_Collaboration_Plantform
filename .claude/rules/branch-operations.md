# 分支操作

Git 分支允许多个开发者在同一仓库中进行隔离更改的开发，从而实现并行开发。

## 创建分支

始终从干净的主分支创建分支：
```bash
# 确保 main 是最新的
git checkout main
git pull origin main

# 为史诗创建分支
git checkout -b epic/{name}
git push -u origin epic/{name}
```

分支将被创建并推送到远程仓库，并设置上游跟踪。

## 在分支中工作

### 代理提交
- 代理直接提交到分支
- 使用小型、专注的提交
- 提交消息格式：`Issue #{number}: {description}`
- 示例：`Issue #1234: 添加用户身份验证架构`

### 文件操作
```bash
# 工作目录是当前目录
# （不需要像工作树那样更改目录）

# 正常的 git 操作都可以使用
git add {files}
git commit -m "Issue #{number}: {change}"

# 查看分支状态
git status
git log --oneline -5
```

## 在同一分支中并行工作

如果多个代理协调文件访问，可以在同一分支中工作：
```bash
# 代理 A 处理 API
git add src/api/*
git commit -m "Issue #1234: 添加用户端点"

# 代理 B 处理 UI （协调以避免冲突！）
git pull origin epic/{name}  # 获取最新更改
git add src/ui/*
git commit -m "Issue #1235: 添加仪表板组件"
```

## 合并分支

当史诗完成时，合并回主分支：
```bash
# 从主仓库
git checkout main
git pull origin main

# 合并史诗分支
git merge epic/{name}

# 如果成功，清理
git branch -d epic/{name}
git push origin --delete epic/{name}
```

## 处理冲突

如果发生合并冲突：
```bash
# 将显示冲突
git status

# 人工解决冲突
# 然后继续合并
git add {resolved-files}
git commit
```

## 分支管理

### 列出活动分支
```bash
git branch -a
```

### 删除过时分支
```bash
# 删除本地分支
git branch -d epic/{name}

# 删除远程分支
git push origin --delete epic/{name}
```

### 检查分支状态
```bash
# 当前分支信息
git branch -v

# 与主分支比较
git log --oneline main..epic/{name}
```

## 最佳实践

1. **每个史诗一个分支** - 不是每个问题
2. **创建前清理** - 始终从更新的 main 开始
3. **频繁提交** - 小型提交更容易合并
4. **推送前拉取** - 获取最新更改以避免冲突
5. **使用描述性分支名** - `epic/feature-name` 而不是 `feature`

## 常见问题

### 分支已存在
```bash
# 先删除旧分支
git branch -D epic/{name}
git push origin --delete epic/{name}
# 然后创建新分支
```

### 无法推送分支
```bash
# 检查分支是否在远程存在
git ls-remote origin epic/{name}

# 使用上游推送
git push -u origin epic/{name}
```

### 拉取时合并冲突
```bash
# 如果需要，暂存更改
git stash

# 拉取并变基
git pull --rebase origin epic/{name}

# 恢复更改
git stash pop
```
