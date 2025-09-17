export interface Agent {
  id: string
  name: string
  description: string
  status: 'idle' | 'running' | 'error' | 'completed'
  type: string
  createdAt: string
  updatedAt: string
}

export interface Task {
  id: string
  title: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  priority: 'low' | 'medium' | 'high'
  assignedTo?: string
  createdAt: string
  updatedAt: string
  dueDate?: string
}

export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  timestamp: string
  agentId?: string
}

export interface SystemStatus {
  status: 'healthy' | 'warning' | 'error'
  agents: {
    total: number
    running: number
    idle: number
    error: number
  }
  tasks: {
    total: number
    pending: number
    running: number
    completed: number
    failed: number
  }
  uptime: string
}