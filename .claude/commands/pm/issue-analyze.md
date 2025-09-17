---
allowed-tools: Bash, Read, Write, LS
---

# 问题分析

分析问题以识别并行工作流以获得最大效率。

## 使用方法
```
/pm:issue-analyze <issue_number>
```

## 快速检查

1. **查找本地任务文件：**
   - 首先检查 `.claude/epics/*/$ARGUMENTS.md` 是否存在（新命名约定）
   - 如果未找到，搜索前置元数据中包含 `github:.*issues/$ARGUMENTS` 的文件（旧命名）
   - 如果未找到："❌ 问题 #$ARGUMENTS 没有本地任务。首先运行：/pm:import"

2. **检查现有分析：**
   ```bash
   test -f .claude/epics/*/$ARGUMENTS-analysis.md && echo "⚠️ 分析已存在。覆盖？(是/否)"
   ```

## 指示

### 1. 读取问题上下文

从 GitHub 获取问题详情：
```bash
gh issue view $ARGUMENTS --json title,body,labels
```

读取本地任务文件以了解：
- 技术要求
- 验收标准
- 依赖关系
- 工作量估算

### 2. 识别并行工作流

分析问题以识别可以并行运行的独立工作：

**常见模式：**
- **数据库层**：架构、迁移、模型
- **服务层**：业务逻辑、数据访问
- **API 层**：端点、验证、中间件
- **UI 层**：组件、页面、样式
- **测试层**：单元测试、集成测试
- **文档**：API 文档、README 更新

**关键问题：**
- 将创建/修改哪些文件？
- 哪些更改可以独立进行？
- 更改之间有什么依赖关系？
- 哪里可能发生冲突？

### 3. 创建分析文件

获取当前日期时间：`date -u +"%Y-%m-%dT%H:%M:%SZ"`

创建 `.claude/epics/{epic_name}/$ARGUMENTS-analysis.md`：

```markdown
---
issue: $ARGUMENTS
title: {issue_title}
analyzed: {current_datetime}
estimated_hours: {total_hours}
parallelization_factor: {1.0-5.0}
---

# 并行工作分析：问题 #$ARGUMENTS

## 概述
{简要描述需要做什么}

## 并行流

### 流 A：{流名称}
**范围**：{此流处理的内容}
**文件**：
- {file_pattern_1}
- {file_pattern_2}
**代理类型**：{backend|frontend|fullstack|database}-specialist
**可以开始**：立即
**估算小时数**：{hours}
**依赖关系**：无

### 流 B：{流名称}
**范围**：{此流处理的内容}
**文件**：
- {file_pattern_1}
- {file_pattern_2}
**代理类型**：{agent_type}
**可以开始**：立即
**估算小时数**：{hours}
**依赖关系**：无

### 流 C：{流名称}
**范围**：{此流处理的内容}
**文件**：
- {file_pattern_1}
**代理类型**：{agent_type}
**可以开始**：流 A 完成后
**估算小时数**：{hours}
**依赖关系**：流 A

## 协调点

### 共享文件
{列出多个流需要修改的任何文件}：
- `src/types/index.ts` - 流 A & B（协调类型更新）
- `package.json` - 流 B（添加依赖）

### 顺序要求
{列出必须按顺序发生的内容}：
1. API 端点之前的数据库架构
2. UI 组件之前的 API 类型
3. 测试之前的核心逻辑

## 冲突风险评估
- **低风险**：流在不同的目录中工作
- **中等风险**：一些共享类型文件，可通过协调管理
- **高风险**：多个流修改相同的核心文件

## 并行化策略

**推荐方法**：{sequential|parallel|hybrid}

{如果并行}：同时启动流 A、B。流 A 完成时启动 C。
{如果顺序}：完成流 A，然后 B，然后 C。
{如果混合}：一起启动 A & B，C 依赖 A，D 依赖 B & C。

## 预期时间线

并行执行：
- 墙上时间：{max_stream_hours} 小时
- 总工作量：{sum_all_hours} 小时
- 效率提升：{percentage}%

无并行执行：
- 墙上时间：{sum_all_hours} 小时

## 注意事项
{任何特殊考虑、警告或建议}
```

### 4. 验证分析

确保：
- 所有主要工作都由流覆盖
- 文件模式没有不必要的重叠
- 依赖关系是逻辑的
- 代理类型与工作类型匹配
- 时间估算是合理的

### 5. 输出

```
✅ 问题 #$ARGUMENTS 分析完成

已识别 {count} 个并行工作流：
  流 A：{name} ({hours}h)
  流 B：{name} ({hours}h)
  流 C：{name} ({hours}h)
  
并行化潜力：{factor}x 加速
  顺序时间：{total}h
  并行时间：{reduced}h

有冲突风险的文件：
  {如果有的话列出共享文件}

下一步：使用 /pm:issue-start $ARGUMENTS 开始工作
```

## 重要说明

- 分析仅限本地 - 不同步到 GitHub
- 专注于实用并行化，而不是理论最大值
- 分配流时考虑代理专业知识
- 在估算中考虑协调开销
- 偏好清晰分离而不是最大并行化