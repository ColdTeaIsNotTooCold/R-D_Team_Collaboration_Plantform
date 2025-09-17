import React from 'react'
import { Space, Typography, Spin } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'

const { Text } = Typography

interface TypingIndicatorProps {
  isVisible: boolean
  message?: string
  agentName?: string
  style?: React.CSSProperties
}

const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  isVisible,
  message = '正在输入...',
  agentName,
  style = {}
}) => {
  if (!isVisible) return null

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'flex-start',
      padding: '8px 0',
      ...style
    }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '12px 16px',
          backgroundColor: '#f6ffed',
          borderRadius: '12px',
          border: '1px solid #b7eb8f',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}
      >
        <Spin
          indicator={
            <LoadingOutlined
              style={{
                fontSize: '16px',
                color: '#52c41a',
                animation: 'spin 1s linear infinite'
              }}
            />
          }
        />
        <Space direction="vertical" size={0}>
          <Text style={{ color: '#52c41a', fontSize: '14px', fontWeight: 500 }}>
            {agentName ? `${agentName} ${message}` : message}
          </Text>
          <div style={{ display: 'flex', gap: '4px' }}>
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                style={{
                  width: '6px',
                  height: '6px',
                  backgroundColor: '#52c41a',
                  borderRadius: '50%',
                  animation: `bounce 1.4s infinite ease-in-out`,
                  animationDelay: `${i * 0.2}s`
                }}
              />
            ))}
          </div>
        </Space>
      </div>
    </div>
  )
}

export default TypingIndicator