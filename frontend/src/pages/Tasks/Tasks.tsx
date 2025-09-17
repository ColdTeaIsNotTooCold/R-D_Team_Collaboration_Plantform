import React, { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  message,
  Popconfirm,
  Row,
  Col,
  Badge
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  FilterOutlined,
  ReloadOutlined,
  SettingOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Task } from '@/types'
import { tasksApi, agentsApi } from '@/api'
import { TASK_STATUS, TASK_PRIORITY, TASK_STATUS_COLORS, PRIORITY_COLORS } from '@/constants'
import type { Agent } from '@/types'
import dayjs from 'dayjs'

// 导入新组件
import TaskDetail from '@/components/Tasks/TaskDetail'
import TaskFilters from '@/components/Tasks/TaskFilters'
import type { TaskFilters as TaskFiltersType } from '@/components/Tasks/TaskFilters'
import TaskBatchActions from '@/components/Tasks/TaskBatchActions'
import { taskRealtimeService, type TaskUpdateEvent } from '@/services/taskRealtimeService'

const { Option } = Select
const { TextArea } = Input

const Tasks: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([])
  const [filteredTasks, setFilteredTasks] = useState<Task[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [showFilters, setShowFilters] = useState(false)
  const [currentFilters, setCurrentFilters] = useState<TaskFiltersType>({})
  const [viewMode, setViewMode] = useState<'list' | 'detail'>('list')

  useEffect(() => {
    fetchTasks()
    fetchAgents()

    // 订阅实时更新
    const unsubscribe = taskRealtimeService.subscribe(handleTaskUpdate)

    return () => {
      unsubscribe()
    }
  }, [])

  // 初始化时设置过滤任务
  useEffect(() => {
    applyFilters(currentFilters)
  }, [tasks, currentFilters])

  const fetchTasks = async () => {
    try {
      setLoading(true)
      const response = await tasksApi.getTasks()
      setTasks(response.data)
      setFilteredTasks(response.data)
    } catch (error) {
      message.error('获取任务列表失败')
    } finally {
      setLoading(false)
    }
  }

  // 处理实时任务更新
  const handleTaskUpdate = useCallback((event: TaskUpdateEvent) => {
    switch (event.type) {
      case 'task_created':
        setTasks(prev => [...prev, event.task])
        break
      case 'task_updated':
        setTasks(prev => prev.map(task =>
          task.id === event.task.id ? event.task : task
        ))
        break
      case 'task_deleted':
        setTasks(prev => prev.filter(task => task.id !== event.task.id))
        break
      case 'task_assigned':
        setTasks(prev => prev.map(task =>
          task.id === event.task.id ? event.task : task
        ))
        break
    }
  }, [])

  // 应用筛选
  const applyFilters = useCallback((filters: TaskFiltersType) => {
    let filtered = [...tasks]

    if (filters.search) {
      const searchLower = filters.search.toLowerCase()
      filtered = filtered.filter(task =>
        task.title.toLowerCase().includes(searchLower) ||
        task.description.toLowerCase().includes(searchLower)
      )
    }

    if (filters.status) {
      filtered = filtered.filter(task => task.status === filters.status)
    }

    if (filters.priority) {
      filtered = filtered.filter(task => task.priority === filters.priority)
    }

    if (filters.assignedTo) {
      filtered = filtered.filter(task => task.assignedTo === filters.assignedTo)
    }

    if (filters.dateRange) {
      const [start, end] = filters.dateRange
      filtered = filtered.filter(task => {
        const taskDate = dayjs(task.createdAt)
        return taskDate.isAfter(start.startOf('day')) &&
               taskDate.isBefore(end.endOf('day'))
      })
    }

    setFilteredTasks(filtered)
  }, [tasks])

  // 处理筛选变化
  const handleFilterChange = useCallback((filters: TaskFiltersType) => {
    setCurrentFilters(filters)
    applyFilters(filters)
  }, [applyFilters])

  // 清除筛选
  const handleClearFilters = useCallback(() => {
    setCurrentFilters({})
    setFilteredTasks(tasks)
  }, [tasks])

  // 处理任务选择
  const handleRowSelect = useCallback((selectedRowKeys: React.Key[]) => {
    setSelectedRowKeys(selectedRowKeys)
  }, [])

  // 批量操作完成
  const handleBatchComplete = useCallback(() => {
    setSelectedRowKeys([])
  }, [])

  // 查看任务详情
  const handleViewDetail = useCallback((task: Task) => {
    setSelectedTask(task)
    setViewMode('detail')
  }, [])

  // 返回列表
  const handleBackToList = useCallback(() => {
    setViewMode('list')
    setSelectedTask(null)
  }, [])

  const fetchAgents = async () => {
    try {
      const response = await agentsApi.getAgents()
      setAgents(response.data)
    } catch (error) {
      console.error('获取智能体列表失败:', error)
    }
  }

  const handleAdd = () => {
    setEditingTask(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (task: Task) => {
    setEditingTask(task)
    form.setFieldsValue({
      ...task,
      dueDate: task.dueDate ? dayjs(task.dueDate) : null
    })
    setModalVisible(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await tasksApi.deleteTask(id)
      message.success('删除成功')
      fetchTasks()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      const taskData = {
        ...values,
        dueDate: values.dueDate ? values.dueDate.format('YYYY-MM-DD') : undefined
      }

      if (editingTask) {
        await tasksApi.updateTask(editingTask.id, taskData)
        message.success('更新成功')
      } else {
        await tasksApi.createTask(taskData)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchTasks()
    } catch (error) {
      message.error(editingTask ? '更新失败' : '创建失败')
    }
  }

  const rowSelection = {
    selectedRowKeys,
    onChange: handleRowSelect,
  }

  const columns: ColumnsType<Task> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: Task) => (
        <Button
          type="link"
          onClick={() => handleViewDetail(record)}
          className="p-0 h-auto"
        >
          {text}
        </Button>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 200,
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
        <Tag color={PRIORITY_COLORS[priority as keyof typeof PRIORITY_COLORS]}>
          {priority === TASK_PRIORITY.HIGH ? '高' : priority === TASK_PRIORITY.MEDIUM ? '中' : '低'}
        </Tag>
      ),
    },
    {
      title: '分配给',
      dataIndex: 'assignedTo',
      key: 'assignedTo',
      render: (assignedTo: string) => {
        const agent = agents.find(a => a.id === assignedTo)
        return agent ? (
          <Badge
            status={agent.status === 'idle' ? 'default' :
                   agent.status === 'running' ? 'processing' :
                   agent.status === 'error' ? 'error' : 'success'}
            text={agent.name}
          />
        ) : '未分配'
      },
    },
    {
      title: '截止日期',
      dataIndex: 'dueDate',
      key: 'dueDate',
      render: (dueDate: string) => dueDate ? (
        <Badge
          status={dayjs(dueDate).isBefore(dayjs()) ? 'error' : 'default'}
          text={dayjs(dueDate).format('YYYY-MM-DD')}
        />
      ) : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm'),
      width: 150,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
            title="查看详情"
          />
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            title="编辑任务"
          />
          <Popconfirm
            title="确定要删除这个任务吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              title="删除任务"
            />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 获取选中的任务
  const selectedTasks = tasks.filter(task => selectedRowKeys.includes(task.id))

  // 如果是详情视图，显示任务详情
  if (viewMode === 'detail' && selectedTask) {
    return (
      <TaskDetail
        task={selectedTask}
        agents={agents}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onBack={handleBackToList}
        onClose={handleBackToList}
      />
    )
  }

  return (
    <div className="tasks-page">
      {/* 批量操作栏 */}
      <TaskBatchActions
        selectedTasks={selectedTasks}
        agents={agents}
        onBatchComplete={handleBatchComplete}
        onRefresh={fetchTasks}
      />

      {/* 主内容区域 */}
      <Card
        title={
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <span>任务管理</span>
              <Badge count={filteredTasks.length} className="ml-2" />
            </div>
            <Space>
              <Button
                icon={<FilterOutlined />}
                onClick={() => setShowFilters(!showFilters)}
                type={showFilters ? 'primary' : 'default'}
              >
                筛选
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchTasks}
                loading={loading}
              >
                刷新
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                添加任务
              </Button>
            </Space>
          </div>
        }
      >
        {/* 筛选器 */}
        {showFilters && (
          <div className="mb-4">
            <TaskFilters
              onFilterChange={handleFilterChange}
              onClearFilters={handleClearFilters}
              agents={agents}
              loading={loading}
            />
          </div>
        )}

        {/* 任务表格 */}
        <Table
          dataSource={filteredTasks}
          columns={columns}
          rowKey="id"
          rowSelection={rowSelection}
          loading={loading}
          pagination={{
            total: filteredTasks.length,
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `显示 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
          scroll={{ x: 1200 }}
          size="middle"
        />
      </Card>

      <Modal
        title={editingTask ? '编辑任务' : '添加任务'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            label="标题"
            name="title"
            rules={[{ required: true, message: '请输入任务标题' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="描述"
            name="description"
            rules={[{ required: true, message: '请输入任务描述' }]}
          >
            <TextArea rows={3} />
          </Form.Item>
          <Form.Item
            label="优先级"
            name="priority"
            rules={[{ required: true, message: '请选择优先级' }]}
          >
            <Select>
              <Option value={TASK_PRIORITY.LOW}>低</Option>
              <Option value={TASK_PRIORITY.MEDIUM}>中</Option>
              <Option value={TASK_PRIORITY.HIGH}>高</Option>
            </Select>
          </Form.Item>
          <Form.Item
            label="分配给"
            name="assignedTo"
          >
            <Select placeholder="选择智能体" allowClear>
              {agents.map(agent => (
                <Option key={agent.id} value={agent.id}>
                  {agent.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="截止日期"
            name="dueDate"
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingTask ? '更新' : '创建'}
              </Button>
              <Button onClick={() => setModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Tasks