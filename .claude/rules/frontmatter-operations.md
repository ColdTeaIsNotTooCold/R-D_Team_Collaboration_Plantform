# 前置元数据操作规则

在 markdown 文件中处理 YAML 前置元数据的标准模式。

## 读取前置元数据

从任何 markdown 文件中提取前置元数据：
1. 查找文件开头 `---` 标记之间的内容
2. 解析为 YAML
3. 如果无效或缺失，使用合理的默认值

## 更新前置元数据

更新现有文件时：
1. 保留所有现有字段
2. 只更新指定的字段
3. 始终使用当前日期时间更新 `updated` 字段（参见 `/rules/datetime.md`）

## 标准字段

### 所有文件
```yaml
---
name: {identifier}
created: {ISO datetime}      # 创建后永不更改
updated: {ISO datetime}      # 任何修改时更新
---
```

### 状态值
- PRD: `backlog`, `in-progress`, `complete`
- 史诗: `backlog`, `in-progress`, `completed`  
- 任务: `open`, `in-progress`, `closed`

### 进度跟踪
```yaml
progress: {0-100}%           # 用于史诗
completion: {0-100}%         # 用于进度文件
```

## 创建新文件

创建 markdown 文件时始终包含前置元数据：
```yaml
---
name: {from_arguments_or_context}
status: {initial_status}
created: {current_datetime}
updated: {current_datetime}
---
```

## 重要说明

- 初始创建后永远不要修改 `created` 字段
- 始终使用系统的真实日期时间（参见 `/rules/datetime.md`）
- 尝试解析前验证前置元数据是否存在
- 在所有文件中使用一致的字段名称