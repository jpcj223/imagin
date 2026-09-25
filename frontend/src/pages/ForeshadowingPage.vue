<template>
  <div class="page page-wide foreshadowing-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">🔍</span>
          伏笔探案板
        </h1>
        <p class="page-subtitle">
          追踪每一条线索，别让剧情债越积越多
        </p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat stat-total">
            <div class="stat-icon">📋</div>
            <div class="stat-content">
              <span class="stat-num">{{ totalCount }}</span>
              <span class="stat-label">线索总数</span>
            </div>
          </div>
          <div class="stat stat-danger">
            <div class="stat-icon">🚨</div>
            <div class="stat-content">
              <span class="stat-num">{{ highRiskCount }}</span>
              <span class="stat-label">高风险</span>
            </div>
          </div>
          <div class="stat stat-success">
            <div class="stat-icon">✅</div>
            <div class="stat-content">
              <span class="stat-num">{{ resolvedCount }}</span>
              <span class="stat-label">已破案</span>
            </div>
          </div>
        </div>
        <n-button type="primary" @click="startCreate" class="add-btn">
          <template #icon>＋</template>
          新增线索
        </n-button>
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">🔍</span>
        <n-input v-model:value="keyword" clearable placeholder="搜索关键词、描述、备注" style="width: 260px">
        </n-input>
      </div>
      <n-select v-model:value="importanceFilter" clearable :options="importanceOptions" placeholder="重要性" style="width: 120px" />
      <n-input-number v-model:value="chapterFilter" clearable :min="1" placeholder="章节范围" style="width: 120px" />
      <div class="filter-spacer"></div>
      <div class="view-toggle">
        <n-button text size="small" @click="load" class="refresh-btn">↻ 刷新</n-button>
      </div>
    </div>

    <!-- 主体：看板 + 详情 -->
    <div class="workbench">
      <!-- 左侧：看板 -->
      <section class="kanban-panel">
        <div class="panel-head">
          <div class="panel-title-group">
            <span class="panel-title-icon">📌</span>
            <h2>线索生命周期</h2>
          </div>
          <div class="panel-sub">拖拽推进 · 一键转态</div>
        </div>
        <div class="kanban-container">
          <div
            v-for="column in statusColumns"
            :key="column.value"
            class="kanban-column"
            :class="[column.value, { 'drag-over': dragOverStatus === column.value }]"
            @dragover="handleColumnDragOver($event, column.value)"
            @dragleave="handleColumnDragLeave($event, column.value)"
            @drop="handleColumnDrop($event, column.value)"
          >
            <div class="column-header">
              <div class="column-title-group">
                <span class="column-dot"></span>
                <strong>{{ column.label }}</strong>
              </div>
              <span class="column-count">{{ itemsByStatus(column.value).length }}</span>
            </div>
            <n-scrollbar class="column-scroll">
              <div class="column-body">
                <div v-if="itemsByStatus(column.value).length === 0" class="column-empty">
                  <span class="empty-emoji">📭</span>
                  <span>暂无</span>
                </div>
                <template v-else>
                  <div
                    v-for="item in itemsByStatus(column.value)"
                    :key="item.id"
                    class="kanban-card"
                    :class="{ active: editingId === item.id, danger: riskOf(item) === 'high', warning: riskOf(item) === 'medium', dragging: draggingItemId === item.id }"
                    draggable="true"
                    @dragstart.stop="handleCardDragStart($event, item)"
                    @dragend.stop="handleCardDragEnd"
                    @click="selectForeshadowing(item)"
                  >
                    <div class="card-accent"></div>
                    <div class="card-content">
                      <div class="card-header">
                        <span class="card-title">{{ item.keyword }}</span>
                        <span class="importance-badge" :class="item.importance">
                          {{ importanceLabel(item.importance) }}
                        </span>
                      </div>
                      <div class="card-chapter">
                        <span class="chip chip-planted">埋 · 第{{ item.planted_chapter ?? '-' }}章</span>
                        <span class="chip-arrow">→</span>
                        <span class="chip chip-payoff">计划回 · 第{{ item.payoff_chapter ?? '-' }}章</span>
                        <span v-if="item.resolved_chapter" class="chip chip-resolved">实际回 · 第{{ item.resolved_chapter }}章</span>
                      </div>
                      <div class="card-desc">{{ shortText(item.description) }}</div>
                      <div class="card-footer">
                        <div class="card-tags">
                          <span v-if="riskOf(item) === 'high'" class="risk-tag high">⚠ 高风险</span>
                          <span v-else-if="riskOf(item) === 'medium'" class="risk-tag medium">⚡ 需关注</span>
                        </div>
                        <div class="card-actions">
                          <n-button
                            v-for="prev in prevStatuses(item.status, item.id)"
                            :key="'prev-' + prev.value"
                            size="tiny"
                            quaternary
                            class="btn-prev"
                            @click.stop="moveStatus(item, prev.value)"
                          >
                            ← {{ prev.short }}
                          </n-button>
                          <n-button
                            v-for="next in nextStatuses(item.status)"
                            :key="'next-' + next.value"
                            size="tiny"
                            type="primary"
                            ghost
                            @click.stop="moveStatus(item, next.value)"
                          >
                            {{ next.short }} →
                          </n-button>
                        </div>
                      </div>
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
            <div class="detail-title-row">
              <span class="detail-icon">{{ editingId ? '📂' : '✨' }}</span>
              <h2>
                {{ editingId ? '线索档案' : '新线索' }}
                <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
              </h2>
            </div>
            <span class="detail-sub" :class="riskTextClass">{{ riskText }}</span>
          </div>
          <div class="detail-actions">
            <n-popconfirm v-if="editingId" positive-text="确认删除" negative-text="取消" @positive-click="remove">
              <template #trigger>
                <n-button type="error" text>🗑️ 删除</n-button>
              </template>
              确认删除这条线索？
            </n-popconfirm>
            <n-button @click="resetCurrent" quaternary>↺ 重置</n-button>
            <n-button type="primary" @click="save">💾 保存</n-button>
          </div>
        </div>

        <div v-if="!editingId && !isCreating" class="detail-empty">
          <div class="empty-icon-wrap">
            <span class="empty-icon">🔎</span>
          </div>
          <p class="empty-title">选一条线索开始调查</p>
          <p class="empty-sub">或点击右上角新增线索</p>
        </div>

        <n-scrollbar v-else class="form-scroll">
          <n-form class="detail-form" label-placement="top">
            <div class="form-section">
              <div class="section-header">
                <span class="section-icon">📝</span>
                <div class="section-title-group">
                  <div class="section-title">基本信息</div>
                  <div class="section-hint">线索的核心标识</div>
                </div>
              </div>
              <n-form-item label="线索关键词">
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
              <div class="section-header">
                <span class="section-icon">⏳</span>
                <div class="section-title-group">
                  <div class="section-title">生命周期</div>
                  <div class="section-hint">埋下和回收的章节节点</div>
                </div>
              </div>
              <div class="form-grid-2">
                <n-form-item label="埋下章节">
                  <n-input-number v-model:value="form.planted_chapter" :min="1" clearable style="width: 100%" />
                </n-form-item>
                <n-form-item label="计划回收章节">
                  <n-input-number v-model:value="form.payoff_chapter" :min="1" clearable style="width: 100%" />
                </n-form-item>
              </div>
              <div v-if="form.status === 'resolved' || form.resolved_chapter" class="form-grid-2">
                <n-form-item label="实际回收章节">
                  <n-input-number v-model:value="form.resolved_chapter" :min="1" clearable style="width: 100%" />
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
              <div class="section-header">
                <span class="section-icon">🔗</span>
                <div class="section-title-group">
                  <div class="section-title">关联线索</div>
                  <div class="section-hint">与其他资料的关联关系</div>
                </div>
              </div>
              <n-form-item label="关联角色">
                <n-select v-model:value="selectedCharacterIds" multiple clearable filterable :options="characterOptions" placeholder="选择牵连的角色" />
              </n-form-item>
              <n-form-item label="关联组织">
                <n-select v-model:value="selectedOrganizationIds" multiple clearable filterable :options="organizationOptions" placeholder="选择牵连的组织" />
              </n-form-item>
              <n-form-item label="关联大纲">
                <n-select v-model:value="selectedOutlineIds" multiple clearable filterable :options="outlineOptions" placeholder="选择埋设或回收所在大纲" />
              </n-form-item>
            </div>

            <div class="form-section">
              <div class="section-header">
                <span class="section-icon">📜</span>
                <div class="section-title-group">
                  <div class="section-title">线索详情</div>
                  <div class="section-hint">详细内容和回收方式</div>
                </div>
              </div>
              <n-form-item label="描述">
                <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 6, maxRows: 10 }" placeholder="详细描述线索具体内容、表现形式、回收方式..." />
              </n-form-item>
              <n-form-item label="调查笔记">
                <n-input v-model:value="form.notes" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" placeholder="额外说明、注意事项、可能的剧情影响..." />
              </n-form-item>
            </div>

            <div v-if="form.status === 'abandoned'" class="form-section">
              <div class="section-header">
                <span class="section-icon">🔄</span>
                <div class="section-title-group">
                  <div class="section-title">废弃处理</div>
                  <div class="section-hint">标记替代线索</div>
                </div>
              </div>
              <n-form-item label="被替代线索">
                <n-select
                  v-model:value="form.replaced_by_id"
                  clearable
                  filterable
                  :options="foreshadowingOptions"
                  placeholder="选择接替本线索的新线索"
                />
                <div class="field-hint">标记后，新线索会出现在原线索的"替代链"中，方便追踪剧情演变。</div>
              </n-form-item>
            </div>
          </n-form>

          <!-- 智能发现入口 -->
          <div class="ai-discovery-entry">
            <div class="ai-discovery-icon">✨</div>
            <div class="ai-discovery-text">
              <div class="ai-discovery-title">智能线索扫描</div>
              <div class="ai-discovery-desc">分析已写章节，自动识别未登记的线索、长期未回收的剧情债。</div>
            </div>
            <n-button size="small" type="primary" ghost disabled>即将上线</n-button>
          </div>

          <!-- 风险提示 -->
          <div class="risk-card" :class="riskCardClass">
            <div class="risk-header">
              <span class="risk-icon">{{ riskCardIcon }}</span>
              <span class="risk-title">{{ riskCardTitle }}</span>
            </div>
            <div class="check-list">
              <div v-for="item in riskHints" :key="item" class="check-row" :class="{ ready: !item.includes('风险') }">
                <span class="check-icon">{{ item.includes('风险') ? '!' : '✓' }}</span>
                <span class="check-text">{{ item }}</span>
              </div>
            </div>
          </div>

          <section v-if="editingId" class="history-card">
            <div class="history-header">
              <div>
                <div class="history-title">变更记录</div>
                <div class="history-subtitle">追踪手动修改与章节分析写回</div>
              </div>
              <n-button size="tiny" quaternary :loading="historyLoading" @click="loadHistory()">刷新</n-button>
            </div>
            <div v-if="historyLoading && historyItems.length === 0" class="history-empty">正在读取记录…</div>
            <div v-else-if="historyItems.length === 0" class="history-empty">暂无变更记录</div>
            <div v-else class="history-list">
              <article v-for="entry in historyItems" :key="entry.id" class="history-entry">
                <div class="history-entry-top">
                  <span class="history-operation" :class="entry.operation">{{ historyOperationLabel(entry.operation) }}</span>
                  <time>{{ formatHistoryTime(entry.created_at) }}</time>
                </div>
                <div class="history-source">
                  {{ entry.source_type === 'chapter_analysis' ? '章节分析审核' : '手动修改' }}
                  <span v-if="entry.chapter_no"> · 第{{ entry.chapter_no }}章{{ entry.chapter_title ? ` ${entry.chapter_title}` : '' }}</span>
                </div>
                <div class="history-fields">
                  <span v-for="field in entry.changed_fields" :key="field">{{ historyFieldLabel(field) }}</span>
                </div>
                <details v-if="entry.rationale || entry.evidence || Object.keys(entry.before_snapshot).length || Object.keys(entry.after_snapshot).length" class="history-details">
                  <summary>查看变化详情</summary>
                  <p v-if="entry.rationale"><strong>变更原因：</strong>{{ entry.rationale }}</p>
                  <p v-if="entry.evidence"><strong>章节依据：</strong>{{ entry.evidence }}</p>
                  <div v-if="entry.before_snapshot.status !== entry.after_snapshot.status" class="history-status-change">
                    {{ statusLabel(String(entry.before_snapshot.status ?? '')) || '无状态' }}
                    <span>→</span>
                    {{ statusLabel(String(entry.after_snapshot.status ?? '')) || (entry.operation === 'delete' ? '已删除' : '无状态') }}
                  </div>
                  <div v-if="entry.after_snapshot.payoff_chapter || entry.after_snapshot.resolved_chapter" class="history-chapters">
                    <span v-if="entry.after_snapshot.payoff_chapter">计划回收：第{{ entry.after_snapshot.payoff_chapter }}章</span>
                    <span v-if="entry.after_snapshot.resolved_chapter">实际回收：第{{ entry.after_snapshot.resolved_chapter }}章</span>
                  </div>
                </details>
              </article>
            </div>
          </section>
        </n-scrollbar>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { createResource, deleteResource, listForeshadowingHistory, listResource, updateResource } from '@/api/resources'
