import { apiClient } from './client'
import type { DashboardData, ForeshadowingHistory, OrganizationHistory, OrganizationRelation } from '@/types/domain'

export interface OrganizationRelationPayload {
  target_org_id: number
  relation_type: OrganizationRelation['relation_type']
  description: string
  effective_from_chapter: number | null
  expires_at_chapter: number | null
}

export async function listOrganizationRelations(projectId: number, organizationId: number) {
  // 组织关系接口按当前组织视角返回对端名称，页面无需处理关系方向。
  const { data } = await apiClient.get<{ items: OrganizationRelation[]; total: number }>(
    `/resources/${projectId}/organizations/${organizationId}/relations`
  )
  return data.items
}

export async function saveOrganizationRelation(
  projectId: number,
  organizationId: number,
  payload: OrganizationRelationPayload,
  relationId?: number
) {
  // 有 relationId 时更新既有关系，否则新增关系。
  const path = `/resources/${projectId}/organizations/${organizationId}/relations`
  const { data } = relationId
    ? await apiClient.put<OrganizationRelation>(`${path}/${relationId}`, payload)
    : await apiClient.post<OrganizationRelation>(path, payload)
  return data
}

export async function deleteOrganizationRelation(projectId: number, organizationId: number, relationId: number) {
  // 删除时同时限定项目、当前组织和关系 ID，避免跨组织误删。
  const { data } = await apiClient.delete<{ ok: boolean; id: number }>(
    `/resources/${projectId}/organizations/${organizationId}/relations/${relationId}`
  )
  return data
}

export async function listOrganizationHistory(projectId: number, organizationId: number, limit = 30) {
  // 历史接口返回章节来源、变更字段和完整前后快照，供组织卡片回溯。
  const { data } = await apiClient.get<{ items: OrganizationHistory[]; total: number }>(
    `/resources/${projectId}/organizations/${organizationId}/history`,
    { params: { limit } }
  )
  return data.items
}

export async function listForeshadowingHistory(projectId: number, foreshadowingId: number, limit = 30) {
  // 变更记录包含章节来源和前后快照，供伏笔看板回看 AI 与手工修改。
  const { data } = await apiClient.get<{ items: ForeshadowingHistory[]; total: number }>(
    `/resources/${projectId}/foreshadowings/${foreshadowingId}/history`,
    { params: { limit } }
  )
  return data.items
}

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
