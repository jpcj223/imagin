<template>
  <div class="page page-wide">
    <div class="page-title">
      <div>
        <h1>🎭 剧情风险看板</h1>
        <p class="muted">把伏笔按生命周期排布，及时发现过期、长期未回收和剧情债。</p>
      </div>
      <div class="title-actions">
        <n-button @click="load">刷新</n-button>
        <n-button type="primary" @click="startCreate">添加伏笔</n-button>
      </div>
    </div>

    <div class="kanban-shell">
      <div class="kanban-filters">
        <n-input v-model:value="keyword" clearable placeholder="搜索关键词、描述、备注" />
        <n-select v-model:value="importanceFilter" clearable :options="importanceOptions" placeholder="重要性" />
        <n-input-number v-model:value="chapterFilter" clearable :min="1" placeholder="章节范围" />
      </div>

      <div class="kanban-workbench">
        <section class="kanban-board">
          <div v-for="column in statusColumns" :key="column.value" class="kanban-column">
            <div class="kanban-head">
              <strong>{{ column.label }}</strong>
              <span>{{ itemsByStatus(column.value).length }}</span>
            </div>
            <div class="kanban-list">
              <n-empty v-if="itemsByStatus(column.value).length === 0" size="small" description="暂无伏笔" />
              <template v-else>
                <button
                  v-for="item in itemsByStatus(column.value)"
                  :key="item.id"
                  class="kanban-card"
                  :class="{ active: editingId === item.id, danger: riskOf(item) === 'high', warning: riskOf(item) === 'medium' }"
                  @click="selectForeshadowing(item)"
                >
                  <div class="item-title">
                    <span>{{ item.keyword }}</span>
                    <span class="muted">{{ importanceLabel(item.importance) }}</span>
                  </div>
                  <div class="item-meta">
                    埋 {{ item.planted_chapter ?? '-' }} · 回 {{ item.payoff_chapter ?? '-' }}
                  </div>
                  <div class="item-meta">{{ shortText(item.description) }}</div>
                  <div class="quick-status">
                    <n-button
                      v-for="target in nextStatuses(item.status)"
                      :key="target.value"
                      size="tiny"
                      @click.stop="moveStatus(item, target.value)"
                    >
                      {{ target.short }}
                    </n-button>
                  </div>
                </button>
              </template>
            </div>
          </div>
        </section>

        <aside class="detail-panel risk-detail">
          <div class="panel-head inline-head">
            <h2>
              {{ editingId ? '伏笔详情' : '新伏笔' }}
              <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
            </h2>
            <span class="muted">{{ riskText }}</span>
          </div>

          <n-form label-placement="top">
            <n-form-item label="伏笔关键词">
              <n-input v-model:value="form.keyword" placeholder="例如：神秘信件" />
            </n-form-item>
            <n-form-item label="伏笔描述">
              <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
            <div class="grid-2">
              <n-form-item label="状态">
                <n-select v-model:value="form.status" :options="statusOptions" />
              </n-form-item>
              <n-form-item label="重要性">
                <n-select v-model:value="form.importance" :options="importanceOptions" />
              </n-form-item>
            </div>
            <div class="grid-2">
              <n-form-item label="埋下章节">
                <n-input-number v-model:value="form.planted_chapter" :min="1" clearable />
              </n-form-item>
              <n-form-item label="回收章节">
                <n-input-number v-model:value="form.payoff_chapter" :min="1" clearable />
              </n-form-item>
            </div>
            <div class="grid-2">
              <n-form-item label="生效起始章节">
                <n-input-number v-model:value="form.effective_from" :min="1" clearable />
              </n-form-item>
              <n-form-item label="失效章节">
                <n-input-number v-model:value="form.expires_at" :min="1" clearable />
              </n-form-item>
            </div>
            <n-form-item label="关联角色">
              <n-select v-model:value="selectedCharacterIds" multiple clearable filterable :options="characterOptions" placeholder="选择伏笔牵连的角色" />
            </n-form-item>
            <n-form-item label="关联组织">
              <n-select v-model:value="selectedOrganizationIds" multiple clearable filterable :options="organizationOptions" placeholder="选择伏笔牵连的组织" />
            </n-form-item>
            <n-form-item label="关联大纲">
              <n-select v-model:value="selectedOutlineIds" multiple clearable filterable :options="outlineOptions" placeholder="选择埋设或回收所在大纲" />
            </n-form-item>
            <n-form-item label="备注">
              <n-input v-model:value="form.notes" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
          </n-form>

          <div class="detail-actions">
            <n-button type="primary" @click="save">保存</n-button>
            <n-button @click="startCreate">新增</n-button>
            <n-button @click="resetCurrent">重置</n-button>
            <n-popconfirm v-if="editingId" positive-text="确认删除" negative-text="取消" @positive-click="remove">
              <template #trigger>
                <n-button type="error">删除</n-button>
              </template>
              确认删除这个伏笔？
            </n-popconfirm>
          </div>

          <div class="insight-card">
            <div class="insight-label">风险提示</div>
            <div class="check-list">
              <div v-for="item in riskHints" :key="item" class="check-row" :class="{ ready: !item.includes('风险') }">
                <span>{{ item.includes('风险') ? '!' : '✓' }}</span>
                <span>{{ item }}</span>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { createResource, deleteResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useDirtySnapshot } from '@/composables/useDirtySnapshot'
