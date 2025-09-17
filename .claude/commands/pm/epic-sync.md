---
allowed-tools: Bash, Read, Write, LS, Task
---

# 史诗同步

将史诗和任务作为问题推送到 GitHub。

## 使用方法
```
/pm:epic-sync <feature_name>
```

## 快速检查

```bash
# 验证史诗存在
test -f .claude/epics/$ARGUMENTS/epic.md || echo "❌ 史诗未找到。运行：/pm:prd-parse $ARGUMENTS"

# 统计任务文件
ls .claude/epics/$ARGUMENTS/*.md 2>/dev/null | grep -v epic.md | wc -l
```

如果未找到任务："❌ 没有要同步的任务。运行：/pm:epic-decompose $ARGUMENTS"

## 指示

### 0. 检查远程仓库

遵循 `/rules/github-operations.md` 确保我们没有同步到 CCPM 模板：

```bash
# 检查远程 origin 是否是 CCPM 模板仓库
remote_url=$(git remote get-url origin 2>/dev/null || echo "")
if [[ "$remote_url" == *"automazeio/ccpm"* ]] || [[ "$remote_url" == *"automazeio/ccpm.git"* ]]; then
  echo "❌ 错误：您正在尝试与 CCPM 模板仓库同步！"
  echo ""
  echo "这个仓库（automazeio/ccpm）是供他人使用的模板。"
  echo "您不应该在这里创建问题或 PR。"
  echo ""
  echo "要解决此问题："
  echo "1. 将此仓库 fork 到您自己的 GitHub 账户"
  echo "2. 更新您的远程 origin："
  echo "   git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
  echo ""
  echo "或者如果是新项目："
  echo "1. 在 GitHub 上创建新仓库"
  echo "2. 更新您的远程 origin："
  echo "   git remote set-url origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
  echo ""
  echo "当前远程：$remote_url"
  exit 1
fi
```

### 1. 创建史诗问题

剥离前置元数据并准备 GitHub 问题正文：
```bash
# 提取没有前置元数据的内容
sed '1,/^---$/d; 1,/^---$/d' .claude/epics/$ARGUMENTS/epic.md > /tmp/epic-body-raw.md

# 删除"## 创建的任务"部分并替换为统计信息
awk '
  /^## Tasks Created/ {
    in_tasks=1
    next
  }
  /^## / && in_tasks {
    in_tasks=0
    # 当我们在 Tasks Created 之后到达下一部分时，添加统计信息
    if (total_tasks) {
      print "## 统计信息\n"
      print "总任务数：" total_tasks
      print "并行任务：" parallel_tasks "（可以同时工作）"
      print "顺序任务：" sequential_tasks "（有依赖关系）"
      if (total_effort) print "估算总工作量：" total_effort " 小时"
      print ""
    }
  }
  /^Total tasks:/ && in_tasks { total_tasks = $3; next }
  /^Parallel tasks:/ && in_tasks { parallel_tasks = $3; next }
  /^Sequential tasks:/ && in_tasks { sequential_tasks = $3; next }
  /^Estimated total effort:/ && in_tasks {
    gsub(/^Estimated total effort: /, "")
    total_effort = $0
    next
  }
  !in_tasks { print }
  END {
    # 如果我们在 EOF 时仍在任务部分，添加统计信息
    if (in_tasks && total_tasks) {
      print "## 统计信息\n"
      print "总任务数：" total_tasks
      print "并行任务：" parallel_tasks "（可以同时工作）"
      print "顺序任务：" sequential_tasks "（有依赖关系）"
      if (total_effort) print "估算总工作量：" total_effort
    }
  }
' /tmp/epic-body-raw.md > /tmp/epic-body.md

# 从内容确定史诗类型（功能 vs 错误）
if grep -qi "bug\|fix\|issue\|problem\|error" /tmp/epic-body.md; then
  epic_type="bug"
else
  epic_type="feature"
fi

# 创建带有标签的史诗问题
epic_number=$(gh issue create \
  --title "史诗：$ARGUMENTS" \
  --body-file /tmp/epic-body.md \
  --label "epic,epic:$ARGUMENTS,$epic_type" \
  --json number -q .number)
```

