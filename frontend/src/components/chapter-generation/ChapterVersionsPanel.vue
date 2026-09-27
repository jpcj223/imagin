<template>
  <div class="tab-content">
    <div class="versions-header">
      <div>
        <span class="block-title">正文版本</span>
        <small>{{ versions.length }} 个版本</small>
      </div>
      <n-button size="tiny" :loading="loading" @click="refresh">刷新</n-button>
    </div>

    <n-alert v-if="chapterId" type="info" :show-icon="true" class="draft-note">
      正文草稿会自动保存；点击「保存当前稿为版本」后才会进入不可变的版本历史。
    </n-alert>
    <div class="toolbar">
      <n-button
        size="small"
        type="primary"
        :loading="snapshotSaving"
        :disabled="!chapterId || !draft.trim()"
        @click="saveDraftAsVersion"
      >保存当前稿为版本</n-button>
      <n-button size="small" :disabled="versions.length < 2" @click="openCompare()">比较两个版本</n-button>
    </div>

    <div v-if="!chapterId" class="empty">请先生成或选择章节</div>
    <div v-else-if="loading && versions.length === 0" class="empty">正在读取版本…</div>
    <div v-else-if="versions.length === 0" class="empty">暂无历史版本</div>
    <div v-else class="version-list">
      <article
        v-for="version in versions"
        :key="version.version_id"
        class="version-item"
        :class="{ current: version.is_current }"
      >
        <div class="version-heading">
          <div class="version-badge">
            v{{ version.version_number }}
            <n-tag v-if="version.is_current" size="tiny" type="success">当前</n-tag>
            <n-tag v-if="version.is_favorite" size="tiny" type="warning">收藏</n-tag>
            <n-tag size="tiny" :type="sourceType(version.source_type).type">{{ sourceType(version.source_type).label }}</n-tag>
          </div>
          <span class="version-words">{{ version.word_count }} 字</span>
        </div>
        <div class="version-summary">{{ version.summary || '暂无版本说明' }}</div>
        <div class="version-meta">
          <span>{{ formatDate(version.created_at) }}</span>
          <span v-if="version.rating">评分：{{ '★'.repeat(version.rating) }}{{ '☆'.repeat(5 - version.rating) }}</span>
        </div>
        <div class="version-actions">
          <n-button size="tiny" text @click="viewVersion(version)">查看正文</n-button>
          <n-button size="tiny" text :disabled="versions.length < 2" @click="openCompare(version.version_id)">比较</n-button>
          <n-button size="tiny" text @click="toggleFavorite(version)">{{ version.is_favorite ? '取消收藏' : '收藏' }}</n-button>
          <n-button size="tiny" text type="warning" :disabled="version.is_current" @click="restore(version)">恢复为当前稿</n-button>
        </div>
      </article>
    </div>

    <n-modal v-model:show="previewVisible" preset="card" :title="previewVersion ? `查看 v${previewVersion.version_number}` : '版本正文'" style="width: min(900px, 94vw)">
      <div v-if="previewVersion" class="preview-meta">
        <n-tag size="small" :type="sourceType(previewVersion.source_type).type">{{ sourceType(previewVersion.source_type).label }}</n-tag>
        <span>{{ previewVersion.word_count }} 字 · {{ formatDate(previewVersion.created_at) }}</span>
      </div>
      <div v-if="previewLoading" class="empty">正在读取版本正文…</div>
      <pre v-else class="content-preview">{{ previewContent }}</pre>
      <template #footer>
        <n-button @click="previewVisible = false">关闭</n-button>
        <n-button v-if="previewVersion && !previewVersion.is_current" type="warning" @click="restore(previewVersion)">恢复为当前稿</n-button>
      </template>
    </n-modal>

    <n-modal v-model:show="compareVisible" preset="card" title="版本比较" style="width: min(1200px, 96vw)">
      <div class="compare-selectors">
        <n-select v-model:value="leftId" :options="versionOptions" placeholder="选择较早版本" />
        <span>对比</span>
        <n-select v-model:value="rightId" :options="versionOptions" placeholder="选择另一个版本" />
        <n-button type="primary" :loading="compareLoading" :disabled="!canCompare" @click="loadComparison">开始比较</n-button>
      </div>
      <n-alert v-if="!canCompare" type="warning" :show-icon="true">需要选择两个不同版本。</n-alert>
      <div v-else class="compare-columns">
        <section>
          <h4>{{ versionLabel(leftId) }}</h4>
          <pre>{{ leftContent || '点击「开始比较」读取版本正文' }}</pre>
        </section>
        <section>
          <h4>{{ versionLabel(rightId) }}</h4>
          <pre>{{ rightContent || '点击「开始比较」读取版本正文' }}</pre>
        </section>
      </div>
      <template #footer>
        <n-button @click="compareVisible = false">关闭</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useMessage } from 'naive-ui'
