import React from 'react'
import { Avatar, Typography, Space, Tooltip } from 'antd'
import { UserOutlined, RobotOutlined, InfoCircleOutlined } from '@ant-design/icons'
import type { Message } from '@/types'
import { MESSAGE_ROLE } from '@/constants'
import { formatTime } from '@/utils/format'
import MarkdownRenderer from './MarkdownRenderer'

const { Text } = Typography

interface MessageListProps {
  messages: Message[]
  loading?: boolean
  getAgentName?: (agentId: string) => string
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  loading = false,
  getAgentName
}) => {
  const renderMessageContent = (message: Message) => {
    const isUser = message.role === MESSAGE_ROLE.USER
    const isSystem = message.role === MESSAGE_ROLE.SYSTEM
    const isAssistant = message.role === MESSAGE_ROLE.ASSISTANT

    return (
      <div
        style={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          marginBottom: '16px',
          animation: 'fadeIn 0.3s ease-in'
        }}
      >
        <div
          style={{
            maxWidth: '70%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: isUser ? 'flex-end' : 'flex-start',
            gap: '4px'
          }}
        >
          {/* 消息头部信息 */}
          <div style={{ fontSize: '12px', color: '#999' }}>
            {isUser && (
              <Space>
                <UserOutlined />
                <span>我</span>
                <span>{formatTime(message.timestamp)}</span>
              </Space>
            )}
            {isAssistant && getAgentName && (
              <Space>
                <RobotOutlined />
                <span>{getAgentName(message.agentId!)}</span>
                <span>{formatTime(message.timestamp)}</span>
              </Space>
            )}
            {isSystem && (
              <Space>
                <InfoCircleOutlined />
                <span>系统</span>
                <span>{formatTime(message.timestamp)}</span>
              </Space>
            )}
          </div>

          {/* 消息内容 */}
          <div
            className={`message-bubble ${isUser ? 'user-message' : isAssistant ? 'assistant-message' : 'system-message'}`}
            style={{
              padding: '12px 16px',
              borderRadius: '12px',
              backgroundColor: isUser ? '#1890ff' :
                           isSystem ? '#f5f5f5' : '#f6ffed',
              color: isUser ? 'white' :
                     isSystem ? '#666' : '#000',
              border: isSystem ? '1px solid #d9d9d9' : 'none',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              wordBreak: 'break-word'
            }}
          >
            {isUser || isSystem ? (
              <Text style={{
                color: 'inherit',
                fontSize: '14px',
                lineHeight: '1.5',
                whiteSpace: 'pre-wrap'
              }}>
                {message.content}
              </Text>
            ) : (
              <div style={{ color: 'inherit' }}>
                <MarkdownRenderer content={message.content} />
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{
      height: '100%',
      overflow: 'auto',
      padding: '16px',
      backgroundColor: '#fafafa',
      borderRadius: '8px'
    }}>
      {messages.length === 0 ? (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%',
            color: '#999',
            gap: '16px'
          }}
        >
          <RobotOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
          <Text style={{ fontSize: '16px' }}>开始与智能体对话吧！</Text>
          <Text style={{ fontSize: '14px' }}>
            选择一个智能体，输入您的消息开始对话
          </Text>
        </div>
      ) : (
        messages.map((message) => (
          <div key={message.id}>
            {renderMessageContent(message)}
          </div>
        ))
      )}

      {/* 加载指示器 */}
      {loading && (
        <div style={{
          display: 'flex',
          justifyContent: 'flex-start',
          padding: '16px 0'
        }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              backgroundColor: '#f6ffed',
              borderRadius: '12px',
              border: '1px solid #b7eb8f'
            }}
          >
            <div
              style={{
                width: '8px',
                height: '8px',
                backgroundColor: '#52c41a',
                borderRadius: '50%',
                animation: 'pulse 1.4s infinite ease-in-out'
              }}
            />
            <Text style={{ color: '#52c41a', fontSize: '14px' }}>
              智能体正在思考...
            </Text>
          </div>
        </div>
      )}
    </div>
  )
}

export default MessageList