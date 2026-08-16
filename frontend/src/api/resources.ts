import { apiClient } from './client'
import type { DashboardData } from '@/types/domain'

export async function getDashboard(projectId: number) {
  // 首页项目概览：计数、字数、最近章节、分布数据等。
  const { data } = await apiClient.get<DashboardData>(`/resources/${projectId}/dashboard`)
  return data
}

export async function listResource<T>(projectId: number, resource: string) {
  // 通用列表接口：resource 是后端白名单中的业务资源名。
  const { data } = await apiClient.get<T[]>(`/resources/${projectId}/${resource}`)
  return data
}

export async function createResource<T>(resource: string, payload: Record<string, unknown>) {
  // 通用新增接口：各页面负责组装表单，接口层只负责请求和类型返回。
  const { data } = await apiClient.post<T>(`/resources/${resource}`, payload)
  return data
}

export async function updateResource<T>(resource: string, id: number, payload: Record<string, unknown>) {
  // 所有资料页统一走这个更新入口，页面只负责维护表单状态。
  const { data } = await apiClient.put<T>(`/resources/${resource}/${id}`, payload)
  return data
}

export async function deleteResource(resource: string, id: number) {
  // 删除接口返回 ok，列表页删除成功后重新拉取最新数据。
  const { data } = await apiClient.delete<{ ok: boolean; id: number }>(`/resources/${resource}/${id}`)
  return data
}
