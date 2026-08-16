import { apiClient } from './client'
import type { Project } from '@/types/domain'

export async function listProjects() {
  // 第一版默认使用第一个项目，后续多项目切换也复用这个接口。
  const { data } = await apiClient.get<Project[]>('/projects')
  return data
}

export async function updateProject(projectId: number, payload: Partial<Project>) {
  // 项目配置页局部更新基础信息。
  const { data } = await apiClient.put<Project>(`/projects/${projectId}`, payload)
  return data
}
