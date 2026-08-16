import { apiClient } from './client'
import type { Project } from '@/types/domain'

/** 获取全部项目列表。 */
export async function listProjects() {
  const { data } = await apiClient.get<Project[]>('/projects')
  return data
}

/** 获取单个项目详情。 */
export async function getProject(projectId: number) {
  const { data } = await apiClient.get<Project>(`/projects/${projectId}`)
  return data
}

/** 创建新项目。 */
export async function createProject(payload: Partial<Project> & { name: string }) {
  const { data } = await apiClient.post<Project>('/projects', payload)
  return data
}

/** 更新项目配置（局部字段）。 */
export async function updateProject(projectId: number, payload: Partial<Project>) {
  const { data } = await apiClient.put<Project>(`/projects/${projectId}`, payload)
  return data
}

/** 删除项目（级联删除所有关联数据）。 */
export async function deleteProject(projectId: number) {
  const { data } = await apiClient.delete<{ id: number; deleted: boolean }>(`/projects/${projectId}`)
  return data
}
