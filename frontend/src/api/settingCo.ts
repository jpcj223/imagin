import { apiClient } from './client'

// ============================================================
// 类型定义
// ============================================================

export interface SettingChatSession {
  id: number
  session_id: string
  project_id: number
  title: string
  target_type: string   // character / world / foreshadowing
  target_id: number | null
  target_name: string
  status: string
  completeness: number
  focus_areas: string
  created_at: string
  updated_at: string
}

export interface SettingChatMessage {
  id: number
  session_id: string
  role: string         // user / assistant
  content: string
  thought: string
  extracted_fields: string  // JSON string
  memory_written: number
  created_at: string
}

export interface ExtractedField {
  key: string
  label: string
  value: string
  confidence: number
  highlights?: string[]
}

export interface SettingIndexItem {
  id: number
  name: string
  role_type?: string
  completeness: number
  status: 'complete' | 'partial' | 'empty'
}

export interface SettingForeshadowingIndexItem extends SettingIndexItem {
  lifecycle_status: string
}

export interface SettingIndexResponse {
  characters: SettingIndexItem[]
  character_count: number
  character_completeness: number
  world: {
    target_id: number | null
    name: string
    completeness: number
    items: { key: string; label: string; status: string }[]
  }
  foreshadowing: {
    completeness: number
    items: SettingForeshadowingIndexItem[]
  }
}

// ============================================================
// API 方法
// ============================================================

/** 获取设定目录 */
export function getSettingIndex(project_id: number) {
  return apiClient.get<SettingIndexResponse>('/setting-co/setting-index', {
    params: { project_id }
  }).then(r => r.data)
}

/** 获取会话列表 */
export function listSessions(project_id: number, target_type?: string) {
  return apiClient.get<{ sessions: SettingChatSession[] }>('/setting-co/sessions', {
    params: { project_id, target_type }
  }).then(r => r.data)
}

/** 创建会话 */
export function createSession(data: {
  project_id: number
  target_type: string
  target_id?: number
  target_name?: string
}) {
  return apiClient.post<{
    session: SettingChatSession
    opening: { message: string; quick_replies: string[] }
  }>('/setting-co/sessions', data).then(r => r.data)
}

/** 获取会话详情（含消息） */
export function getSession(session_id: string) {
  return apiClient.get<{
    session: SettingChatSession
    messages: SettingChatMessage[]
  }>(`/setting-co/sessions/${session_id}`).then(r => r.data)
}

/** 获取消息列表 */
export function listMessages(session_id: string) {
  return apiClient.get<{ messages: SettingChatMessage[] }>(
    `/setting-co/sessions/${session_id}/messages`
  ).then(r => r.data)
}

/** 发送消息 */
export function sendMessage(session_id: string, message: string) {
  return apiClient.post<{
    reply: {
      role: string
      content: string
      thought: string
      extracted_fields: ExtractedField[]
      memory_written: number
      created_at: string
    }
    quick_replies: string[]
    session: SettingChatSession
    setting_detail: Record<string, any>
  }>(`/setting-co/sessions/${session_id}/messages`, {
    message
  }).then(r => r.data)
}

/** 获取设定详情 */
export function getSettingDetail(target_type: string, target_id: number, project_id: number) {
  return apiClient.get<{ detail: Record<string, any> }>('/setting-co/setting-detail', {
    params: { target_type, target_id, project_id }
  }).then(r => r.data)
}
