import React, { useState, useEffect, useRef } from 'react'
import { Card } from 'antd'
import type { Message, Agent } from '@/types'
import { agentsApi } from '@/api'
import { initWebSocket } from '@/utils/websocket'
import { MESSAGE_ROLE } from '@/constants'
import MessageList from '@/components/Chat/MessageList'
import MessageInput from '@/components/Chat/MessageInput'
import AgentSelector from '@/components/Chat/AgentSelector'
import TypingIndicator from '@/components/Chat/TypingIndicator'
import ConnectionStatus from '@/components/Chat/ConnectionStatus'

const Chat: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedAgent, setSelectedAgent] = useState<string>('')
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const wsClientRef = useRef<any>(null)

  useEffect(() => {
    fetchAgents()
    initWebSocketConnection()
    return () => {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect()
      }
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const fetchAgents = async () => {
    try {
      const data = await agentsApi.getAgents()
      setAgents(data)
      if (data.length > 0 && !selectedAgent) {
        setSelectedAgent(data[0].id)
      }
    } catch (error) {
      message.error('获取智能体列表失败')
    }
  }

  const initWebSocketConnection = () => {
    const wsClient = initWebSocket()
    wsClientRef.current = wsClient

    wsClient.on('connected', () => {
      setWsConnected(true)
      addSystemMessage('已连接到服务器')
    })

    wsClient.on('disconnected', () => {
      setWsConnected(false)
      addSystemMessage('与服务器断开连接')
    })

    wsClient.on('message', (data: any) => {
      if (data.type === 'chat_response') {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          content: data.content,
          role: MESSAGE_ROLE.ASSISTANT,
          timestamp: new Date().toISOString(),
          agentId: data.agentId
        }])
      }
    })

    wsClient.on('error', (error: any) => {
      console.error('WebSocket错误:', error)
      addSystemMessage('连接错误，请检查网络')
    })
  }

  const addSystemMessage = (content: string) => {
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      content,
      role: MESSAGE_ROLE.SYSTEM,
      timestamp: new Date().toISOString()
    }])
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) {
      message.warning('请输入消息内容')
      return
    }

    if (!selectedAgent) {
      message.warning('请选择智能体')
      return
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage,
      role: MESSAGE_ROLE.USER,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setLoading(true)

    try {
      if (wsClientRef.current && wsClientRef.current.isConnected()) {
        // 使用WebSocket发送消息
        wsClientRef.current.send({
          type: 'chat_message',
          content: inputMessage,
          agentId: selectedAgent,
          timestamp: new Date().toISOString()
        })
      } else {
        // 模拟回复（实际应用中应该调用API）
        setTimeout(() => {
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            content: `我收到了您的消息："${inputMessage}"。这是一个模拟回复。`,
            role: MESSAGE_ROLE.ASSISTANT,
            timestamp: new Date().toISOString(),
            agentId: selectedAgent
          }])
        }, 1000)
      }
    } catch (error) {
      message.error('发送消息失败')
      addSystemMessage('发送消息失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  
  const getAgentName = (agentId: string) => {
    const agent = agents.find(a => a.id === agentId)
    return agent?.name || '未知智能体'
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Card style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* 连接状态和Agent选择 */}
        <div style={{ marginBottom: '16px' }}>
          <ConnectionStatus
            isConnected={wsConnected}
            onReconnect={initWebSocketConnection}
          />
        </div>

        <AgentSelector
          agents={agents}
          selectedAgent={selectedAgent}
          onAgentChange={setSelectedAgent}
          loading={!agents.length}
        />

        {/* 消息列表 */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div style={{
            flex: 1,
            overflow: 'auto',
            marginBottom: '16px'
          }}>
            <MessageList
              messages={messages}
              loading={loading}
              getAgentName={getAgentName}
            />
            <div ref={messagesEndRef} />
          </div>

          {/* 消息输入 */}
          <MessageInput
            value={inputMessage}
            onChange={setInputMessage}
            onSend={handleSendMessage}
            loading={loading}
            disabled={!selectedAgent}
            placeholder={selectedAgent ? '输入消息...' : '请先选择智能体'}
            quickCommands={[
              { label: 'help', value: '帮助', description: '获取帮助信息' },
              { label: 'status', value: '状态', description: '查看当前状态' },
              { label: 'clear', value: '清除对话', description: '清除当前对话历史' }
            ]}
          />
        </div>
      </Card>
    </div>
  )
}

export default Chat