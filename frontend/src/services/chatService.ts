import { agentsApi } from '@/api'
import { initWebSocket } from '@/utils/websocket'
import type { Message, Agent } from '@/types'
import { MESSAGE_ROLE } from '@/constants'

export interface ChatServiceConfig {
  onMessage?: (message: Message) => void
  onConnected?: () => void
  onDisconnected?: () => void
  onError?: (error: any) => void
}

export class ChatService {
  private agents: Agent[] = []
  private selectedAgent: string = ''
  private messages: Message[] = []
  private wsClient: any = null
  private config: ChatServiceConfig

  constructor(config: ChatServiceConfig = {}) {
    this.config = config
  }

  // 初始化聊天服务
  async initialize(): Promise<void> {
    await this.loadAgents()
    this.initWebSocket()
  }

  // 加载智能体列表
  async loadAgents(): Promise<void> {
    try {
      const response = await agentsApi.getAgents()
      this.agents = response.data
      if (response.data.length > 0 && !this.selectedAgent) {
        this.selectedAgent = response.data[0].id
      }
    } catch (error) {
      console.error('Failed to load agents:', error)
      throw error
    }
  }

  // 初始化WebSocket连接
  private initWebSocket(): void {
    this.wsClient = initWebSocket()

    this.wsClient.on('connected', () => {
      this.config.onConnected?.()
    })

    this.wsClient.on('disconnected', () => {
      this.config.onDisconnected?.()
    })

    this.wsClient.on('message', (data: any) => {
      if (data.type === 'chat_response') {
        const message: Message = {
          id: Date.now().toString(),
          content: data.content,
          role: MESSAGE_ROLE.ASSISTANT,
          timestamp: new Date().toISOString(),
          agentId: data.agentId
        }
        this.addMessage(message)
        this.config.onMessage?.(message)
      }
    })

    this.wsClient.on('error', (error: any) => {
      this.config.onError?.(error)
    })
  }

  // 发送消息
  async sendMessage(content: string): Promise<boolean> {
    if (!content.trim()) {
      return false
    }

    if (!this.selectedAgent) {
      throw new Error('No agent selected')
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      role: MESSAGE_ROLE.USER,
      timestamp: new Date().toISOString()
    }

    this.addMessage(userMessage)

    try {
      if (this.wsClient && this.wsClient.isConnected()) {
        return this.wsClient.send({
          type: 'chat_message',
          content,
          agentId: this.selectedAgent,
          timestamp: new Date().toISOString()
        })
      } else {
        // 模拟回复
        setTimeout(() => {
          const response: Message = {
            id: Date.now().toString(),
            content: `我收到了您的消息："${content}"。这是一个模拟回复。`,
            role: MESSAGE_ROLE.ASSISTANT,
            timestamp: new Date().toISOString(),
            agentId: this.selectedAgent
          }
          this.addMessage(response)
          this.config.onMessage?.(response)
        }, 1000)
        return true
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      return false
    }
  }

  // 添加消息到列表
  private addMessage(message: Message): void {
    this.messages.push(message)
  }

  // 设置选中的智能体
  setSelectedAgent(agentId: string): void {
    this.selectedAgent = agentId
  }

  // 获取智能体列表
  getAgents(): Agent[] {
    return this.agents
  }

  // 获取选中的智能体
  getSelectedAgent(): string {
    return this.selectedAgent
  }

  // 获取消息列表
  getMessages(): Message[] {
    return [...this.messages]
  }

  // 清空消息
  clearMessages(): void {
    this.messages = []
  }

  // 获取智能体名称
  getAgentName(agentId: string): string {
    const agent = this.agents.find(a => a.id === agentId)
    return agent?.name || '未知智能体'
  }

  // 添加系统消息
  addSystemMessage(content: string): void {
    const message: Message = {
      id: Date.now().toString(),
      content,
      role: MESSAGE_ROLE.SYSTEM,
      timestamp: new Date().toISOString()
    }
    this.addMessage(message)
  }

  // 检查连接状态
  isConnected(): boolean {
    return this.wsClient?.isConnected() || false
  }

  // 重新连接
  reconnect(): void {
    if (this.wsClient) {
      this.wsClient.disconnect()
    }
    this.initWebSocket()
  }

  // 销毁服务
  destroy(): void {
    if (this.wsClient) {
      this.wsClient.disconnect()
    }
    this.agents = []
    this.selectedAgent = ''
    this.messages = []
  }
}

// 创建聊天服务实例的工厂函数
export const createChatService = (config: ChatServiceConfig = {}) => {
  return new ChatService(config)
}