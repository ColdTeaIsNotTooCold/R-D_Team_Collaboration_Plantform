---
allowed-tools: Read, Write, LS
---

# 史诗编辑

创建后编辑史诗详情。

## 使用方法
```
/pm:epic-edit <epic_name>
```

## 指示

### 1. 读取当前史诗

读取 `.claude/epics/$ARGUMENTS/epic.md`：
- 解析前置元数据
- 读取内容部分

### 2. 交互式编辑

询问用户要编辑什么：
- 名称/标题
- 描述/概述
- 架构决策
- 技术方法
- 依赖关系
- 成功标准

### 3. 更新史诗文件

获取当前日期时间：`date -u +"%Y-%m-%dT%H:%M:%SZ"`

更新 epic.md：
- 保留除 `updated` 外的所有前置元数据
- 将用户的编辑应用到内容
- 用当前日期时间更新 `updated` 字段

### 4. 选择更新 GitHub

如果史诗在前置元数据中有 GitHub URL：
询问："更新 GitHub 问题？(是/否)"

如果是：
```bash
gh issue edit {issue_number} --body-file .claude/epics/$ARGUMENTS/epic.md
```

### 5. 输出

```
✅ 已更新史诗：$ARGUMENTS
  已更改的部分：{sections_edited}
  
{如果 GitHub 已更新}：GitHub 问题已更新 ✅

查看史诗：/pm:epic-show $ARGUMENTS
```

## 重要说明

保留前置元数据历史（created、github URL 等）。
编辑史诗时不要更改任务文件。
遵循 `/rules/frontmatter-operations.md`。