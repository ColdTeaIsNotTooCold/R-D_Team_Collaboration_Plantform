#!/bin/bash

echo "正在验证 PM 系统..."
echo ""
echo ""

echo "🔍 正在验证 PM 系统"
echo "======================="
echo ""

errors=0
warnings=0

# Check directory structure
echo "📁 目录结构："
[ -d ".claude" ] && echo "  ✅ .claude 目录存在" || { echo "  ❌ .claude 目录缺失"; ((errors++)); }
[ -d ".claude/prds" ] && echo "  ✅ PRDs 目录存在" || echo "  ⚠️ PRDs 目录缺失"
[ -d ".claude/epics" ] && echo "  ✅ Epics 目录存在" || echo "  ⚠️ Epics 目录缺失"
[ -d ".claude/rules" ] && echo "  ✅ Rules 目录存在" || echo "  ⚠️ Rules 目录缺失"
echo ""

# Check for orphaned files
echo "🗂️ 数据完整性："

# Check epics have epic.md files
for epic_dir in .claude/epics/*/; do
  [ -d "$epic_dir" ] || continue
  if [ ! -f "$epic_dir/epic.md" ]; then
    echo "  ⚠️ $(basename "$epic_dir") 中缺少 epic.md"
    ((warnings++))
  fi
done

# Check for tasks without epics
orphaned=$(find .claude -name "[0-9]*.md" -not -path ".claude/epics/*/*" 2>/dev/null | wc -l)
[ $orphaned -gt 0 ] && echo "  ⚠️ 发现 $orphaned 个孤立的任务文件" && ((warnings++))

# Check for broken references
echo ""
echo "🔗 引用检查："

for task_file in .claude/epics/*/[0-9]*.md; do
  [ -f "$task_file" ] || continue

  deps=$(grep "^depends_on:" "$task_file" | head -1 | sed 's/^depends_on: *\[//' | sed 's/\]//' | sed 's/,/ /g')
  if [ -n "$deps" ] && [ "$deps" != "depends_on:" ]; then
    epic_dir=$(dirname "$task_file")
    for dep in $deps; do
      if [ ! -f "$epic_dir/$dep.md" ]; then
        echo "  ⚠️ 任务 $(basename "$task_file" .md) 引用了缺失的任务：$dep"
        ((warnings++))
      fi
    done
  fi
done

[ $warnings -eq 0 ] && [ $errors -eq 0 ] && echo "  ✅ 所有引用均有效"

# Check frontmatter
echo ""
echo "📝 前置元数据验证："
invalid=0

for file in $(find .claude -name "*.md" -path "*/epics/*" -o -path "*/prds/*" 2>/dev/null); do
  if ! grep -q "^---" "$file"; then
    echo "  ⚠️ 缺少前置元数据：$(basename "$file")"
    ((invalid++))
  fi
done

[ $invalid -eq 0 ] && echo "  ✅ 所有文件都有前置元数据"

# Summary
echo ""
echo "📊 验证摘要："
echo "  错误：$errors"
echo "  警告：$warnings"
echo "  无效文件：$invalid"

if [ $errors -eq 0 ] && [ $warnings -eq 0 ] && [ $invalid -eq 0 ]; then
  echo ""
  echo "✅ 系统健康！"
else
  echo ""
  echo "💡 运行 /pm:clean 自动修复一些问题"
fi

exit 0
