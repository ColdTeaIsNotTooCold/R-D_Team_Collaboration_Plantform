# GitHub 操作规则

所有命令中 GitHub CLI 操作的标准模式。

## 关键：仓库保护

**在任何创建/修改问题或 PR 的 GitHub 操作之前：**

```bash
# 检查远程 origin 是否是 CCPM 模板仓库
remote_url=$(git remote get-url origin 2>/dev/null || echo "")
if [[ "$remote_url" == *"automazeio/ccpm"* ]] || [[ "$remote_url" == *"automazeio/ccpm.git"* ]]; then
  echo "❌ 错误：您正在尝试与 CCPM 模板仓库同步！"
  echo ""
  echo "此仓库 (automazeio/ccpm) 是供他人使用的模板。"
  echo "您不应该在此处创建问题或 PR。"
  echo ""
  echo "解决方法："
  echo "1. 将此仓库 fork 到您自己的 GitHub 账户"
  echo "2. 更新您的远程 origin："
  echo "   git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
  echo ""
  echo "或者如果是新项目："
  echo "1. 在 GitHub 上创建新仓库"
  echo "2. 更新您的远程 origin："
  echo "   git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
  echo ""
  echo "当前远程仓库：$remote_url"
  exit 1
fi
```

此检查必须在所有执行以下操作的命令中执行：
- 创建问题 (`gh issue create`)
- 编辑问题 (`gh issue edit`)
- 评论问题 (`gh issue comment`)
- 创建 PR (`gh pr create`)
- 任何其他修改 GitHub 仓库的操作

## 身份验证

**不要预先检查身份验证。** 只需运行命令并处理失败：

```bash
gh {command} || echo "❌ GitHub CLI 失败。运行：gh auth login"
```

## 常见操作

### 获取问题详情
```bash
gh issue view {number} --json state,title,labels,body
```

### 创建问题
```bash
# 始终先检查远程 origin！
gh issue create --title "{title}" --body-file {file} --label "{labels}"
```

### 更新问题
```bash
# 始终先检查远程 origin！
gh issue edit {number} --add-label "{label}" --add-assignee @me
```

### 添加评论
```bash
# 始终先检查远程 origin！
gh issue comment {number} --body-file {file}
```

## 错误处理

如果任何 gh 命令失败：
1. 显示清晰错误："❌ GitHub 操作失败：{command}"
2. 建议修复："运行：gh auth login" 或检查问题编号
3. 不要自动重试

## 重要说明

- **始终**在对 GitHub 进行任何写操作之前检查远程 origin
- 相信 gh CLI 已安装并已身份验证
- 解析时使用 --json 获取结构化输出
- 保持操作原子化 - 每个操作一个 gh 命令
- 不要预先检查速率限制