import { notify } from '@/utils/notify'
import type { CharacterItem, ChapterItem, ForeshadowingItem, OrganizationItem, OutlineItem } from '@/types/domain'

const projectStore = useProjectStore()
const foreshadowings = ref<ForeshadowingItem[]>([])
const chapters = ref<ChapterItem[]>([])
const characters = ref<CharacterItem[]>([])
const organizations = ref<OrganizationItem[]>([])
const outlines = ref<OutlineItem[]>([])
const keyword = ref('')
const importanceFilter = ref<string | null>(null)
const chapterFilter = ref<number | null>(null)
const editingId = ref<number | null>(null)
const loading = ref(false)
const form = reactive({
  keyword: '',
  description: '',
  status: 'pending',
  importance: 'medium',
  planted_chapter: 1 as number | null,
  payoff_chapter: null as number | null,
  effective_from: null as number | null,
  expires_at: null as number | null,
  notes: '',
  related_character_ids: '',
  related_organization_ids: '',
  related_outline_ids: ''
})

// 脏数据检测：切换伏笔、新增、重置前检查是否有未保存修改。
const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form, '当前伏笔有未保存的修改，确定要离开吗？')

const statusColumns = [
  { label: '待埋设', value: 'pending', short: '待埋' },
  { label: '已埋设', value: 'planted', short: '已埋' },
  { label: '发展中', value: 'developing', short: '发展' },
  { label: '待回收', value: 'payoff_pending', short: '回收' },
  { label: '已回收', value: 'resolved', short: '完成' },
  { label: '废弃', value: 'abandoned', short: '废弃' }
]
const statusOptions = statusColumns.map(({ label, value }) => ({ label, value }))
const importanceOptions = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' }
]

const latestChapterNo = computed(() => Math.max(0, ...chapters.value.map((item) => item.chapter_no)))
const filteredForeshadowings = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return foreshadowings.value.filter((item) => {
    const matchedText = !text || [item.keyword, item.description, item.notes].join(' ').toLowerCase().includes(text)
    const matchedImportance = !importanceFilter.value || item.importance === importanceFilter.value
    const matchedChapter = !chapterFilter.value || includesChapter(item, chapterFilter.value)
    return matchedText && matchedImportance && matchedChapter
  })
})
const riskText = computed(() => {
  const risk = riskOf(form as ForeshadowingItem)
  if (risk === 'high') return '高风险'
  if (risk === 'medium') return '需关注'
  return '正常'
})
const riskHints = computed(() => {
  const hints = []
  if (!form.payoff_chapter && ['planted', 'developing', 'payoff_pending'].includes(form.status)) hints.push('风险：未设置回收章节')
  if (form.expires_at && latestChapterNo.value > form.expires_at && form.status !== 'resolved') hints.push('风险：已超过失效章节')
  if (form.importance === 'high' && form.status === 'pending') hints.push('高重要性伏笔尚未埋设')
  if (!hints.length) hints.push('生命周期信息清晰')
  return hints
})
const characterOptions = computed(() => characters.value.map((item) => ({ label: item.name, value: item.id })))
const organizationOptions = computed(() => organizations.value.map((item) => ({ label: item.name, value: item.id })))
const outlineOptions = computed(() =>
  outlines.value.map((item) => ({ label: `${item.chapter_no ? `第${item.chapter_no}章 · ` : ''}${item.title}`, value: item.id }))
)
const selectedCharacterIds = computed({
  get: () => parseIds(form.related_character_ids),
  set: (value: number[]) => {
    form.related_character_ids = joinIds(value)
  }
})
const selectedOrganizationIds = computed({
  get: () => parseIds(form.related_organization_ids),
  set: (value: number[]) => {
    form.related_organization_ids = joinIds(value)
  }
})
const selectedOutlineIds = computed({
  get: () => parseIds(form.related_outline_ids),
  set: (value: number[]) => {
    form.related_outline_ids = joinIds(value)
  }
})

