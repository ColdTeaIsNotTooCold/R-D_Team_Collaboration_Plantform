import React, { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Progress,
  Statistic,
  Space,
  Typography,
  Alert,
  Button,
  Tooltip,
  Badge,
  List,
  Avatar,
  Divider
} from 'antd'
import {
  ThunderboltOutlined,
  DatabaseOutlined,
  GlobalOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  LineChartOutlined,
  BarChartOutlined,
  PieChartOutlined
} from '@ant-design/icons'
import type { SystemStatus } from '@/types'

const { Text, Title } = Typography

interface PerformanceMetrics {
  cpu: {
    usage: number
    temperature: number
    cores: number
    frequency: number
  }
  memory: {
    usage: number
    total: number
    available: number
    used: number
  }
  disk: {
    usage: number
    total: number
    available: number
    readSpeed: number
    writeSpeed: number
  }
  network: {
    latency: number
    downloadSpeed: number
    uploadSpeed: number
    packetLoss: number
  }
  system: {
    uptime: string
    loadAverage: number[]
    processes: number
    threads: number
  }
}

interface PerformanceMonitorProps {
  performance?: PerformanceMetrics
  systemStatus: SystemStatus
  loading?: boolean
  onRefresh: () => void
}

const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({
  performance = {
    cpu: { usage: 0, temperature: 0, cores: 4, frequency: 2.4 },
    memory: { usage: 0, total: 16, available: 16, used: 0 },
    disk: { usage: 0, total: 500, available: 500, readSpeed: 0, writeSpeed: 0 },
    network: { latency: 0, downloadSpeed: 0, uploadSpeed: 0, packetLoss: 0 },
    system: { uptime: '0分钟', loadAverage: [0, 0, 0], processes: 0, threads: 0 }
  },
  systemStatus,
  loading = false,
  onRefresh
}) => {
  const [selectedTab, setSelectedTab] = useState('overview')

  const getStatusColor = (value: number, type: 'cpu' | 'memory' | 'disk' | 'network') => {
    const thresholds = {
      cpu: { warning: 70, critical: 85 },
      memory: { warning: 75, critical: 90 },
      disk: { warning: 80, critical: 95 },
      network: { warning: 100, critical: 200 }
    }

    const threshold = thresholds[type]
    if (value >= threshold.critical) return '#ff4d4f'
    if (value >= threshold.warning) return '#faad14'
    return '#52c41a'
  }

  const getStatusText = (value: number, type: 'cpu' | 'memory' | 'disk' | 'network') => {
    const thresholds = {
      cpu: { warning: 70, critical: 85 },
      memory: { warning: 75, critical: 90 },
      disk: { warning: 80, critical: 95 },
      network: { warning: 100, critical: 200 }
    }

    const threshold = thresholds[type]
    if (value >= threshold.critical) return '严重'
    if (value >= threshold.warning) return '警告'
    return '正常'
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatSpeed = (speed: number) => {
    return formatBytes(speed) + '/s'
  }

  const getAlerts = () => {
    const alerts = []

    if (performance.cpu.usage > 85) {
      alerts.push({
        type: 'error',
        title: 'CPU使用率过高',
        description: `当前CPU使用率为${performance.cpu.usage}%，请检查系统负载`
      })
    } else if (performance.cpu.usage > 70) {
      alerts.push({
        type: 'warning',
        title: 'CPU使用率偏高',
        description: `当前CPU使用率为${performance.cpu.usage}%，建议关注系统性能`
      })
    }

    if (performance.memory.usage > 90) {
      alerts.push({
        type: 'error',
        title: '内存使用率过高',
        description: `当前内存使用率为${performance.memory.usage}%，请及时释放内存`
      })
    } else if (performance.memory.usage > 75) {
      alerts.push({
        type: 'warning',
        title: '内存使用率偏高',
        description: `当前内存使用率为${performance.memory.usage}%，建议关注内存使用情况`
      })
    }

    if (performance.network.latency > 200) {
      alerts.push({
        type: 'error',
        title: '网络延迟过高',
        description: `当前网络延迟为${performance.network.latency}ms，请检查网络连接`
      })
    }

    return alerts
  }

  const alerts = getAlerts()

  const renderOverview = () => (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small">
            <Statistic
              title="CPU使用率"
              value={performance.cpu.usage}
              suffix="%"
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: getStatusColor(performance.cpu.usage, 'cpu') }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              温度: {performance.cpu.temperature}°C | {performance.cpu.cores}核心
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card size="small">
            <Statistic
              title="内存使用率"
              value={performance.memory.usage}
              suffix="%"
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: getStatusColor(performance.memory.usage, 'memory') }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              可用: {performance.memory.available}GB
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card size="small">
            <Statistic
              title="磁盘使用率"
              value={performance.disk.usage}
              suffix="%"
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: getStatusColor(performance.disk.usage, 'disk') }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              可用: {performance.disk.available}GB
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card size="small">
            <Statistic
              title="网络延迟"
              value={performance.network.latency}
              suffix="ms"
              prefix={<GlobalOutlined />}
              valueStyle={{ color: getStatusColor(performance.network.latency, 'network') }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              丢包率: {performance.network.packetLoss}%
            </div>
          </Card>
        </Col>
      </Row>

      {/* 警告信息 */}
      {alerts.length > 0 && (
        <div style={{ marginTop: 16 }}>
          {alerts.map((alert, index) => (
            <Alert
              key={index}
              message={alert.title}
              description={alert.description}
              type={alert.type as any}
              showIcon
              style={{ marginBottom: 8 }}
            />
          ))}
        </div>
      )}
    </div>
  )

  const renderDetailedMetrics = () => (
    <div>
      <Row gutter={[16, 16]}>
        {/* CPU详细信息 */}
        <Col xs={24} lg={12}>
          <Card title="CPU详细信息" size="small">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text strong>CPU使用率</Text>
                  <Text>{performance.cpu.usage}%</Text>
                </div>
                <Progress
                  percent={performance.cpu.usage}
                  status={performance.cpu.usage > 85 ? 'exception' : performance.cpu.usage > 70 ? 'active' : 'normal'}
                />
              </div>

              <Row gutter={[16, 16]}>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: '#1890ff' }}>{performance.cpu.cores}</div>
                    <div style={{ fontSize: 12, color: '#666' }}>核心数</div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: '#52c41a' }}>{performance.cpu.frequency}</div>
                    <div style={{ fontSize: 12, color: '#666' }}>频率(GHz)</div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: performance.cpu.temperature > 70 ? '#ff4d4f' : '#faad14' }}>
                      {performance.cpu.temperature}°C
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>温度</div>
                  </div>
                </Col>
              </Row>
            </Space>
          </Card>
        </Col>

        {/* 内存详细信息 */}
        <Col xs={24} lg={12}>
          <Card title="内存详细信息" size="small">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text strong>内存使用率</Text>
                  <Text>{performance.memory.usage}%</Text>
                </div>
                <Progress
                  percent={performance.memory.usage}
                  status={performance.memory.usage > 90 ? 'exception' : performance.memory.usage > 75 ? 'active' : 'normal'}
                />
              </div>

              <Row gutter={[16, 16]}>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: '#1890ff' }}>{performance.memory.total}</div>
                    <div style={{ fontSize: 12, color: '#666' }}>总容量(GB)</div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: '#52c41a' }}>{performance.memory.available}</div>
                    <div style={{ fontSize: 12, color: '#666' }}>可用(GB)</div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: '#ff4d4f' }}>{performance.memory.used}</div>
                    <div style={{ fontSize: 12, color: '#666' }}>已用(GB)</div>
                  </div>
                </Col>
              </Row>
            </Space>
          </Card>
        </Col>

        {/* 磁盘详细信息 */}
        <Col xs={24} lg={12}>
          <Card title="磁盘详细信息" size="small">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text strong>磁盘使用率</Text>
                  <Text>{performance.disk.usage}%</Text>
                </div>
                <Progress
                  percent={performance.disk.usage}
                  status={performance.disk.usage > 95 ? 'exception' : performance.disk.usage > 80 ? 'active' : 'normal'}
                />
              </div>

              <Row gutter={[16, 16]}>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: '#1890ff' }}>{performance.disk.total}</div>
                    <div style={{ fontSize: 12, color: '#666' }}>总容量(GB)</div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: '#52c41a' }}>{performance.disk.available}</div>
                    <div style={{ fontSize: 12, color: '#666' }}>可用(GB)</div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: '#faad14' }}>{performance.disk.readSpeed}</div>
                    <div style={{ fontSize: 12, color: '#666' }}>读取(MB/s)</div>
                  </div>
                </Col>
              </Row>
            </Space>
          </Card>
        </Col>

        {/* 网络详细信息 */}
        <Col xs={24} lg={12}>
          <Card title="网络详细信息" size="small">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text strong>网络延迟</Text>
                  <Text>{performance.network.latency}ms</Text>
                </div>
                <Progress
                  percent={Math.min(performance.network.latency / 2, 100)}
                  status={performance.network.latency > 200 ? 'exception' : performance.network.latency > 100 ? 'active' : 'normal'}
                />
              </div>

              <Row gutter={[16, 16]}>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: '#52c41a' }}>{performance.network.downloadSpeed}</div>
                    <div style={{ fontSize: 12, color: '#666' }}>下载(MB/s)</div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: '#1890ff' }}>{performance.network.uploadSpeed}</div>
                    <div style={{ fontSize: 12, color: '#666' }}>上传(MB/s)</div>
                  </div>
                </Col>
                <Col span={8}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 24, color: performance.network.packetLoss > 0 ? '#ff4d4f' : '#52c41a' }}>
                      {performance.network.packetLoss}%
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>丢包率</div>
                  </div>
                </Col>
              </Row>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* 系统信息 */}
      <Card title="系统信息" size="small" style={{ marginTop: 16 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={6}>
            <div style={{ textAlign: 'center' }}>
              <ClockCircleOutlined style={{ fontSize: 24, color: '#1890ff' }} />
              <div style={{ fontSize: 18, fontWeight: 'bold', marginTop: 4 }}>
                {performance.system.uptime}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>运行时间</div>
            </div>
          </Col>
          <Col xs={24} sm={6}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 'bold', color: '#52c41a' }}>
                {performance.system.loadAverage[0].toFixed(2)}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>系统负载(1分钟)</div>
            </div>
          </Col>
          <Col xs={24} sm={6}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 'bold', color: '#faad14' }}>
                {performance.system.processes}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>进程数</div>
            </div>
          </Col>
          <Col xs={24} sm={6}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 'bold', color: '#722ed1' }}>
                {performance.system.threads}
              </div>
              <div style={{ fontSize: 12, color: '#666' }}>线程数</div>
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  )

  return (
    <div>
      <Card
        title={
          <Space>
            <LineChartOutlined />
            性能监控
            {alerts.length > 0 && (
              <Badge count={alerts.length} size="small">
                <WarningOutlined style={{ color: '#ff4d4f' }} />
              </Badge>
            )}
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={onRefresh}
              loading={loading}
              size="small"
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 选项卡 */}
          <div>
            <Space>
              <Button
                type={selectedTab === 'overview' ? 'primary' : 'default'}
                size="small"
                onClick={() => setSelectedTab('overview')}
              >
                概览
              </Button>
              <Button
                type={selectedTab === 'detailed' ? 'primary' : 'default'}
                size="small"
                onClick={() => setSelectedTab('detailed')}
              >
                详细信息
              </Button>
            </Space>
          </div>

          {/* 内容区域 */}
          {selectedTab === 'overview' ? renderOverview() : renderDetailedMetrics()}
        </Space>
      </Card>
    </div>
  )
}

export default PerformanceMonitor