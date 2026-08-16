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
          集中查看章节摘要、人物变化、世界观变化和时间线沉淀
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
          <h2>摘要索引</h2>
          <n-tag size="tiny" type="default">{{ filteredSummaries.length }} 条</n-tag>
        </div>
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索章节、摘要或时间线">
            <template #prefix>🔍</template>
          </n-input>
          <n-select v-model:value="chapterFilter" clearable :options="chapterOptions" placeholder="按章节筛选" />
        </div>
        <n-scrollbar class="list-scroll">
          <div v-if="loading" class="list-loading">
            <n-spin size="small" />
            <span>加载中...</span>
          </div>
          <div v-else-if="filteredSummaries.length === 0" class="list-empty">
            <div class="empty-icon">📑</div>
            <p>暂无可用记忆</p>
            <p class="empty-sub">生成章节后会自动提取摘要</p>
          </div>
          <template v-else>
            <div class="summary-list">
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
          </template>
        </n-scrollbar>
      </aside>

      <!-- 中间：记忆详情 -->
      <section class="detail-panel">
        <div class="detail-header">
          <div class="detail-title">
            <h2>
              {{ selectedSummary ? `第 ${selectedSummary.chapter_no} 章记忆` : '记忆详情' }}
            </h2>
            <span class="detail-sub">
              {{ selectedSummary ? `ID ${selectedSummary.id}` : '未选择' }}
            </span>
          </div>
        </div>

        <div v-if="selectedSummary" class="memory-content">
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
        </div>

        <div v-else class="detail-empty">
          <div class="empty-icon">📝</div>
          <p>从左侧选择一条章节摘要</p>
          <p class="empty-sub">查看沉淀后的长期记忆</p>
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
import { listResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import { notify } from '@/utils/notify'
import type { ChapterItem, ChapterSummary } from '@/types/domain'

const projectStore = useProjectStore()
const keyword = ref('')
const chapterFilter = ref<number | null>(null)
const summaries = ref<ChapterSummary[]>([])
const chapters = ref<ChapterItem[]>([])
const selectedSummary = ref<ChapterSummary | null>(null)
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

function shortText(value: string, max = 60) {
  return value?.length > max ? `${value.slice(0, max)}...` : value || '暂无摘要'
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

async function loadMemories() {
  const projectId = projectStore.currentProject!.id
  loading.value = true
  try {
    const [chapterList, summaryList] = await Promise.all([
      listResource<ChapterItem>(projectId, 'chapters'),
      getChapterSummaries(projectId, 50)
    ])
    chapters.value = chapterList
    summaries.value = summaryList
    if (!selectedSummary.value || !summaryList.some((item) => item.id === selectedSummary.value?.id)) {
      selectedSummary.value = summaryList[0] ?? null
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
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
