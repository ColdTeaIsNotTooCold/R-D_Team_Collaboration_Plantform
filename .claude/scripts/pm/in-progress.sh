#!/bin/bash
echo "正在获取状态..."
echo ""
echo ""

echo "🔄 进行中的工作"
echo "==================="
echo ""

# Check for active work in updates directories
found=0

if [ -d ".claude/epics" ]; then
  for updates_dir in .claude/epics/*/updates/*/; do
    [ -d "$updates_dir" ] || continue

    issue_num=$(basename "$updates_dir")
    epic_name=$(basename $(dirname $(dirname "$updates_dir")))

    if [ -f "$updates_dir/progress.md" ]; then
      completion=$(grep "^completion:" "$updates_dir/progress.md" | head -1 | sed 's/^completion: *//')
      [ -z "$completion" ] && completion="0%"

      # Get task name from the task file
      task_file=".claude/epics/$epic_name/$issue_num.md"
      if [ -f "$task_file" ]; then
        task_name=$(grep "^name:" "$task_file" | head -1 | sed 's/^name: *//')
      else
        task_name="Unknown task"
      fi

      echo "📝 问题 #$issue_num - $task_name"
      echo "   史诗：$epic_name"
      echo "   进度：$completion 完成"

      # Check for recent updates
      if [ -f "$updates_dir/progress.md" ]; then
        last_update=$(grep "^last_sync:" "$updates_dir/progress.md" | head -1 | sed 's/^last_sync: *//')
        [ -n "$last_update" ] && echo "   最后更新：$last_update"
      fi

      echo ""
      ((found++))
    fi
  done
fi

# Also check for in-progress epics
echo "📚 活跃史诗："
for epic_dir in .claude/epics/*/; do
  [ -d "$epic_dir" ] || continue
  [ -f "$epic_dir/epic.md" ] || continue

  status=$(grep "^status:" "$epic_dir/epic.md" | head -1 | sed 's/^status: *//')
  if [ "$status" = "in-progress" ] || [ "$status" = "active" ]; then
    epic_name=$(grep "^name:" "$epic_dir/epic.md" | head -1 | sed 's/^name: *//')
    progress=$(grep "^progress:" "$epic_dir/epic.md" | head -1 | sed 's/^progress: *//')
    [ -z "$epic_name" ] && epic_name=$(basename "$epic_dir")
    [ -z "$progress" ] && progress="0%"

    echo "   • $epic_name - $progress 完成"
  fi
done

echo ""
if [ $found -eq 0 ]; then
  echo "未找到活跃的工作项。"
  echo ""
  echo "💡 开始工作：/pm:next"
else
  echo "📊 总计活跃项：$found"
fi

exit 0
