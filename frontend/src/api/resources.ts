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

export async function renumberOutlines(projectId: number, volumeId?: number) {
  // 重新排列章节号：按卷顺序 + 卷内排序，重新分配连续的 chapter_no
  const { data } = await apiClient.post<{ ok: boolean; chapter_no: number }>(
    '/resources/outlines/renumber',
    { project_id: projectId, volume_id: volumeId }
  )
  return data
}

export async function reorderVolumes(sourceId: number, targetId: number, position: 'before' | 'after') {
  // 调整卷顺序
  const { data } = await apiClient.post('/resources/outlines/reorder-volume', {
    source_id: sourceId,
    target_id: targetId,
    position,
  })
  return data
}

export async function reorderChapter(sourceId: number, targetId: number, position: 'before' | 'after') {
  // 调整章节顺序（同卷或跨卷），完成后自动重新编号
  const { data } = await apiClient.post('/resources/outlines/reorder-chapter', {
    source_id: sourceId,
    target_id: targetId,
    position,
  })
  return data
}

export async function moveChapterToVolume(chapterId: number, volumeId: number) {
  // 移动章节到指定卷末尾，完成后自动重新编号
  const { data } = await apiClient.post('/resources/outlines/move-chapter', {
    chapter_id: chapterId,
    volume_id: volumeId,
  })
  return data
}
