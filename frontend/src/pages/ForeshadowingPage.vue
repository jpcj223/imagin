<template>
  <div class="page page-wide foreshadowing-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">🎭</span>
          伏笔看板
        </h1>
        <p class="page-subtitle">
          把伏笔按生命周期排布，及时发现过期、长期未回收和剧情债
        </p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ totalCount }}</span>
            <span class="stat-label">伏笔总数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num danger">{{ highRiskCount }}</span>
            <span class="stat-label">高风险</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num success">{{ resolvedCount }}</span>
            <span class="stat-label">已回收</span>
          </div>
        </div>
        <n-button type="primary" @click="startCreate">
          <template #icon>＋</template>
          添加伏笔
        </n-button>
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <n-input v-model:value="keyword" clearable placeholder="搜索关键词、描述、备注" style="width: 280px">
        <template #prefix>🔍</template>
      </n-input>
      <n-select v-model:value="importanceFilter" clearable :options="importanceOptions" placeholder="重要性" style="width: 120px" />
      <n-input-number v-model:value="chapterFilter" clearable :min="1" placeholder="章节范围" style="width: 120px" />
      <div class="filter-spacer"></div>
      <n-button text size="small" @click="load">↻ 刷新</n-button>
    </div>

    <!-- 主体：看板 + 详情 -->
    <div class="workbench">
      <!-- 左侧：看板 -->
      <section class="kanban-panel">
        <div class="panel-head">
          <h2>伏笔生命周期</h2>
        </div>
        <div class="kanban-container">
          <div v-for="column in statusColumns" :key="column.value" class="kanban-column">
            <div class="column-header">
              <strong>{{ column.label }}</strong>
              <n-tag size="tiny" type="default">{{ itemsByStatus(column.value).length }}</n-tag>
            </div>
            <n-scrollbar class="column-scroll">
              <div class="column-body">
                <n-empty v-if="itemsByStatus(column.value).length === 0" size="small" description="暂无伏笔" />
                <template v-else>
                  <div
                    v-for="item in itemsByStatus(column.value)"
                    :key="item.id"
                    class="kanban-card"
                    :class="{ active: editingId === item.id, danger: riskOf(item) === 'high', warning: riskOf(item) === 'medium' }"
                    @click="selectForeshadowing(item)"
                  >
                    <div class="card-header">
                      <span class="card-title">{{ item.keyword }}</span>
                      <n-tag size="tiny" :type="importanceTagType(item.importance)">
                        {{ importanceLabel(item.importance) }}
                      </n-tag>
                    </div>
                    <div class="card-meta">
                      埋 {{ item.planted_chapter ?? '-' }} · 回 {{ item.payoff_chapter ?? '-' }}
                    </div>
                    <div class="card-desc">{{ shortText(item.description) }}</div>
                    <div class="card-actions">
                      <n-button
                        v-for="target in nextStatuses(item.status)"
                        :key="target.value"
                        size="tiny"
                        @click.stop="moveStatus(item, target.value)"
                      >
                        {{ target.short }}
                      </n-button>
                    </div>
                  </div>
                </template>
              </div>
            </n-scrollbar>
          </div>
        </div>
      </section>

      <!-- 右侧：详情编辑 -->
      <aside class="detail-panel">
        <div class="detail-header">
          <div class="detail-title">
            <h2>
              {{ editingId ? '伏笔详情' : '新伏笔' }}
              <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
            </h2>
            <span class="detail-sub">{{ riskText }}</span>
          </div>
          <div class="detail-actions">
            <n-popconfirm v-if="editingId" positive-text="确认删除" negative-text="取消" @positive-click="remove">
              <template #trigger>
                <n-button type="error" text>🗑️ 删除</n-button>
              </template>
              确认删除这个伏笔？
            </n-popconfirm>
            <n-button @click="resetCurrent">↺ 重置</n-button>
            <n-button type="primary" @click="save">💾 保存</n-button>
          </div>
        </div>

        <div v-if="!editingId && !isCreating" class="detail-empty">
          <div class="empty-icon">✏️</div>
          <p>从左侧选择一个伏笔进行编辑</p>
          <p class="empty-sub">或点击右上角添加</p>
        </div>

        <n-scrollbar v-else class="form-scroll">
          <n-form class="detail-form" label-placement="top">
            <div class="form-section">
              <div class="section-title">
                基本信息
                <span class="section-hint">伏笔的核心标识</span>
              </div>
              <n-form-item label="伏笔关键词">
                <n-input v-model:value="form.keyword" placeholder="例如：神秘信件" size="large" />
              </n-form-item>
              <div class="form-grid-2">
                <n-form-item label="状态">
                  <n-select v-model:value="form.status" :options="statusOptions" />
                </n-form-item>
                <n-form-item label="重要性">
                  <n-select v-model:value="form.importance" :options="importanceOptions" />
                </n-form-item>
              </div>
            </div>

            <div class="form-section">
              <div class="section-title">
                生命周期
                <span class="section-hint">埋下和回收的章节节点</span>
              </div>
              <div class="form-grid-2">
                <n-form-item label="埋下章节">
                  <n-input-number v-model:value="form.planted_chapter" :min="1" clearable style="width: 100%" />
                </n-form-item>
                <n-form-item label="回收章节">
                  <n-input-number v-model:value="form.payoff_chapter" :min="1" clearable style="width: 100%" />
                </n-form-item>
              </div>
              <div class="form-grid-2">
                <n-form-item label="生效起始章节">
                  <n-input-number v-model:value="form.effective_from" :min="1" clearable style="width: 100%" />
                </n-form-item>
                <n-form-item label="失效章节">
                  <n-input-number v-model:value="form.expires_at" :min="1" clearable style="width: 100%" />
                </n-form-item>
              </div>
            </div>

            <div class="form-section">
              <div class="section-title">
                关联数据
                <span class="section-hint">与其他资料的关联关系</span>
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
            </div>

            <div class="form-section">
              <div class="section-title">
                伏笔描述
                <span class="section-hint">详细内容和回收方式</span>
              </div>
              <n-form-item label="描述">
                <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 6, maxRows: 10 }" placeholder="详细描述伏笔具体内容、表现形式、回收方式..." />
              </n-form-item>
              <n-form-item label="备注">
                <n-input v-model:value="form.notes" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" placeholder="额外说明、注意事项、可能的剧情影响..." />
              </n-form-item>
            </div>

            <div v-if="form.status === 'abandoned'" class="form-section">
              <div class="section-title">
                废弃处理
                <span class="section-hint">标记替代伏笔</span>
              </div>
              <n-form-item label="被替代伏笔">
                <n-select
                  v-model:value="form.replaced_by_id"
                  clearable
                  filterable
                  :options="foreshadowingOptions"
                  placeholder="选择接替本伏笔的新伏笔"
                />
                <div class="field-hint">标记后，新伏笔会出现在原伏笔的"替代链"中，方便追踪剧情演变。</div>
              </n-form-item>
            </div>
          </n-form>

          <!-- 智能发现入口 -->
          <div class="ai-discovery-entry">
            <div class="ai-discovery-icon">✨</div>
            <div class="ai-discovery-text">
              <div class="ai-discovery-title">智能伏笔发现</div>
              <div class="ai-discovery-desc">分析已写章节，自动识别未登记的伏笔、长期未回收的剧情债。</div>
            </div>
            <n-button size="small" type="primary" ghost disabled>即将上线</n-button>
          </div>

          <!-- 风险提示 -->
          <div class="risk-card">
            <div class="risk-header">
              <span class="risk-icon">⚠️</span>
              <span class="risk-title">风险提示</span>
            </div>
            <div class="check-list">
              <div v-for="item in riskHints" :key="item" class="check-row" :class="{ ready: !item.includes('风险') }">
                <span class="check-icon">{{ item.includes('风险') ? '!' : '✓' }}</span>
                <span class="check-text">{{ item }}</span>
              </div>
            </div>
          </div>
        </n-scrollbar>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { createResource, deleteResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
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
const isCreating = ref(false)
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
  related_outline_ids: '',
  replaced_by_id: null as number | null
})