import { useDictStore } from '@/stores/dict'
import { useForeshadowingStore } from '@/stores/foreshadowing'
import { useProjectStore } from '@/stores/project'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import { useDirtySnapshot } from '@/composables/useDirtySnapshot'
import { notify } from '@/utils/notify'
import type { CharacterItem, ChapterItem, ForeshadowingHistory, ForeshadowingItem, OrganizationItem, OutlineItem } from '@/types/domain'

const projectStore = useProjectStore()
const dictStore = useDictStore()
const foreshadowStore = useForeshadowingStore()
// 伏笔数据从共享 store 读取，跨页面自动同步
const foreshadowings = computed(() => foreshadowStore.foreshadowings)
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
const historyItems = ref<ForeshadowingHistory[]>([])
const historyLoading = ref(false)
const draggingItemId = ref<number | null>(null)
const dragOverStatus = ref<string | null>(null)
// 记录每个伏笔的状态移动历史栈（用于多级回撤），key: 伏笔id, value: 状态历史数组（栈顶为最近一次）
const statusHistoryMap = new Map<number, string[]>()
const form = reactive({
  keyword: '',
  description: '',
  status: 'pending',
  importance: 'medium',
  planted_chapter: 1 as number | null,
  payoff_chapter: null as number | null,
  resolved_chapter: null as number | null,
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
const importanceOptions = computed(() => dictStore.options('importance'))

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
  return '状态正常'
})