存储返回的问题编号以用于史诗前置元数据更新。

### 2. 创建任务子问题

检查 gh-sub-issue 是否可用：
```bash
if gh extension list | grep -q "yahsan2/gh-sub-issue"; then
  use_subissues=true
else
  use_subissues=false
  echo "⚠️ gh-sub-issue 未安装。使用备用模式。"
fi
```

统计任务文件以确定策略：
```bash
task_count=$(ls .claude/epics/$ARGUMENTS/[0-9][0-9][0-9].md 2>/dev/null | wc -l)
```

### 对于小批量（< 5 个任务）：顺序创建

```bash
if [ "$task_count" -lt 5 ]; then
  # 为小批量顺序创建
  for task_file in .claude/epics/$ARGUMENTS/[0-9][0-9][0-9].md; do
    [ -f "$task_file" ] || continue

    # 从前置元数据提取任务名称
    task_name=$(grep '^name:' "$task_file" | sed 's/^name: *//')

    # 从任务内容剥离前置元数据
    sed '1,/^---$/d; 1,/^---$/d' "$task_file" > /tmp/task-body.md

    # 创建带有标签的子问题
    if [ "$use_subissues" = true ]; then
      task_number=$(gh sub-issue create \
        --parent "$epic_number" \
        --title "$task_name" \
        --body-file /tmp/task-body.md \
        --label "task,epic:$ARGUMENTS" \
        --json number -q .number)
    else
      task_number=$(gh issue create \
        --title "$task_name" \
        --body-file /tmp/task-body.md \
        --label "task,epic:$ARGUMENTS" \
        --json number -q .number)
    fi

    # 记录映射以用于重命名
    echo "$task_file:$task_number" >> /tmp/task-mapping.txt
  done

  # 创建所有问题后，更新引用并重命名文件
  # 这遵循与下面步骤 3 相同的过程
fi
```

### 对于大批量：并行创建

```bash
if [ "$task_count" -ge 5 ]; then
  echo "正在并行创建 $task_count 个子问题..."

  # 检查 gh-sub-issue 是否可用于并行代理
  if gh extension list | grep -q "yahsan2/gh-sub-issue"; then
    subissue_cmd="gh sub-issue create --parent $epic_number"
  else
    subissue_cmd="gh issue create"
  fi

  # 批量任务以进行并行处理
  # 启动代理以使用适当标签并行创建子问题
  # 每个代理必须使用：--label "task,epic:$ARGUMENTS"
fi
```

使用任务工具进行并行创建：
```yaml
Task:
  description: "创建 GitHub 子问题批次 {X}"
  subagent_type: "general-purpose"
  prompt: |
    为史诗 $ARGUMENTS 中的任务创建 GitHub 子问题
    父史诗问题：#$epic_number

    要处理的任务：
    - {3-4 个任务文件列表}

    对于每个任务文件：
    1. 从前置元数据提取任务名称
    2. 使用以下剥离前置元数据：sed '1,/^---$/d; 1,/^---$/d'
    3. 使用以下创建子问题：
       - 如果 gh-sub-issue 可用：
         gh sub-issue create --parent $epic_number --title "$task_name" \
           --body-file /tmp/task-body.md --label "task,epic:$ARGUMENTS"
       - 否则：
         gh issue create --title "$task_name" --body-file /tmp/task-body.md \
           --label "task,epic:$ARGUMENTS"
    4. 记录：task_file:issue_number

    重要：始终包含带有 "task,epic:$ARGUMENTS" 的 --label 参数

    返回文件到问题编号的映射。
```

