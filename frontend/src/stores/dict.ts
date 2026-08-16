/**
 * 字典数据全局 Store
 *
 * 所有字典/枚举数据从后端数据库加载，全局缓存，按需获取。
 * 使用方式：
 *   const dictStore = useDictStore()
 *   const novelTypes = dictStore.items('novel_type')  // 同步获取（需先加载）
 *   await dictStore.load('novel_type')                 // 异步加载单个字典
 *   await dictStore.loadBatch(['novel_type', 'importance'])  // 批量加载
 */
import { defineStore } from 'pinia'
import { fetchDictItems, type DictItem } from '@/api/core'

interface DictState {
  itemsMap: Record<string, DictItem[]>
  loadingMap: Record<string, boolean>
}

export const useDictStore = defineStore('dict', {
  state: (): DictState => ({
    itemsMap: {},
    loadingMap: {},
  }),

  actions: {
    /** 获取字典项列表（同步，需确保已加载） */
    items(dictCode: string): DictItem[] {
      return this.itemsMap[dictCode] || []
    },

    /** 获取字典选项（用于 select 组件） */
    options(dictCode: string): Array<{ label: string; value: string }> {
      return this.items(dictCode).map((item) => ({
        label: item.item_label,
        value: item.item_value,
      }))
    },

    /** 根据 value 获取 label */
    label(dictCode: string, value: string): string {
      const item = this.items(dictCode).find((i) => i.item_value === value)
      return item?.item_label || value
    },

    /** 加载单个字典 */
    async load(dictCode: string): Promise<DictItem[]> {
      if (this.itemsMap[dictCode]) {
        return this.itemsMap[dictCode]
      }
      if (this.loadingMap[dictCode]) {
        // 正在加载，等待完成
        await new Promise((resolve) => {
          const check = () => {
            if (!this.loadingMap[dictCode]) {
              resolve(null)
            } else {
              setTimeout(check, 100)
            }
          }
          check()
        })
        return this.itemsMap[dictCode] || []
      }

      this.loadingMap[dictCode] = true
      try {
        const data = await fetchDictItems(dictCode)
        this.itemsMap[dictCode] = data
        return data
      } finally {
        this.loadingMap[dictCode] = false
      }
    },

    /** 批量加载多个字典 */
    async loadBatch(codes: string[]): Promise<void> {
      const needLoad = codes.filter((c) => !this.itemsMap[c])
      if (needLoad.length === 0) return
      await Promise.all(needLoad.map((code) => this.load(code)))
    },

    /** 强制刷新某个字典 */
    async refresh(dictCode: string): Promise<DictItem[]> {
      delete this.itemsMap[dictCode]
      return this.load(dictCode)
    },
  },
})
