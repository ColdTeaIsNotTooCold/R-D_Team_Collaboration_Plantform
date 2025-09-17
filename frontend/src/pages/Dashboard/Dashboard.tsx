import React, { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Space,
  Alert,
  Spin
} from 'antd'
import {
  RobotOutlined,
  TaskOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Agent, Task, SystemStatus } from '@/types'
import { agentsApi, tasksApi } from '@/api'
import { AGENT_STATUS, TASK_STATUS, STATUS_COLORS, TASK_STATUS_COLORS } from '@/constants'

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

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [agentsData, tasksData] = await Promise.all([
        agentsApi.getAgents(),
        tasksApi.getTasks()
      ])

      setAgents(agentsData)
      setTasks(tasksData)

      // 计算系统状态
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
    } catch (error) {
      console.error('获取数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const agentColumns: ColumnsType<Agent> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status as keyof typeof STATUS_COLORS]}>
          {status === AGENT_STATUS.RUNNING ? '运行中' :
           status === AGENT_STATUS.IDLE ? '空闲' :
           status === AGENT_STATUS.ERROR ? '错误' : '已完成'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button size="small" type="primary">
            {record.status === AGENT_STATUS.RUNNING ? '停止' : '启动'}
          </Button>
        </Space>
      ),
    },
  ]

  const taskColumns: ColumnsType<Task> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={TASK_STATUS_COLORS[status as keyof typeof TASK_STATUS_COLORS]}>
          {status === TASK_STATUS.PENDING ? '待处理' :
           status === TASK_STATUS.RUNNING ? '运行中' :
           status === TASK_STATUS.COMPLETED ? '已完成' : '失败'}
        </Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => (
        <Tag color={priority === 'high' ? 'red' : priority === 'medium' ? 'orange' : 'default'}>
          {priority === 'high' ? '高' : priority === 'medium' ? '中' : '低'}
        </Tag>
      ),
    },
    {
      title: '分配给',
      dataIndex: 'assignedTo',
      key: 'assignedTo',
      render: (assignedTo: string) => assignedTo || '未分配',
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (time: string) => new Date(time).toLocaleString(),
    },
  ]

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="系统状态"
              value={systemStatus.status === 'healthy' ? '正常' : '异常'}
              prefix={systemStatus.status === 'healthy' ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
              valueStyle={{ color: systemStatus.status === 'healthy' ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="智能体总数"
              value={systemStatus.agents.total}
              prefix={<RobotOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="任务总数"
              value={systemStatus.tasks.total}
              prefix={<TaskOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行时间"
              value={systemStatus.uptime}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title="智能体状态" extra={<Button onClick={fetchData}>刷新</Button>}>
            <Table
              dataSource={agents}
              columns={agentColumns}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="最近任务" extra={<Button onClick={fetchData}>刷新</Button>}>
            <Table
              dataSource={tasks.slice(0, 5)}
              columns={taskColumns}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard