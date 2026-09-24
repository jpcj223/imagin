<template>
  <div class="page page-wide memory-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">🧠</span>
          长期记忆中心
        </h1>
        <p class="page-subtitle">
          查看章节摘要与审核通过的人物、关系、组织、伏笔和时间线记忆
        </p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ chapterCount }}</span>
            <span class="stat-label">章节</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ summaryCount }}</span>
            <span class="stat-label">摘要</span>
            <n-tooltip>
              <template #trigger>
                <span class="stat-hint">ⓘ</span>
              </template>
              AI 自动提取的章节关键信息
            </n-tooltip>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ coverageRate }}%</span>
            <span class="stat-label">覆盖率</span>
          </div>
        </div>
        <n-button @click="loadMemories">
          <template #icon>🔄</template>
          刷新记忆
        </n-button>
      </div>
    </div>

    <!-- 主体：三栏布局 -->
    <div class="workbench">
      <!-- 左侧：摘要索引 -->
      <aside class="list-panel">
        <div class="panel-head">
          <h2>{{ activeIndex === 'summaries' ? '摘要索引' : '长期记忆' }}</h2>
          <div class="index-actions">
            <n-tag size="tiny" type="default">{{ activeIndex === 'summaries' ? filteredSummaries.length : filteredMemoryItems.length }} 条</n-tag>
            <n-button size="tiny" secondary @click="switchIndex">
              {{ activeIndex === 'summaries' ? '查看记忆条目' : '查看章节摘要' }}
            </n-button>
          </div>
        </div>
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable :placeholder="activeIndex === 'summaries' ? '搜索章节、摘要或时间线' : '搜索记忆标题或内容'">
            <template #prefix>🔍</template>
          </n-input>
          <n-select v-if="activeIndex === 'summaries'" v-model:value="chapterFilter" clearable :options="chapterOptions" placeholder="按章节筛选" />
        </div>
        <n-scrollbar class="list-scroll">
          <div v-if="loading" class="list-loading">
            <n-spin size="small" />
            <span>加载中...</span>
          </div>
          <div v-else-if="activeIndex === 'summaries' && filteredSummaries.length === 0" class="list-empty">
            <div class="empty-icon">📑</div>
            <p>暂无可用记忆</p>
            <p class="empty-sub">生成章节后会自动提取摘要</p>
          </div>
          <div v-else-if="activeIndex === 'items' && filteredMemoryItems.length === 0" class="list-empty">
            <div class="empty-icon">🧠</div>
            <p>暂无长期记忆条目</p>
            <p class="empty-sub">章节分析提案审核通过后会沉淀到这里</p>
          </div>
          <template v-else>
            <div v-if="activeIndex === 'summaries'" class="summary-list">
              <div
                v-for="item in filteredSummaries"
                :key="item.id"
                class="summary-item"
                :class="{ active: selectedSummary?.id === item.id }"
                @click="selectSummary(item)"
              >
                <div class="item-header">
                  <span class="chapter-no">第 {{ item.chapter_no }} 章</span>
                  <span class="create-time">{{ formatDate(item.created_at) }}</span>
                </div>
                <div class="item-title">{{ item.title }}</div>
                <p class="summary-excerpt">{{ shortText(item.summary, 72) }}</p>
              </div>
            </div>
            <div v-else class="summary-list">
              <div
                v-for="item in filteredMemoryItems"
                :key="item.memory_id"
                class="summary-item"
                :class="{ active: selectedMemoryItem?.memory_id === item.memory_id }"
                @click="selectMemoryItem(item)"
              >
                <div class="item-header">
                  <span class="chapter-no">{{ memoryTypeLabel(item.memory_type) }}</span>
                  <span class="create-time">{{ formatDate(item.updated_at || item.created_at || '') }}</span>
                </div>
                <div class="item-title">{{ item.title }}</div>
                <p class="summary-excerpt">{{ shortText(item.content_summary || item.content, 72) }}</p>
              </div>
            </div>
          </template>
        </n-scrollbar>
      </aside>

      <!-- 中间：记忆详情 -->
      <section class="detail-panel">
        <div class="detail-header">
          <div class="detail-title">
            <h2>
              {{ activeIndex === 'summaries' && selectedSummary ? `第 ${selectedSummary.chapter_no} 章记忆` : activeIndex === 'items' && selectedMemoryItem ? '长期记忆详情' : '记忆详情' }}
            </h2>
            <span class="detail-sub">
              {{ activeIndex === 'summaries' && selectedSummary ? `ID ${selectedSummary.id}` : activeIndex === 'items' && selectedMemoryItem ? selectedMemoryItem.memory_id : '未选择' }}
            </span>
          </div>
        </div>

        <div v-if="activeIndex === 'summaries' && selectedSummary" class="memory-content">
          <div class="detail-hero">
            <h2>{{ selectedSummary.title }}</h2>
            <p class="chapter-meta">
              <span>第 {{ selectedSummary.chapter_no }} 章</span>
              <span class="dot">·</span>
              <span>{{ formatDate(selectedSummary.created_at) }}</span>
            </p>
            <div class="summary-content">
              <h3>章节摘要</h3>
              <p>{{ selectedSummary.summary || '暂无摘要' }}</p>
            </div>
          </div>

          <div class="memory-grid">
            <div v-for="card in detailCards" :key="card.label" class="memory-card">
              <div class="card-header">
                <span class="card-icon">{{ card.icon }}</span>
                <h3>{{ card.label }}</h3>
              </div>
              <div class="card-content">
                <p v-if="card.value">{{ card.value }}</p>
                <p v-else class="empty-content">暂无记录</p>
              </div>
            </div>
          </div>
          <p class="analysis-disclaimer">此处是章节分析提取结果；人物、关系、组织、伏笔等正式资料只会在章节工作台审核通过后更新。</p>
        </div>

        <div v-else-if="activeIndex === 'items' && selectedMemoryItem" class="memory-content">
          <div class="detail-hero memory-item-hero">
            <div class="memory-item-heading">
              <h2>{{ selectedMemoryItem.title }}</h2>
              <n-tag size="small" type="success">已沉淀</n-tag>
            </div>
            <p class="chapter-meta">
              <span>{{ memoryTypeLabel(selectedMemoryItem.memory_type) }}</span>
              <span class="dot">·</span>
              <span>重要性 {{ selectedMemoryItem.importance }}/100</span>
              <span class="dot">·</span>
              <span>{{ formatDate(selectedMemoryItem.updated_at || selectedMemoryItem.created_at || '') }}</span>
            </p>
            <div v-if="selectedMemoryItem.content_summary" class="memory-item-summary">
              <strong>摘要</strong>
              <p>{{ selectedMemoryItem.content_summary }}</p>
            </div>
            <div class="memory-item-content">
              <h3>记忆内容</h3>
              <p>{{ selectedMemoryItem.content || '暂无内容' }}</p>
            </div>
          </div>

          <div class="memory-grid">
            <div class="memory-card">
              <div class="card-header"><span class="card-icon">🔗</span><h3>来源追踪</h3></div>
              <div class="card-content">
                <p>来源类型：{{ sourceTypeLabel(selectedMemoryItem.source_type) }}</p>
                <p>来源引用：{{ selectedMemoryItem.source_ref || '无' }}</p>
                <p>记录 ID：{{ selectedMemoryItem.memory_id }}</p>
              </div>
            </div>
            <div class="memory-card">
              <div class="card-header"><span class="card-icon">🏷️</span><h3>记忆分类</h3></div>
              <div class="card-content">
                <p>分类：{{ memoryTypeLabel(selectedMemoryItem.memory_type) }}</p>
                <p>创建时间：{{ formatDate(selectedMemoryItem.created_at || '') }}</p>
                <p>更新时间：{{ formatDate(selectedMemoryItem.updated_at || '') }}</p>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="detail-empty">
          <div class="empty-icon">📝</div>
          <p>从左侧选择一条{{ activeIndex === 'summaries' ? '章节摘要' : '长期记忆' }}</p>
          <p class="empty-sub">查看内容及来源记录</p>
        </div>
      </section>

      <!-- 右侧：检索策略 -->
      <aside class="side-panel">
        <div class="insight-card primary-card">
          <div class="card-header">
            <span class="card-icon">🔍</span>
            <span class="card-title">检索策略</span>
          </div>
          <div class="strategy-list">
            <div class="strategy-item ready">
              <strong>最近摘要读取</strong>
              <p>章节生成会优先读取最近章节摘要，保障剧情连续性。</p>
            </div>
            <div class="strategy-item ready">
              <strong>关键词过滤</strong>
              <p>当前用 SQLite 普通查询结果做前端筛选，足够支撑轻量创作。</p>
            </div>
            <div class="strategy-item">
              <strong>未来向量检索边界</strong>
              <p>后续只需要替换摘要检索接口，不影响章节生成页面和资料页。</p>
            </div>
          </div>
        </div>

        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">📊</span>
            <span class="card-title">资料统计</span>
          </div>
          <div class="stat-grid">
            <div class="stat-cell">
              <span>章节草稿</span>
              <strong>{{ chapterCount }}</strong>
            </div>
            <div class="stat-cell">
              <span>摘要记忆</span>
              <strong>{{ summaryCount }}</strong>
            </div>
            <div class="stat-cell">
              <span>已分析比例</span>
              <strong>{{ coverageRate }}%</strong>
            </div>
            <div class="stat-cell">
              <span>长期条目</span>
              <strong>{{ memoryItems.length }}</strong>
            </div>
          </div>
        </div>

        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">💡</span>
            <span class="card-title">AI 摘要规则</span>
          </div>
          <div class="rule-list">
            <div class="rule-item">
              <span class="rule-icon">✓</span>
              <span class="rule-text">自动提取主要情节转折点</span>
            </div>
            <div class="rule-item">
              <span class="rule-icon">✓</span>
              <span class="rule-text">记录人物关系变化</span>
            </div>
            <div class="rule-item">
              <span class="rule-icon">✓</span>
              <span class="rule-text">标记新出现的伏笔</span>
            </div>
            <div class="rule-item">
              <span class="rule-icon">✓</span>
              <span class="rule-text">提取关键对话和决策</span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { getChapterSummaries } from '@/api/agents'