const riskTextClass = computed(() => {
  const risk = riskOf(form as ForeshadowingItem)
  if (risk === 'high') return 'risk-high'
  if (risk === 'medium') return 'risk-medium'
  return 'risk-low'
})

const riskCardClass = computed(() => {
  const risk = riskOf(form as ForeshadowingItem)
  if (risk === 'high') return 'card-high'
  if (risk === 'medium') return 'card-medium'
  return 'card-safe'
})

const riskCardIcon = computed(() => {
  const risk = riskOf(form as ForeshadowingItem)
  if (risk === 'high') return '🚨'
  if (risk === 'medium') return '⚡'
  return '✅'
})

const riskCardTitle = computed(() => {
  const risk = riskOf(form as ForeshadowingItem)
  if (risk === 'high') return '高风险预警'
  if (risk === 'medium') return '需要关注'
  return '线索健康'
})

const riskHints = computed(() => {
  const hints = []
  if (!form.payoff_chapter && ['planted', 'developing', 'payoff_pending'].includes(form.status)) hints.push('风险：未设置回收章节')
  if (form.payoff_chapter && latestChapterNo.value > form.payoff_chapter && !['resolved', 'abandoned'].includes(form.status)) {
    hints.push(`风险：计划在第${form.payoff_chapter}章回收，当前已到第${latestChapterNo.value}章`)
  }
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

function handleCardDragStart(event: DragEvent, item: ForeshadowingItem) {
  // 步骤 1：记录拖动卡片 ID；步骤 2：通过原生拖放数据传递 ID，兼容浏览器默认拖放机制。
  draggingItemId.value = item.id
  dragOverStatus.value = null
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(item.id))
  }
}