function parseIds(value: string) {
  return value
    .split(',')
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isFinite(item) && item > 0)
}

function joinIds(value: number[]) {
  return value.join(',')
}

function itemsByStatus(status: string) {
  return filteredForeshadowings.value.filter((item) => item.status === status)
}

function includesChapter(item: ForeshadowingItem, chapterNo: number) {
  const start = item.effective_from ?? item.planted_chapter ?? 1
  const end = item.expires_at ?? item.payoff_chapter ?? Number.MAX_SAFE_INTEGER
  return chapterNo >= start && chapterNo <= end
}

function riskOf(item: Partial<ForeshadowingItem>) {
  const unresolved = !['resolved', 'abandoned'].includes(item.status ?? '')
  if (unresolved && item.expires_at && latestChapterNo.value > item.expires_at) return 'high'
  if (unresolved && item.importance === 'high' && !item.payoff_chapter) return 'medium'
  return 'low'
}

function nextStatuses(status: string) {
  // 卡片上的快捷动作只提供邻近状态，避免误把伏笔跳到很远的生命周期节点。
  const order = statusColumns.map((item) => item.value)
  const index = order.indexOf(status)
  return statusColumns.filter((_, itemIndex) => itemIndex === index + 1 || itemIndex === statusColumns.length - 1)
}

function shortText(value: string) {
  return value?.length > 48 ? `${value.slice(0, 48)}...` : value || '描述未填写'
}

function fillForm(item?: Partial<ForeshadowingItem>) {
  Object.assign(form, {
    keyword: item?.keyword ?? '',
    description: item?.description ?? '',
    status: item?.status ?? 'pending',
    importance: item?.importance ?? 'medium',
    planted_chapter: item?.planted_chapter ?? 1,
    payoff_chapter: item?.payoff_chapter ?? null,
    effective_from: item?.effective_from ?? null,
    expires_at: item?.expires_at ?? null,
    notes: item?.notes ?? '',
    related_character_ids: item?.related_character_ids ?? '',
    related_organization_ids: item?.related_organization_ids ?? '',
    related_outline_ids: item?.related_outline_ids ?? ''
  })
}

function importanceLabel(value: string) {
  return importanceOptions.find((item) => item.value === value)?.label ?? value
}

async function startCreate() {
  // 新增伏笔前检查脏数据，避免丢失当前编辑内容。
  if (!(await confirmIfDirty())) return
  editingId.value = null
  fillForm()
  await nextTick()
  markClean()
}

async function selectForeshadowing(item: ForeshadowingItem) {
  // 看板卡片点击负责切换详情；同一条目重复点击直接跳过。
  if (editingId.value === item.id) return
  if (!(await confirmIfDirty())) return
  editingId.value = item.id
  fillForm(item)
  await nextTick()
  markClean()
}

async function resetCurrent() {
  if (!(await confirmIfDirty('确定要重置当前伏笔吗？'))) return
  const current = foreshadowings.value.find((item) => item.id === editingId.value)
  if (current) {
    fillForm(current)
  } else {
    editingId.value = null
    fillForm()
  }
  await nextTick()
  markClean()
}

async function moveStatus(item: ForeshadowingItem, status: string) {
  const updated = await updateResource<ForeshadowingItem>('foreshadowings', item.id, { status })
  notify.success(`已移动到「${statusColumns.find((column) => column.value === status)?.label}」`)
  await load()
  const fresh = foreshadowings.value.find((f) => f.id === updated.id)
  if (fresh && editingId.value === updated.id) {
    fillForm(fresh)
    await nextTick()
    markClean()
  }
}

async function ensureProject() {
  if (!projectStore.currentProject) await projectStore.loadDefaultProject()
  return projectStore.currentProject?.id
}