import { getLongTermMemoryItems, type LongTermMemoryItem } from '@/api/agentsV3'
import { listResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import { notify } from '@/utils/notify'
import type { ChapterItem, ChapterSummary } from '@/types/domain'

const projectStore = useProjectStore()
const activeIndex = ref<'summaries' | 'items'>('summaries')
const keyword = ref('')
const chapterFilter = ref<number | null>(null)
const summaries = ref<ChapterSummary[]>([])
const memoryItems = ref<LongTermMemoryItem[]>([])
const chapters = ref<ChapterItem[]>([])
const selectedSummary = ref<ChapterSummary | null>(null)
const selectedMemoryItem = ref<LongTermMemoryItem | null>(null)
const loading = ref(false)

const chapterOptions = computed(() =>
  chapters.value.map((item) => ({
    label: `第 ${item.chapter_no} 章 · ${item.title}`,
    value: item.chapter_no
  }))
)

const chapterCount = computed(() => chapters.value.length)
const summaryCount = computed(() => summaries.value.length)
const coverageRate = computed(() => {
  if (chapters.value.length === 0) return 0
  return Math.round((summaries.value.length / chapters.value.length) * 100)
})

const filteredSummaries = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return summaries.value.filter((item) => {
    const matchesChapter = chapterFilter.value ? item.chapter_no === chapterFilter.value : true
    const haystack = [item.title, item.summary, item.character_changes, item.world_changes, item.new_foreshadowings, item.timeline_events]
      .join(' ')
      .toLowerCase()
    return matchesChapter && (!text || haystack.includes(text))
  })
})

