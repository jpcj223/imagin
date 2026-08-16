import { apiClient } from './client'

export interface ModelConfig {
  id: number
  name: string
  base_url: string
  api_key: string
  model: string
  is_active: number
  temperature?: number | null
  max_tokens?: number | null
  top_p?: number | null
  frequency_penalty?: number | null
  presence_penalty?: number | null
  proxy_url?: string
  created_at?: string
  updated_at?: string
}

export interface ModelConfigPayload {
  name: string
  base_url: string
  api_key: string
  model: string
  is_active?: boolean
  temperature?: number | null
  max_tokens?: number | null
  top_p?: number | null
  frequency_penalty?: number | null
  presence_penalty?: number | null
  proxy_url?: string
}

/** 列出所有模型配置。 */
export async function listModelConfigs() {
  const { data } = await apiClient.get<ModelConfig[]>('/models')
  return data
}

/** 获取当前启用的配置。 */
export async function getActiveConfig() {
  const { data } = await apiClient.get<ModelConfig | null>('/models/active')
  return data
}

/** 获取单条配置详情。 */
export async function getModelConfig(id: number) {
  const { data } = await apiClient.get<ModelConfig>(`/models/${id}`)
  return data
}

/** 新建配置。 */
export async function createModelConfig(payload: ModelConfigPayload) {
  const { data } = await apiClient.post<ModelConfig>('/models', payload)
  return data
}

/** 更新配置。 */
export async function updateModelConfig(id: number, payload: ModelConfigPayload) {
  const { data } = await apiClient.put<ModelConfig>(`/models/${id}`, payload)
  return data
}

/** 设为启用配置。 */
export async function activateModelConfig(id: number) {
  const { data } = await apiClient.post<ModelConfig>(`/models/${id}/activate`)
  return data
}

/** 删除配置。 */
export async function deleteModelConfig(id: number) {
  const { data } = await apiClient.delete<{ success: boolean }>(`/models/${id}`)
  return data
}

/** 测试当前启用的模型连接。 */
export async function testModelConnection() {
  const { data } = await apiClient.post<{ ok: boolean; message: string }>('/models/test')
  return data
}
