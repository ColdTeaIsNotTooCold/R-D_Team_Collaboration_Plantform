import React from 'react'
import {
  Select,
  Space,
  Tag,
  Tooltip,
  Typography,
  Card
} from 'antd'
import {
  RobotOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  ApiOutlined
} from '@ant-design/icons'
import type { Agent } from '@/types'
import { AGENT_STATUS } from '@/constants'

const { Option } = Select
const { Text } = Typography

interface AgentSelectorProps {
  agents: Agent[]
  selectedAgent: string
  onAgentChange: (agentId: string) => void
  loading?: boolean
  disabled?: boolean
  showStatus?: boolean
}

const AgentSelector: React.FC<AgentSelectorProps> = ({
  agents,
  selectedAgent,
  onAgentChange,
  loading = false,
  disabled = false,
  showStatus = true
}) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case AGENT_STATUS.IDLE:
        return <ClockCircleOutlined style={{ color: '#8c8c8c' }} />
      case AGENT_STATUS.RUNNING:
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />
      case AGENT_STATUS.ERROR:
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
      case AGENT_STATUS.COMPLETED:
        return <CheckCircleOutlined style={{ color: '#1890ff' }} />
      default:
        return <ApiOutlined />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case AGENT_STATUS.IDLE:
        return 'default'
      case AGENT_STATUS.RUNNING:
        return 'success'
      case AGENT_STATUS.ERROR:
        return 'error'
      case AGENT_STATUS.COMPLETED:
        return 'processing'
      default:
        return 'default'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case AGENT_STATUS.IDLE:
        return '空闲'
      case AGENT_STATUS.RUNNING:
        return '运行中'
      case AGENT_STATUS.ERROR:
        return '错误'
      case AGENT_STATUS.COMPLETED:
        return '已完成'
      default:
        return '未知'
    }
  }

  const agentOptionRenderer = (agent: Agent) => (
    <div style={{ padding: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
        <RobotOutlined />
        <Text strong>{agent.name}</Text>
        {showStatus && (
          <Tag color={getStatusColor(agent.status)} style={{ marginLeft: 'auto' }}>
            {getStatusText(agent.status)}
          </Tag>
        )}
      </div>
      <Text type="secondary" style={{ fontSize: '12px', display: 'block' }}>
        {agent.description}
      </Text>
      <div style={{ fontSize: '11px', color: '#999', marginTop: '4px' }}>
        类型: {agent.type} | 创建时间: {new Date(agent.createdAt).toLocaleDateString()}
      </div>
    </div>
  )

  return (
    <Card size="small" style={{ marginBottom: '16px' }}>
      <Space align="center" style={{ width: '100%' }}>
        <Text strong>选择智能体：</Text>
        <Select
          value={selectedAgent}
          onChange={onAgentChange}
          style={{ flex: 1, minWidth: '200px' }}
          placeholder="选择智能体"
          loading={loading}
          disabled={disabled || agents.length === 0}
          optionLabelProp="children"
          optionFilterProp="children"
          showSearch
          filterOption={(input, option) =>
            (option?.children as unknown as string)?.toLowerCase().includes(input.toLowerCase())
          }
        >
          {agents.map((agent) => (
            <Option key={agent.id} value={agent.id}>
              <Space>
                {getStatusIcon(agent.status)}
                <span>{agent.name}</span>
                {showStatus && (
                  <Tag color={getStatusColor(agent.status)} size="small">
                    {getStatusText(agent.status)}
                  </Tag>
                )}
              </Space>
            </Option>
          ))}
        </Select>

        {/* 智能体数量统计 */}
        <Tooltip title={`总共 ${agents.length} 个智能体`}>
          <Tag color="blue">
            {agents.length} 个智能体
          </Tag>
        </Tooltip>
      </Space>

      {/* 当前选中智能体的详细信息 */}
      {selectedAgent && (
        <div style={{ marginTop: '12px', padding: '8px', backgroundColor: '#f5f5f5', borderRadius: '6px' }}>
          {(() => {
            const currentAgent = agents.find(a => a.id === selectedAgent)
            if (!currentAgent) return null

            return (
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {getStatusIcon(currentAgent.status)}
                  <Text strong>{currentAgent.name}</Text>
                  <Tag color={getStatusColor(currentAgent.status)}>
                    {getStatusText(currentAgent.status)}
                  </Tag>
                </div>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {currentAgent.description}
                </Text>
                <div style={{ fontSize: '11px', color: '#999', display: 'flex', gap: '16px' }}>
                  <span>类型: {currentAgent.type}</span>
                  <span>创建: {new Date(currentAgent.createdAt).toLocaleDateString()}</span>
                  {currentAgent.updatedAt !== currentAgent.createdAt && (
                    <span>更新: {new Date(currentAgent.updatedAt).toLocaleDateString()}</span>
                  )}
                </div>
              </Space>
            )
          })()}
        </div>
      )}
    </Card>
  )
}

export default AgentSelector