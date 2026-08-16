import { createDiscreteApi, type ConfigProviderProps } from 'naive-ui'

/**
 * 全局通知工具
 * ------------------------------------------------------------------
 * 使用 Naive UI 的 discrete API 创建脱离组件树的 message / dialog / notification 实例，
 * 让 API 层、路由守卫等非组件代码也能弹出友好提示。
 *
 * 设计原则：
 * 1. 懒加载初始化，首次使用时才挂载到 body，避免 SSR 或启动期异常。
 * 2. 统一暗色主题，和工作台整体风格一致。
 * 3. 错误信息优先展示后端返回的 detail，没有则兜底为通用文案。
 */

let _message: ReturnType<typeof createDiscreteApi>['message'] | null = null
let _dialog: ReturnType<typeof createDiscreteApi>['dialog'] | null = null
let _notification: ReturnType<typeof createDiscreteApi>['notification'] | null = null

const themeOverrides: ConfigProviderProps['themeOverrides'] = {
  common: {
    primaryColor: '#3b82f6',
    primaryColorHover: '#60a5fa',
    primaryColorPressed: '#2563eb',
    borderRadius: '6px'
  }
}

function ensureInitialized() {
  if (_message && _dialog && _notification) return

  const discrete = createDiscreteApi(['message', 'dialog', 'notification'], {
    configProviderProps: {
      themeOverrides
    }
  })
  _message = discrete.message
  _dialog = discrete.dialog
  _notification = discrete.notification
}

export const notify = {
  /** 普通提示 */
  info(content: string, duration = 2500) {
    ensureInitialized()
    _message?.info(content, { duration })
  },
  /** 成功提示 */
  success(content: string, duration = 2500) {
    ensureInitialized()
    _message?.success(content, { duration })
  },
  /** 警告提示 */
  warning(content: string, duration = 3000) {
    ensureInitialized()
    _message?.warning(content, { duration })
  },
  /** 错误提示（优先展示后端 detail） */
  error(error: unknown, fallback = '操作失败，请稍后重试') {
    ensureInitialized()
    const msg = extractErrorMessage(error, fallback)
    _message?.error(msg, { duration: 4000 })
  },
  /** 确认对话框，返回 boolean */
  confirm(title: string, content: string, positiveText = '确定', negativeText = '取消'): Promise<boolean> {
    ensureInitialized()
    return new Promise((resolve) => {
      _dialog?.warning({
        title,
        content,
        positiveText,
        negativeText,
        onPositiveClick: () => resolve(true),
        onNegativeClick: () => resolve(false),
        onMaskClick: () => resolve(false),
        onClose: () => resolve(false)
      })
    })
  },
  /** 右上角通知（重要信息） */
  notifySuccess(title: string, description?: string) {
    ensureInitialized()
    _notification?.success({ title, description, duration: 3500 })
  },
  notifyError(title: string, description?: string) {
    ensureInitialized()
    _notification?.error({ title, description, duration: 5000 })
  }
}

/**
 * 从各种错误对象中提取可读的错误信息
 * 支持 AxiosError、普通 Error、字符串、以及后端返回的 { detail } 结构
 */
export function extractErrorMessage(error: unknown, fallback = '操作失败'): string {
  if (!error) return fallback

  if (typeof error === 'string') return error

  // AxiosError 风格：response.data.detail
  const err = error as Record<string, unknown>
  if (err.response && typeof err.response === 'object') {
    const data = (err.response as Record<string, unknown>).data
    if (data && typeof data === 'object') {
      const detail = (data as Record<string, unknown>).detail
      if (typeof detail === 'string') return detail
      const msg = (data as Record<string, unknown>).message
      if (typeof msg === 'string') return msg
    }
  }

  // 普通 Error
  if (err.message && typeof err.message === 'string') {
    // 网络错误兜底文案
    if (err.message.includes('Network Error') || err.message.includes('timeout')) {
      return '网络连接失败，请检查后端服务是否启动'
    }
    return err.message
  }

  return fallback
}
