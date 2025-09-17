import React from 'react'
import {
  Space,
  Tooltip,
  Typography,
  Button,
  Badge
} from 'antd'
import {
  WifiOutlined,
  DisconnectOutlined,
  ReloadOutlined
} from '@ant-design/icons'

const { Text } = Typography

interface ConnectionStatusProps {
  isConnected: boolean
  onReconnect?: () => void
  showReconnectButton?: boolean
  style?: React.CSSProperties
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  isConnected,
  onReconnect,
  showReconnectButton = true,
  style = {}
}) => {
  const getStatusColor = () => {
    return isConnected ? 'success' : 'error'
  }

  const getStatusText = () => {
    return isConnected ? '已连接' : '未连接'
  }

  const getStatusIcon = () => {
    return isConnected ? <WifiOutlined /> : <DisconnectOutlined />
  }

  const getStatusDescription = () => {
    if (isConnected) {
      return 'WebSocket连接正常，可以实时接收消息'
    } else {
      return 'WebSocket连接断开，消息可能会有延迟'
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', ...style }}>
      <Tooltip title={getStatusDescription()}>
        <Badge
          status={getStatusColor() as 'success' | 'error' | 'default' | 'processing'}
          text={
            <Space>
              {getStatusIcon()}
              <Text>{getStatusText()}</Text>
            </Space>
          }
        />
      </Tooltip>

      {!isConnected && showReconnectButton && (
        <Tooltip title="重新连接">
          <Button
            type="link"
            size="small"
            icon={<ReloadOutlined />}
            onClick={onReconnect}
            loading={!isConnected}
          >
            重连
          </Button>
        </Tooltip>
      )}

      {/* 连接详细信息 */}
      <Tooltip title={getStatusDescription()}>
        <Text type="secondary" style={{ fontSize: '12px' }}>
          {isConnected ? '实时同步' : '连接中断'}
        </Text>
      </Tooltip>
    </div>
  )
}

export default ConnectionStatus