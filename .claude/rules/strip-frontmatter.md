# 剥离前置元数据

在将内容发送到 GitHub 之前移除 YAML 前置元数据的标准方法。

## 问题所在

YAML 前置元数据包含不应出现在 GitHub 问题中的内部元数据：
- status、created、updated 字段
- 内部引用和 ID
- 本地文件路径

## 解决方案

使用 sed 从任何 markdown 文件中剥离前置元数据：

```bash
# 剥离前置元数据（前两个 --- 行之间的所有内容）
sed '1,/^---$/d; 1,/^---$/d' input.md > output.md
```

这将移除：
1. 开头的 `---` 行
2. 所有 YAML 内容
3. 结尾的 `---` 行

## 何时剥离前置元数据

在以下情况下始终剥离前置元数据：
- 从 markdown 文件创建 GitHub 问题
- 将文件内容发布为评论
- 向外部用户显示内容
- 同步到任何外部系统

## 示例

### 从文件创建问题
```bash
# 不好 - 包含前置元数据
gh issue create --body-file task.md

# 好 - 剥离前置元数据
sed '1,/^---$/d; 1,/^---$/d' task.md > /tmp/clean.md
gh issue create --body-file /tmp/clean.md
```

### 发布评论
```bash
# 发布前剥离前置元数据
sed '1,/^---$/d; 1,/^---$/d' progress.md > /tmp/comment.md
gh issue comment 123 --body-file /tmp/comment.md
```

### 在循环中
```bash
for file in *.md; do
  # 从每个文件剥离前置元数据
  sed '1,/^---$/d; 1,/^---$/d' "$file" > "/tmp/$(basename $file)"
  # 使用清理后的版本
done
```

## 替代方法

如果 sed 不可用或您需要更多控制：

```bash
# 使用 awk
awk 'BEGIN{fm=0} /^---$/{fm++; next} fm==2{print}' input.md > output.md

# 使用 grep 和行号
grep -n "^---$" input.md | head -2 | tail -1 | cut -d: -f1 | xargs -I {} tail -n +$(({}+1)) input.md
```

## 重要说明

- 始终先用示例文件测试
- 保持原始文件完整
- 为清理后的内容使用临时文件
- 某些文件可能没有前置元数据 - 命令能优雅地处理这种情况