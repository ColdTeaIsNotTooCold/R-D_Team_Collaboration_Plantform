import { getWebSocketClient } from '@/utils/websocket'
import type { Agent, Task, SystemStatus } from '@/types'
import { AGENT_STATUS, TASK_STATUS } from '@/constants'

export interface RealtimeData {
  agents: Agent[]
  tasks: Task[]
  systemStatus: SystemStatus
  performance: {
    cpu: number
    memory: number
    disk: number
    network: number
  }
}

export class RealtimeService {
  private wsClient: ReturnType<typeof getWebSocketClient>
  private subscribers: Map<string, ((data: any) => void)[]> = new Map()
  private isConnected = false
  private reconnectTimer: NodeJS.Timeout | null = null

  constructor() {
    this.wsClient = getWebSocketClient()
    this.setupWebSocket()
  }

  private setupWebSocket() {
    // 连接事件
    this.wsClient.on('connected', () => {
      this.isConnected = true
      this.emit('connection_changed', { connected: true })
      console.log('实时服务已连接')
    })

    // 断开事件
    this.wsClient.on('disconnected', () => {
      this.isConnected = false
      this.emit('connection_changed', { connected: false })
      console.log('实时服务已断开')
      this.scheduleReconnect()
    })

    // 消息事件
    this.wsClient.on('message', (data) => {
      this.handleMessage(data)
    })

    // 错误事件
    this.wsClient.on('error', (error) => {
      console.error('WebSocket错误:', error)
      this.emit('error', error)
    })
  }

  private handleMessage(data: any) {
    try {
      switch (data.type) {
        case 'agent_update':
          this.handleAgentUpdate(data.data)
          break
        case 'task_update':
          this.handleTaskUpdate(data.data)
          break
        case 'system_status':
          this.handleSystemStatusUpdate(data.data)
          break
        case 'performance_metrics':
          this.handlePerformanceUpdate(data.data)
          break
        case 'heartbeat':
          this.handleHeartbeat(data.data)
          break
        default:
          console.log('未知消息类型:', data.type)
      }
    } catch (error) {
      console.error('处理消息时出错:', error)
    }
  }

  private handleAgentUpdate(data: any) {
    const agent: Agent = {
      id: data.id,
      name: data.name,
      description: data.description,
      status: data.status,
      type: data.type,
      createdAt: data.createdAt,
      updatedAt: data.updatedAt
    }
    this.emit('agent_updated', agent)
  }

  private handleTaskUpdate(data: any) {
    const task: Task = {
      id: data.id,
      title: data.title,
      description: data.description,
      status: data.status,
      priority: data.priority,
      assignedTo: data.assignedTo,
      createdAt: data.createdAt,
      updatedAt: data.updatedAt,
      dueDate: data.dueDate
    }
    this.emit('task_updated', task)
  }

  private handleSystemStatusUpdate(data: any) {
    const systemStatus: SystemStatus = {
      status: data.status,
      agents: data.agents,
      tasks: data.tasks,
      uptime: data.uptime
    }
    this.emit('system_status_updated', systemStatus)
  }

  private handlePerformanceUpdate(data: any) {
    const performance = {
      cpu: data.cpu || 0,
      memory: data.memory || 0,
      disk: data.disk || 0,
      network: data.network || 0
    }
    this.emit('performance_updated', performance)
  }

  private handleHeartbeat(data: any) {
    this.emit('heartbeat', data)
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    this.reconnectTimer = setTimeout(() => {
      if (!this.isConnected) {
        this.connect()
      }
    }, 5000)
  }

  // 公共方法
  connect() {
    if (!this.isConnected) {
      this.wsClient.connect()
    }
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.wsClient.disconnect()
    this.isConnected = false
  }

  // 事件订阅
  on(event: string, callback: (data: any) => void) {
    if (!this.subscribers.has(event)) {
      this.subscribers.set(event, [])
    }
    this.subscribers.get(event)!.push(callback)
  }

  off(event: string, callback: (data: any) => void) {
    const callbacks = this.subscribers.get(event)
    if (callbacks) {
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  private emit(event: string, data: any) {
    const callbacks = this.subscribers.get(event)
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`执行回调函数时出错 (${event}):`, error)
        }
      })
    }
  }

  // 获取连接状态
  getConnectionStatus() {
    return {
      connected: this.isConnected,
      reconnecting: this.reconnectTimer !== null
    }
  }

  // 发送消息到服务器
  sendMessage(type: string, data: any) {
    if (this.isConnected) {
      this.wsClient.send({
        type,
        data,
        timestamp: new Date().toISOString()
      })
    } else {
      console.warn('WebSocket未连接，无法发送消息')
    }
  }

  // 请求系统状态更新
  requestSystemStatus() {
    this.sendMessage('request_system_status', {})
  }

  // 请求性能指标
  requestPerformanceMetrics() {
    this.sendMessage('request_performance_metrics', {})
  }
}

// 创建全局实例
let realtimeService: RealtimeService | null = null

export const getRealtimeService = (): RealtimeService => {
  if (!realtimeService) {
    realtimeService = new RealtimeService()
  }
  return realtimeService
}

// 便捷的Hook函数
export const useRealtimeData = () => {
  const service = getRealtimeService()

  return {
    service,
    connect: () => service.connect(),
    disconnect: () => service.disconnect(),
    connectionStatus: service.getConnectionStatus(),
    onAgentUpdate: (callback: (agent: Agent) => void) => {
      service.on('agent_updated', callback)
    },
    onTaskUpdate: (callback: (task: Task) => void) => {
      service.on('task_updated', callback)
    },
    onSystemStatusUpdate: (callback: (status: SystemStatus) => void) => {
      service.on('system_status_updated', callback)
    },
    onPerformanceUpdate: (callback: (performance: any) => void) => {
      service.on('performance_updated', performance)
    },
    onConnectionChange: (callback: (status: { connected: boolean }) => void) => {
      service.on('connection_changed', callback)
    },
    onError: (callback: (error: any) => void) => {
      service.on('error', callback)
    }
  }
}

export default RealtimeService