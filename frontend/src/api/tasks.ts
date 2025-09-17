import api from './index'
import type { Task } from '@/types'

export const tasksApi = {
  // 获取所有任务
  getTasks: () => api.get<Task[]>('/tasks'),

  // 获取单个任务
  getTask: (id: string) => api.get<Task>(`/tasks/${id}`),

  // 创建任务
  createTask: (data: Omit<Task, 'id' | 'createdAt' | 'updatedAt'>) =>
    api.post<Task>('/tasks', data),

  // 更新任务
  updateTask: (id: string, data: Partial<Task>) =>
    api.put<Task>(`/tasks/${id}`, data),

  // 删除任务
  deleteTask: (id: string) => api.delete(`/tasks/${id}`),

  // 分配任务
  assignTask: (id: string, agentId: string) =>
    api.post(`/tasks/${id}/assign`, { agentId }),
}