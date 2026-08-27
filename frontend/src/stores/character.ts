/**
 * 人物卡片全局 Store
 *
 * 角色数据在多个页面共享（人物卡片页、组织势力页等），
 * 统一通过此 store 管理，确保数据同步。
 */
import { defineStore } from 'pinia'
import { listResource, updateResource } from '@/api/resources'
import type { CharacterItem } from '@/types/domain'

interface CharacterState {
  characters: CharacterItem[]
  loaded: boolean
  loading: boolean
}

export const useCharacterStore = defineStore('character', {
  state: (): CharacterState => ({
    characters: [],
    loaded: false,
    loading: false,
  }),

  actions: {
    /** 加载角色列表（如果已加载则跳过，除非 force 为 true） */
    async load(projectId: number, force = false): Promise<CharacterItem[]> {
      if (this.loaded && !force && this.characters.length > 0) {
        return this.characters
      }
      this.loading = true
      try {
        const list = await listResource<CharacterItem>(projectId, 'characters')
        this.characters = list
        this.loaded = true
        return list
      } finally {
        this.loading = false
      }
    },

    /** 强制刷新 */
    async reload(projectId: number): Promise<CharacterItem[]> {
      return this.load(projectId, true)
    },

    /** 根据 ID 获取角色 */
    getById(id: number): CharacterItem | undefined {
      return this.characters.find((c) => c.id === id)
    },

    /** 添加角色到列表（保存后调用） */
    add(char: CharacterItem) {
      this.characters.unshift(char)
    },

    /** 更新列表中的角色（保存后调用） */
    update(char: CharacterItem) {
      const idx = this.characters.findIndex((c) => c.id === char.id)
      if (idx >= 0) {
        this.characters.splice(idx, 1, char)
      } else {
        this.characters.unshift(char)
      }
    },

    /** 从列表中移除角色（删除后调用） */
    remove(id: number) {
      const idx = this.characters.findIndex((c) => c.id === id)
      if (idx >= 0) {
        this.characters.splice(idx, 1)
      }
    },

    /**
     * 清除所有角色中指定组织的关联关系
     * 组织被删除时调用，同步更新所有角色的 org_relations
     */
    removeOrgFromAll(orgId: number) {
      this.characters.forEach((char) => {
        let relations: any[] = []
        try {
          if (char.org_relations && typeof char.org_relations === 'string') {
            relations = JSON.parse(char.org_relations)
          } else if (Array.isArray(char.org_relations)) {
            relations = char.org_relations
          }
        } catch { /* ignore */ }
        const newRelations = relations.filter((r) => Number(r.org_id) !== orgId)
        if (newRelations.length !== relations.length) {
          ;(char as any).org_relations = JSON.stringify(newRelations)
        }
      })
    },

    /**
     * 更新某个角色的组织关系
     * 角色页面修改组织关系时调用，同步到 store
     */
    updateCharacterOrgRelations(charId: number, orgRelations: string) {
      const char = this.characters.find((c) => c.id === charId)
      if (char) {
        ;(char as any).org_relations = orgRelations
      }
    },

    /** 清空缓存 */
    clear() {
      this.characters = []
      this.loaded = false
    },
  },
})