整合来自并行代理的结果：
```bash
# 收集来自代理的所有映射
cat /tmp/batch-*/mapping.txt >> /tmp/task-mapping.txt

# 重要：整合后，遵循步骤 3 以：
# 1. 构建旧->新 ID 映射
# 2. 更新所有任务引用（depends_on、conflicts_with）
# 3. 使用适当的前置元数据更新重命名文件
```

### 3. 重命名任务文件并更新引用

首先，构建旧编号到新问题 ID 的映射：
```bash
# 创建从旧任务编号（001、002 等）到新问题 ID 的映射
> /tmp/id-mapping.txt
while IFS=: read -r task_file task_number; do
  # 从文件名提取旧编号（例如，从 001.md 提取 001）
  old_num=$(basename "$task_file" .md)
  echo "$old_num:$task_number" >> /tmp/id-mapping.txt
done < /tmp/task-mapping.txt
```

然后重命名文件并更新所有引用：
```bash
# 处理每个任务文件
while IFS=: read -r task_file task_number; do
  new_name="$(dirname "$task_file")/${task_number}.md"

  # 读取文件内容
  content=$(cat "$task_file")

  # 更新 depends_on 和 conflicts_with 引用
  while IFS=: read -r old_num new_num; do
    # 更新像 [001, 002] 这样的数组以使用新问题编号
    content=$(echo "$content" | sed "s/\b$old_num\b/$new_num/g")
  done < /tmp/id-mapping.txt

  # 将更新的内容写入新文件
  echo "$content" > "$new_name"

  # 如果与旧文件不同则删除旧文件
  [ "$task_file" != "$new_name" ] && rm "$task_file"

  # 更新前置元数据中的 github 字段
  # 将 GitHub URL 添加到前置元数据
  repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
  github_url="https://github.com/$repo/issues/$task_number"

  # 使用 GitHub URL 和当前时间戳更新前置元数据
  current_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # 使用 sed 更新 github 和 updated 字段
  sed -i.bak "/^github:/c\github: $github_url" "$new_name"
  sed -i.bak "/^updated:/c\updated: $current_date" "$new_name"
  rm "${new_name}.bak"
done < /tmp/task-mapping.txt
```

### 4. 使用任务列表更新史诗（仅备用）

如果不使用 gh-sub-issue，将任务列表添加到史诗：

```bash
if [ "$use_subissues" = false ]; then
  # 获取当前史诗正文
  gh issue view {epic_number} --json body -q .body > /tmp/epic-body.md

  # 附加任务列表
  cat >> /tmp/epic-body.md << 'EOF'

  ## 任务
  - [ ] #{task1_number} {task1_name}
  - [ ] #{task2_number} {task2_name}
  - [ ] #{task3_number} {task3_name}
  EOF

  # 更新史诗问题
  gh issue edit {epic_number} --body-file /tmp/epic-body.md
fi
```

使用 gh-sub-issue，这是自动的！

### 5. 更新史诗文件

使用 GitHub URL、时间戳和真实任务 ID 更新史诗文件：

#### 5a. 更新前置元数据
```bash
# 获取仓库信息
repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
epic_url="https://github.com/$repo/issues/$epic_number"
current_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 更新史诗前置元数据
sed -i.bak "/^github:/c\github: $epic_url" .claude/epics/$ARGUMENTS/epic.md
sed -i.bak "/^updated:/c\updated: $current_date" .claude/epics/$ARGUMENTS/epic.md
rm .claude/epics/$ARGUMENTS/epic.md.bak
```

