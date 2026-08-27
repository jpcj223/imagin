/**
 * 伏笔看板全局 Store
 *
 * 伏笔数据在多个页面共享（伏笔看板页、大纲页、章节生成等），
 * 统一通过此 store 管理，确保数据同步。
 */
import { defineStore } from 'pinia'
import { listResource, createResource, updateResource, deleteResource } from '@/api/resources'
import type { ForeshadowingItem } from '@/types/domain'

interface ForeshadowingState {
  foreshadowings: ForeshadowingItem[]
  loaded: boolean
  loading: boolean
}

export const useForeshadowingStore = defineStore('foreshadowing', {
  state: (): ForeshadowingState => ({
    foreshadowings: [],
    loaded: false,
    loading: false,
  }),

  actions: {
    /** 加载伏笔列表（如果已加载则跳过，除非 force 为 true） */
    async load(projectId: number, force = false): Promise<ForeshadowingItem[]> {
      if (this.loaded && !force && this.foreshadowings.length > 0) {
        return this.foreshadowings
      }
      this.loading = true
      try {
        const list = await listResource<ForeshadowingItem>(projectId, 'foreshadowings')
        this.foreshadowings = list
        this.loaded = true
        return list
      } finally {
        this.loading = false
      }
    },

    /** 强制刷新 */
    async reload(projectId: number): Promise<ForeshadowingItem[]> {
      return this.load(projectId, true)
    },

    /** 根据 ID 获取伏笔 */
    getById(id: number): ForeshadowingItem | undefined {
      return this.foreshadowings.find((f) => f.id === id)
    },

    /** 添加伏笔到列表（保存后调用） */
    add(item: ForeshadowingItem) {
      this.foreshadowings.unshift(item)
    },

    /** 更新列表中的伏笔（保存后调用） */
    update(item: ForeshadowingItem) {
      const idx = this.foreshadowings.findIndex((f) => f.id === item.id)
      if (idx >= 0) {
        this.foreshadowings.splice(idx, 1, item)
      } else {
        this.foreshadowings.unshift(item)
      }
    },

    /** 从列表中移除伏笔（删除后调用） */
    remove(id: number) {
      const idx = this.foreshadowings.findIndex((f) => f.id === id)
      if (idx >= 0) {
        this.foreshadowings.splice(idx, 1)
      }
    },

    /** 清空缓存 */
    clear() {
      this.foreshadowings = []
      this.loaded = false
    },
  },
})