function handleColumnDragOver(event: DragEvent, status: string) {
  if (draggingItemId.value == null) return
  event.preventDefault()
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'
  dragOverStatus.value = status
}

function handleColumnDragLeave(event: DragEvent, status: string) {
  // 指针在列内卡片间移动时不清除高亮，只在离开整列后清除。
  const column = event.currentTarget as HTMLElement
  const nextTarget = event.relatedTarget
  if (nextTarget instanceof Node && column.contains(nextTarget)) return
  if (dragOverStatus.value === status) dragOverStatus.value = null
}

async function handleColumnDrop(event: DragEvent, status: string) {
  // 步骤 1：读取拖动 ID 并立即复位视觉状态；步骤 2：目标状态不同时复用统一迁移逻辑。
  event.preventDefault()
  const draggedId = Number(event.dataTransfer?.getData('text/plain')) || draggingItemId.value
  draggingItemId.value = null
  dragOverStatus.value = null
  if (draggedId == null) return
  const item = foreshadowings.value.find((candidate) => candidate.id === draggedId)
  if (!item || item.status === status) return
  await moveStatus(item, status)
}

function handleCardDragEnd() {
  draggingItemId.value = null
  dragOverStatus.value = null
}

function includesChapter(item: ForeshadowingItem, chapterNo: number) {
  const start = item.effective_from ?? item.planted_chapter ?? 1
  // 计划回收章节只代表预期节点；真正失效范围由 expires_at 控制。
  const end = item.expires_at ?? Number.MAX_SAFE_INTEGER
  return chapterNo >= start && chapterNo <= end
}

