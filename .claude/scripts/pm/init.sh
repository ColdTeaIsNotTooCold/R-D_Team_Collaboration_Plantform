#!/bin/bash

echo "正在初始化..."
echo ""
echo ""

echo " ██████╗ ██████╗██████╗ ███╗   ███╗"
echo "██╔════╝██╔════╝██╔══██╗████╗ ████║"
echo "██║     ██║     ██████╔╝██╔████╔██║"
echo "╚██████╗╚██████╗██║     ██║ ╚═╝ ██║"
echo " ╚═════╝ ╚═════╝╚═╝     ╚═╝     ╚═╝"


echo ""
echo ""
echo "======================================"
echo "🚀 正在初始化 Claude Code 项目管理系统"
echo "======================================"
echo ""

# Check for required tools
echo "🔍 正在检查依赖..."

# Check gh CLI
if command -v gh &> /dev/null; then
  echo "  ✅ GitHub CLI (gh) 已安装"
else
  echo "  ❌ 未找到 GitHub CLI (gh)"
  echo ""
  echo "  正在安装 gh..."
  if command -v brew &> /dev/null; then
    brew install gh
  elif command -v apt-get &> /dev/null; then
    sudo apt-get update && sudo apt-get install gh
  else
    echo "  请手动安装 GitHub CLI：https://cli.github.com/"
    exit 1
  fi
fi

# Check gh auth status
echo ""
echo "🔐 正在检查 GitHub 身份验证..."
if gh auth status &> /dev/null; then
  echo "  ✅ GitHub 已验证身份"
else
  echo "  ⚠️ GitHub 未验证身份"
  echo "  正在运行：gh auth login"
  gh auth login
fi

# Check for gh-sub-issue extension
echo ""
echo "📦 正在检查 gh 扩展..."
if gh extension list | grep -q "yahsan2/gh-sub-issue"; then
  echo "  ✅ gh-sub-issue 扩展已安装"
else
  echo "  📥 正在安装 gh-sub-issue 扩展..."
  gh extension install yahsan2/gh-sub-issue
fi

# Create directory structure
echo ""
echo "📁 正在创建目录结构..."
mkdir -p .claude/prds
mkdir -p .claude/epics
mkdir -p .claude/rules
mkdir -p .claude/agents
mkdir -p .claude/scripts/pm
echo "  ✅ 目录已创建"

# Copy scripts if in main repo
if [ -d "scripts/pm" ] && [ ! "$(pwd)" = *"/.claude"* ]; then
  echo ""
  echo "📝 正在复制 PM 脚本..."
  cp -r scripts/pm/* .claude/scripts/pm/
  chmod +x .claude/scripts/pm/*.sh
  echo "  ✅ 脚本已复制并设为可执行"
fi

# Check for git
echo ""
echo "🔗 正在检查 Git 配置..."
if git rev-parse --git-dir > /dev/null 2>&1; then
  echo "  ✅ 检测到 Git 仓库"

  # Check remote
  if git remote -v | grep -q origin; then
    remote_url=$(git remote get-url origin)
    echo "  ✅ 远程仓库已配置：$remote_url"
    
    # Check if remote is the CCPM template repository
    if [[ "$remote_url" == *"automazeio/ccpm"* ]] || [[ "$remote_url" == *"automazeio/ccpm.git"* ]]; then
      echo ""
      echo "  ⚠️ 警告：您的远程仓库指向 CCPM 模板仓库！"
      echo "  这意味着您创建的问题将发送到模板仓库，而不是您的项目。"
      echo ""
      echo "  要解决此问题："
      echo "  1. Fork 该仓库或在 GitHub 上创建您自己的仓库"
      echo "  2. 更新您的远程仓库："
      echo "     git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
      echo ""
    fi
  else
    echo "  ⚠️ 未配置远程仓库"
    echo "  添加方式：git remote add origin <url>"
  fi
else
  echo "  ⚠️ 不是 git 仓库"
  echo "  初始化方式：git init"
fi

# Create CLAUDE.md if it doesn't exist
if [ ! -f "CLAUDE.md" ]; then
  echo ""
  echo "📄 正在创建 CLAUDE.md..."
  cat > CLAUDE.md << 'EOF'
# CLAUDE.md

> Think carefully and implement the most concise solution that changes as little code as possible.

## Project-Specific Instructions

Add your project-specific instructions here.

## Testing

Always run tests before committing:
- `npm test` or equivalent for your stack

## Code Style

Follow existing patterns in the codebase.
EOF
  echo "  ✅ CLAUDE.md 已创建"
fi

# Summary
echo ""
echo "✅ 初始化完成！"
echo "=========================="
echo ""
echo "📊 系统状态："
gh --version | head -1
echo "  扩展：$(gh extension list | wc -l) 个已安装"
echo "  身份验证：$(gh auth status 2>&1 | grep -o 'Logged in to [^ ]*' || echo '未验证身份')"
echo ""
echo "🎯 下一步："
echo "  1. 创建您的第一个 PRD：/pm:prd-new <feature-name>"
echo "  2. 查看帮助：/pm:help"
echo "  3. 检查状态：/pm:status"
echo ""
echo "📚 文档：README.md"

exit 0