async function load() {
  const projectId = await ensureProject()
  if (!projectId) return
  loading.value = true
  try {
    const [foreshadowingList, chapterList, characterList, organizationList, outlineList] = await Promise.all([
      listResource<ForeshadowingItem>(projectId, 'foreshadowings'),
      listResource<ChapterItem>(projectId, 'chapters'),
      listResource<CharacterItem>(projectId, 'characters'),
      listResource<OrganizationItem>(projectId, 'organizations'),
      listResource<OutlineItem>(projectId, 'outlines')
    ])
    foreshadowings.value = foreshadowingList
    chapters.value = chapterList
    characters.value = characterList
    organizations.value = organizationList
    outlines.value = outlineList
    // 首次加载时自动选中第一条，但只有在没有正在编辑的条目时才覆盖。
    if (!editingId.value && foreshadowings.value[0]) {
      editingId.value = foreshadowings.value[0].id
      fillForm(foreshadowings.value[0])
      await nextTick()
      markClean()
    }
  } finally {
    loading.value = false
  }
}

async function save() {
  const projectId = await ensureProject()
  if (!projectId) return

  // 保存后刷新整块看板，让状态列、风险提示和详情区保持一致。
  if (editingId.value) {
    const updated = await updateResource<ForeshadowingItem>('foreshadowings', editingId.value, { ...form })
    notify.success('伏笔已更新')
    await load()
    const fresh = foreshadowings.value.find((item) => item.id === updated.id)
    if (fresh) {
      fillForm(fresh)
      await nextTick()
      markClean()
    }
  } else {
    const created = await createResource<ForeshadowingItem>('foreshadowings', { project_id: projectId, ...form })
    notify.success('伏笔已添加')
    await load()
    const fresh = foreshadowings.value.find((item) => item.id === created.id)
    if (fresh) {
      editingId.value = fresh.id
      fillForm(fresh)
      await nextTick()
      markClean()
    }
  }
}

async function remove() {
  if (!editingId.value) return
  const currentIndex = foreshadowings.value.findIndex((item) => item.id === editingId.value)
  await deleteResource('foreshadowings', editingId.value)
  notify.success('伏笔已删除')
  // 删除后自动选择下一条；如果是最后一条，选上一条；如果都没有，进入新建状态。
  const nextItem = foreshadowings.value[currentIndex + 1] || foreshadowings.value[currentIndex - 1]
  if (nextItem) {
    editingId.value = nextItem.id
    fillForm(nextItem)
  } else {
    editingId.value = null
    fillForm()
  }
  await load()
  await nextTick()
  markClean()
}

onMounted(load)
</script>

<style scoped>
.title-actions {
  display: flex;
  gap: 10px;
}

.kanban-shell {
  display: grid;
  gap: 14px;
}

.kanban-filters {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) 180px 160px;
  gap: 12px;
  padding: 14px;
  border: 1px solid #363b42;
  border-radius: 8px;
  background: #202327;
}

.kanban-workbench {
  display: grid;
  grid-template-columns: minmax(760px, 1fr) 360px;
  gap: 16px;
  align-items: start;
}

.kanban-board {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.kanban-column {
  min-height: 360px;
  border: 1px solid #363b42;
  border-radius: 8px;
  background: #202327;
}

.kanban-head {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid #32363c;
  color: #e5e7eb;
}

.kanban-list {
  display: grid;
  gap: 10px;
  min-height: 260px;
  padding: 10px;
}

.kanban-card {
  width: 100%;
  padding: 10px;
  border: 1px solid #30343a;
  border-radius: 8px;
  color: #d1d5db;
  background: #181b1f;
  text-align: left;
  cursor: pointer;
}

.kanban-card:hover,
.kanban-card.active {
  border-color: #4f8cff;
  background: #222936;
}

.kanban-card.warning {
  border-color: rgba(242, 201, 125, 0.6);
}

.kanban-card.danger {
  border-color: rgba(232, 128, 128, 0.75);
}

.quick-status {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.risk-detail {
  position: sticky;
  top: 16px;
}

.insight-card {
  margin-top: 14px;
  padding: 12px;
  border: 1px solid #30343a;
  border-radius: 8px;
  background: #181b1f;
}

.insight-label {
  margin-bottom: 8px;
  color: #e5e7eb;
  font-weight: 800;
}

.dirty-dot {
  margin-left: 6px;
  color: #f59e0b;
  font-size: 12px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