// 脏数据检测
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
const totalCount = computed(() => foreshadowings.value.length)
const highRiskCount = computed(() => foreshadowings.value.filter((item) => riskOf(item) === 'high').length)
const resolvedCount = computed(() => foreshadowings.value.filter((item) => item.status === 'resolved').length)

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
const foreshadowingOptions = computed(() =>
  foreshadowings.value
    .filter((item) => item.id !== editingId.value)
    .map((item) => ({ label: item.keyword, value: item.id }))
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

function importanceTagType(importance: string): 'default' | 'success' | 'warning' | 'info' | 'error' {
  const map: Record<string, 'default' | 'success' | 'warning' | 'info' | 'error'> = {
    high: 'error',
    medium: 'warning',
    low: 'default'
  }
  return map[importance] || 'default'
}

function nextStatuses(status: string) {
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
    related_outline_ids: item?.related_outline_ids ?? '',
    replaced_by_id: item?.replaced_by_id ?? null
  })
}

function importanceLabel(value: string) {
  return importanceOptions.find((item) => item.value === value)?.label ?? value
}

async function startCreate() {
  if (!(await confirmIfDirty())) return
  editingId.value = null
  isCreating.value = true
  fillForm()
  await nextTick()
  markClean()
}

async function selectForeshadowing(item: ForeshadowingItem) {
  if (editingId.value === item.id) return
  if (!(await confirmIfDirty())) return
  editingId.value = item.id
  isCreating.value = false
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
    isCreating.value = false
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
  const projectId = projectStore.currentProject!.id
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
    if (!editingId.value && foreshadowings.value[0]) {
      editingId.value = foreshadowings.value[0].id
      isCreating.value = false
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
      isCreating.value = false
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
  const nextItem = foreshadowings.value[currentIndex + 1] || foreshadowings.value[currentIndex - 1]
  if (nextItem) {
    editingId.value = nextItem.id
    fillForm(nextItem)
  } else {
    editingId.value = null
    isCreating.value = false
    fillForm()
  }
  await load()
  await nextTick()
  markClean()
}

useProjectDataLoader(load)
</script>

<style scoped>
.foreshadowing-page {
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 12px;
}

/* ===== 页头 ===== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0px;
}

.title-icon {
  font-size: 18px;
  margin-right: -2px;
}

.page-subtitle {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 14px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 50px;
}

.stat-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--n-color-primary, #3b82f6);
  line-height: 1.2;
}

.stat-num.danger {
  color: #ef4444;
}

.stat-num.success {
  color: #10b981;
}

.stat-label {
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 2px;
}

.stat-divider {
  width: 1px;
  height: 24px;
  background: var(--n-border-color, #2a2f3a);
}

/* ===== 筛选栏 ===== */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  flex-shrink: 0;
}

