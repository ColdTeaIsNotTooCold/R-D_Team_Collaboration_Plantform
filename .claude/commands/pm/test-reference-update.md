---
allowed-tools: Bash, Read, Write
---

# 测试引用更新

测试在 epic-sync 中使用的任务引用更新逻辑。

## 使用方法
```
/pm:test-reference-update
```

## 指示

### 1. 创建测试文件

创建带有引用的测试任务文件：
```bash
mkdir -p /tmp/test-refs
cd /tmp/test-refs

# 创建任务 001
cat > 001.md << 'EOF'
---
name: 任务一
status: open
depends_on: []
parallel: true
conflicts_with: [002, 003]
---
# 任务一
这是任务 001。
EOF

# 创建任务 002
cat > 002.md << 'EOF'
---
name: 任务二
status: open
depends_on: [001]
parallel: false
conflicts_with: [003]
---
# 任务二
这是任务 002，依赖于 001。
EOF

# 创建任务 003
cat > 003.md << 'EOF'
---
name: 任务三
status: open
depends_on: [001, 002]
parallel: false
conflicts_with: []
---
# 任务三
这是任务 003，依赖于 001 和 002。
EOF
```

### 2. 创建映射

模拟问题创建映射：
```bash
# 模拟任务 -> 问题编号映射
cat > /tmp/task-mapping.txt << 'EOF'
001.md:42
002.md:43
003.md:44
EOF

# 创建旧 ID -> 新 ID 映射
> /tmp/id-mapping.txt
while IFS=: read -r task_file task_number; do
  old_num=$(basename "$task_file" .md)
  echo "$old_num:$task_number" >> /tmp/id-mapping.txt
done < /tmp/task-mapping.txt

echo "ID 映射："
cat /tmp/id-mapping.txt
```

### 3. 更新引用

处理每个文件并更新引用：
```bash
while IFS=: read -r task_file task_number; do
  echo "处理：$task_file -> $task_number.md"
  
  # 读取文件内容
  content=$(cat "$task_file")
  
  # 更新引用
  while IFS=: read -r old_num new_num; do
    content=$(echo "$content" | sed "s/\b$old_num\b/$new_num/g")
  done < /tmp/id-mapping.txt
  
  # 写入新文件
  new_name="${task_number}.md"
  echo "$content" > "$new_name"
  
  echo "更新内容预览："
  grep -E "depends_on:|conflicts_with:" "$new_name"
  echo "---"
done < /tmp/task-mapping.txt
```

### 4. 验证结果

检查引用是否正确更新：
```bash
echo "=== 最终结果 ==="
for file in 42.md 43.md 44.md; do
  echo "文件：$file"
  grep -E "name:|depends_on:|conflicts_with:" "$file"
  echo ""
done
```

预期输出：
- 42.md 应该有 conflicts_with: [43, 44]
- 43.md 应该有 depends_on: [42] 和 conflicts_with: [44]
- 44.md 应该有 depends_on: [42, 43]

### 5. 清理

```bash
cd -
rm -rf /tmp/test-refs
rm -f /tmp/task-mapping.txt /tmp/id-mapping.txt
echo "✅ 测试完成并已清理"
```