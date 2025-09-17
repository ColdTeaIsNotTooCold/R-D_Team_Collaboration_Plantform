import React, { useState } from 'react'
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Progress,
  Statistic,
  Row,
  Col,
  List,
  Avatar,
  Typography,
  Tooltip,
  Badge
} from 'antd'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  PlusOutlined,
  FilterOutlined,
  ExportOutlined,
  EyeOutlined,
  UserOutlined,
  CalendarOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Task } from '@/types'
import { TASK_STATUS, TASK_PRIORITY, TASK_STATUS_COLORS, PRIORITY_COLORS } from '@/constants'

const { Text } = Typography

interface TaskOverviewProps {
  tasks: Task[]
  loading?: boolean
  onRefresh: () => void
  onTaskAction?: (taskId: string, action: string) => void
}

const TaskOverview: React.FC<TaskOverviewProps> = ({
  tasks,
  loading = false,
  onRefresh,
  onTaskAction
}) => {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [detailModalVisible, setDetailModalVisible] = useState(false)

  const showTaskDetail = (task: Task) => {
    setSelectedTask(task)
    setDetailModalVisible(true)
  }

  const getPriorityBadge = (priority: string) => {
    const priorityConfig = {
      [TASK_PRIORITY.HIGH]: { color: 'red', text: '高' },
      [TASK_PRIORITY.MEDIUM]: { color: 'orange', text: '中' },
      [TASK_PRIORITY.LOW]: { color: 'default', text: '低' }
    }

    const config = priorityConfig[priority as keyof typeof priorityConfig] || { color: 'default', text: '未知' }

    return (
      <Badge
        color={config.color}
        text={config.text}
      />
    )
  }

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      [TASK_STATUS.PENDING]: { status: 'default', text: '待处理' },
      [TASK_STATUS.RUNNING]: { status: 'processing', text: '运行中' },
      [TASK_STATUS.COMPLETED]: { status: 'success', text: '已完成' },
      [TASK_STATUS.FAILED]: { status: 'error', text: '失败' }
    }

    const config = statusConfig[status as keyof typeof statusConfig] || { status: 'default', text: '未知' }

    return (
      <Badge
        status={config.status as any}
        text={config.text}
      />
    )
  }

  const getProgressPercentage = () => {
    if (tasks.length === 0) return 0
    const completedTasks = tasks.filter(task => task.status === TASK_STATUS.COMPLETED).length
    return Math.round((completedTasks / tasks.length) * 100)
  }

  const getRecentTasks = () => {
    return tasks
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, 5)
  }

  const getOverdueTasks = () => {
    const now = new Date()
    return tasks.filter(task => {
      if (task.dueDate && task.status !== TASK_STATUS.COMPLETED) {
        return new Date(task.dueDate) < now
      }
      return false
    })
  }

  const columns: ColumnsType<Task> = [
    {
      title: '任务标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: Task) => (
        <Space>
          <div style={{ maxWidth: 200 }}>
            <div style={{ fontWeight: 500 }}>{text}</div>
            <div style={{ fontSize: 12, color: '#666' }}>
              {record.description.substring(0, 50)}...
            </div>
          </div>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusBadge(status),
      sorter: (a, b) => a.status.localeCompare(b.status),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => getPriorityBadge(priority),
      sorter: (a, b) => a.priority.localeCompare(b.priority),
    },
    {
      title: '分配给',
      dataIndex: 'assignedTo',
      key: 'assignedTo',
      render: (assignedTo: string) => (
        <Space>
          <Avatar size="small" icon={<UserOutlined />} />
          <span>{assignedTo || '未分配'}</span>
        </Space>
      ),
    },
    {
      title: '截止时间',
      dataIndex: 'dueDate',
      key: 'dueDate',
      render: (dueDate: string) => {
        if (!dueDate) return '-'

        const due = new Date(dueDate)
        const now = new Date()
        const isOverdue = due < now

        return (
          <Text type={isOverdue ? 'danger' : undefined}>
            {due.toLocaleDateString()}
          </Text>
        )
      },
      sorter: (a, b) => {
        if (!a.dueDate) return -1
        if (!b.dueDate) return 1
        return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime()
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => showTaskDetail(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  const taskStats = {
    total: tasks.length,
    pending: tasks.filter(t => t.status === TASK_STATUS.PENDING).length,
    running: tasks.filter(t => t.status === TASK_STATUS.RUNNING).length,
    completed: tasks.filter(t => t.status === TASK_STATUS.COMPLETED).length,
    failed: tasks.filter(t => t.status === TASK_STATUS.FAILED).length,
    overdue: getOverdueTasks().length
  }

  return (
    <div>
      {/* 任务统计概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic
              title="任务总数"
              value={taskStats.total}
              prefix={<CalendarOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic
              title="进行中"
              value={taskStats.running}
              valueStyle={{ color: '#faad14' }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic
              title="已完成"
              value={taskStats.completed}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic
              title="失败/逾期"
              value={taskStats.failed + taskStats.overdue}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 任务进度和最近任务 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card
            title="任务列表"
            extra={
              <Space>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  size="small"
                >
                  新建任务
                </Button>
                <Button
                  icon={<FilterOutlined />}
                  size="small"
                >
                  筛选
                </Button>
                <Button
                  icon={<ExportOutlined />}
                  size="small"
                >
                  导出
                </Button>
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
            <Table
              dataSource={tasks}
              columns={columns}
              rowKey="id"
              loading={loading}
              pagination={{
                pageSize: 8,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
              }}
              scroll={{ x: 800 }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          {/* 任务进度 */}
          <Card title="任务进度" size="small" style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <Text strong>总体进度</Text>
                <Text>{getProgressPercentage()}%</Text>
              </div>
              <Progress
                percent={getProgressPercentage()}
                strokeColor={{
                  '0%': '#ff4d4f',
                  '50%': '#faad14',
                  '100%': '#52c41a',
                }}
              />
            </div>

            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>待处理</Text>
                <Text>{taskStats.pending}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>运行中</Text>
                <Text>{taskStats.running}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>已完成</Text>
                <Text>{taskStats.completed}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>失败</Text>
                <Text>{taskStats.failed}</Text>
              </div>
            </Space>
          </Card>

          {/* 最近任务 */}
          <Card title="最近任务" size="small">
            <List
              dataSource={getRecentTasks()}
              size="small"
              renderItem={(task) => (
                <List.Item
                  actions={[
                    <Button
                      type="link"
                      size="small"
                      icon={<EyeOutlined />}
                      onClick={() => showTaskDetail(task)}
                    >
                      查看
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    avatar={
                      <Avatar
                        size="small"
                        style={{ backgroundColor: TASK_STATUS_COLORS[task.status as keyof typeof TASK_STATUS_COLORS] }}
                      >
                        {task.title.charAt(0)}
                      </Avatar>
                    }
                    title={
                      <div style={{ maxWidth: 150 }}>
                        <Text ellipsis>{task.title}</Text>
                      </div>
                    }
                    description={
                      <Space size="small">
                        <Tag color={PRIORITY_COLORS[task.priority as keyof typeof PRIORITY_COLORS]}>
                          {task.priority === 'high' ? '高' : task.priority === 'medium' ? '中' : '低'}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {new Date(task.createdAt).toLocaleDateString()}
                        </Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      {/* 任务详情弹窗 */}
      <Modal
        title={`任务详情 - ${selectedTask?.title}`}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={700}
      >
        {selectedTask && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={8}>
                <Space direction="vertical" style={{ width: '100%' }} size="small">
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 48, marginBottom: 8 }}>
                      {getStatusBadge(selectedTask.status)}
                    </div>
                    <Progress
                      percent={selectedTask.status === TASK_STATUS.COMPLETED ? 100 :
                              selectedTask.status === TASK_STATUS.RUNNING ? 50 : 0}
                      size="small"
                    />
                  </div>
                </Space>
              </Col>
              <Col span={16}>
                <Space direction="vertical" style={{ width: '100%' }} size="small">
                  <div>
                    <strong>标题：</strong> {selectedTask.title}
                  </div>
                  <div>
                    <strong>描述：</strong> {selectedTask.description}
                  </div>
                  <div>
                    <strong>状态：</strong> {getStatusBadge(selectedTask.status)}
                  </div>
                  <div>
                    <strong>优先级：</strong> {getPriorityBadge(selectedTask.priority)}
                  </div>
                  <div>
                    <strong>分配给：</strong> {selectedTask.assignedTo || '未分配'}
                  </div>
                  <div>
                    <strong>创建时间：</strong> {new Date(selectedTask.createdAt).toLocaleString()}
                  </div>
                  <div>
                    <strong>更新时间：</strong> {new Date(selectedTask.updatedAt).toLocaleString()}
                  </div>
                  {selectedTask.dueDate && (
                    <div>
                      <strong>截止时间：</strong> {new Date(selectedTask.dueDate).toLocaleString()}
                    </div>
                  )}
                </Space>
              </Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default TaskOverview