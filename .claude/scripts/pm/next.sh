#!/bin/bash
echo "正在获取状态..."
echo ""
echo ""

echo "📋 下一个可用任务"
echo "======================="
echo ""

# Find tasks that are open and have no dependencies or whose dependencies are closed
found=0

for epic_dir in .claude/epics/*/; do
  [ -d "$epic_dir" ] || continue
  epic_name=$(basename "$epic_dir")

  for task_file in "$epic_dir"[0-9]*.md; do
    [ -f "$task_file" ] || continue

    # Check if task is open
    status=$(grep "^status:" "$task_file" | head -1 | sed 's/^status: *//')
    [ "$status" != "open" ] && [ -n "$status" ] && continue

    # Check dependencies
    deps=$(grep "^depends_on:" "$task_file" | head -1 | sed 's/^depends_on: *\[//' | sed 's/\]//')

    # If no dependencies or empty, task is available
    if [ -z "$deps" ] || [ "$deps" = "depends_on:" ]; then
      task_name=$(grep "^name:" "$task_file" | head -1 | sed 's/^name: *//')
      task_num=$(basename "$task_file" .md)
      parallel=$(grep "^parallel:" "$task_file" | head -1 | sed 's/^parallel: *//')

      echo "✅ 准备就绪：#$task_num - $task_name"
      echo "   史诗：$epic_name"
      [ "$parallel" = "true" ] && echo "   🔄 可并行运行"
      echo ""
      ((found++))
    fi
  done
done

if [ $found -eq 0 ]; then
  echo "未找到可用任务。"
  echo ""
  echo "💡 建议："
  echo "  • 检查被阻塞的任务：/pm:blocked"
  echo "  • 查看所有任务：/pm:epic-list"
fi

echo ""
echo "📊 摘要：$found 个任务准备开始"

exit 0
