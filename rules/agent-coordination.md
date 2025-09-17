# Agent Coordination Rules

## 工作流协调规则

### 1. 流分配
- 每个Agent负责特定的工作流部分
- 流A：注册中心
- 流B：通信机制
- 流C：任务分发

### 2. 文件所有权
- backend/app/core/communication.py - 流B（通信机制）
- backend/app/core/messaging.py - 流B（通信机制）
- backend/app/api/messages.py - 流B（通信机制）
- backend/app/core/registry.py - 流A（注册中心）
- backend/app/api/agents.py - 流A（注册中心）
- backend/app/core/task_queue.py - 流C（任务分发）
- backend/app/api/tasks.py - 流C（任务分发）

### 3. 依赖管理
- 流B（通信机制）依赖于流A（注册中心）的完成
- 流C（任务分发）依赖于流A和流B的完成
- 检查依赖状态后再开始工作

### 4. 进度更新
- 每个流在自己的进度文件中更新状态
- 格式：`.claude/epics/team_collaboration_plantform/updates/002/stream-{letter}.md`
- 包含：开始时间、完成时间、状态、遇到的问题

### 5. 冲突解决
- 如果需要修改其他流拥有的文件，先检查进度
- 在进度文件中标记依赖等待
- 使用明确的协调消息