import { computed, toRaw } from 'vue'
import { notify } from '@/utils/notify'

function snapshotOf(value: unknown) {
  return JSON.stringify(toRaw(value))
}

/**
 * 脏数据检测 composable
 * ------------------------------------------------------------------
 * 通过 JSON 序列化快照对比，检测表单是否有未保存的修改。
 *
 * 用法：
 *   const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form)
 *   - isDirty: computed<boolean>  是否有未保存修改
 *   - markClean(): 保存/重置/切换条目后调用，同步快照
 *   - confirmIfDirty(): 如果有未保存修改，弹出确认框，返回 Promise<boolean>
 *
 * 设计要点：
 * 1. 浅检测够用，避免深比较的性能开销（资料页表单规模不大）。
 * 2. markClean 必须在表单数据被外部覆盖后立即调用，否则 isDirty 会误报。
 * 3. confirmIfDirty 复用全局 notify.confirm，保持弹窗风格统一。
 */
export function useDirtySnapshot<T extends object>(form: T, dirtyMessage = '当前内容有未保存的修改，确定要离开吗？') {
  let savedSnapshot = snapshotOf(form)

  const isDirty = computed(() => snapshotOf(form) !== savedSnapshot)

  function markClean() {
    // 保存、重置或切换资料后同步快照，后续才知道用户又改了哪些字段。
    savedSnapshot = snapshotOf(form)
  }

  /**
   * 如果有未保存修改，弹出确认对话框。
   * 返回 Promise<boolean>：true 表示用户确认继续，false 表示取消。
   * 如果没有脏数据，直接返回 true。
   */
  async function confirmIfDirty(customMessage?: string): Promise<boolean> {
    if (!isDirty.value) return true
    const ok = await notify.confirm('未保存的修改', customMessage || dirtyMessage, '离开', '取消')
    return ok
  }

  return { isDirty, markClean, confirmIfDirty }
}
