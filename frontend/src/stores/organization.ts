/**
 * 组织势力全局 Store
 *
 * 组织数据在多个页面共享（人物卡片页、组织势力页等），
 * 统一通过此 store 管理，确保数据同步。
 */
import { defineStore } from 'pinia'
import { listResource, createResource, updateResource, deleteResource } from '@/api/resources'
import type { OrganizationItem } from '@/types/domain'

interface OrganizationState {
  organizations: OrganizationItem[]
  loaded: boolean
  loading: boolean
}

export const useOrganizationStore = defineStore('organization', {
  state: (): OrganizationState => ({
    organizations: [],
    loaded: false,
    loading: false,
  }),

  actions: {
    /** 加载组织列表（如果已加载则跳过，除非 force 为 true） */
    async load(projectId: number, force = false): Promise<OrganizationItem[]> {
      if (this.loaded && !force && this.organizations.length > 0) {
        return this.organizations
      }
      this.loading = true
      try {
        const list = await listResource<OrganizationItem>(projectId, 'organizations')
        this.organizations = list
        this.loaded = true
        return list
      } finally {
        this.loading = false
      }
    },

    /** 强制刷新 */
    async reload(projectId: number): Promise<OrganizationItem[]> {
      return this.load(projectId, true)
    },

    /** 根据 ID 获取组织 */
    getById(id: number): OrganizationItem | undefined {
      return this.organizations.find((o) => o.id === id)
    },

    /** 添加组织到列表（保存后调用） */
    add(org: OrganizationItem) {
      this.organizations.unshift(org)
    },

    /** 更新列表中的组织（保存后调用） */
    update(org: OrganizationItem) {
      const idx = this.organizations.findIndex((o) => o.id === org.id)
      if (idx >= 0) {
        this.organizations.splice(idx, 1, org)
      } else {
        this.organizations.unshift(org)
      }
    },

    /** 从列表中移除组织（删除后调用） */
    remove(id: number) {
      const idx = this.organizations.findIndex((o) => o.id === id)
      if (idx >= 0) {
        this.organizations.splice(idx, 1)
      }
    },

    /** 清空缓存 */
    clear() {
      this.organizations = []
      this.loaded = false
    },
  },
})
