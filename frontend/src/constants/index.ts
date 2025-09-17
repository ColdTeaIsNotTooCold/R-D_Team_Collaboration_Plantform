// Agent状态
export const AGENT_STATUS = {
  IDLE: 'idle',
  RUNNING: 'running',
  ERROR: 'error',
  COMPLETED: 'completed',
} as const

// 任务状态
export const TASK_STATUS = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const

// 任务优先级
export const TASK_PRIORITY = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
} as const

// 系统状态
export const SYSTEM_STATUS = {
  HEALTHY: 'healthy',
  WARNING: 'warning',
  ERROR: 'error',
} as const

// 消息角色
export const MESSAGE_ROLE = {
  USER: 'user',
  ASSISTANT: 'assistant',
  SYSTEM: 'system',
} as const

// 颜色映射
export const STATUS_COLORS = {
  [AGENT_STATUS.IDLE]: '#8c8c8c',
  [AGENT_STATUS.RUNNING]: '#52c41a',
  [AGENT_STATUS.ERROR]: '#ff4d4f',
  [AGENT_STATUS.COMPLETED]: '#1890ff',
} as const

export const TASK_STATUS_COLORS = {
  [TASK_STATUS.PENDING]: '#8c8c8c',
  [TASK_STATUS.RUNNING]: '#faad14',
  [TASK_STATUS.COMPLETED]: '#52c41a',
  [TASK_STATUS.FAILED]: '#ff4d4f',
} as const

export const PRIORITY_COLORS = {
  [TASK_PRIORITY.LOW]: '#8c8c8c',
  [TASK_PRIORITY.MEDIUM]: '#faad14',
  [TASK_PRIORITY.HIGH]: '#ff4d4f',
} as const