# 工作树操作

Git 工作树允许多个工作目录用于同一仓库，从而实现并行开发。

## 创建工作树

始终从干净的主分支创建工作树：
```bash
# 确保 main 是最新的
git checkout main
git pull origin main

# 为史诗创建工作树
git worktree add ../epic-{name} -b epic/{name}
```

工作树将作为同级目录创建，以保持干净的分离。

## 在工作树中工作

### 代理提交
- 代理直接提交到工作树
- 使用小型、专注的提交
- 提交消息格式：`Issue #{number}: {description}`
- 示例：`Issue #1234: 添加用户身份验证架构`

### 文件操作
```bash
# 工作目录是工作树
cd ../epic-{name}

# 正常的 git 操作都可以使用
git add {files}
git commit -m "Issue #{number}: {change}"

# 查看工作树状态
git status
```

## 在同一工作树中并行工作

如果多个代理处理不同的文件，可以在同一工作树中工作：
```bash
# 代理 A 处理 API
git add src/api/*
git commit -m "Issue #1234: 添加用户端点"

# 代理 B 处理 UI （无冲突！）
git add src/ui/*
git commit -m "Issue #1235: 添加仪表板组件"
```

## 合并工作树

当史诗完成时，合并回主分支：
```bash
# 从主仓库（不是工作树）
cd {main-repo}
git checkout main
git pull origin main

# 合并史诗分支
git merge epic/{name}

# 如果成功，清理
git worktree remove ../epic-{name}
git branch -d epic/{name}
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

## 工作树管理

### 列出活动工作树
```bash
git worktree list
```

### 删除过时工作树
```bash
# 如果工作树目录被删除
git worktree prune

# 强制删除工作树
git worktree remove --force ../epic-{name}
```

### 检查工作树状态
```bash
# 从主仓库
cd ../epic-{name} && git status && cd -
```

## 最佳实践

1. **每个史诗一个工作树** - 不是每个问题
2. **创建前清理** - 始终从更新的 main 开始
3. **频繁提交** - 小型提交更容易合并
4. **合并后删除** - 不要留下过时的工作树
5. **使用描述性分支名** - `epic/feature-name` 而不是 `feature`

## 常见问题

### 工作树已存在
```bash
# 先删除旧工作树
git worktree remove ../epic-{name}
# 然后创建新的
```

### 分支已存在
```bash
# 删除旧分支
git branch -D epic/{name}
# 或使用现有分支
git worktree add ../epic-{name} epic/{name}
```

### 无法删除工作树
```bash
# 强制删除
git worktree remove --force ../epic-{name}
# 清理引用
git worktree prune
```