import axios from 'axios'

export const apiClient = axios.create({
  // 前端路由里有 /api-config，所以后端接口使用独立前缀，避免路由和代理互相抢路径。
  baseURL: '/backend-api',
  // 长章节生成可能超过 2 分钟，超时时间与后端 API_TIMEOUT_MS 默认值保持一致。
  timeout: 300000
})