const filteredMemoryItems = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return memoryItems.value.filter((item) => {
    const haystack = [item.title, item.content, item.content_summary, item.memory_type, item.source_ref]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    return !text || haystack.includes(text)
  })
})

const detailCards = computed(() => {
  const item = selectedSummary.value
  if (!item) return []
  return [
    { label: '人物变化', value: item.character_changes, icon: '👤' },
    { label: '世界观变化', value: item.world_changes, icon: '🌍' },
    { label: '新增伏笔', value: item.new_foreshadowings, icon: '🎭' },
    { label: '时间线事件', value: item.timeline_events, icon: '⏱️' }
  ]
})

function shortText(value: string | null | undefined, max = 60) {
  if (!value) return '暂无摘要'
  return value.length > max ? `${value.slice(0, max)}...` : value
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleDateString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

function selectSummary(item: ChapterSummary) {
  selectedSummary.value = item
}

function selectMemoryItem(item: LongTermMemoryItem) {
  selectedMemoryItem.value = item
}

function switchIndex() {
  // 步骤 1：切换左侧索引类型并清空不适用的章节筛选。
  activeIndex.value = activeIndex.value === 'summaries' ? 'items' : 'summaries'
  keyword.value = ''
  chapterFilter.value = null
  // 步骤 2：优先保留当前有效选择，否则选择新索引中的第一条。
  if (activeIndex.value === 'items' && !memoryItems.value.some((item) => item.memory_id === selectedMemoryItem.value?.memory_id)) {
    selectedMemoryItem.value = memoryItems.value[0] ?? null
  }
  if (activeIndex.value === 'summaries' && !summaries.value.some((item) => item.id === selectedSummary.value?.id)) {
    selectedSummary.value = summaries.value[0] ?? null
  }
}

function memoryTypeLabel(value: string | null | undefined) {
  const labels: Record<string, string> = {
    character: '人物记忆',
    relationship: '关系记忆',
    organization: '组织记忆',
    foreshadowing: '伏笔记忆',
    world_setting: '世界观记忆',
    timeline: '时间线事件',
    timeline_event: '时间线事件',
    chapter: '章节记忆',
  }
  const key = value || ''
  return labels[key] || key || '通用记忆'
}

function sourceTypeLabel(value: string | null | undefined) {
  const labels: Record<string, string> = {
    chapter_analysis: '章节分析审核',
    auto_generated: '自动生成',
    extracted: '内容提取',
    manual: '手动记录',
  }
  const key = value || ''
  return labels[key] || key || '未知来源'
}

async function loadMemories() {
  const projectId = projectStore.currentProject!.id
  loading.value = true
  try {
    const [chapterList, summaryList, memoryItemList] = await Promise.all([
      listResource<ChapterItem>(projectId, 'chapters'),
      getChapterSummaries(projectId, 50),
      getLongTermMemoryItems(projectId, 100),
    ])
    chapters.value = chapterList
    summaries.value = summaryList
    memoryItems.value = memoryItemList
    if (!selectedSummary.value || !summaryList.some((item) => item.id === selectedSummary.value?.id)) {
      selectedSummary.value = summaryList[0] ?? null
    }
    if (!selectedMemoryItem.value || !memoryItemList.some((item) => item.memory_id === selectedMemoryItem.value?.memory_id)) {
      selectedMemoryItem.value = memoryItemList[0] ?? null
    }
    notify.success('长期记忆已刷新')
  } finally {
    loading.value = false
  }
}

useProjectDataLoader(loadMemories)
</script>

<style scoped>
.memory-page {
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
  position: relative;
}

.stat-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--n-color-primary, #3b82f6);
  line-height: 1.2;
}

