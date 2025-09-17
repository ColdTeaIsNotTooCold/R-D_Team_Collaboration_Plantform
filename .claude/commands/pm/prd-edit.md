---
allowed-tools: Read, Write, LS
---

# PRD 编辑

编辑现有的产品需求文档。

## 使用方法
```
/pm:prd-edit <feature_name>
```

## 指示

### 1. 读取当前 PRD

读取 `.claude/prds/$ARGUMENTS.md`：
- 解析前置元数据
- 读取所有部分

### 2. 交互式编辑

询问用户要编辑哪些部分：
- 执行摘要
- 问题陈述  
- 用户故事
- 需求（功能性/非功能性）
- 成功标准
- 约束和假设
- 范围外内容
- 依赖项

### 3. 更新 PRD

获取当前日期时间：`date -u +"%Y-%m-%dT%H:%M:%SZ"`

更新 PRD 文件：
- 保留前置元数据，除了 `updated` 字段
- 将用户的编辑应用到所选部分
- 用当前日期时间更新 `updated` 字段

### 4. 检查史诗影响

如果 PRD 有关联的史诗：
- 通知用户："此 PRD 有史诗：{epic_name}"
- 询问："史诗可能需要根据 PRD 更改进行更新。要审查史诗吗？（是/否）"
- 如果是，显示："使用以下命令审查：/pm:epic-edit {epic_name}"

### 5. 输出

```
✅ 已更新 PRD：$ARGUMENTS
  已编辑部分：{list_of_sections}
  
{如果有史诗}：⚠️ 史诗可能需要审查：{epic_name}

下一步：/pm:prd-parse $ARGUMENTS 更新史诗
```

## 重要说明

保留原始创建日期。
如果需要，在前置元数据中保留版本历史。
遵循 `/rules/frontmatter-operations.md`。