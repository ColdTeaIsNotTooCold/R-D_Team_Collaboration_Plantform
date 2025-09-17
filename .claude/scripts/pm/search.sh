#!/bin/bash

query="$1"

if [ -z "$query" ]; then
  echo "❌ 请提供搜索查询"
  echo "用法：/pm:search <查询>"
  exit 1
fi

echo "正在搜索 '$query'..."
echo ""
echo ""

echo "🔍 '$query' 的搜索结果："
echo "================================"
echo ""

# Search in PRDs
if [ -d ".claude/prds" ]; then
  echo "📄 PRD："
  results=$(grep -l -i "$query" .claude/prds/*.md 2>/dev/null)
  if [ -n "$results" ]; then
    for file in $results; do
      name=$(basename "$file" .md)
      matches=$(grep -c -i "$query" "$file")
      echo "  • $name ($matches 个匹配项)"
    done
  else
    echo "  无匹配结果"
  fi
  echo ""
fi

# Search in Epics
if [ -d ".claude/epics" ]; then
  echo "📚 史诗："
  results=$(find .claude/epics -name "epic.md" -exec grep -l -i "$query" {} \; 2>/dev/null)
  if [ -n "$results" ]; then
    for file in $results; do
      epic_name=$(basename $(dirname "$file"))
      matches=$(grep -c -i "$query" "$file")
      echo "  • $epic_name ($matches 个匹配项)"
    done
  else
    echo "  无匹配结果"
  fi
  echo ""
fi

# Search in Tasks
if [ -d ".claude/epics" ]; then
  echo "📝 任务："
  results=$(find .claude/epics -name "[0-9]*.md" -exec grep -l -i "$query" {} \; 2>/dev/null | head -10)
  if [ -n "$results" ]; then
    for file in $results; do
      epic_name=$(basename $(dirname "$file"))
      task_num=$(basename "$file" .md)
      echo "  • $epic_name 中的任务 #$task_num"
    done
  else
    echo "  无匹配结果"
  fi
fi

# Summary
total=$(find .claude -name "*.md" -exec grep -l -i "$query" {} \; 2>/dev/null | wc -l)
echo ""
echo "📊 总计匹配文件：$total"

exit 0
