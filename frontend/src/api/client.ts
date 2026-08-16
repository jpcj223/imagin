import axios from 'axios'
import { notify } from '@/utils/notify'

export const apiClient = axios.create({
  // 前端路由里有 /api-config，所以后端接口使用独立前缀，避免路由和代理互相抢路径。
  baseURL: '/backend-api',
  // 长章节生成可能超过 2 分钟，超时时间与后端 API_TIMEOUT_MS 默认值保持一致。
  timeout: 300000
})

/**
 * 响应拦截器：统一处理后端错误
 * ------------------------------------------------------------------
 * 1. 4xx / 5xx 错误统一弹出友好提示（使用全局 notify）。
 * 2. 网络错误、超时错误给出明确的中文提示。
 * 3. 错误继续向外抛出，由调用方决定是否需要额外处理（比如加载状态重置）。
 *
 * 注意：
 * - 流式接口（fetch + NDJSON）不走 axios，错误处理见 agents.ts 内部。
 * - 如果调用方需要自定义错误提示，可在自己的 catch 里覆盖或使用 silent 模式。
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // 401 未授权 - 不弹通用错误，由业务层决定跳转登录或提示
    if (error.response?.status === 401) {
      notify.warning('请先配置 API 密钥')
      return Promise.reject(error)
    }

    // 404 - 资源不存在
    if (error.response?.status === 404) {
      notify.error(error, '请求的资源不存在')
      return Promise.reject(error)
    }

    // 5xx - 服务端错误
    if (error.response?.status >= 500) {
      notify.error(error, '服务器错误，请稍后重试')
      return Promise.reject(error)
    }

    // 网络错误 / 超时
    if (!error.response || error.code === 'ECONNABORTED') {
      notify.error(error, '网络连接失败，请检查后端服务是否启动')
      return Promise.reject(error)
    }

    // 其他业务错误（400、422 等）
    notify.error(error)
    return Promise.reject(error)
  }
)