function riskOf(item: Partial<ForeshadowingItem>) {
  const unresolved = !['resolved', 'abandoned'].includes(item.status ?? '')
  if (unresolved && item.expires_at && latestChapterNo.value > item.expires_at) return 'high'
  if (unresolved && item.payoff_chapter && latestChapterNo.value > item.payoff_chapter) return 'high'
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

function prevStatuses(status: string, itemId?: number) {
  // 从历史栈中取上一个状态（支持多级回撤）
  if (itemId != null) {
    const history = statusHistoryMap.get(itemId)
    if (history && history.length > 0) {
      const prevStatus = history[history.length - 1]
      const prevCol = statusColumns.find((c) => c.value === prevStatus)
      if (prevCol) return [prevCol]
    }
  }
  // 没有历史记录时，按顺序返回上一个状态
  const order = statusColumns.map((item) => item.value)
  const index = order.indexOf(status)
  if (index <= 0) return []
  return [statusColumns[index - 1]]
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
    resolved_chapter: item?.resolved_chapter ?? null,
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
  return dictStore.label('importance', value)
}

async function loadHistory(itemId = editingId.value) {
  // 步骤 1：创建态不请求记录；步骤 2：仅把仍对应当前卡片的结果写回页面。
  const projectId = projectStore.currentProject?.id
  if (!projectId || !itemId) {
    historyItems.value = []
    historyLoading.value = false
    return
  }
  historyLoading.value = true
  try {
    const records = await listForeshadowingHistory(projectId, itemId)
    if (editingId.value === itemId) historyItems.value = records
  } finally {
    if (editingId.value === itemId) historyLoading.value = false
  }
}

function historyOperationLabel(operation: string) {
  const labels: Record<string, string> = {
    create: '创建',
    update: '资料更新',
    status_transition: '状态变化',
    delete: '删除',
  }
  return labels[operation] ?? '资料变化'
}

function statusLabel(value: string) {
  return statusColumns.find((item) => item.value === value)?.label ?? ''
}

function historyFieldLabel(field: string) {
  const labels: Record<string, string> = {
    keyword: '关键词', description: '描述', status: '状态', importance: '重要性',
    planted_chapter: '埋设章节', payoff_chapter: '计划回收', resolved_chapter: '实际回收',
    effective_from: '生效章节', expires_at: '失效章节', notes: '调查笔记',
    related_character_ids: '关联角色', related_organization_ids: '关联组织',
    related_outline_ids: '关联大纲', replaced_by_id: '替代线索',
  }
  return labels[field] ?? field
}

function formatHistoryTime(value: string | null) {
  if (!value) return '时间未知'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

async function startCreate() {
  if (!(await confirmIfDirty())) return
  editingId.value = null
  isCreating.value = true
  historyItems.value = []
  fillForm()
  await nextTick()
  markClean()
}

async function selectForeshadowing(item: ForeshadowingItem) {
  if (editingId.value === item.id) return
  if (!(await confirmIfDirty())) return
  editingId.value = item.id
  isCreating.value = false
  historyItems.value = []
  fillForm(item)
  await nextTick()
  markClean()
  await loadHistory(item.id)
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
  // 步骤 1：先计算目标状态与章节事实，回收时记录当前最新章节。
  // 判断是否是回撤操作（目标状态在历史栈顶）
  const history = statusHistoryMap.get(item.id) || []
  const isUndo = history.length > 0 && history[history.length - 1] === status
  const changes: Partial<ForeshadowingItem> = { status: status as ForeshadowingItem['status'] }
  if (status === 'planted' && !item.planted_chapter && latestChapterNo.value > 0) {
    changes.planted_chapter = latestChapterNo.value
  }
  if (status === 'resolved' && latestChapterNo.value > 0) {
    changes.resolved_chapter = latestChapterNo.value
  }
  if (item.status === 'resolved' && status !== 'resolved') {
    changes.resolved_chapter = null
  }

  // 步骤 2：先提交后更新撤销栈，避免接口失败却留下虚假的本地历史。
  const updated = await updateResource<ForeshadowingItem>('foreshadowings', item.id, changes)
  if (isUndo) {
    history.pop()
    if (history.length > 0) statusHistoryMap.set(item.id, history)
    else statusHistoryMap.delete(item.id)
  } else {
    statusHistoryMap.set(item.id, [...history, item.status])
  }
  const label = statusColumns.find((column) => column.value === status)?.label
  notify.success(isUndo ? `已回撤到「${label}」` : `已移动到「${label}」`)
  // 同步更新共享 store
  foreshadowStore.update(updated)
  const fresh = foreshadowings.value.find((f) => f.id === updated.id)
  if (fresh && editingId.value === updated.id) {
    fillForm(fresh)
    await nextTick()
    markClean()
  }
  await loadHistory(updated.id)
}

async function ensureProject() {
  if (!projectStore.currentProject) await projectStore.loadDefaultProject()
  return projectStore.currentProject?.id
}

async function load() {
  const projectId = projectStore.currentProject!.id
  loading.value = true
  try {
    await dictStore.load('importance')
    const [, chapterList, characterList, organizationList, outlineList] = await Promise.all([
      foreshadowStore.load(projectId),
      listResource<ChapterItem>(projectId, 'chapters'),
      listResource<CharacterItem>(projectId, 'characters'),
      listResource<OrganizationItem>(projectId, 'organizations'),
      listResource<OutlineItem>(projectId, 'outlines')
    ])
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
      await loadHistory(foreshadowings.value[0].id)
    }
  } finally {
    loading.value = false
  }
}

async function save() {
  const projectId = await ensureProject()
  if (!projectId) return

  // 步骤 1：手动将线索标记为已回收时，若未填实际章节则记录当前最新章节。
  if (form.status === 'resolved' && !form.resolved_chapter && latestChapterNo.value > 0) {
    form.resolved_chapter = latestChapterNo.value
  }

  if (editingId.value) {
    const updated = await updateResource<ForeshadowingItem>('foreshadowings', editingId.value, { ...form })
    notify.success('伏笔已更新')
    // 同步更新共享 store，其他页面会自动响应
    foreshadowStore.update(updated)
    const fresh = foreshadowings.value.find((item) => item.id === updated.id)
    if (fresh) {
      fillForm(fresh)
      await nextTick()
      markClean()
      await loadHistory(updated.id)
    }
  } else {
    const created = await createResource<ForeshadowingItem>('foreshadowings', { project_id: projectId, ...form })
    notify.success('伏笔已添加')
    // 同步更新共享 store
    foreshadowStore.add(created)
    const fresh = foreshadowings.value.find((item) => item.id === created.id)
    if (fresh) {
      editingId.value = fresh.id
      isCreating.value = false
      fillForm(fresh)
      await nextTick()
      markClean()
      await loadHistory(created.id)
    }
  }
}

async function remove() {
  if (!editingId.value) return
  const currentIndex = foreshadowings.value.findIndex((item) => item.id === editingId.value)
  await deleteResource('foreshadowings', editingId.value)
  notify.success('伏笔已删除')
  // 同步更新共享 store
  foreshadowStore.remove(editingId.value)
  const nextItem = foreshadowings.value[currentIndex + 1] || foreshadowings.value[currentIndex - 1]
  if (nextItem) {
    editingId.value = nextItem.id
    fillForm(nextItem)
    await loadHistory(nextItem.id)
  } else {
    editingId.value = null
    isCreating.value = false
    historyItems.value = []
    fillForm()
  }
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
  gap: 14px;
  padding-bottom: 14px;
  background: linear-gradient(180deg, var(--n-color-body, #141619) 0%, var(--n-color-body, #141619) 100%);
}

/* ===== 页头 ===== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 4px 2px 0;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.3px;
  background: linear-gradient(135deg, var(--n-text-color-1, #f0f0f0) 0%, var(--n-text-color-2, #9ca3af) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.title-icon {
  font-size: 20px;
  margin-right: 6px;
  -webkit-text-fill-color: initial;
}

.page-subtitle {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  margin: 0;
  letter-spacing: 0.2px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-stats {
  display: flex;
  align-items: stretch;
  gap: 1px;
  background: var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  padding: 1px;
  overflow: hidden;
}

.stat {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--n-color-card, #1a1d21);
  transition: all 0.2s ease;
}

.stat:hover {
  background: var(--n-color-hover, #23272f);
}

.stat-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.stat-num {
  font-size: 18px;
  font-weight: 700;
  color: var(--n-text-color-1, #f0f0f0);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.stat-total .stat-num {
  color: var(--n-color-primary, #3b82f6);
}

.stat-danger .stat-num {
  color: #ef4444;
}

.stat-success .stat-num {
  color: #10b981;
}

.stat-label {
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  font-weight: 500;
}

.add-btn {
  font-weight: 600;
}

/* ===== 筛选栏 ===== */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 12px;
  flex-shrink: 0;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 14px;
  opacity: 0.7;
}

.filter-spacer {
  flex: 1;
}

.refresh-btn {
  opacity: 0.7;
  transition: all 0.2s ease;
}

.refresh-btn:hover {
  opacity: 1;
}

/* ===== 工作区 ===== */
.workbench {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 380px);
  gap: 14px;
  min-height: 0;
}

/* ===== 看板面板 ===== */
.kanban-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 12px;
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
  padding: 14px 18px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.04) 0%, transparent 100%);
}

