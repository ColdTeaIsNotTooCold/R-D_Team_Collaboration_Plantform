import { useState, useEffect, useCallback, useRef } from 'react'
import { createChatService, type ChatService } from '@/services/chatService'
import type { Message, Agent } from '@/types'
import { message } from 'antd'

export interface UseChatOptions {
  autoConnect?: boolean
}

export const useChat = (options: UseChatOptions = {}) => {
  const { autoConnect = true } = options
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedAgent, setSelectedAgent] = useState<string>('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [initialized, setInitialized] = useState(false)

  const chatServiceRef = useRef<ChatService | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 初始化聊天服务
  useEffect(() => {
    const initializeChat = async () => {
      try {
        const service = createChatService({
          onMessage: (newMessage) => {
            setMessages(prev => [...prev, newMessage])
            setLoading(false)
          },
          onConnected: () => {
            setWsConnected(true)
            if (chatServiceRef.current) {
              chatServiceRef.current.addSystemMessage('已连接到服务器')
            }
          },
          onDisconnected: () => {
            setWsConnected(false)
            if (chatServiceRef.current) {
              chatServiceRef.current.addSystemMessage('与服务器断开连接')
            }
          },
          onError: (error) => {
            console.error('Chat error:', error)
            message.error('连接错误，请检查网络')
          }
        })

        await service.initialize()
        chatServiceRef.current = service
        setAgents(service.getAgents())
        setSelectedAgent(service.getSelectedAgent())
        setMessages(service.getMessages())
        setInitialized(true)
      } catch (error) {
        console.error('Failed to initialize chat:', error)
        message.error('初始化聊天服务失败')
      }
    }

    if (autoConnect) {
      initializeChat()
    }

    return () => {
      if (chatServiceRef.current) {
        chatServiceRef.current.destroy()
      }
    }
  }, [autoConnect])

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 发送消息
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || !chatServiceRef.current) {
      return false
    }

    setLoading(true)
    try {
      return await chatServiceRef.current.sendMessage(content)
    } catch (error) {
      console.error('Failed to send message:', error)
      message.error('发送消息失败')
      setLoading(false)
      return false
    }
  }, [])

  // 选择智能体
  const selectAgent = useCallback((agentId: string) => {
    if (chatServiceRef.current) {
      chatServiceRef.current.setSelectedAgent(agentId)
      setSelectedAgent(agentId)
    }
  }, [])

  // 清空消息
  const clearMessages = useCallback(() => {
    if (chatServiceRef.current) {
      chatServiceRef.current.clearMessages()
      setMessages([])
      chatServiceRef.current.addSystemMessage('对话历史已清除')
    }
  }, [])

  // 重新连接
  const reconnect = useCallback(() => {
    if (chatServiceRef.current) {
      chatServiceRef.current.reconnect()
    }
  }, [])

  // 获取智能体名称
  const getAgentName = useCallback((agentId: string) => {
    return chatServiceRef.current?.getAgentName(agentId) || '未知智能体'
  }, [])

  // 添加系统消息
  const addSystemMessage = useCallback((content: string) => {
    if (chatServiceRef.current) {
      chatServiceRef.current.addSystemMessage(content)
      setMessages(prev => [...prev])
    }
  }, [])

  // 获取连接状态
  const getConnectionStatus = useCallback(() => {
    return {
      connected: wsConnected,
      initialized,
      loading
    }
  }, [wsConnected, initialized, loading])

  return {
    // 数据
    agents,
    selectedAgent,
    messages,
    wsConnected,
    initialized,
    loading,

    // 方法
    sendMessage,
    selectAgent,
    clearMessages,
    reconnect,
    getAgentName,
    addSystemMessage,
    getConnectionStatus,

    // 引用
    messagesEndRef,
    chatService: chatServiceRef.current
  }
}

export type UseChatReturn = ReturnType<typeof useChat>