.stat-label {
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 2px;
  display: flex;
  align-items: center;
  gap: 3px;
}

.stat-hint {
  font-size: 10px;
  cursor: help;
  opacity: 0.6;
}

.stat-divider {
  width: 1px;
  height: 24px;
  background: var(--n-border-color, #2a2f3a);
}

/* ===== 工作区 ===== */
.workbench {
  flex: 1;
  display: grid;
  grid-template-columns: 320px minmax(480px, 1fr) 280px;
  gap: 12px;
  min-height: 0;
}

/* ===== 通用面板 ===== */
.list-panel,
.detail-panel,
.side-panel {
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

.index-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-tools {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.list-scroll {
  flex: 1;
  min-height: 0;
}

.list-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 20px;
  color: var(--n-text-color-3, #6b7280);
  font-size: 13px;
}

.list-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 60px 20px;
  color: var(--n-text-color-3, #6b7280);
  text-align: center;
}

.list-empty .empty-icon {
  font-size: 36px;
}

.list-empty p {
  margin: 0;
  font-size: 13px;
}

.list-empty .empty-sub {
  font-size: 12px;
  opacity: 0.7;
}

.summary-list {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.summary-item {
  padding: 10px 12px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  background: var(--n-color-1, #1e2228);
  cursor: pointer;
  transition: all 0.15s ease;
}

.summary-item:hover {
  border-color: var(--n-color-primary-3, #3b82f6);
  background: var(--n-color-hover, #23272f);
}

.summary-item.active {
  border-color: var(--n-color-primary, #3b82f6);
  background: rgba(59, 130, 246, 0.08);
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.chapter-no {
  font-size: 12px;
  font-weight: 600;
  color: var(--n-color-primary, #3b82f6);
}

.create-time {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
}

.item-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.summary-excerpt {
  margin: 0;
  color: var(--n-text-color-2, #9ca3af);
  font-size: 12px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ===== 详情面板 ===== */
.detail-header {
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
}

.detail-sub {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
}

.memory-content {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-hero {
  padding: 18px;
  border: 1px solid rgba(79, 140, 255, 0.2);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(79, 140, 255, 0.12), rgba(99, 226, 183, 0.06));
}

.detail-hero h2 {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 700;
}

.memory-item-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.memory-item-heading h2 {
  min-width: 0;
  overflow-wrap: anywhere;
}

.memory-item-summary,
.memory-item-content {
  margin-top: 14px;
}

.memory-item-summary strong,
.memory-item-content h3 {
  display: block;
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
}

.memory-item-summary p,
.memory-item-content p {
  margin: 0;
  color: var(--n-text-color-2, #d1d5db);
  line-height: 1.8;
  font-size: 13px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.chapter-meta {
  margin: 0 0 14px 0;
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  display: flex;
  align-items: center;
  gap: 6px;
}

.chapter-meta .dot {
  opacity: 0.5;
}

.summary-content h3 {
  margin: 0 0 8px 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
}

.summary-content p {
  margin: 0;
  color: var(--n-text-color-2, #d1d5db);
  line-height: 1.8;
  font-size: 13px;
}

.memory-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.analysis-disclaimer {
  margin: 0;
  color: var(--n-text-color-3, #6b7280);
  font-size: 11px;
  line-height: 1.6;
}

.memory-card {
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  padding: 14px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.card-icon {
  font-size: 16px;
}

.memory-card h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
}

.card-content {
  font-size: 12px;
  line-height: 1.7;
  color: var(--n-text-color-2, #9ca3af);
}

.card-content p {
  margin: 0;
}

.empty-content {
  color: var(--n-text-color-3, #6b7280);
  font-style: italic;
  opacity: 0.6;
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
  opacity: 0.7;
}

/* ===== 右侧面板 ===== */
.side-panel {
  padding: 12px;
  gap: 12px;
  overflow-y: auto;
}

.insight-card {
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  padding: 14px;
}

.insight-card.primary-card {
  border-color: rgba(79, 140, 255, 0.25);
  background: linear-gradient(135deg, rgba(79, 140, 255, 0.08), rgba(99, 226, 183, 0.04));
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.card-icon {
  font-size: 16px;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
}

.strategy-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.strategy-item {
  padding: 10px 12px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 6px;
  background: var(--n-color-card, #1a1d21);
}

.strategy-item.ready {
  border-color: rgba(16, 185, 129, 0.3);
}

.strategy-item strong {
  font-size: 12px;
  color: var(--n-text-color-1, #e5e7eb);
}

.strategy-item p {
  margin: 6px 0 0;
  color: var(--n-text-color-3, #9ca3af);
  font-size: 11px;
  line-height: 1.6;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.stat-cell {
  padding: 10px 8px;
  text-align: center;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 6px;
}

.stat-cell span {
  display: block;
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  margin-bottom: 4px;
}

.stat-cell strong {
  font-size: 18px;
  font-weight: 700;
  color: var(--n-text-color-1, #f8fafc);
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rule-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--n-text-color-2, #9ca3af);
}

.rule-icon {
  color: #10b981;
  font-size: 12px;
  flex-shrink: 0;
}
</style>
