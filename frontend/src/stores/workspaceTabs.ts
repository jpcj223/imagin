import { defineStore } from 'pinia'

export interface WorkspaceTab {
  /** 路由路径，用作标签唯一键。 */
  path: string
  /** 标签显示标题。 */
  title: string
  /** 标签图标，和左侧导航保持一致。 */
  icon: string
}

const TABS_STORAGE_KEY = 'yixiang:workspace-tabs'
const TABS_CLEARED_KEY = 'yixiang:workspace-tabs-cleared'
const KNOWN_TAB_PATHS = new Set([
  '/dashboard',
  '/chapter-generate',
  '/world',
  '/outline',
  '/characters',
  '/organizations',
  '/foreshadowings',
  '/memory',
  '/project-config',
  '/api-config'
])

const defaultTabs: WorkspaceTab[] = [{ path: '/dashboard', title: '创作中心', icon: '🚀' }]

function sanitizeTabs(tabs: WorkspaceTab[]) {
  // 旧版本可能缓存过“页面”这类临时标签；启动和保存时统一按业务路由白名单清洗。
  return tabs.filter((item) => KNOWN_TAB_PATHS.has(item.path) && item.title && item.title !== '页面')
}

function readInitialTabs() {
  // 标签清空后写入单独标记，避免刷新页面时又自动恢复默认首页标签。
  if (localStorage.getItem(TABS_CLEARED_KEY) === '1') return []

  const raw = localStorage.getItem(TABS_STORAGE_KEY)
  if (!raw) return defaultTabs

  try {
    const tabs = JSON.parse(raw) as WorkspaceTab[]
    return Array.isArray(tabs) ? sanitizeTabs(tabs) : defaultTabs
  } catch {
    return defaultTabs
  }
}

function persistTabs(tabs: WorkspaceTab[]) {
  const safeTabs = sanitizeTabs(tabs)
  // 打开标签时保存当前工作台；清空标签时同时清掉缓存并记录清空态。
  if (safeTabs.length === 0) {
    localStorage.removeItem(TABS_STORAGE_KEY)
    localStorage.setItem(TABS_CLEARED_KEY, '1')
    return
  }
  localStorage.setItem(TABS_STORAGE_KEY, JSON.stringify(safeTabs))
  localStorage.removeItem(TABS_CLEARED_KEY)
}

export const useWorkspaceTabsStore = defineStore('workspaceTabs', {
  state: () => ({
    tabs: readInitialTabs() as WorkspaceTab[]
  }),
  actions: {
    open(tab: WorkspaceTab) {
      // 顶部标签模拟 IDE 工作流：重复打开只激活，不新增。
      if (!this.tabs.some((item) => item.path === tab.path)) {
        this.tabs.push(tab)
      }
      this.tabs = sanitizeTabs(this.tabs)
      persistTabs(this.tabs)
    },
    close(path: string) {
      // 允许清空最后一个标签，同时同步清理本地标签缓存。
      this.tabs = this.tabs.filter((item) => item.path !== path)
      persistTabs(this.tabs)
    },
    sanitize() {
      // 页面加载或热更新后立即清理旧缓存残留，避免“页面”标签继续显示。
      this.tabs = sanitizeTabs(this.tabs)
      persistTabs(this.tabs)
    },
    isRouteOpen(path: string) {
      return this.tabs.some((item) => item.path === path)
    }
  }
})
