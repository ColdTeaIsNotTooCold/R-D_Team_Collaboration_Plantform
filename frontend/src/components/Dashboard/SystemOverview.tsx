import React from 'react'
import {
  Card,
  Row,
  Col,
  Statistic,
  Progress,
  Alert,
  Space,
  Typography
} from 'antd'
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  ApiOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'
import type { SystemStatus } from '@/types'
import { SYSTEM_STATUS } from '@/constants'

const { Text } = Typography

interface SystemOverviewProps {
  systemStatus: SystemStatus
  performance?: {
    cpu: number
    memory: number
    disk: number
    network: number
  }
}

const SystemOverview: React.FC<SystemOverviewProps> = ({
  systemStatus,
  performance = { cpu: 0, memory: 0, disk: 0, network: 0 }
}) => {
  const getStatusIcon = () => {
    switch (systemStatus.status) {
      case SYSTEM_STATUS.HEALTHY:
        return <CheckCircleOutlined />
      case SYSTEM_STATUS.WARNING:
        return <WarningOutlined />
      case SYSTEM_STATUS.ERROR:
        return <ExclamationCircleOutlined />
      default:
        return <CheckCircleOutlined />
    }
  }

  const getStatusColor = () => {
    switch (systemStatus.status) {
      case SYSTEM_STATUS.HEALTHY:
        return '#3f8600'
      case SYSTEM_STATUS.WARNING:
        return '#faad14'
      case SYSTEM_STATUS.ERROR:
        return '#cf1322'
      default:
        return '#3f8600'
    }
  }

  const getStatusText = () => {
    switch (systemStatus.status) {
      case SYSTEM_STATUS.HEALTHY:
        return '正常'
      case SYSTEM_STATUS.WARNING:
        return '警告'
      case SYSTEM_STATUS.ERROR:
        return '异常'
      default:
        return '正常'
    }
  }

  const formatUptime = (uptime: string) => {
    if (uptime.includes('分钟')) {
      return uptime
    }
    return uptime
  }

  return (
    <div>
      {/* 系统状态警告 */}
      {systemStatus.status === SYSTEM_STATUS.WARNING && (
        <Alert
          message="系统警告"
          description="检测到部分组件运行异常，请及时处理"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {systemStatus.status === SYSTEM_STATUS.ERROR && (
        <Alert
          message="系统异常"
          description="检测到严重错误，请立即处理"
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 系统概览卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="系统状态"
              value={getStatusText()}
              prefix={getStatusIcon()}
              valueStyle={{ color: getStatusColor() }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="智能体总数"
              value={systemStatus.agents.total}
              suffix={
                <Text type="secondary">
                  {systemStatus.agents.running > 0 && (
                    <span>({systemStatus.agents.running} 运行中)</span>
                  )}
                </Text>
              }
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="任务总数"
              value={systemStatus.tasks.total}
              suffix={
                <Text type="secondary">
                  {systemStatus.tasks.running > 0 && (
                    <span>({systemStatus.tasks.running} 运行中)</span>
                  )}
                </Text>
              }
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="运行时间"
              value={formatUptime(systemStatus.uptime)}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 性能监控 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="系统性能" size="small">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text><ThunderboltOutlined /> CPU使用率</Text>
                  <Text>{performance.cpu}%</Text>
                </div>
                <Progress
                  percent={performance.cpu}
                  size="small"
                  status={performance.cpu > 80 ? 'exception' : performance.cpu > 60 ? 'active' : 'normal'}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text><DatabaseOutlined /> 内存使用率</Text>
                  <Text>{performance.memory}%</Text>
                </div>
                <Progress
                  percent={performance.memory}
                  size="small"
                  status={performance.memory > 80 ? 'exception' : performance.memory > 60 ? 'active' : 'normal'}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text><DatabaseOutlined /> 磁盘使用率</Text>
                  <Text>{performance.disk}%</Text>
                </div>
                <Progress
                  percent={performance.disk}
                  size="small"
                  status={performance.disk > 90 ? 'exception' : performance.disk > 70 ? 'active' : 'normal'}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text><ApiOutlined /> 网络延迟</Text>
                  <Text>{performance.network}ms</Text>
                </div>
                <Progress
                  percent={Math.min(performance.network / 2, 100)}
                  size="small"
                  status={performance.network > 200 ? 'exception' : performance.network > 100 ? 'active' : 'normal'}
                />
              </div>
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="任务分布" size="small">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text>待处理</Text>
                  <Text>{systemStatus.tasks.pending}</Text>
                </div>
                <Progress
                  percent={(systemStatus.tasks.pending / systemStatus.tasks.total) * 100 || 0}
                  size="small"
                  strokeColor="#8c8c8c"
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text>运行中</Text>
                  <Text>{systemStatus.tasks.running}</Text>
                </div>
                <Progress
                  percent={(systemStatus.tasks.running / systemStatus.tasks.total) * 100 || 0}
                  size="small"
                  strokeColor="#faad14"
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text>已完成</Text>
                  <Text>{systemStatus.tasks.completed}</Text>
                </div>
                <Progress
                  percent={(systemStatus.tasks.completed / systemStatus.tasks.total) * 100 || 0}
                  size="small"
                  strokeColor="#52c41a"
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text>失败</Text>
                  <Text>{systemStatus.tasks.failed}</Text>
                </div>
                <Progress
                  percent={(systemStatus.tasks.failed / systemStatus.tasks.total) * 100 || 0}
                  size="small"
                  strokeColor="#ff4d4f"
                />
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default SystemOverview