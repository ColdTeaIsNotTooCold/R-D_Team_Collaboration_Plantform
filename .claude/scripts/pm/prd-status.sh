#!/bin/bash

echo "📄 PRD 状态报告"
echo "===================="
echo ""

if [ ! -d ".claude/prds" ]; then
  echo "未找到 PRD 目录。"
  exit 0
fi

total=$(ls .claude/prds/*.md 2>/dev/null | wc -l)
[ $total -eq 0 ] && echo "未找到 PRD。" && exit 0

# Count by status
backlog=0
in_progress=0
implemented=0

for file in .claude/prds/*.md; do
  [ -f "$file" ] || continue
  status=$(grep "^status:" "$file" | head -1 | sed 's/^status: *//')

  case "$status" in
    backlog|draft|"") ((backlog++)) ;;
    in-progress|active) ((in_progress++)) ;;
    implemented|completed|done) ((implemented++)) ;;
    *) ((backlog++)) ;;
  esac
done

echo "正在获取状态..."
echo ""
echo ""

# Display chart
echo "📊 分布情况："
echo "================"

echo ""
echo "  积压中：    $(printf '%-3d' $backlog) [$(printf '%0.s█' $(seq 1 $((backlog*20/total))))]"
echo "  进行中：    $(printf '%-3d' $in_progress) [$(printf '%0.s█' $(seq 1 $((in_progress*20/total))))]"
echo "  已实现：    $(printf '%-3d' $implemented) [$(printf '%0.s█' $(seq 1 $((implemented*20/total))))]"
echo ""
echo "  PRD 总计：$total"

# Recent activity
echo ""
echo "📅 最近修改的 PRD（前5个）："
ls -t .claude/prds/*.md 2>/dev/null | head -5 | while read file; do
  name=$(grep "^name:" "$file" | head -1 | sed 's/^name: *//')
  [ -z "$name" ] && name=$(basename "$file" .md)
  echo "  • $name"
done

# Suggestions
echo ""
echo "💡 下一步操作："
[ $backlog -gt 0 ] && echo "  • 将积压 PRD 解析为史诗：/pm:prd-parse <名称>"
[ $in_progress -gt 0 ] && echo "  • 检查活跃 PRD 的进度：/pm:epic-status <名称>"
[ $total -eq 0 ] && echo "  • 创建您的第一个 PRD：/pm:prd-new <名称>"

exit 0
