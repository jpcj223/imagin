import { ref, watch, onMounted, type Ref } from 'vue'
import { useProjectStore } from '@/stores/project'

/**
 * 项目数据加载器 composable
 * ------------------------------------------------------------------
 * 解决"切换项目后页面数据不刷新"的问题。
 *
 * 用法：
 *   const { loading } = useProjectDataLoader(async () => {
 *     // 你的数据加载逻辑
 *     await loadCharacters()
 *   })
 *
 * 自动处理：
 * 1. onMounted 时确保项目已加载，然后执行 load
 * 2. 监听 projectStore.currentProject.id 变化，切换项目时自动重新 load
 * 3. loading 状态在加载期间为 true，可用于显示加载指示器
 *
 * 设计要点：
 * - 保持向后兼容：不破坏现有页面的 onMounted 逻辑
 * - 防抖：快速连续切换项目时，只使用最后一次的加载结果
 * - 错误由各页面自己通过 notify 处理，composable 只负责触发
 */
export function useProjectDataLoader(
  loadFn: () => Promise<void> | void,
  options: { immediate?: boolean } = {}
) {
  const { immediate = true } = options
  const projectStore = useProjectStore()
  const loading = ref(false)
  let loadSeq = 0 // 加载序号，防止旧请求覆盖新数据

  async function doLoad() {
    const seq = ++loadSeq
    // 如果项目还没加载，先等一下
    if (!projectStore.currentProject) {
      await projectStore.loadProjects()
    }
    if (!projectStore.currentProject) return
    try {
      loading.value = true
      await loadFn()
    } finally {
      // 只有最新一次加载才修改 loading，避免快速切换时闪烁
      if (seq === loadSeq) {
        loading.value = false
      }
    }
  }

  if (immediate) {
    onMounted(() => {
      doLoad()
    })
  }

  // 监听项目切换：currentProject 的 id 变化时重新加载数据
  watch(
    () => projectStore.currentProject?.id,
    (newId, oldId) => {
      if (newId && newId !== oldId) {
        doLoad()
      }
    },
  )

  return {
    loading,
    reload: doLoad,
  }
}