.filter-spacer {
  flex: 1;
}

/* ===== 工作区 ===== */
.workbench {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(700px, 1fr) 360px;
  gap: 12px;
  min-height: 0;
}

/* ===== 看板面板 ===== */
.kanban-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.panel-head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.kanban-container {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  padding: 12px;
  min-height: 0;
}

.kanban-column {
  display: flex;
  flex-direction: column;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  min-height: 0;
  overflow: hidden;
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  font-size: 13px;
  flex-shrink: 0;
}

.column-scroll {
  flex: 1;
  min-height: 0;
}

.column-body {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kanban-card {
  padding: 10px 12px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  background: var(--n-color-card, #1a1d21);
  cursor: pointer;
  transition: all 0.15s ease;
}

.kanban-card:hover {
  border-color: var(--n-color-primary-3, #3b82f6);
  background: var(--n-color-hover, #23272f);
}

.kanban-card.active {
  border-color: var(--n-color-primary, #3b82f6);
  background: rgba(59, 130, 246, 0.08);
}

.kanban-card.warning {
  border-color: rgba(242, 201, 125, 0.5);
}

.kanban-card.danger {
  border-color: rgba(239, 68, 68, 0.5);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  margin-bottom: 6px;
}

.card-desc {
  font-size: 12px;
  color: var(--n-text-color-2, #9ca3af);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
}

/* ===== 详情面板 ===== */
.detail-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.detail-title {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-title h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.detail-sub {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.dirty-dot {
  color: #f59e0b;
  font-size: 10px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.form-scroll {
  flex: 1;
  min-height: 0;
  padding: 0 16px 16px;
}

.detail-form {
  padding-top: 16px;
}

.form-section {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
}

.form-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
  padding-left: 10px;
  border-left: 3px solid var(--n-color-primary, #3b82f6);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--n-text-color-3, #6b7280);
}

.form-grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field-hint {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 6px;
  line-height: 1.5;
}

.detail-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--n-text-color-3, #6b7280);
}

.detail-empty .empty-icon {
  font-size: 40px;
}

.detail-empty p {
  margin: 0;
  font-size: 13px;
}

.detail-empty .empty-sub {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  opacity: 0.7;
}

/* ===== AI 发现入口 ===== */
.ai-discovery-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  margin: 16px 0;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.08));
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 8px;
}

.ai-discovery-icon { font-size: 24px; flex-shrink: 0; }
.ai-discovery-text { flex: 1; min-width: 0; }
.ai-discovery-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 2px;
}
.ai-discovery-desc {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  line-height: 1.4;
}

/* ===== 风险卡片 ===== */
.risk-card {
  padding: 12px 14px;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.risk-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
}

.risk-icon {
  font-size: 14px;
}

.check-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.check-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: var(--n-text-color-2, #9ca3af);
}

.check-row.ready {
  color: var(--n-text-color-2, #9ca3af);
}

.check-icon {
  color: #f59e0b;
  font-weight: 700;
  flex-shrink: 0;
}

.check-row.ready .check-icon {
  color: #10b981;
}
</style>
