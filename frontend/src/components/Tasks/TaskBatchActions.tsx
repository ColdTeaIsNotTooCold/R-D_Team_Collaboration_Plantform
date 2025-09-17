import React, { useState } from 'react'
import {
  Button,
  Dropdown,
  Menu,
  Modal,
  message,
  Tag,
  Space,
  Alert
} from 'antd'
import {
  MoreOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  UserOutlined
} from '@ant-design/icons'
import type { Task, Agent } from '@/types'
import { TASK_STATUS, TASK_PRIORITY } from '@/constants'
import { tasksApi } from '@/api'

interface TaskBatchActionsProps {
  selectedTasks: Task[]
  agents: Agent[]
  onBatchComplete: () => void
  onRefresh: () => void
}

const TaskBatchActions: React.FC<TaskBatchActionsProps> = ({
  selectedTasks,
  agents,
  onBatchComplete,
  onRefresh
}) => {
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [batchAction, setBatchAction] = useState<string>('')
  const [selectedAgent, setSelectedAgent] = useState<string>('')

  if (selectedTasks.length === 0) {
    return null
  }

  const handleBatchAction = async (action: string) => {
    if (action === 'delete') {
      Modal.confirm({
        title: '确认批量删除',
        content: `确定要删除选中的 ${selectedTasks.length} 个任务吗？此操作不可恢复。`,
        okText: '删除',
        cancelText: '取消',
        okButtonProps: { danger: true },
        onOk: async () => {
          await executeBatchAction('delete')
        }
      })
    } else if (action === 'assign') {
      setBatchAction('assign')
      setModalVisible(true)
    } else {
      await executeBatchAction(action)
    }
  }

  const executeBatchAction = async (action: string) => {
    setLoading(true)
    try {
      const taskIds = selectedTasks.map(task => task.id)

      switch (action) {
        case 'delete':
          await Promise.all(taskIds.map(id => tasksApi.deleteTask(id)))
          message.success(`成功删除 ${taskIds.length} 个任务`)
          break

        case 'complete':
          await Promise.all(taskIds.map(id =>
            tasksApi.updateTask(id, { status: TASK_STATUS.COMPLETED })
          ))
          message.success(`成功完成 ${taskIds.length} 个任务`)
          break

        case 'pending':
          await Promise.all(taskIds.map(id =>
            tasksApi.updateTask(id, { status: TASK_STATUS.PENDING })
          ))
          message.success(`成功将 ${taskIds.length} 个任务设为待处理`)
          break

        case 'running':
          await Promise.all(taskIds.map(id =>
            tasksApi.updateTask(id, { status: TASK_STATUS.RUNNING })
          ))
          message.success(`成功启动 ${taskIds.length} 个任务`)
          break

        case 'assign':
          if (!selectedAgent) {
            message.error('请选择要分配的智能体')
            return
          }
          await Promise.all(taskIds.map(id =>
            tasksApi.updateTask(id, { assignedTo: selectedAgent })
          ))
          message.success(`成功将 ${taskIds.length} 个任务分配给选中的智能体`)
          break

        default:
          message.error('未知的批量操作')
          return
      }

      onBatchComplete()
      onRefresh()
    } catch (error) {
      message.error('批量操作失败')
    } finally {
      setLoading(false)
      setModalVisible(false)
      setBatchAction('')
      setSelectedAgent('')
    }
  }

  const menu = (
    <Menu
      items={[
        {
          key: 'complete',
          icon: <CheckOutlined />,
          label: '标记为已完成',
          onClick: () => handleBatchAction('complete')
        },
        {
          key: 'pending',
          icon: <PauseCircleOutlined />,
          label: '标记为待处理',
          onClick: () => handleBatchAction('pending')
        },
        {
          key: 'running',
          icon: <PlayCircleOutlined />,
          label: '标记为运行中',
          onClick: () => handleBatchAction('running')
        },
        {
          key: 'assign',
          icon: <UserOutlined />,
          label: '分配给智能体',
          onClick: () => handleBatchAction('assign')
        },
        {
          type: 'divider'
        },
        {
          key: 'delete',
          icon: <DeleteOutlined />,
          label: '删除任务',
          danger: true,
          onClick: () => handleBatchAction('delete')
        }
      ]}
    />
  )

  const getStatusSummary = () => {
    const summary = {
      pending: 0,
      running: 0,
      completed: 0,
      failed: 0
    }

    selectedTasks.forEach(task => {
      summary[task.status as keyof typeof summary]++
    })

    return summary
  }

  const statusSummary = getStatusSummary()

  return (
    <div className="batch-actions">
      <Alert
        message={`已选择 ${selectedTasks.length} 个任务`}
        description={
          <Space wrap>
            <Tag color="default">待处理: {statusSummary.pending}</Tag>
            <Tag color="processing">运行中: {statusSummary.running}</Tag>
            <Tag color="success">已完成: {statusSummary.completed}</Tag>
            <Tag color="error">失败: {statusSummary.failed}</Tag>
          </Space>
        }
        type="info"
        showIcon
        action={
          <Space>
            <Dropdown overlay={menu} trigger={['click']}>
              <Button icon={<MoreOutlined />} loading={loading}>
                批量操作
              </Button>
            </Dropdown>
          </Space>
        }
        className="mb-4"
      />

      <Modal
        title="批量分配任务"
        open={modalVisible}
        onOk={() => executeBatchAction('assign')}
        onCancel={() => setModalVisible(false)}
        confirmLoading={loading}
      >
        <div className="mb-4">
          <p>将 {selectedTasks.length} 个任务分配给以下智能体：</p>
          <div className="grid grid-cols-1 gap-2 mt-4">
            {agents.map(agent => (
              <div
                key={agent.id}
                className={`p-3 border rounded cursor-pointer hover:bg-gray-50 ${
                  selectedAgent === agent.id ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
                }`}
                onClick={() => setSelectedAgent(agent.id)}
              >
                <div className="flex items-center">
                  <div className={`w-3 h-3 rounded-full mr-2 ${
                    agent.status === 'idle' ? 'bg-gray-400' :
                    agent.status === 'running' ? 'bg-green-500' :
                    agent.status === 'error' ? 'bg-red-500' : 'bg-blue-500'
                  }`} />
                  <div>
                    <div className="font-medium">{agent.name}</div>
                    <div className="text-sm text-gray-500">{agent.description}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default TaskBatchActions