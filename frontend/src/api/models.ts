import { apiClient } from './client'

export interface ModelConfig {
  id: number
  name: string
  base_url: string
  api_key: string
  model: string
  is_active: number
}

export async function listModelConfigs() {
  // 读取历史配置，用于进入页面时回填当前启用模型，避免用户反复手输。
  const { data } = await apiClient.get<ModelConfig[]>('/models')
  return data
}

export async function saveModelConfig(payload: Record<string, unknown>) {
  // 保存 OpenAI-compatible 配置，后端会将 active 配置用于 Agent 调用。
  const { data } = await apiClient.post('/models', payload)
  return data
}

export async function testModelConnection() {
  // 用一个最小聊天请求验证当前启用模型是否可用。
  const { data } = await apiClient.post<{ ok: boolean; message: string }>('/models/test')
  return data
}
