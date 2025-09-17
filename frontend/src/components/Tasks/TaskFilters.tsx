import React from 'react'
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  DatePicker,
  Tag,
  Row,
  Col
} from 'antd'
import {
  SearchOutlined,
  FilterOutlined,
  ClearOutlined,
  ReloadOutlined
} from '@ant-design/icons'
import type { Task } from '@/types'
import { TASK_STATUS, TASK_PRIORITY } from '@/constants'
import dayjs from 'dayjs'

const { Option } = Select
const { RangePicker } = DatePicker
const { Search } = Input

interface TaskFiltersProps {
  onFilterChange: (filters: TaskFilters) => void
  onClearFilters: () => void
  agents: any[]
  loading?: boolean
}

export interface TaskFilters {
  search?: string
  status?: string
  priority?: string
  assignedTo?: string
  dateRange?: [dayjs.Dayjs, dayjs.Dayjs]
}

const TaskFilters: React.FC<TaskFiltersProps> = ({
  onFilterChange,
  onClearFilters,
  agents,
  loading = false
}) => {
  const [form] = Form.useForm()

  const handleSearch = (values: any) => {
    const filters: TaskFilters = {
      search: values.search,
      status: values.status,
      priority: values.priority,
      assignedTo: values.assignedTo,
      dateRange: values.dateRange
    }
    onFilterChange(filters)
  }

  const handleClear = () => {
    form.resetFields()
    onClearFilters()
  }

  const getActiveFiltersCount = () => {
    const values = form.getFieldsValue()
    return Object.values(values).filter(value => value !== undefined && value !== null && value !== '').length
  }

  return (
    <Card
      title={
        <div className="flex items-center">
          <FilterOutlined className="mr-2" />
          任务筛选
          {getActiveFiltersCount() > 0 && (
            <Tag color="blue" className="ml-2">
              {getActiveFiltersCount()} 个筛选条件
            </Tag>
          )}
        </div>
      }
      size="small"
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSearch}
      >
        <Row gutter={16}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="search" label="搜索任务">
              <Search
                placeholder="搜索标题或描述"
                allowClear
                enterButton={<SearchOutlined />}
                onSearch={(value) => form.submit()}
              />
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="status" label="任务状态">
              <Select
                placeholder="选择状态"
                allowClear
                onChange={() => form.submit()}
              >
                <Option value={TASK_STATUS.PENDING}>待处理</Option>
                <Option value={TASK_STATUS.RUNNING}>运行中</Option>
                <Option value={TASK_STATUS.COMPLETED}>已完成</Option>
                <Option value={TASK_STATUS.FAILED}>失败</Option>
              </Select>
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="priority" label="优先级">
              <Select
                placeholder="选择优先级"
                allowClear
                onChange={() => form.submit()}
              >
                <Option value={TASK_PRIORITY.HIGH}>高优先级</Option>
                <Option value={TASK_PRIORITY.MEDIUM}>中优先级</Option>
                <Option value={TASK_PRIORITY.LOW}>低优先级</Option>
              </Select>
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="assignedTo" label="分配给">
              <Select
                placeholder="选择智能体"
                allowClear
                onChange={() => form.submit()}
              >
                {agents.map(agent => (
                  <Option key={agent.id} value={agent.id}>
                    {agent.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8} lg={6}>
            <Form.Item name="dateRange" label="创建时间">
              <RangePicker
                style={{ width: '100%' }}
                onChange={() => form.submit()}
              />
            </Form.Item>
          </Col>
        </Row>

        <div className="flex justify-end space-x-2">
          <Button
            icon={<ClearOutlined />}
            onClick={handleClear}
            disabled={getActiveFiltersCount() === 0}
          >
            清除筛选
          </Button>
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={() => form.submit()}
            loading={loading}
          >
            应用筛选
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => form.submit()}
          >
            刷新
          </Button>
        </div>
      </Form>
    </Card>
  )
}

export default TaskFilters