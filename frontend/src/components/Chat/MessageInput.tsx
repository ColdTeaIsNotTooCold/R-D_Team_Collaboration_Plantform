import React, { useState, useRef, useEffect } from 'react'
import {
  Input,
  Button,
  Space,
  Upload,
  message,
  Tooltip,
  Dropdown,
  Menu
} from 'antd'
import {
  SendOutlined,
  PaperClipOutlined,
  SmileOutlined,
  ThunderboltOutlined,
  ClearOutlined
} from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'

const { TextArea } = Input

interface MessageInputProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  onFileUpload?: (files: UploadFile[]) => void
  loading?: boolean
  placeholder?: string
  disabled?: boolean
  quickCommands?: Array<{
    label: string
    value: string
    description?: string
  }>
}

const MessageInput: React.FC<MessageInputProps> = ({
  value,
  onChange,
  onSend,
  onFileUpload,
  loading = false,
  placeholder = '输入消息...',
  disabled = false,
  quickCommands = []
}) => {
  const [files, setFiles] = useState<UploadFile[]>([])
  const textAreaRef = useRef<any>(null)

  useEffect(() => {
    // 自动调整文本框高度
    if (textAreaRef.current) {
      textAreaRef.current.style.height = 'auto'
      textAreaRef.current.style.height = Math.min(textAreaRef.current.scrollHeight, 120) + 'px'
    }
  }, [value])

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSend = () => {
    if (!value.trim() && files.length === 0) {
      message.warning('请输入消息或选择文件')
      return
    }
    onSend()
  }

  const handleFileChange = ({ fileList }: { fileList: UploadFile[] }) => {
    setFiles(fileList)
    if (onFileUpload) {
      onFileUpload(fileList)
    }
  }

  const handleClear = () => {
    onChange('')
    setFiles([])
  }

  const handleQuickCommand = (command: string) => {
    onChange(command)
    setTimeout(() => {
      if (textAreaRef.current) {
        textAreaRef.current.focus()
      }
    }, 100)
  }

  const quickCommandsMenu = (
    <Menu
      items={quickCommands.map((cmd, index) => ({
        key: index,
        label: (
          <div>
            <div style={{ fontWeight: 'bold' }}>{cmd.label}</div>
            {cmd.description && (
              <div style={{ fontSize: '12px', color: '#999' }}>
                {cmd.description}
              </div>
            )}
          </div>
        ),
        onClick: () => handleQuickCommand(cmd.value)
      }))}
    />
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {/* 文件上传区域 */}
      {files.length > 0 && (
        <div style={{
          padding: '8px',
          backgroundColor: '#f5f5f5',
          borderRadius: '6px',
          border: '1px solid #d9d9d9'
        }}>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
            已选择文件：
          </div>
          {files.map((file) => (
            <div key={file.uid} style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '4px',
              backgroundColor: 'white',
              borderRadius: '4px',
              marginBottom: '4px'
            }}>
              <PaperClipOutlined />
              <span style={{ fontSize: '12px' }}>{file.name}</span>
              <span style={{ fontSize: '12px', color: '#999' }}>
                ({(file.size! / 1024).toFixed(1)} KB)
              </span>
            </div>
          ))}
        </div>
      )}

      {/* 输入区域 */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
        <TextArea
          ref={textAreaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          rows={1}
          style={{
            flex: 1,
            resize: 'none',
            fontSize: '14px'
          }}
          disabled={disabled || loading}
          autoSize={{ minRows: 1, maxRows: 4 }}
        />

        {/* 快捷命令按钮 */}
        {quickCommands.length > 0 && (
          <Dropdown overlay={quickCommandsMenu} placement="topRight">
            <Button
              icon={<ThunderboltOutlined />}
              disabled={disabled || loading}
              title="快捷命令"
            />
          </Dropdown>
        )}

        {/* 文件上传按钮 */}
        <Upload
          multiple
          beforeUpload={() => false}
          onChange={handleFileChange}
          showUploadList={false}
          disabled={disabled || loading}
        >
          <Button
            icon={<PaperClipOutlined />}
            disabled={disabled || loading}
            title="上传文件"
          />
        </Upload>

        {/* 清除按钮 */}
        {(value || files.length > 0) && (
          <Button
            icon={<ClearOutlined />}
            onClick={handleClear}
            disabled={disabled || loading}
            title="清除"
          />
        )}

        {/* 发送按钮 */}
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSend}
          loading={loading}
          disabled={disabled || (!value.trim() && files.length === 0)}
          style={{ height: 'auto' }}
        >
          发送
        </Button>
      </div>

      {/* 快捷命令提示 */}
      {quickCommands.length > 0 && (
        <div style={{ fontSize: '12px', color: '#999', textAlign: 'center' }}>
          快捷命令：{quickCommands.map(cmd => `/${cmd.label}`).join(' ')}
        </div>
      )}
    </div>
  )
}

export default MessageInput