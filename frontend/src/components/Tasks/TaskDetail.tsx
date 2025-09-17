import React, { useState, useEffect } from 'react'
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Timeline,
  Modal,
  message,
  Progress,
  Divider
} from 'antd'
import {
  EditOutlined,
  DeleteOutlined,
  ArrowLeftOutlined,
  ClockCircleOutlined,
  UserOutlined
} from '@ant-design/icons'
import type { Task, Agent } from '@/types'
import { TASK_STATUS, TASK_PRIORITY, TASK_STATUS_COLORS, PRIORITY_COLORS } from '@/constants'
import dayjs from 'dayjs'

const { Item: DescriptionsItem } = Descriptions

interface TaskDetailProps {
  task: Task
  agents: Agent[]
  onEdit: (task: Task) => void
  onDelete: (id: string) => void
  onBack: () => void
  onClose: () => void
}

const TaskDetail: React.FC<TaskDetailProps> = ({
  task,
  agents,
  onEdit,
  onDelete,
  onBack,
  onClose
}) => {
  const [progress, setProgress] = useState(0)
  const [timeLineItems, setTimeLineItems] = useState<any[]>([])

  useEffect(() => {
    // 计算任务进度
    if (task.status === TASK_STATUS.COMPLETED) {
      setProgress(100)
    } else if (task.status === TASK_STATUS.RUNNING) {
      setProgress(50)
    } else {
      setProgress(0)
    }

    // 生成时间线
    const timeline = [
      {
        color: 'green',
        children: (
          <div>
            <p>任务创建</p>
            <p className="text-gray-500 text-sm">{dayjs(task.createdAt).format('YYYY-MM-DD HH:mm')}</p>
          </div>
        ),
      },
    ]

    if (task.dueDate) {
      timeline.push({
        color: task.status === TASK_STATUS.COMPLETED ? 'green' : 'blue',
        children: (
          <div>
            <p>截止日期</p>
            <p className="text-gray-500 text-sm">{dayjs(task.dueDate).format('YYYY-MM-DD')}</p>
          </div>
        ),
      })
    }

    if (task.status === TASK_STATUS.COMPLETED) {
      timeline.push({
        color: 'green',
        children: (
          <div>
            <p>任务完成</p>
            <p className="text-gray-500 text-sm">{dayjs(task.updatedAt).format('YYYY-MM-DD HH:mm')}</p>
          </div>
        ),
      })
    }

    setTimeLineItems(timeline)
  }, [task])

  const getPriorityText = (priority: string) => {
    switch (priority) {
      case TASK_PRIORITY.HIGH:
        return '高优先级'
      case TASK_PRIORITY.MEDIUM:
        return '中优先级'
      case TASK_PRIORITY.LOW:
        return '低优先级'
      default:
        return '未知'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case TASK_STATUS.PENDING:
        return '待处理'
      case TASK_STATUS.RUNNING:
        return '运行中'
      case TASK_STATUS.COMPLETED:
        return '已完成'
      case TASK_STATUS.FAILED:
        return '失败'
      default:
        return '未知'
    }
  }

  const getAssignedAgent = () => {
    if (!task.assignedTo) return '未分配'
    const agent = agents.find(a => a.id === task.assignedTo)
    return agent ? agent.name : '未知智能体'
  }

  const handleDelete = () => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个任务吗？此操作不可恢复。',
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => {
        onDelete(task.id)
        message.success('任务已删除')
      }
    })
  }

  return (
    <div className="task-detail">
      <div className="mb-4">
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={onBack}>
            返回列表
          </Button>
          <Button type="primary" icon={<EditOutlined />} onClick={() => onEdit(task)}>
            编辑任务
          </Button>
          <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
            删除任务
          </Button>
        </Space>
      </div>

      <Card title="任务详情" className="mb-4">
        <Descriptions bordered column={2}>
          <DescriptionsItem label="任务标题" span={2}>
            <h3 className="text-lg font-semibold">{task.title}</h3>
          </DescriptionsItem>

          <DescriptionsItem label="任务描述" span={2}>
            <p className="text-gray-700">{task.description}</p>
          </DescriptionsItem>

          <DescriptionsItem label="状态">
            <Tag color={TASK_STATUS_COLORS[task.status as keyof typeof TASK_STATUS_COLORS]}>
              {getStatusText(task.status)}
            </Tag>
          </DescriptionsItem>

          <DescriptionsItem label="优先级">
            <Tag color={PRIORITY_COLORS[task.priority as keyof typeof PRIORITY_COLORS]}>
              {getPriorityText(task.priority)}
            </Tag>
          </DescriptionsItem>

          <DescriptionsItem label="分配给">
            <Tag icon={<UserOutlined />}>
              {getAssignedAgent()}
            </Tag>
          </DescriptionsItem>

          <DescriptionsItem label="截止日期">
            {task.dueDate ? dayjs(task.dueDate).format('YYYY-MM-DD') : '未设置'}
          </DescriptionsItem>

          <DescriptionsItem label="创建时间">
            {dayjs(task.createdAt).format('YYYY-MM-DD HH:mm:ss')}
          </DescriptionsItem>

          <DescriptionsItem label="更新时间">
            {dayjs(task.updatedAt).format('YYYY-MM-DD HH:mm:ss')}
          </DescriptionsItem>
        </Descriptions>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="任务进度">
          <Progress
            percent={progress}
            status={task.status === TASK_STATUS.FAILED ? 'exception' : 'active'}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
          <div className="mt-4 text-center">
            <p className="text-lg font-semibold">{progress}%</p>
            <p className="text-gray-500">{getStatusText(task.status)}</p>
          </div>
        </Card>

        <Card title="任务时间线">
          <Timeline mode="left" items={timeLineItems} />
        </Card>
      </div>
    </div>
  )
}

export default TaskDetail