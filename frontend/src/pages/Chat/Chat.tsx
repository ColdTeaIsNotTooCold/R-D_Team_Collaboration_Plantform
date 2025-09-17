import React from 'react'
import { Card } from 'antd'
import { useChat } from '@/hooks/useChat'
import MessageList from '@/components/Chat/MessageList'
import MessageInput from '@/components/Chat/MessageInput'
import AgentSelector from '@/components/Chat/AgentSelector'
import ConnectionStatus from '@/components/Chat/ConnectionStatus'

const Chat: React.FC = () => {
  const {
    agents,
    selectedAgent,
    messages,
    wsConnected,
    loading,
    sendMessage,
    selectAgent,
    clearMessages,
    reconnect,
    getAgentName,
    messagesEndRef
  } = useChat({ autoConnect: true })

  const [inputMessage, setInputMessage] = React.useState('')

  const handleSendMessage = async () => {
    if (await sendMessage(inputMessage)) {
      setInputMessage('')
    }
  }

  const handleQuickCommand = (command: string) => {
    switch (command) {
      case '帮助':
        setInputMessage('帮助')
        break
      case '状态':
        setInputMessage('状态')
        break
      case '清除对话':
        clearMessages()
        break
      default:
        setInputMessage(command)
    }
  }

  return (
    <div className="chat-container" style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      padding: '16px',
      backgroundColor: '#f0f2f5'
    }}>
      <Card
        className="chat-card"
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          borderRadius: '12px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
        }}
        bodyStyle={{
          padding: '16px',
          height: '100%',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* 连接状态和Agent选择 */}
        <div className="chat-header" style={{ marginBottom: '16px' }}>
          <ConnectionStatus
            isConnected={wsConnected}
            onReconnect={reconnect}
          />
        </div>

        <div className="agent-selector-wrapper" style={{ marginBottom: '16px' }}>
          <AgentSelector
            agents={agents}
            selectedAgent={selectedAgent}
            onAgentChange={selectAgent}
            loading={!agents.length}
          />
        </div>

        {/* 消息列表 */}
        <div className="chat-content" style={{
          flex: 1,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0
        }}>
          <div className="messages-wrapper" style={{
            flex: 1,
            overflow: 'auto',
            marginBottom: '16px',
            borderRadius: '8px',
            backgroundColor: '#fafafa'
          }}>
            <MessageList
              messages={messages}
              loading={loading}
              getAgentName={getAgentName}
            />
            <div ref={messagesEndRef} />
          </div>

          {/* 消息输入 */}
          <div className="input-wrapper">
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
              onQuickCommand={handleQuickCommand}
            />
          </div>
        </div>
      </Card>
    </div>
  )
}

export default Chat