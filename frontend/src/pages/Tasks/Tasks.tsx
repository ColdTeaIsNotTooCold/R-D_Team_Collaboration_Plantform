import React, { useState, useEffect } from 'react'
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
  Popconfirm
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Task } from '@/types'
import { tasksApi, agentsApi } from '@/api'
import { TASK_STATUS, TASK_PRIORITY, TASK_STATUS_COLORS, PRIORITY_COLORS } from '@/constants'
import type { Agent } from '@/types'
import dayjs from 'dayjs'

const { Option } = Select
const { TextArea } = Input

const Tasks: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()
  const [editingTask, setEditingTask] = useState<Task | null>(null)

  useEffect(() => {
    fetchTasks()
    fetchAgents()
  }, [])

  const fetchTasks = async () => {
    try {
      setLoading(true)
      const data = await tasksApi.getTasks()
      setTasks(data)
    } catch (error) {
      message.error('获取任务列表失败')
    } finally {
      setLoading(false)
    }
  }

  const fetchAgents = async () => {
    try {
      const data = await agentsApi.getAgents()
      setAgents(data)
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

  const columns: ColumnsType<Task> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
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
        return agent ? agent.name : '未分配'
      },
    },
    {
      title: '截止日期',
      dataIndex: 'dueDate',
      key: 'dueDate',
      render: (dueDate: string) => dueDate ? new Date(dueDate).toLocaleDateString() : '-',
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
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleEdit(record)}
          >
            查看
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个任务吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card
        title="任务管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加任务
          </Button>
        }
      >
        <Table
          dataSource={tasks}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            total: tasks.length,
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
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