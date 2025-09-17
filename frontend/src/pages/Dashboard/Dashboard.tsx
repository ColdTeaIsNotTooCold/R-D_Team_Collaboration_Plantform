import React, { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Button,
  Space,
  Tabs,
  Badge,
  Typography
} from 'antd'
import {
  ReloadOutlined,
  WifiOutlined,
  DisconnectOutlined,
  WarningOutlined,
  RocketOutlined,
  LineChartOutlined
} from '@ant-design/icons'
import type { Agent, Task, SystemStatus } from '@/types'
import { agentsApi, tasksApi } from '@/api'
import { AGENT_STATUS, TASK_STATUS } from '@/constants'
import { useRealtimeData } from '@/services/realtimeService'
import SystemOverview from '@/components/Dashboard/SystemOverview'
import AgentMonitor from '@/components/Dashboard/AgentMonitor'
import TaskOverview from '@/components/Dashboard/TaskOverview'
import PerformanceMonitor from '@/components/Dashboard/PerformanceMonitor'
import ErrorHandler, { DashboardSkeleton, StatusIndicator } from '@/components/Dashboard/ErrorHandler'

const { Text } = Typography

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [agents, setAgents] = useState<Agent[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    status: 'healthy',
    agents: { total: 0, running: 0, idle: 0, error: 0 },
    tasks: { total: 0, pending: 0, running: 0, completed: 0, failed: 0 },
    uptime: '0分钟'
  })
  const [performance, setPerformance] = useState({
    cpu: 0,
    memory: 0,
    disk: 0,
    network: 0
  })
  const [connectionStatus, setConnectionStatus] = useState({ connected: false, reconnecting: false })
  const [error, setError] = useState<Error | string | null>(null)

  // 初始化实时数据服务
  const realtimeService = useRealtimeData()

  useEffect(() => {
    fetchData()
    setupRealtimeService()
    return () => {
      realtimeService.disconnect()
    }
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [agentsData, tasksData] = await Promise.all([
        agentsApi.getAgents(),
        tasksApi.getTasks()
      ])

      setAgents(agentsData)
      setTasks(tasksData)
      updateSystemStatus(agentsData, tasksData)
    } catch (error) {
      console.error('获取数据失败:', error)
      setError(error instanceof Error ? error : '获取数据失败')
    } finally {
      setLoading(false)
    }
  }

  const updateSystemStatus = (agentsData: Agent[], tasksData: Task[]) => {
    const agentStats = {
      total: agentsData.length,
      running: agentsData.filter(a => a.status === AGENT_STATUS.RUNNING).length,
      idle: agentsData.filter(a => a.status === AGENT_STATUS.IDLE).length,
      error: agentsData.filter(a => a.status === AGENT_STATUS.ERROR).length
    }

    const taskStats = {
      total: tasksData.length,
      pending: tasksData.filter(t => t.status === TASK_STATUS.PENDING).length,
      running: tasksData.filter(t => t.status === TASK_STATUS.RUNNING).length,
      completed: tasksData.filter(t => t.status === TASK_STATUS.COMPLETED).length,
      failed: tasksData.filter(t => t.status === TASK_STATUS.FAILED).length
    }

    setSystemStatus({
      status: agentStats.error > 0 ? 'error' : 'healthy',
      agents: agentStats,
      tasks: taskStats,
      uptime: '5分钟' // 模拟数据
    })
  }

  const setupRealtimeService = () => {
    // 连接状态监听
    realtimeService.onConnectionChange((status) => {
      setConnectionStatus(status)
    })

    // Agent更新监听
    realtimeService.onAgentUpdate((agent) => {
      setAgents(prev => {
        const index = prev.findIndex(a => a.id === agent.id)
        if (index >= 0) {
          const updated = [...prev]
          updated[index] = agent
          updateSystemStatus(updated, tasks)
          return updated
        }
        return [...prev, agent]
      })
    })

    // 任务更新监听
    realtimeService.onTaskUpdate((task) => {
      setTasks(prev => {
        const index = prev.findIndex(t => t.id === task.id)
        if (index >= 0) {
          const updated = [...prev]
          updated[index] = task
          updateSystemStatus(agents, updated)
          return updated
        }
        return [...prev, task]
      })
    })

    // 系统状态更新监听
    realtimeService.onSystemStatusUpdate((status) => {
      setSystemStatus(status)
    })

    // 性能指标更新监听
    realtimeService.onPerformanceUpdate((metrics) => {
      setPerformance(metrics)
    })

    // 错误事件监听
    realtimeService.onError((error) => {
      console.error('实时服务错误:', error)
      setError(error instanceof Error ? error : '实时服务连接失败')
    })

    // 连接实时服务
    realtimeService.connect()
  }

  const handleAgentAction = (agentId: string, action: 'start' | 'stop' | 'restart') => {
    // 发送Agent操作指令
    console.log(`Agent操作: ${action} ${agentId}`)
    // 这里可以调用API或通过WebSocket发送指令
  }

  const handleRefresh = () => {
    fetchData()
    // 请求实时数据更新
    realtimeService.service.requestSystemStatus()
    realtimeService.service.requestPerformanceMetrics()
  }

  return (
    <ErrorHandler
      loading={loading}
      error={error}
      connectionStatus={connectionStatus}
      onRetry={handleRefresh}
      onReconnect={() => realtimeService.connect()}
    >
      <div>
        {/* 连接状态指示器 */}
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row justify="space-between" align="middle">
            <Col xs={24} sm={16}>
              <Space wrap>
                <StatusIndicator
                  status={connectionStatus.connected ? 'success' : 'error'}
                  text={
                    connectionStatus.connected ? '实时连接正常' :
                    connectionStatus.reconnecting ? '正在重连...' : '连接断开'
                  }
                  description={
                    connectionStatus.connected ? 'WebSocket连接正常' :
                    connectionStatus.reconnecting ? '正在尝试重新连接' : '请检查网络连接'
                  }
                />
                {systemStatus.status === 'error' && (
                  <StatusIndicator
                    status="error"
                    text="系统异常"
                    description="检测到系统异常，请及时处理"
                  />
                )}
                {agents.length > 0 && (
                  <StatusIndicator
                    status="success"
                    text={`${agents.length} 个智能体`}
                    description={`${agents.filter(a => a.status === AGENT_STATUS.RUNNING).length} 运行中`}
                  />
                )}
                {tasks.length > 0 && (
                  <StatusIndicator
                    status="success"
                    text={`${tasks.length} 个任务`}
                    description={`${tasks.filter(t => t.status === TASK_STATUS.RUNNING).length} 运行中`}
                  />
                )}
              </Space>
            </Col>
            <Col xs={24} sm={8}>
              <div style={{ display: 'flex', justifyContent: { xs: 'flex-start', sm: 'flex-end' }, marginTop: { xs: 8, sm: 0 } }}>
                <Space>
                  <Button
                    type="primary"
                    icon={<ReloadOutlined />}
                    onClick={handleRefresh}
                    loading={loading}
                    size="small"
                  >
                    刷新
                  </Button>
                  <Button
                    icon={<RocketOutlined />}
                    onClick={() => realtimeService.connect()}
                    disabled={connectionStatus.connected}
                    size="small"
                  >
                    重连
                  </Button>
                </Space>
              </div>
            </Col>
          </Row>
        </Card>

        {/* 主要内容区域 */}
        <Tabs
          defaultActiveKey="overview"
          type="card"
          centered
          style={{ marginTop: 16 }}
        >
          <Tabs.TabPane
            tab={
              <Space>
                系统概览
                {systemStatus.agents.error > 0 && (
                  <Badge count={systemStatus.agents.error} size="small" />
                )}
              </Space>
            }
            key="overview"
          >
            <SystemOverview
              systemStatus={systemStatus}
              performance={performance}
            />
          </Tabs.TabPane>

          <Tabs.TabPane
            tab={
              <Space>
                智能体监控
                <Badge
                  count={agents.filter(a => a.status === AGENT_STATUS.RUNNING).length}
                  size="small"
                />
              </Space>
            }
            key="agents"
          >
            <AgentMonitor
              agents={agents}
              loading={loading}
              onRefresh={handleRefresh}
              onAgentAction={handleAgentAction}
            />
          </Tabs.TabPane>

          <Tabs.TabPane
            tab={
              <Space>
                任务管理
                <Badge
                  count={tasks.filter(t => t.status === TASK_STATUS.RUNNING).length}
                  size="small"
                />
              </Space>
            }
            key="tasks"
          >
            <TaskOverview
              tasks={tasks}
              loading={loading}
              onRefresh={handleRefresh}
            />
          </Tabs.TabPane>

          <Tabs.TabPane
            tab={
              <Space>
                性能监控
                <LineChartOutlined />
              </Space>
            }
            key="performance"
          >
            <PerformanceMonitor
              performance={performance}
              loading={loading}
              onRefresh={handleRefresh}
            />
          </Tabs.TabPane>
        </Tabs>
      </div>
    </ErrorHandler>
  )
}

export default Dashboard