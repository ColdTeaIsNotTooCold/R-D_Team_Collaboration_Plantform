#!/bin/bash
echo "正在获取任务..."
echo ""
echo ""

echo "🚫 被阻塞的任务"
echo "================"
echo ""

found=0

for epic_dir in .claude/epics/*/; do
  [ -d "$epic_dir" ] || continue
  epic_name=$(basename "$epic_dir")

  for task_file in "$epic_dir"[0-9]*.md; do
    [ -f "$task_file" ] || continue

    # Check if task is open
    status=$(grep "^status:" "$task_file" | head -1 | sed 's/^status: *//')
    [ "$status" != "open" ] && [ -n "$status" ] && continue

    # Check for dependencies
    deps=$(grep "^depends_on:" "$task_file" | head -1 | sed 's/^depends_on: *\[//' | sed 's/\]//' | sed 's/,/ /g')

    if [ -n "$deps" ] && [ "$deps" != "depends_on:" ]; then
      task_name=$(grep "^name:" "$task_file" | head -1 | sed 's/^name: *//')
      task_num=$(basename "$task_file" .md)

      echo "⏸️ 任务 #$task_num - $task_name"
      echo "   史诗：$epic_name"
      echo "   被阻塞于：[$deps]"

      # Check status of dependencies
      open_deps=""
      for dep in $deps; do
        dep_file="$epic_dir$dep.md"
        if [ -f "$dep_file" ]; then
          dep_status=$(grep "^status:" "$dep_file" | head -1 | sed 's/^status: *//')
          [ "$dep_status" = "open" ] && open_deps="$open_deps #$dep"
        fi
      done

      [ -n "$open_deps" ] && echo "   等待中：$open_deps"
      echo ""
      ((found++))
    fi
  done
done

if [ $found -eq 0 ]; then
  echo "未发现被阻塞的任务！"
  echo ""
  echo "💡 所有有依赖的任务要么已完成，要么正在进行中。"
else
  echo "📊 总计被阻塞：$found 个任务"
fi

exit 0
