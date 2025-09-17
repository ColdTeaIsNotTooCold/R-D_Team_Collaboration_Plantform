import { message } from 'antd'
import type { Task } from '@/types'
import { websocketService } from '@/utils/websocket'

export interface TaskUpdateEvent {
  type: 'task_created' | 'task_updated' | 'task_deleted' | 'task_assigned'
  task: Task
  timestamp: string
}

export interface TaskNotification {
  id: string
  type: 'success' | 'info' | 'warning' | 'error'
  title: string
  message: string
  task?: Task
  timestamp: string
}

class TaskRealtimeService {
  private listeners: Set<(event: TaskUpdateEvent) => void> = new Set()
  private notificationListeners: Set<(notification: TaskNotification) => void> = new Set()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5

  constructor() {
    this.initializeWebSocket()
  }

  private initializeWebSocket() {
    // 订阅任务更新事件
    websocketService.subscribe('task_update', this.handleTaskUpdate.bind(this))

    // 订阅任务通知
    websocketService.subscribe('task_notification', this.handleTaskNotification.bind(this))

    // 监听连接状态
    websocketService.on('connected', this.handleConnected.bind(this))
    websocketService.on('disconnected', this.handleDisconnected.bind(this))
    websocketService.on('error', this.handleWebSocketError.bind(this))
  }

  private handleConnected() {
    this.reconnectAttempts = 0
    console.log('任务实时服务连接成功')
  }

  private handleDisconnected() {
    console.log('任务实时服务连接断开')
    this.attemptReconnect()
  }

  private handleWebSocketError(error: any) {
    console.error('WebSocket错误:', error)
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      setTimeout(() => {
        console.log(`尝试重新连接任务实时服务 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
        websocketService.connect()
      }, 1000 * Math.pow(2, this.reconnectAttempts - 1))
    } else {
      console.error('任务实时服务重连失败，达到最大重试次数')
    }
  }

  private handleTaskUpdate(event: TaskUpdateEvent) {
    console.log('收到任务更新:', event)

    // 通知所有监听器
    this.listeners.forEach(listener => {
      try {
        listener(event)
      } catch (error) {
        console.error('任务更新监听器执行错误:', error)
      }
    })

    // 显示通知
    this.showTaskNotification(event)
  }

  private handleTaskNotification(notification: TaskNotification) {
    console.log('收到任务通知:', notification)

    // 通知所有通知监听器
    this.notificationListeners.forEach(listener => {
      try {
        listener(notification)
      } catch (error) {
        console.error('任务通知监听器执行错误:', error)
      }
    })

    // 显示通知
    this.showNotification(notification)
  }

  private showTaskNotification(event: TaskUpdateEvent) {
    let title = ''
    let content = ''

    switch (event.type) {
      case 'task_created':
        title = '新任务创建'
        content = `任务 "${event.task.title}" 已创建`
        break
      case 'task_updated':
        title = '任务更新'
        content = `任务 "${event.task.title}" 已更新`
        break
      case 'task_deleted':
        title = '任务删除'
        content = `任务 "${event.task.title}" 已删除`
        break
      case 'task_assigned':
        title = '任务分配'
        content = `任务 "${event.task.title}" 已分配`
        break
      default:
        return
    }

    message.info({
      content: content,
      duration: 3,
    })
  }

  private showNotification(notification: TaskNotification) {
    switch (notification.type) {
      case 'success':
        message.success(notification.message, 3)
        break
      case 'info':
        message.info(notification.message, 3)
        break
      case 'warning':
        message.warning(notification.message, 3)
        break
      case 'error':
        message.error(notification.message, 5)
        break
    }
  }

  // 订阅任务更新
  subscribe(callback: (event: TaskUpdateEvent) => void): () => void {
    this.listeners.add(callback)

    // 返回取消订阅函数
    return () => {
      this.listeners.delete(callback)
    }
  }

  // 订阅任务通知
  subscribeNotifications(callback: (notification: TaskNotification) => void): () => void {
    this.notificationListeners.add(callback)

    // 返回取消订阅函数
    return () => {
      this.notificationListeners.delete(callback)
    }
  }

  // 手动发送任务更新（用于测试）
  sendTaskUpdate(event: TaskUpdateEvent) {
    websocketService.send(event)
  }

  // 手动发送任务通知（用于测试）
  sendTaskNotification(notification: TaskNotification) {
    websocketService.send(notification)
  }

  // 获取连接状态
  isConnected(): boolean {
    return websocketService.isConnected()
  }

  // 重新连接
  reconnect() {
    this.reconnectAttempts = 0
    websocketService.connect()
  }

  // 销毁服务
  destroy() {
    this.listeners.clear()
    this.notificationListeners.clear()
    websocketService.unsubscribe('task_update')
    websocketService.unsubscribe('task_notification')
  }
}

// 创建单例实例
export const taskRealtimeService = new TaskRealtimeService()

// 类型已经在前面导出，不需要重复导出