.panel-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-title-icon {
  font-size: 16px;
}

.panel-head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.panel-sub {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  font-weight: 500;
}

.kanban-container {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 14px;
  min-height: 0;
}

.kanban-column {
  display: flex;
  flex-direction: column;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  min-height: 0;
  overflow: hidden;
  transition: border-color 0.2s ease;
}

.kanban-column.drag-over {
  border-color: var(--n-color-primary, #3b82f6);
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.09), var(--n-color-1, #1e2228) 38%);
  box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.22);
}

.kanban-column.pending { border-top: 3px solid #6b7280; }
.kanban-column.planted { border-top: 3px solid #3b82f6; }
.kanban-column.developing { border-top: 3px solid #8b5cf6; }
.kanban-column.payoff_pending { border-top: 3px solid #f59e0b; }
.kanban-column.resolved { border-top: 3px solid #10b981; }
.kanban-column.abandoned { border-top: 3px solid #64748b; }

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  font-size: 13px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.015);
}

.column-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.column-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--n-text-color-3, #6b7280);
}

.pending .column-dot { background: #6b7280; }
.planted .column-dot { background: #3b82f6; box-shadow: 0 0 8px rgba(59, 130, 246, 0.5); }
.developing .column-dot { background: #8b5cf6; box-shadow: 0 0 8px rgba(139, 92, 246, 0.5); }
.payoff_pending .column-dot { background: #f59e0b; box-shadow: 0 0 8px rgba(245, 158, 11, 0.5); }
.resolved .column-dot { background: #10b981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.5); }
.abandoned .column-dot { background: #64748b; }

.column-count {
  font-size: 11px;
  font-weight: 600;
  color: var(--n-text-color-2, #9ca3af);
  background: var(--n-color-2, #23272f);
  padding: 2px 8px;
  border-radius: 10px;
  min-width: 20px;
  text-align: center;
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

.column-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 30px 10px;
  color: var(--n-text-color-3, #6b7280);
  font-size: 12px;
  opacity: 0.6;
}

.empty-emoji {
  font-size: 24px;
}

/* ===== 卡片 ===== */
.kanban-card {
  position: relative;
  display: flex;
  border-radius: 10px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.kanban-card[draggable="true"] { cursor: grab; }
.kanban-card[draggable="true"]:active { cursor: grabbing; }
.kanban-card.dragging { opacity: 0.42; transform: scale(0.985); }

.kanban-card:hover {
  border-color: var(--n-color-primary-3, #3b82f6);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.kanban-card.active {
  border-color: var(--n-color-primary, #3b82f6);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15), 0 8px 24px rgba(0, 0, 0, 0.3);
}

.kanban-card.warning {
  border-color: rgba(245, 158, 11, 0.4);
}

.kanban-card.danger {
  border-color: rgba(239, 68, 68, 0.5);
  animation: danger-pulse 2s ease-in-out infinite;
}

@keyframes danger-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
  50% { box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15); }
}

.card-accent {
  width: 3px;
  flex-shrink: 0;
  background: var(--n-color-primary, #3b82f6);
  transition: all 0.2s ease;
}

.warning .card-accent { background: #f59e0b; }
.danger .card-accent { background: #ef4444; }
.resolved .card-accent { background: #10b981; }
.abandoned .card-accent { background: #64748b; }

.card-content {
  flex: 1;
  padding: 10px 12px;
  min-width: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--n-text-color-1, #f0f0f0);
}

.importance-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 4px;
  flex-shrink: 0;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.importance-badge.high {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.importance-badge.medium {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.importance-badge.low {
  background: rgba(107, 114, 128, 0.15);
  color: #9ca3af;
  border: 1px solid rgba(107, 114, 128, 0.3);
}

.card-chapter {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 11px;
}

.chip {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  font-size: 10px;
}

.chip-planted {
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
}

.chip-payoff {
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
}

.chip-resolved {
  background: rgba(139, 92, 246, 0.12);
  color: #a78bfa;
}

.chip-arrow {
  color: var(--n-text-color-3, #6b7280);
  font-size: 10px;
}

.card-desc {
  font-size: 12px;
  color: var(--n-text-color-2, #9ca3af);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 10px;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
}

.card-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.risk-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
}

.risk-tag.high {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.risk-tag.medium {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.card-actions {
  display: flex;
  gap: 4px;
}

/* ===== 详情面板 ===== */
.detail-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
  background: linear-gradient(180deg, rgba(139, 92, 246, 0.04) 0%, transparent 100%);
}

.detail-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-icon {
  font-size: 18px;
}

.detail-title h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
  letter-spacing: 0.2px;
}

.detail-sub {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
  width: fit-content;
}

.detail-sub.risk-high {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.detail-sub.risk-medium {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.detail-sub.risk-low {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}

.detail-actions {
  display: flex;
  gap: 6px;
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

/* ===== 表单 ===== */
.form-scroll {
  flex: 1;
  min-height: 0;
  padding: 0 16px 16px;
}

.detail-form {
  padding-top: 16px;
}

.form-section {
  margin-bottom: 22px;
  padding-bottom: 22px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
}

.form-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.section-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 14px;
}

.section-icon {
  font-size: 16px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 6px;
  flex-shrink: 0;
}

.section-title-group {
  flex: 1;
  min-width: 0;
}

.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--n-text-color-1, #f0f0f0);
  letter-spacing: 0.2px;
}

.section-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 2px;
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

/* ===== 空状态 ===== */
.detail-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 20px;
}

.empty-icon-wrap {
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
  border-radius: 20px;
  margin-bottom: 4px;
}

.empty-icon {
  font-size: 36px;
}

.empty-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--n-text-color-1, #f0f0f0);
}

.empty-sub {
  margin: 0;
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  opacity: 0.7;
}

/* ===== AI 发现入口 ===== */
.ai-discovery-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  margin: 18px 0;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.08));
  border: 1px solid rgba(139, 92, 246, 0.25);
  border-radius: 10px;
  position: relative;
  overflow: hidden;
}

.ai-discovery-entry::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 100px;
  height: 100px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.15) 0%, transparent 70%);
  pointer-events: none;
}

.ai-discovery-icon { font-size: 24px; flex-shrink: 0; }
.ai-discovery-text { flex: 1; min-width: 0; position: relative; z-index: 1; }
.ai-discovery-title {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 2px;
}
.ai-discovery-desc {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  line-height: 1.5;
}

/* ===== 风险卡片 ===== */
.risk-card {
  padding: 14px;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  transition: all 0.3s ease;
}

.risk-card.card-high {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.02));
  border-color: rgba(239, 68, 68, 0.3);
}

.risk-card.card-medium {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(245, 158, 11, 0.02));
  border-color: rgba(245, 158, 11, 0.3);
}

.risk-card.card-safe {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.06), rgba(16, 185, 129, 0.01));
  border-color: rgba(16, 185, 129, 0.2);
}

.risk-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 700;
}

.risk-icon {
  font-size: 16px;
}

.check-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.check-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: var(--n-text-color-2, #9ca3af);
  line-height: 1.5;
}

.check-icon {
  color: #f59e0b;
  font-weight: 700;
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  background: rgba(245, 158, 11, 0.15);
  border-radius: 50%;
}

.check-row.ready {
  color: var(--n-text-color-2, #9ca3af);
}

.check-row.ready .check-icon {
  color: #10b981;
  background: rgba(16, 185, 129, 0.15);
}

.history-card {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  background: var(--n-color-1, #1e2228);
}

.history-header,
.history-entry-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.history-title {
  color: var(--n-text-color-1, #f0f0f0);
  font-size: 13px;
  font-weight: 700;
}

.history-subtitle,
.history-source,
.history-entry time,
.history-empty {
  color: var(--n-text-color-3, #6b7280);
  font-size: 11px;
}

.history-subtitle { margin-top: 3px; }
.history-empty { padding: 18px 0 4px; text-align: center; }
.history-list { display: flex; flex-direction: column; margin-top: 10px; }

.history-entry {
  padding: 12px 0;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
}

.history-operation {
  padding: 3px 7px;
  border-radius: 5px;
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
  font-size: 11px;
}

.history-operation.status_transition { background: rgba(139, 92, 246, 0.14); color: #a78bfa; }
.history-operation.delete { background: rgba(239, 68, 68, 0.12); color: #f87171; }
.history-source { margin-top: 7px; line-height: 1.5; }
.history-fields,.history-chapters { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }

.history-fields span,
.history-chapters span {
  padding: 3px 6px;
  border-radius: 4px;
  background: rgba(148, 163, 184, 0.1);
  color: var(--n-text-color-2, #9ca3af);
  font-size: 10px;
}

.history-details { margin-top: 9px; color: var(--n-text-color-2, #9ca3af); font-size: 11px; }
.history-details summary { cursor: pointer; color: #60a5fa; }
.history-details p { margin: 7px 0 0; line-height: 1.5; white-space: pre-wrap; }
.history-status-change { display: flex; gap: 8px; margin-top: 8px; color: var(--n-text-color-1, #f0f0f0); }

@media (max-width: 1280px) {
  .workbench { grid-template-columns: minmax(0, 1fr) minmax(300px, 340px); }
  .kanban-container { gap: 9px; padding: 10px; }
  .column-header { padding: 10px; }
}

@media (max-width: 960px) {
  .foreshadowing-page { height: auto; min-height: calc(100vh - 60px); }
  .workbench { grid-template-columns: minmax(0, 1fr); flex: initial; overflow: visible; }
  .kanban-panel { min-height: 620px; }
  .detail-panel { height: min(82vh, 900px); min-height: 620px; }
  .kanban-container { grid-template-columns: repeat(2, minmax(220px, 1fr)); }
}

@media (max-width: 600px) {
  .page-header { align-items: flex-start; flex-direction: column; gap: 12px; }
  .header-right { width: 100%; justify-content: space-between; }
  .header-stats { flex: 1; min-width: 0; }
  .filter-bar { flex-wrap: wrap; }
  .filter-group { flex: 1 1 100%; }
  .filter-group :deep(.n-input) { width: 100% !important; }
  .kanban-container { grid-template-columns: minmax(0, 1fr); }
  .kanban-panel { min-height: 900px; }
  .form-grid-2 { grid-template-columns: minmax(0, 1fr); }
  .detail-panel { min-height: 680px; }
}
</style>
