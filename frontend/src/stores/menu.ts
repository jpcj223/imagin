/**
 * 菜单全局 Store
 *
 * 菜单从后端数据库加载，支持树形结构。
 */
import { defineStore } from 'pinia'
import { fetchMenuTree, type MenuItem } from '@/api/core'

export type { MenuItem }

interface MenuState {
  tree: MenuItem[]
  flatList: MenuItem[]
  loaded: boolean
  loading: boolean
}

export const useMenuStore = defineStore('menu', {
  state: (): MenuState => ({
    tree: [],
    flatList: [],
    loaded: false,
    loading: false,
  }),

  getters: {
    /** 可视菜单树（排除隐藏的） */
    visibleTree(state): MenuItem[] {
      return state.tree
        .filter((m) => m.is_visible === 1)
        .map((m) => ({
          ...m,
          children: m.children?.filter((c) => c.is_visible === 1) || [],
        }))
    },

    /** 扁平化的菜单项（用于路由匹配等） */
    allFlatItems(state): MenuItem[] {
      return state.flatList
    },

    /** 根据路径查找菜单项 */
    findByPath: (state) => (path: string): MenuItem | undefined => {
      return state.flatList.find((m) => m.path === path)
    },

    /** 第一个可访问的菜单路径（用于默认跳转） */
    firstMenuPath(state): string {
      const visible = state.flatList.filter(
        (m) => m.is_visible === 1 && m.menu_type === 'menu' && m.path
      )
      return visible.length > 0 ? visible[0].path : '/dashboard'
    },
  },

  actions: {
    /** 加载菜单树 */
    async load(): Promise<MenuItem[]> {
      if (this.loaded) return this.tree
      if (this.loading) {
        await new Promise((resolve) => {
          const check = () => {
            if (!this.loading) {
              resolve(null)
            } else {
              setTimeout(check, 100)
            }
          }
          check()
        })
        return this.tree
      }

      this.loading = true
      try {
        const data = await fetchMenuTree()
        this.tree = data
        this.flatList = this._flatten(data)
        this.loaded = true
        return data
      } finally {
        this.loading = false
      }
    },

    /** 强制刷新菜单 */
    async refresh(): Promise<MenuItem[]> {
      this.loaded = false
      return this.load()
    },

    /** 树形结构扁平化 */
    _flatten(items: MenuItem[]): MenuItem[] {
      const result: MenuItem[] = []
      for (const item of items) {
        result.push(item)
        if (item.children && item.children.length > 0) {
          result.push(...this._flatten(item.children))
        }
      }
      return result
    },
  },
})
