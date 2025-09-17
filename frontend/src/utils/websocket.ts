import type { Message } from '@/types'

export class WebSocketClient {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectInterval = 1000
  private listeners: Map<string, Function[]> = new Map()
  private url: string
  private heartbeatInterval: number = 30000 // 30秒心跳间隔
  private heartbeatTimer: NodeJS.Timeout | null = null
  private connectionTimeout: number = 10000 // 10秒连接超时
  private connectionTimer: NodeJS.Timeout | null = null
  private messageQueue: any[] = [] // 消息队列
  private isConnecting = false

  constructor(url: string) {
    this.url = url
  }

  connect() {
    if (this.isConnecting || this.isConnected()) {
      return
    }

    this.isConnecting = true

    try {
      this.ws = new WebSocket(this.url)

      // 设置连接超时
      this.connectionTimer = setTimeout(() => {
        if (this.ws?.readyState === WebSocket.CONNECTING) {
          this.ws.close()
          this.emit('error', new Error('Connection timeout'))
          this.reconnect()
        }
      }, this.connectionTimeout)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.clearConnectionTimer()
        this.startHeartbeat()
        this.flushMessageQueue()
        this.emit('connected')
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          // 处理心跳响应
          if (data.type === 'pong') {
            return
          }

          this.emit('message', data)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
          this.emit('error', new Error('Failed to parse message'))
        }
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        this.isConnecting = false
        this.clearConnectionTimer()
        this.clearHeartbeat()
        this.emit('disconnected', { code: event.code, reason: event.reason })

        // 非正常关闭才重连
        if (event.code !== 1000) {
          this.reconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.isConnecting = false
        this.clearConnectionTimer()
        this.emit('error', error)
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      this.isConnecting = false
      this.clearConnectionTimer()
      this.reconnect()
    }
  }

  disconnect() {
    this.clearConnectionTimer()
    this.clearHeartbeat()
    if (this.ws) {
      this.ws.close(1000, 'Disconnect requested')
      this.ws = null
    }
    this.messageQueue = []
    this.isConnecting = false
  }

  private reconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      setTimeout(() => {
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`)
        this.connect()
      }, this.reconnectInterval * this.reconnectAttempts)
    } else {
      console.error('Max reconnection attempts reached')
      this.emit('max_reconnect_reached')
    }
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(data))
      } catch (error) {
        console.error('Failed to send message:', error)
        this.emit('error', error)
        return false
      }
    } else {
      console.warn('WebSocket is not connected, message queued')
      this.messageQueue.push(data)
      return false
    }
    return true
  }

  on(event: string, callback: Function) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event)!.push(callback)
  }

  off(event: string, callback: Function) {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  private emit(event: string, data?: any) {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.forEach(callback => callback(data))
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  private clearConnectionTimer() {
    if (this.connectionTimer) {
      clearTimeout(this.connectionTimer)
      this.connectionTimer = null
    }
  }

  private startHeartbeat() {
    this.clearHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.send({ type: 'ping', timestamp: Date.now() })
      } else {
        this.clearHeartbeat()
      }
    }, this.heartbeatInterval)
  }

  private clearHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private flushMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()
      if (message) {
        this.send(message)
      }
    }
  }
}

// 全局WebSocket实例
let wsClient: WebSocketClient | null = null

export const getWebSocketClient = (): WebSocketClient => {
  if (!wsClient) {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
    wsClient = new WebSocketClient(wsUrl)
  }
  return wsClient
}

export const initWebSocket = (): WebSocketClient => {
  const client = getWebSocketClient()
  client.connect()
  return client
}

// 为了向后兼容，导出websocketService别名
export const websocketService = getWebSocketClient()