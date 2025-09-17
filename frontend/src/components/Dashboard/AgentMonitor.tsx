import React, { useState } from 'react'
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Modal,
  message,
  Tooltip,
  Badge,
  Row,
  Col
} from 'antd'
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  SettingOutlined,
  InfoCircleOutlined,
  RobotOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Agent } from '@/types'
import { AGENT_STATUS, STATUS_COLORS } from '@/constants'

interface AgentMonitorProps {
  agents: Agent[]
  loading?: boolean
  onRefresh: () => void
  onAgentAction: (agentId: string, action: 'start' | 'stop' | 'restart') => void
}

const AgentMonitor: React.FC<AgentMonitorProps> = ({
  agents,
  loading = false,
  onRefresh,
  onAgentAction
}) => {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [detailModalVisible, setDetailModalVisible] = useState(false)

  const handleAction = async (agentId: string, action: 'start' | 'stop' | 'restart') => {
    try {
      onAgentAction(agentId, action)
      message.success(`操作成功：${action === 'start' ? '启动' : action === 'stop' ? '停止' : '重启'}智能体`)
    } catch (error) {
      message.error(`操作失败：${error}`)
    }
  }

  const showAgentDetail = (agent: Agent) => {
    setSelectedAgent(agent)
    setDetailModalVisible(true)
  }

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      [AGENT_STATUS.RUNNING]: { status: 'processing', text: '运行中' },
      [AGENT_STATUS.IDLE]: { status: 'default', text: '空闲' },
      [AGENT_STATUS.ERROR]: { status: 'error', text: '错误' },
      [AGENT_STATUS.COMPLETED]: { status: 'success', text: '已完成' }
    }

    const config = statusConfig[status as keyof typeof statusConfig] || { status: 'default', text: '未知' }

    return (
      <Badge
        status={config.status as any}
        text={config.text}
      />
    )
  }

  const getActionButtons = (agent: Agent) => {
    const canStart = agent.status === AGENT_STATUS.IDLE || agent.status === AGENT_STATUS.ERROR
    const canStop = agent.status === AGENT_STATUS.RUNNING

    return (
      <Space size="small">
        {canStart && (
          <Tooltip title="启动智能体">
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleAction(agent.id, 'start')}
            />
          </Tooltip>
        )}
        {canStop && (
          <Tooltip title="停止智能体">
            <Button
              danger
              size="small"
              icon={<PauseCircleOutlined />}
              onClick={() => handleAction(agent.id, 'stop')}
            />
          </Tooltip>
        )}
        <Tooltip title="重启智能体">
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => handleAction(agent.id, 'restart')}
          />
        </Tooltip>
        <Tooltip title="查看详情">
          <Button
            size="small"
            icon={<InfoCircleOutlined />}
            onClick={() => showAgentDetail(agent)}
          />
        </Tooltip>
      </Space>
    )
  }

  const columns: ColumnsType<Agent> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Agent) => (
        <Space>
          <RobotOutlined style={{ color: STATUS_COLORS[record.status as keyof typeof STATUS_COLORS] }} />
          <span>{text}</span>
        </Space>
      ),
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color="blue">{type}</Tag>
      ),
      filters: [
        { text: '分析器', value: 'analyzer' },
        { text: '执行器', value: 'executor' },
        { text: '协调器', value: 'coordinator' },
      ],
      onFilter: (value: any, record) => record.type === value,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => getStatusBadge(status),
      sorter: (a, b) => a.status.localeCompare(b.status),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 200,
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (time: string) => new Date(time).toLocaleString(),
      sorter: (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_, record) => getActionButtons(record),
    },
  ]

  const runningAgents = agents.filter(agent => agent.status === AGENT_STATUS.RUNNING).length
  const errorAgents = agents.filter(agent => agent.status === AGENT_STATUS.ERROR).length

  return (
    <div>
      {/* 智能体统计概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                {agents.length}
              </div>
              <div style={{ color: '#666' }}>智能体总数</div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                {runningAgents}
              </div>
              <div style={{ color: '#666' }}>运行中</div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>
                {errorAgents}
              </div>
              <div style={{ color: '#666' }}>异常</div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 智能体列表 */}
      <Card
        title="智能体监控"
        extra={
          <Space>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={onRefresh}
              loading={loading}
            >
              刷新
            </Button>
            <Button icon={<SettingOutlined />}>
              设置
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={agents}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
          scroll={{ x: 800 }}
        />
      </Card>

      {/* 智能体详情弹窗 */}
      <Modal
        title={`智能体详情 - ${selectedAgent?.name}`}
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedAgent && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={8}>
                <div style={{ textAlign: 'center' }}>
                  <RobotOutlined style={{ fontSize: 48, color: STATUS_COLORS[selectedAgent.status as keyof typeof STATUS_COLORS] }} />
                  <div style={{ marginTop: 8 }}>
                    {getStatusBadge(selectedAgent.status)}
                  </div>
                </div>
              </Col>
              <Col span={16}>
                <Space direction="vertical" style={{ width: '100%' }} size="small">
                  <div>
                    <strong>名称：</strong> {selectedAgent.name}
                  </div>
                  <div>
                    <strong>类型：</strong> <Tag color="blue">{selectedAgent.type}</Tag>
                  </div>
                  <div>
                    <strong>描述：</strong> {selectedAgent.description}
                  </div>
                  <div>
                    <strong>创建时间：</strong> {new Date(selectedAgent.createdAt).toLocaleString()}
                  </div>
                  <div>
                    <strong>更新时间：</strong> {new Date(selectedAgent.updatedAt).toLocaleString()}
                  </div>
                </Space>
              </Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default AgentMonitor