import {
  createVersionSnapshot,
  getGenerationVersions,
  getVersionContent,
  setCurrentVersion,
  setVersionFavorite,
  type GenerationVersion,
} from '@/api/agentsV3'

const props = defineProps<{
  chapterId: number | null
  draft: string
  persistDraft: () => Promise<boolean>
}>()
const emit = defineEmits<{
  restore: [payload: { content: string; version: GenerationVersion }]
}>()
const message = useMessage()

const versions = ref<GenerationVersion[]>([])
const loading = ref(false)
const snapshotSaving = ref(false)
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewVersion = ref<GenerationVersion | null>(null)
const previewContent = ref('')
const compareVisible = ref(false)
const compareLoading = ref(false)
const leftId = ref<string | null>(null)
const rightId = ref<string | null>(null)
const leftContent = ref('')
const rightContent = ref('')
let listRequestId = 0
let contentRequestId = 0

const versionOptions = computed(() => versions.value.map((version) => ({
  label: `v${version.version_number} · ${sourceType(version.source_type).label} · ${formatDate(version.created_at)}`,
  value: version.version_id,
})))
const canCompare = computed(() => Boolean(leftId.value && rightId.value && leftId.value !== rightId.value))

async function refresh() {
  if (!props.chapterId) {
    listRequestId += 1
    versions.value = []
    loading.value = false
    return
  }
  const chapterId = props.chapterId
  const requestId = ++listRequestId
  loading.value = true
  try {
    const result = await getGenerationVersions(chapterId, 100)
    if (requestId === listRequestId && props.chapterId === chapterId) versions.value = result
  } catch (error) {
    if (requestId === listRequestId) message.error(errorMessage(error, '版本列表读取失败'))
  } finally {
    if (requestId === listRequestId) loading.value = false
  }
}

watch(() => props.chapterId, () => {
  contentRequestId += 1
  previewVisible.value = false
  compareVisible.value = false
  previewVersion.value = null
  previewContent.value = ''
  leftContent.value = ''
  rightContent.value = ''
  void refresh()
}, { immediate: true })

function sourceType(source: GenerationVersion['source_type']) {
  const labels: Record<string, { label: string; type: 'success' | 'info' | 'warning' | 'primary' | 'default' }> = {
    generated: { label: '生成稿', type: 'primary' },
    dialogue_edit: { label: '对话改稿', type: 'info' },
    polish: { label: '精修稿', type: 'warning' },
    restored: { label: '恢复版本', type: 'success' },
    manual_edit: { label: '手动固化', type: 'default' },
  }
  return labels[source ?? ''] ?? { label: '旧版本', type: 'default' as const }
}

async function saveDraftAsVersion() {
  if (!props.chapterId || !props.draft.trim() || snapshotSaving.value) return
  const chapterId = props.chapterId
  const content = props.draft
  snapshotSaving.value = true
  try {
    if (!await props.persistDraft()) return
    if (props.chapterId !== chapterId || props.draft !== content) {
      message.warning('正文在保存期间发生变化，请稍后重新保存版本')
      return
    }
    const result = await createVersionSnapshot(chapterId, content)
    if (props.chapterId !== chapterId) return
    await refresh()
    message.success(`已保存为 v${result.version.version_number}`)
  } catch (error) {
    message.error(errorMessage(error, '保存版本失败'))
  } finally {
    snapshotSaving.value = false
  }
}

async function viewVersion(version: GenerationVersion) {
  if (!props.chapterId) return
  const chapterId = props.chapterId
  const requestId = ++contentRequestId
  previewVersion.value = version
  previewContent.value = ''
  previewVisible.value = true
  previewLoading.value = true
  try {
    const result = await getVersionContent(chapterId, version.version_id)
    if (requestId === contentRequestId && props.chapterId === chapterId) previewContent.value = result.content
  } catch (error) {
    if (requestId === contentRequestId && props.chapterId === chapterId) message.error(errorMessage(error, '读取版本正文失败'))
  } finally {
    if (requestId === contentRequestId) previewLoading.value = false
  }
}

function openCompare(initialVersionId?: string) {
  const current = versions.value.find((version) => version.is_current)
  const other = versions.value.find((version) => version.version_id !== (initialVersionId ?? current?.version_id))
  leftId.value = initialVersionId ?? other?.version_id ?? null
  rightId.value = current?.version_id ?? other?.version_id ?? null
  if (leftId.value === rightId.value) {
    rightId.value = versions.value.find((version) => version.version_id !== leftId.value)?.version_id ?? null
  }
  leftContent.value = ''
  rightContent.value = ''
  compareVisible.value = true
  if (canCompare.value) void loadComparison()
}

