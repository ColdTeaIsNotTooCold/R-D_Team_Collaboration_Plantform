import React from 'react'
import {
  Result,
  Button,
  Alert,
  Spin,
  Card,
  Typography,
  Space
} from 'antd'
import {
  ReloadOutlined,
  WarningOutlined,
  DisconnectOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined
} from '@ant-design/icons'

const { Text } = Typography

interface ErrorHandlerProps {
  loading?: boolean
  error?: Error | string | null
  connectionStatus?: {
    connected: boolean
    reconnecting: boolean
  }
  onRetry?: () => void
  onReconnect?: () => void
  children?: React.ReactNode
}

const ErrorHandler: React.FC<ErrorHandlerProps> = ({
  loading = false,
  error = null,
  connectionStatus = { connected: true, reconnecting: false },
  onRetry,
  onReconnect,
  children
}) => {
  // 显示加载状态
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '400px',
        flexDirection: 'column'
      }}>
        <Spin size="large" />
        <div style={{ marginTop: 16, color: '#666' }}>
          正在加载数据...
        </div>
      </div>
    )
  }

  // 显示错误状态
  if (error) {
    return (
      <Result
        status="error"
        title="加载失败"
        subTitle={typeof error === 'string' ? error : error.message}
        extra={[
          <Button
            key="retry"
            type="primary"
            icon={<ReloadOutlined />}
            onClick={onRetry}
          >
            重试
          </Button>,
          onReconnect && (
            <Button
              key="reconnect"
              icon={<DisconnectOutlined />}
              onClick={onReconnect}
            >
              重新连接
            </Button>
          )
        ]}
      />
    )
  }

  // 显示连接断开状态
  if (!connectionStatus.connected) {
    return (
      <div>
        <Alert
          message={
            <Space>
              <DisconnectOutlined />
              连接断开
            </Space>
          }
          description={
            connectionStatus.reconnecting
              ? "正在尝试重新连接服务器..."
              : "与服务器的连接已断开，请检查网络连接"
          }
          type="warning"
          showIcon
          action={
            <Space>
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={onRetry}
              >
                刷新
              </Button>
              {onReconnect && (
                <Button
                  size="small"
                  type="primary"
                  icon={<DisconnectOutlined />}
                  onClick={onReconnect}
                >
                  重连
                </Button>
              )}
            </Space>
          }
          style={{ marginBottom: 16 }}
        />
        {children}
      </div>
    )
  }

  // 显示连接成功但可能有问题
  if (connectionStatus.connected && connectionStatus.reconnecting) {
    return (
      <div>
        <Alert
          message={
            <Space>
              <WarningOutlined />
              连接不稳定
            </Space>
          }
          description="网络连接不稳定，正在尝试优化连接..."
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        {children}
      </div>
    )
  }

  // 正常显示子组件
  return <>{children}</>
}

// 骨架屏组件
export const DashboardSkeleton: React.FC = () => {
  return (
    <div>
      {/* 状态卡片骨架屏 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              style={{
                flex: 1,
                minWidth: 200,
                height: 100,
                backgroundColor: '#f5f5f5',
                borderRadius: 8,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <Spin size="small" />
            </div>
          ))}
        </div>
      </div>

      {/* 内容区域骨架屏 */}
      <div style={{
        height: 400,
        backgroundColor: '#f5f5f5',
        borderRadius: 8,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <Spin size="large" />
      </div>
    </div>
  )
}

// 空状态组件
export const EmptyState: React.FC<{
  type: 'no-data' | 'no-agents' | 'no-tasks' | 'no-connection'
  onAction?: () => void
}> = ({ type, onAction }) => {
  const getConfig = () => {
    switch (type) {
      case 'no-data':
        return {
          icon: <ExclamationCircleOutlined style={{ color: '#faad14' }} />,
          title: '暂无数据',
          description: '当前没有可显示的数据，请稍后再试',
          buttonText: '刷新数据',
          buttonIcon: <ReloadOutlined />
        }
      case 'no-agents':
        return {
          icon: <ExclamationCircleOutlined style={{ color: '#1890ff' }} />,
          title: '暂无智能体',
          description: '当前没有活跃的智能体，请先配置并启动智能体',
          buttonText: '配置智能体',
          buttonIcon: <ReloadOutlined />
        }
      case 'no-tasks':
        return {
          icon: <ExclamationCircleOutlined style={{ color: '#52c41a' }} />,
          title: '暂无任务',
          description: '当前没有任务，可以创建新任务开始工作',
          buttonText: '创建任务',
          buttonIcon: <ReloadOutlined />
        }
      case 'no-connection':
        return {
          icon: <DisconnectOutlined style={{ color: '#ff4d4f' }} />,
          title: '连接断开',
          description: '无法连接到服务器，请检查网络连接',
          buttonText: '重新连接',
          buttonIcon: <DisconnectOutlined />
        }
      default:
        return {
          icon: <ExclamationCircleOutlined style={{ color: '#666' }} />,
          title: '暂无数据',
          description: '当前没有可显示的数据',
          buttonText: '刷新',
          buttonIcon: <ReloadOutlined />
        }
    }
  }

  const config = getConfig()

  return (
    <Result
      icon={config.icon}
      title={config.title}
      subTitle={config.description}
      extra={
        onAction && (
          <Button
            type="primary"
            icon={config.buttonIcon}
            onClick={onAction}
          >
            {config.buttonText}
          </Button>
        )
      }
    />
  )
}

// 数据卡片包装器
export const DataCard: React.FC<{
  title: React.ReactNode
  loading?: boolean
  error?: Error | string | null
  children: React.ReactNode
  extra?: React.ReactNode
  height?: number
}> = ({ title, loading = false, error = null, children, extra, height }) => {
  return (
    <Card
      title={title}
      extra={extra}
      style={{ height: height || 'auto' }}
      bodyStyle={loading ? { padding: 0 } : undefined}
    >
      <ErrorHandler loading={loading} error={error}>
        {children}
      </ErrorHandler>
    </Card>
  )
}

// 状态指示器组件
export const StatusIndicator: React.FC<{
  status: 'success' | 'warning' | 'error' | 'loading'
  text: string
  description?: string
}> = ({ status, text, description }) => {
  const getConfig = () => {
    switch (status) {
      case 'success':
        return {
          color: '#52c41a',
          icon: <CheckCircleOutlined />
        }
      case 'warning':
        return {
          color: '#faad14',
          icon: <WarningOutlined />
        }
      case 'error':
        return {
          color: '#ff4d4f',
          icon: <ExclamationCircleOutlined />
        }
      case 'loading':
        return {
          color: '#1890ff',
          icon: <Spin size="small" />
        }
      default:
        return {
          color: '#666',
          icon: <ExclamationCircleOutlined />
        }
    }
  }

  const config = getConfig()

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ color: config.color }}>{config.icon}</span>
      <div>
        <Text>{text}</Text>
        {description && (
          <div style={{ fontSize: 12, color: '#666' }}>
            {description}
          </div>
        )}
      </div>
    </div>
  )
}

export default ErrorHandler