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
  message,
  Popconfirm
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Agent } from '@/types'
import { agentsApi } from '@/api'
import { AGENT_STATUS, STATUS_COLORS } from '@/constants'

const { Option } = Select

const Agents: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [form] = Form.useForm()
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null)

  useEffect(() => {
    fetchAgents()
  }, [])

  const fetchAgents = async () => {
    try {
      setLoading(true)
      const response = await agentsApi.getAgents()
      setAgents(response.data)
    } catch (error) {
      message.error('获取智能体列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = () => {
    setEditingAgent(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (agent: Agent) => {
    setEditingAgent(agent)
    form.setFieldsValue(agent)
    setModalVisible(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await agentsApi.deleteAgent(id)
      message.success('删除成功')
      fetchAgents()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      if (editingAgent) {
        await agentsApi.updateAgent(editingAgent.id, values)
        message.success('更新成功')
      } else {
        await agentsApi.createAgent(values)
        message.success('创建成功')
      }
      setModalVisible(false)
      fetchAgents()
    } catch (error) {
      message.error(editingAgent ? '更新失败' : '创建失败')
    }
  }

  const handleStartStop = async (agent: Agent) => {
    try {
      if (agent.status === AGENT_STATUS.RUNNING) {
        await agentsApi.stopAgent(agent.id)
        message.success('停止成功')
      } else {
        await agentsApi.startAgent(agent.id)
        message.success('启动成功')
      }
      fetchAgents()
    } catch (error) {
      message.error(agent.status === AGENT_STATUS.RUNNING ? '停止失败' : '启动失败')
    }
  }

  const columns: ColumnsType<Agent> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
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
          <Button
            size="small"
            type="primary"
            icon={record.status === AGENT_STATUS.RUNNING ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() => handleStartStop(record)}
          >
            {record.status === AGENT_STATUS.RUNNING ? '停止' : '启动'}
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个智能体吗？"
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
        title="智能体管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加智能体
          </Button>
        }
      >
        <Table
          dataSource={agents}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            total: agents.length,
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      <Modal
        title={editingAgent ? '编辑智能体' : '添加智能体'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            label="名称"
            name="name"
            rules={[{ required: true, message: '请输入智能体名称' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="描述"
            name="description"
            rules={[{ required: true, message: '请输入智能体描述' }]}
          >
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item
            label="类型"
            name="type"
            rules={[{ required: true, message: '请选择智能体类型' }]}
          >
            <Select>
              <Option value="chat">对话型</Option>
              <Option value="task">任务型</Option>
              <Option value="analysis">分析型</Option>
              <Option value="monitor">监控型</Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingAgent ? '更新' : '创建'}
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

export default Agents