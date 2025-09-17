# !/bin/bash
# Check if PRD directory exists
if [ ! -d ".claude/prds" ]; then
  echo "📁 未找到 PRD 目录。使用以下命令创建您的第一个 PRD：/pm:prd-new <feature-name>"
  exit 0
fi

# Check for PRD files
if ! ls .claude/prds/*.md >/dev/null 2>&1; then
  echo "📁 未找到 PRD。使用以下命令创建您的第一个 PRD：/pm:prd-new <feature-name>"
  exit 0
fi

# Initialize counters
backlog_count=0
in_progress_count=0
implemented_count=0
total_count=0

echo "正在获取 PRD..."
echo ""
echo ""


echo "📋 PRD 列表"
echo "==========="
echo ""

# Display by status groups
echo "🔍 积压中的 PRD："
for file in .claude/prds/*.md; do
  [ -f "$file" ] || continue
  status=$(grep "^status:" "$file" | head -1 | sed 's/^status: *//')
  if [ "$status" = "backlog" ] || [ "$status" = "draft" ] || [ -z "$status" ]; then
    name=$(grep "^name:" "$file" | head -1 | sed 's/^name: *//')
    desc=$(grep "^description:" "$file" | head -1 | sed 's/^description: *//')
    [ -z "$name" ] && name=$(basename "$file" .md)
    [ -z "$desc" ] && desc="无描述"
    # echo "   📋 $name - $desc"
    echo "   📋 $file - $desc"
    ((backlog_count++))
  fi
  ((total_count++))
done
[ $backlog_count -eq 0 ] && echo "   （无）"

echo ""
echo "🔄 进行中的 PRD："
for file in .claude/prds/*.md; do
  [ -f "$file" ] || continue
  status=$(grep "^status:" "$file" | head -1 | sed 's/^status: *//')
  if [ "$status" = "in-progress" ] || [ "$status" = "active" ]; then
    name=$(grep "^name:" "$file" | head -1 | sed 's/^name: *//')
    desc=$(grep "^description:" "$file" | head -1 | sed 's/^description: *//')
    [ -z "$name" ] && name=$(basename "$file" .md)
    [ -z "$desc" ] && desc="无描述"
    # echo "   📋 $name - $desc"
    echo "   📋 $file - $desc"
    ((in_progress_count++))
  fi
done
[ $in_progress_count -eq 0 ] && echo "   （无）"

echo ""
echo "✅ 已实现的 PRD："
for file in .claude/prds/*.md; do
  [ -f "$file" ] || continue
  status=$(grep "^status:" "$file" | head -1 | sed 's/^status: *//')
  if [ "$status" = "implemented" ] || [ "$status" = "completed" ] || [ "$status" = "done" ]; then
    name=$(grep "^name:" "$file" | head -1 | sed 's/^name: *//')
    desc=$(grep "^description:" "$file" | head -1 | sed 's/^description: *//')
    [ -z "$name" ] && name=$(basename "$file" .md)
    [ -z "$desc" ] && desc="无描述"
    # echo "   📋 $name - $desc"
    echo "   📋 $file - $desc"
    ((implemented_count++))
  fi
done
[ $implemented_count -eq 0 ] && echo "   （无）"

# Display summary
echo ""
echo "📊 PRD 摘要"
echo "   PRD 总数：$total_count"
echo "   积压中：$backlog_count"
echo "   进行中：$in_progress_count"
echo "   已实现：$implemented_count"

exit 0
