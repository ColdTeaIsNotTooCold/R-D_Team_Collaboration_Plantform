import api from './index'
import type { Agent } from '@/types'

export const agentsApi = {
  // 获取所有agents
  getAgents: () => api.get<Agent[]>('/agents'),

  // 获取单个agent
  getAgent: (id: string) => api.get<Agent>(`/agents/${id}`),

  // 创建agent
  createAgent: (data: Omit<Agent, 'id' | 'createdAt' | 'updatedAt'>) =>
    api.post<Agent>('/agents', data),

  // 更新agent
  updateAgent: (id: string, data: Partial<Agent>) =>
    api.put<Agent>(`/agents/${id}`, data),

  // 删除agent
  deleteAgent: (id: string) => api.delete(`/agents/${id}`),

  // 启动agent
  startAgent: (id: string) => api.post(`/agents/${id}/start`),

  // 停止agent
  stopAgent: (id: string) => api.post(`/agents/${id}/stop`),
}