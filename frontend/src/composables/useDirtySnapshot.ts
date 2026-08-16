import { computed, toRaw } from 'vue'

function snapshotOf(value: unknown) {
  return JSON.stringify(toRaw(value))
}

export function useDirtySnapshot<T extends object>(form: T) {
  let savedSnapshot = snapshotOf(form)

  const isDirty = computed(() => snapshotOf(form) !== savedSnapshot)

  function markClean() {
    // 保存、重置或切换资料后同步快照，后续才知道用户又改了哪些字段。
    savedSnapshot = snapshotOf(form)
  }

  return { isDirty, markClean }
}