#### 5b. 更新创建的任务部分
```bash
# 创建带有更新的创建任务部分的临时文件
cat > /tmp/tasks-section.md << 'EOF'
## 创建的任务
EOF

# 添加每个任务及其真实问题编号
for task_file in .claude/epics/$ARGUMENTS/[0-9]*.md; do
  [ -f "$task_file" ] || continue

  # 获取问题编号（没有 .md 的文件名）
  issue_num=$(basename "$task_file" .md)

  # 从前置元数据获取任务名称
  task_name=$(grep '^name:' "$task_file" | sed 's/^name: *//')

  # 获取并行状态
  parallel=$(grep '^parallel:' "$task_file" | sed 's/^parallel: *//')

  # 添加到任务部分
  echo "- [ ] #${issue_num} - ${task_name} (并行：${parallel})" >> /tmp/tasks-section.md
done

# 添加摘要统计
total_count=$(ls .claude/epics/$ARGUMENTS/[0-9]*.md 2>/dev/null | wc -l)
parallel_count=$(grep -l '^parallel: true' .claude/epics/$ARGUMENTS/[0-9]*.md 2>/dev/null | wc -l)
sequential_count=$((total_count - parallel_count))

cat >> /tmp/tasks-section.md << EOF

总任务数：${total_count}
并行任务：${parallel_count}
顺序任务：${sequential_count}
EOF

# 替换 epic.md 中的创建任务部分
# 首先，创建备份
cp .claude/epics/$ARGUMENTS/epic.md .claude/epics/$ARGUMENTS/epic.md.backup

# 使用 awk 替换部分
awk '
  /^## Tasks Created/ {
    skip=1
    while ((getline line < "/tmp/tasks-section.md") > 0) print line
    close("/tmp/tasks-section.md")
  }
  /^## / && !/^## Tasks Created/ { skip=0 }
  !skip && !/^## Tasks Created/ { print }
' .claude/epics/$ARGUMENTS/epic.md.backup > .claude/epics/$ARGUMENTS/epic.md

# 清理
rm .claude/epics/$ARGUMENTS/epic.md.backup
rm /tmp/tasks-section.md
```

### 6. 创建映射文件

创建 `.claude/epics/$ARGUMENTS/github-mapping.md`：
```bash
# 创建映射文件
cat > .claude/epics/$ARGUMENTS/github-mapping.md << EOF
# GitHub 问题映射

史诗：#${epic_number} - https://github.com/${repo}/issues/${epic_number}

任务：
EOF

# 添加每个任务映射
for task_file in .claude/epics/$ARGUMENTS/[0-9]*.md; do
  [ -f "$task_file" ] || continue

  issue_num=$(basename "$task_file" .md)
  task_name=$(grep '^name:' "$task_file" | sed 's/^name: *//')

  echo "- #${issue_num}: ${task_name} - https://github.com/${repo}/issues/${issue_num}" >> .claude/epics/$ARGUMENTS/github-mapping.md
done

# 添加同步时间戳
echo "" >> .claude/epics/$ARGUMENTS/github-mapping.md
echo "已同步：$(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> .claude/epics/$ARGUMENTS/github-mapping.md
```

### 7. 创建工作树

遵循 `/rules/worktree-operations.md` 创建开发工作树：

```bash
# 确保 main 是最新的
git checkout main
git pull origin main

# 为史诗创建工作树
git worktree add ../epic-$ARGUMENTS -b epic/$ARGUMENTS

echo "✅ 已创建工作树：../epic-$ARGUMENTS"
```

### 8. 输出

```
✅ 已同步到 GitHub
  - 史诗：#{epic_number} - {epic_title}
  - 任务：{count} 个子问题已创建
  - 已应用标签：epic、task、epic:{name}
  - 文件已重命名：001.md → {issue_id}.md
  - 引用已更新：depends_on/conflicts_with 现在使用问题 ID
  - 工作树：../epic-$ARGUMENTS

下一步：
  - 开始并行执行：/pm:epic-start $ARGUMENTS
  - 或处理单个问题：/pm:issue-start {issue_number}
  - 查看史诗：https://github.com/{owner}/{repo}/issues/{epic_number}
```

## 错误处理

遵循 `/rules/github-operations.md` 处理 GitHub CLI 错误。

如果任何问题创建失败：
- 报告成功的内容
- 注意失败的内容
- 不要尝试回滚（部分同步没问题）

## 重要说明

- 信任 GitHub CLI 身份验证
- 不要预先检查重复项
- 仅在成功创建后更新前置元数据
- 保持操作简单和原子化