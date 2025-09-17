import React from 'react'
import { Typography } from 'antd'

const { Text, Paragraph } = Typography

interface MarkdownRendererProps {
  content: string
  style?: React.CSSProperties
}

// 简单的Markdown解析器
const parseMarkdown = (text: string): React.ReactNode[] => {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []
  let currentIndex = 0

  while (currentIndex < lines.length) {
    const line = lines[currentIndex]

    // 标题处理
    if (line.startsWith('# ')) {
      elements.push(
        <Text key={currentIndex} strong style={{ fontSize: '20px', display: 'block', margin: '8px 0' }}>
          {line.substring(2)}
        </Text>
      )
    } else if (line.startsWith('## ')) {
      elements.push(
        <Text key={currentIndex} strong style={{ fontSize: '18px', display: 'block', margin: '6px 0' }}>
          {line.substring(3)}
        </Text>
      )
    } else if (line.startsWith('### ')) {
      elements.push(
        <Text key={currentIndex} strong style={{ fontSize: '16px', display: 'block', margin: '4px 0' }}>
          {line.substring(4)}
        </Text>
      )
    }
    // 列表处理
    else if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(
        <div key={currentIndex} style={{ marginLeft: '20px', margin: '2px 0' }}>
          • {line.substring(2)}
        </div>
      )
    }
    // 有序列表处理
    else if (/^\d+\./.test(line)) {
      elements.push(
        <div key={currentIndex} style={{ marginLeft: '20px', margin: '2px 0' }}>
          {line}
        </div>
      )
    }
    // 代码块处理
    else if (line.startsWith('```')) {
      const language = line.substring(3)
      const codeLines: string[] = []
      currentIndex++

      while (currentIndex < lines.length && !lines[currentIndex].startsWith('```')) {
        codeLines.push(lines[currentIndex])
        currentIndex++
      }

      elements.push(
        <div key={currentIndex} style={{
          backgroundColor: '#f6f6f6',
          border: '1px solid #e8e8e8',
          borderRadius: '4px',
          padding: '12px',
          margin: '8px 0',
          fontFamily: 'monospace',
          fontSize: '13px',
          whiteSpace: 'pre-wrap',
          overflow: 'auto'
        }}>
          {codeLines.join('\n')}
        </div>
      )
    }
    // 内联代码处理
    else if (line.includes('`')) {
      const parts = line.split(/`([^`]+)`/g)
      const lineElements: React.ReactNode[] = []

      for (let i = 0; i < parts.length; i++) {
        if (i % 2 === 1) {
          // 代码部分
          lineElements.push(
            <Text key={i} code style={{ backgroundColor: '#f6f6f6', padding: '2px 4px' }}>
              {parts[i]}
            </Text>
          )
        } else {
          // 普通文本部分
          if (parts[i]) {
            lineElements.push(<span key={i}>{parts[i]}</span>)
          }
        }
      }

      elements.push(
        <div key={currentIndex} style={{ margin: '2px 0' }}>
          {lineElements}
        </div>
      )
    }
    // 链接处理
    else if (line.includes('[') && line.includes('](')) {
      const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g
      const parts = line.split(linkRegex)
      const lineElements: React.ReactNode[] = []

      for (let i = 0; i < parts.length; i++) {
        if (i % 3 === 1) {
          // 链接文本
          const url = parts[i + 1]
          lineElements.push(
            <a
              key={i}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#1890ff' }}
            >
              {parts[i]}
            </a>
          )
          i++ // 跳过URL部分
        } else {
          // 普通文本
          if (parts[i]) {
            lineElements.push(<span key={i}>{parts[i]}</span>)
          }
        }
      }

      elements.push(
        <div key={currentIndex} style={{ margin: '2px 0' }}>
          {lineElements}
        </div>
      )
    }
    // 引用处理
    else if (line.startsWith('> ')) {
      elements.push(
        <div key={currentIndex} style={{
          borderLeft: '4px solid #d9d9d9',
          paddingLeft: '12px',
          margin: '4px 0',
          color: '#666',
          fontStyle: 'italic'
        }}>
          {line.substring(2)}
        </div>
      )
    }
    // 空行处理
    else if (line.trim() === '') {
      elements.push(<div key={currentIndex} style={{ height: '8px' }} />)
    }
    // 普通文本
    else {
      elements.push(
        <div key={currentIndex} style={{ margin: '2px 0' }}>
          {line}
        </div>
      )
    }

    currentIndex++
  }

  return elements
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  style = {}
}) => {
  return (
    <div style={{
      lineHeight: '1.6',
      ...style
    }}>
      {parseMarkdown(content)}
    </div>
  )
}

export default MarkdownRenderer