import React from 'react'
import {
  Card,
  Form,
  Input,
  InputNumber,
  Switch,
  Button,
  Space,
  message,
  Divider,
  Typography
} from 'antd'
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons'

const { Title } = Typography
const { TextArea } = Input

const Settings: React.FC = () => {
  const [form] = Form.useForm()

  const handleSave = async (values: any) => {
    try {
      // 这里应该调用API保存设置
      console.log('保存设置:', values)
      message.success('设置保存成功')
    } catch (error) {
      message.error('设置保存失败')
    }
  }

  const handleReset = () => {
    form.resetFields()
    message.info('设置已重置')
  }

  return (
    <div>
      <Title level={3}>系统设置</Title>

      <Card title="基础设置" style={{ marginBottom: 24 }}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            systemName: '团队协作平台',
            systemDescription: '基于AI的团队协作管理平台',
            maxConcurrentTasks: 10,
            enableNotifications: true,
            enableAutoSave: true,
            sessionTimeout: 30,
            logLevel: 'info',
            apiTimeout: 30,
          }}
        >
          <Form.Item
            label="系统名称"
            name="systemName"
            rules={[{ required: true, message: '请输入系统名称' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            label="系统描述"
            name="systemDescription"
          >
            <TextArea rows={3} />
          </Form.Item>

          <Form.Item
            label="最大并发任务数"
            name="maxConcurrentTasks"
            rules={[{ required: true, message: '请输入最大并发任务数' }]}
          >
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            label="会话超时时间（分钟）"
            name="sessionTimeout"
            rules={[{ required: true, message: '请输入会话超时时间' }]}
          >
            <InputNumber min={5} max={480} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="功能设置" style={{ marginBottom: 24 }}>
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            label="启用通知"
            name="enableNotifications"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            label="启用自动保存"
            name="enableAutoSave"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            label="日志级别"
            name="logLevel"
          >
            <Input />
          </Form.Item>

          <Form.Item
            label="API超时时间（秒）"
            name="apiTimeout"
          >
            <InputNumber min={5} max={300} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Card>

      <Card title="API设置" style={{ marginBottom: 24 }}>
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            label="API基础URL"
            name="apiBaseUrl"
          >
            <Input placeholder="http://localhost:8000" />
          </Form.Item>

          <Form.Item
            label="WebSocket URL"
            name="wsUrl"
          >
            <Input placeholder="ws://localhost:8000/ws" />
          </Form.Item>

          <Form.Item
            label="API密钥"
            name="apiKey"
          >
            <Input.Password placeholder="输入API密钥" />
          </Form.Item>
        </Form>
      </Card>

      <Card title="操作">
        <Space>
          <Button type="primary" icon={<SaveOutlined />} onClick={() => form.submit()}>
            保存设置
          </Button>
          <Button icon={<ReloadOutlined />} onClick={handleReset}>
            重置设置
          </Button>
        </Space>
      </Card>
    </div>
  )
}

export default Settings