async function loadComparison() {
  if (!props.chapterId || !canCompare.value) return
  const chapterId = props.chapterId
  const leftVersionId = leftId.value!
  const rightVersionId = rightId.value!
  const requestId = ++contentRequestId
  compareLoading.value = true
  try {
    const [left, right] = await Promise.all([
      getVersionContent(chapterId, leftVersionId),
      getVersionContent(chapterId, rightVersionId),
    ])
    if (requestId === contentRequestId && props.chapterId === chapterId
      && leftId.value === leftVersionId && rightId.value === rightVersionId) {
      leftContent.value = left.content
      rightContent.value = right.content
    }
  } catch (error) {
    if (requestId === contentRequestId && props.chapterId === chapterId) message.error(errorMessage(error, '读取版本比较内容失败'))
  } finally {
    if (requestId === contentRequestId) compareLoading.value = false
  }
}

async function toggleFavorite(version: GenerationVersion) {
  if (!props.chapterId) return
  try {
    await setVersionFavorite(props.chapterId, version.version_id, !version.is_favorite)
    await refresh()
    message.success(version.is_favorite ? '已取消收藏' : '已收藏版本')
  } catch (error) {
    message.error(errorMessage(error, '收藏状态更新失败'))
  }
}

async function restore(version: GenerationVersion) {
  if (!props.chapterId || version.is_current) return
  const chapterId = props.chapterId
  if (!window.confirm(`恢复 v${version.version_number} 会生成一条新的当前版本，并先保留编辑区现有正文。继续吗？`)) return
  try {
    if (!await props.persistDraft()) return
    const content = props.draft
    await createVersionSnapshot(chapterId, content)
    if (props.chapterId !== chapterId || props.draft !== content) {
      throw new Error('正文在恢复期间发生变化，已取消恢复；当前稿保持不变。')
    }
    const result = await setCurrentVersion(chapterId, version.version_id, content)
    await refresh()
    previewVisible.value = false
    emit('restore', { content: result.content, version: result.version ?? version })
    message.success('已恢复为新版本；原版本记录均已保留')
  } catch (error) {
    message.error(errorMessage(error, '版本恢复失败'))
  }
}

function versionLabel(versionId: string | null) {
  const version = versions.value.find((item) => item.version_id === versionId)
  return version ? `v${version.version_number} · ${sourceType(version.source_type).label}` : '未选择版本'
}

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const elapsed = Date.now() - date.getTime()
  const minutes = Math.floor(elapsed / 60_000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(elapsed / 3_600_000)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(elapsed / 86_400_000)
  return days < 7 ? `${days} 天前` : date.toLocaleDateString('zh-CN')
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

defineExpose({ refresh })
</script>

<style scoped>
.tab-content { display: grid; gap: 10px; }
.block-title { color: var(--n-text-color, #e2e8f0); font-size: 13px; font-weight: 600; }
.versions-header { display: flex; justify-content: space-between; align-items: center; }
.versions-header > div { display: grid; gap: 3px; }
.versions-header small, .version-meta, .version-words { color: var(--n-text-color-3, #7b8494); font-size: 11px; }
.draft-note { margin-bottom: 2px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; }
.empty { padding: 32px 16px; color: var(--n-text-color-3, #7b8494); text-align: center; }
.version-list { display: flex; flex-direction: column; gap: 10px; }
.version-item { padding: 12px; border: 1px solid var(--n-border-color, rgba(148, 163, 184, .2)); border-radius: 10px; background: var(--n-color-embedded, rgba(30, 41, 59, .46)); }
.version-item.current { border-color: rgba(52, 211, 153, .68); background: rgba(16, 185, 129, .08); }
.version-heading { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.version-badge { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; color: var(--n-text-color, #e2e8f0); font-size: 14px; font-weight: 600; }
.version-summary { display: -webkit-box; overflow: hidden; margin-bottom: 8px; color: var(--n-text-color-2, #a8b1c2); font-size: 13px; line-height: 1.5; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.version-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.version-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 6px 12px; }
.preview-meta { display: flex; gap: 10px; align-items: center; margin-bottom: 10px; color: var(--n-text-color-3, #7b8494); font-size: 12px; }
.content-preview, .compare-columns pre { max-height: min(70vh, 720px); overflow: auto; margin: 0; padding: 14px; border: 1px solid var(--n-border-color, rgba(148, 163, 184, .2)); border-radius: 8px; color: var(--n-text-color, #e2e8f0); background: rgba(15, 23, 42, .5); font: inherit; line-height: 1.75; white-space: pre-wrap; overflow-wrap: anywhere; }
.compare-selectors { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) auto; gap: 10px; align-items: center; margin-bottom: 14px; }
.compare-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.compare-columns h4 { margin: 0 0 8px; color: var(--n-text-color, #e2e8f0); }
@media (max-width: 760px) { .compare-selectors, .compare-columns { grid-template-columns: 1fr; } .compare-selectors > span { display: none; } }
</style>
