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
            <span class="stat-num">{{ memoryItemTotal }}</span>
            <span class="stat-label">长期条目</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ coverageRate }}%</span>
            <span class="stat-label">覆盖率</span>
          </div>
        </div>
        <n-button secondary :disabled="batchRunning || loading" @click="startExistingBackfill">
          <template #icon>🧠</template>
          补充已有章节记忆
        </n-button>
        <n-button type="primary" :disabled="batchRunning || loading" @click="openNovelPicker">
          <template #icon>📚</template>
          读取小说
        </n-button>
        <n-button secondary :disabled="batchRunning || loading" @click="() => loadMemories()">
          <template #icon>🔄</template>
          刷新
        </n-button>
        <input
          ref="novelFileInput"
          class="hidden-file-input"
          type="file"
          accept=".txt,.md,.markdown,text/plain,text/markdown"
          @change="handleNovelFileChange"
        />
      </div>
    </div>

    <!-- 主体：三栏布局 -->
    <div class="workbench">
      <!-- 左侧：摘要索引 -->
      <aside class="list-panel">
        <div class="panel-head">
          <h2>{{ activeIndex === 'summaries' ? '摘要索引' : '长期记忆' }}</h2>
          <div class="index-actions">
            <n-tag size="tiny" type="default">{{ activeIndex === 'summaries' ? filteredSummaries.length : memoryPageTotal }} 条</n-tag>
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
          <n-select v-else v-model:value="memoryTypeFilter" clearable :options="memoryTypeOptions" placeholder="按记忆类型筛选" />
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
            <p class="empty-sub">设定共创确认写回后、或章节变化审核通过后会沉淀到这里</p>
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
        <div v-if="activeIndex === 'items' && memoryPageTotal > memoryPageSize" class="memory-pagination">
          <n-pagination
            :page="memoryPage"
            :page-size="memoryPageSize"
            :item-count="memoryPageTotal"
            size="small"
            @update:page="changeMemoryPage"
          />
        </div>
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
                <p v-if="selectedMemoryMetadata.target_type">目标类型：{{ settingTargetLabel(String(selectedMemoryMetadata.target_type)) }}</p>
                <p v-if="selectedMemoryMetadata.target_id">目标档案 ID：{{ selectedMemoryMetadata.target_id }}</p>
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
              <p>长期条目按关键词和类型在数据库侧筛选，再分页读取。</p>
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
              <strong>{{ memoryItemTotal }}</strong>
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

    <n-modal
      v-model:show="importDialogVisible"
      preset="card"
      title="读取小说并补充记忆"
      class="memory-import-modal"
      :style="{ width: 'min(920px, 94vw)' }"
      :mask-closable="!batchRunning"
      :close-on-esc="!batchRunning"
    >
      <div class="memory-import-body">
        <n-alert type="info" :show-icon="true">
          支持 TXT、Markdown。系统会预览识别到的章节；正文按章节保存，再依次生成摘要和待审核变化，不会直接覆盖人物、关系或组织设定。
        </n-alert>

        <div v-if="!batchStarted" class="novel-file-row">
          <div class="novel-file-name">
            <span class="novel-file-icon">📄</span>
            <div>
              <strong>{{ novelFileName || '还没有选择小说文件' }}</strong>
              <span>{{ parsedNovelChapters.length ? `识别到 ${parsedNovelChapters.length} 章` : '单个文件最大 20 MB' }}</span>
            </div>
          </div>
          <n-button secondary @click="openNovelPicker">选择文件</n-button>
        </div>

        <div v-if="!batchStarted && parsedNovelChapters.length" class="import-options">
          <div class="import-option">
            <span class="option-label">已有章节</span>
            <span class="import-option-hint">保留已有正文；缺少摘要的章节会使用项目现有正文补充记忆</span>
          </div>
          <div class="import-option">
            <span class="option-label">记忆处理</span>
            <n-checkbox v-model:checked="analyzeAfterImport" :disabled="batchRunning">导入后逐章分析并补充记忆</n-checkbox>
          </div>
        </div>

        <div v-if="!batchStarted && parsedNovelChapters.length" class="novel-preview">
          <div class="preview-heading">
            <strong>章节预览</strong>
            <span>可修改章节号和标题；正文取文件中的章节内容</span>
          </div>
          <n-alert v-if="!novelHasHeadings" type="warning" :show-icon="true" class="preview-alert">
            未识别到常见章节标题，当前文件会按一章导入。若这是整本小说，请先按“第 X 章”或“Chapter X”分章。
          </n-alert>
          <n-alert v-if="duplicateImportNumbers.length" type="error" :show-icon="true" class="preview-alert">
            章节号重复：{{ duplicateImportNumbers.join('、') }}。请调整后再导入。
          </n-alert>
          <n-alert v-if="ambiguousExistingNumbers.length" type="warning" :show-icon="true" class="preview-alert">
            项目中这些章节号已有多条正文，系统不会自动选择覆盖目标：{{ ambiguousExistingNumbers.join('、') }}。
          </n-alert>
          <n-scrollbar class="novel-preview-scroll">
            <div class="novel-chapter-list">
              <div v-for="chapter in parsedNovelChapters" :key="chapter.key" class="novel-chapter-preview">
                <div class="novel-chapter-fields">
                  <n-input-number v-model:value="chapter.chapter_no" :min="1" :max="999999" :disabled="batchRunning" class="chapter-number-input">
                    <template #prefix>第</template>
                    <template #suffix>章</template>
                  </n-input-number>
                  <n-input v-model:value="chapter.title" :disabled="batchRunning" placeholder="章节标题" />
                  <n-tag size="small" :type="chapter.content.trim() ? 'success' : 'error'">
                    {{ chapter.content.trim() ? `${chapter.content.length.toLocaleString()} 字` : '正文为空' }}
                  </n-tag>
                </div>
                <p class="novel-chapter-excerpt">{{ shortText(chapter.content.replace(/\s+/g, ' '), 150) }}</p>
              </div>
            </div>
          </n-scrollbar>
        </div>

        <div v-if="batchStarted" class="memory-batch-progress">
          <div class="batch-progress-heading">
            <strong>{{ batchLabel }}</strong>
            <span>{{ batchFinishedCount }} / {{ batchTasks.length }} 项完成</span>
          </div>
          <n-progress
            type="line"
            :percentage="batchProgress"
            :status="batchRunning ? 'default' : batchFailedCount ? 'warning' : 'success'"
            :show-indicator="true"
          />
          <div v-if="batchRunning" class="batch-running-hint">
            当前按章节顺序处理。可以停止后续章节；已经保存的正文和分析结果会保留。
            <n-button size="tiny" type="warning" secondary :disabled="batchStopRequested" @click="requestStopBatch">
              {{ batchStopRequested ? '正在停止…' : '停止后续章节' }}
            </n-button>
          </div>
          <n-scrollbar class="batch-task-scroll">
            <div class="batch-task-list">
              <div v-for="task in batchTasks" :key="task.key" class="batch-task-row">
                <span class="batch-task-state" :class="`state-${task.state}`">{{ batchTaskStateLabel(task.state) }}</span>
                <strong>第 {{ task.chapter_no }} 章 · {{ task.title }}</strong>
                <span v-if="task.error" class="batch-task-error">{{ task.error }}</span>
              </div>
            </div>
          </n-scrollbar>
          <n-alert v-if="!batchRunning" :type="batchFailedCount ? 'warning' : 'success'" :show-icon="true">
            {{ batchCompletionMessage }}
          </n-alert>
        </div>

        <div class="memory-import-actions">
          <n-button v-if="batchStarted && !batchRunning && batchFailedCount" secondary @click="retryFailedTasks">重试失败项</n-button>
          <n-button v-if="!batchRunning" @click="closeImportDialog">{{ batchStarted ? '关闭' : '取消' }}</n-button>
          <n-button
            v-if="!batchStarted"
            type="primary"
            :disabled="!canStartImport"
            @click="startNovelImport"
          >
            {{ analyzeAfterImport ? '导入并补充记忆' : '仅导入章节' }}
          </n-button>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { analyzeChapter, getChapterAnalysisStatus, getChapterSummaries, type ChapterAnalysisStatus } from '@/api/agents'
import { getLongTermMemoryItems, type LongTermMemoryItem } from '@/api/agentsV3'
import { createResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import { notify } from '@/utils/notify'
import type { ChapterItem, ChapterSummary } from '@/types/domain'

interface NovelChapterDraft {
  key: string
  chapter_no: number
  title: string
  content: string
}

type BatchTaskState = 'waiting' | 'saving' | 'analyzing' | 'imported' | 'done' | 'skipped' | 'failed' | 'stopped'

interface MemoryBatchTask {
  key: string
  chapter_no: number
  title: string
  content: string
  state: BatchTaskState
  chapter_id?: number
  existing_chapter_id?: number
  error?: string
}

const projectStore = useProjectStore()
const activeIndex = ref<'summaries' | 'items'>('summaries')
const keyword = ref('')
const chapterFilter = ref<number | null>(null)
const memoryTypeFilter = ref<string | null>(null)
const summaries = ref<ChapterSummary[]>([])
const memoryItems = ref<LongTermMemoryItem[]>([])
const memoryItemTotal = ref(0)
const memoryPageTotal = ref(0)
const memoryPage = ref(1)
const memoryPageSize = 50
const chapters = ref<ChapterItem[]>([])
const analysisStatus = ref<ChapterAnalysisStatus[]>([])
const selectedSummary = ref<ChapterSummary | null>(null)
const selectedMemoryItem = ref<LongTermMemoryItem | null>(null)
const loading = ref(false)
const hasLoadedMemories = ref(false)
const novelFileInput = ref<HTMLInputElement | null>(null)
const importDialogVisible = ref(false)
const novelFileName = ref('')
const parsedNovelChapters = ref<NovelChapterDraft[]>([])
const novelHasHeadings = ref(false)
const analyzeAfterImport = ref(true)
const batchStarted = ref(false)
const batchRunning = ref(false)
const batchStopRequested = ref(false)
const batchLabel = ref('')
const batchTasks = ref<MemoryBatchTask[]>([])
let memoryLoadSequence = 0
let currentProjectId: number | null = null
let memoryFilterTimer: ReturnType<typeof setTimeout> | null = null

const chapterOptions = computed(() =>
  chapters.value.map((item) => ({
    label: `第 ${item.chapter_no} 章 · ${item.title}`,
    value: item.chapter_no
  }))
)
const memoryTypeOptions = [
  'character', 'relationship', 'organization', 'foreshadowing', 'foreshadow', 'world_setting',
  'setting', 'general', 'timeline', 'timeline_event', 'chapter',
].map((value) => ({ label: memoryTypeLabel(value), value }))

const chapterCount = computed(() => analysisStatus.value.length || chapters.value.length)
const summaryCount = computed(() => analysisStatus.value.length
  ? analysisStatus.value.filter((item) => item.has_summary).length
  : summaries.value.length)
const coverageRate = computed(() => {
  const readableChapters = analysisStatus.value.filter((item) => item.has_content)
  if (!readableChapters.length) return 0
  const analyzedChapters = readableChapters.filter((item) => item.has_summary).length
  return Math.round((analyzedChapters / readableChapters.length) * 100)
})

const duplicateImportNumbers = computed(() => {
  const counts = new Map<number, number>()
  parsedNovelChapters.value.forEach((chapter) => counts.set(chapter.chapter_no, (counts.get(chapter.chapter_no) || 0) + 1))
  return [...counts.entries()].filter(([, count]) => count > 1).map(([chapterNo]) => chapterNo).sort((a, b) => a - b)
})

const ambiguousExistingNumbers = computed(() => {
  const counts = new Map<number, number>()
  chapters.value.forEach((chapter) => counts.set(chapter.chapter_no, (counts.get(chapter.chapter_no) || 0) + 1))
  const importNumbers = new Set(parsedNovelChapters.value.map((chapter) => chapter.chapter_no))
  return [...counts.entries()]
    .filter(([chapterNo, count]) => count > 1 && importNumbers.has(chapterNo))
    .map(([chapterNo]) => chapterNo)
    .sort((a, b) => a - b)
})

const canStartImport = computed(() => {
  const hasInvalidDraft = parsedNovelChapters.value.some((chapter) =>
    !Number.isInteger(chapter.chapter_no) || chapter.chapter_no < 1 || !chapter.content.trim()
  )
  return Boolean(
    novelFileName.value
    && parsedNovelChapters.value.length
    && !hasInvalidDraft
    && !duplicateImportNumbers.value.length
    && !ambiguousExistingNumbers.value.length
    && !batchRunning.value
  )
})

const batchFinishedCount = computed(() => batchTasks.value.filter((task) =>
  ['imported', 'done', 'skipped', 'failed', 'stopped'].includes(task.state)
).length)
const batchFailedCount = computed(() => batchTasks.value.filter((task) => task.state === 'failed').length)
const batchProgress = computed(() => batchTasks.value.length
  ? Math.round((batchFinishedCount.value / batchTasks.value.length) * 100)
  : 0)
const batchCompletionMessage = computed(() => {
  const completed = batchTasks.value.filter((task) => task.state === 'done' || task.state === 'imported').length
  const skipped = batchTasks.value.filter((task) => task.state === 'skipped').length
  const stopped = batchTasks.value.filter((task) => task.state === 'stopped').length
  const failed = batchFailedCount.value
  return `完成 ${completed} 项，跳过 ${skipped} 项，失败 ${failed} 项${stopped ? `，已停止 ${stopped} 项` : ''}。已保存内容可刷新后继续处理。`
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
    const matchesType = !memoryTypeFilter.value || (item.memory_type || 'general') === memoryTypeFilter.value
    return matchesType && (!text || haystack.includes(text))
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
  memoryTypeFilter.value = null
  // 步骤 2：优先保留当前有效选择，否则选择新索引中的第一条。
  if (activeIndex.value === 'items' && !memoryItems.value.some((item) => item.memory_id === selectedMemoryItem.value?.memory_id)) {
    selectedMemoryItem.value = memoryItems.value[0] ?? null
  }
  if (activeIndex.value === 'summaries' && !summaries.value.some((item) => item.id === selectedSummary.value?.id)) {
    selectedSummary.value = summaries.value[0] ?? null
  }
}

watch([activeIndex, keyword, memoryTypeFilter], () => {
  // 步骤 1：章节摘要使用本地过滤；长期条目使用全量数据库过滤并回到第一页。
  if (activeIndex.value !== 'items' || !hasLoadedMemories.value) return
  memoryPage.value = 1
  if (memoryFilterTimer) clearTimeout(memoryFilterTimer)
  memoryFilterTimer = setTimeout(() => {
    void loadMemories(true)
  }, 250)
})

const selectedMemoryMetadata = computed<Record<string, unknown>>(() => {
  if (!selectedMemoryItem.value?.metadata_json) return {}
  try {
    const parsed = JSON.parse(selectedMemoryItem.value.metadata_json)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
  } catch {
    return {}
  }
})

function memoryTypeLabel(value: string | null | undefined) {
  const labels: Record<string, string> = {
    character: '人物记忆',
    relationship: '关系记忆',
    organization: '组织记忆',
    foreshadowing: '伏笔记忆',
    world_setting: '世界观记忆',
    setting: '设定记忆',
    general: '通用记忆',
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
    setting_co: '设定共创',
  }
  const key = value || ''
  return labels[key] || key || '未知来源'
}

function settingTargetLabel(value: string) {
  const labels: Record<string, string> = { character: '人物', world: '世界观', foreshadowing: '伏笔' }
  return labels[value] || value || '未知'
}

function openNovelPicker() {
  // 步骤 1：阻止批处理中切换文件；步骤 2：打开浏览器本地文件选择器。
  if (batchRunning.value) return
  novelFileInput.value?.click()
}

async function handleNovelFileChange(event: Event) {
  // 步骤 1：校验文件格式和大小；步骤 2：在浏览器本地读取并解析章节标题。
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!['txt', 'md', 'markdown'].includes(extension || '')) {
    notify.error('请选择 TXT 或 Markdown 文件')
    return
  }
  if (file.size > 20 * 1024 * 1024) {
    notify.error('单个小说文件不能超过 20 MB')
    return
  }

  try {
    const bytes = await file.arrayBuffer()
    let text: string
    try {
      // UTF-8 是默认编码；旧版 Windows 文本无法按 UTF-8 解码时再尝试 GB18030。
      text = new TextDecoder('utf-8', { fatal: true }).decode(bytes)
    } catch {
      text = new TextDecoder('gb18030').decode(bytes)
    }
    text = text.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').trim()
    if (!text) {
      notify.warning('文件内容为空')
      return
    }

    novelFileName.value = file.name
    const nextChapterNo = Math.max(0, ...analysisStatus.value.map((item) => item.chapter_no)) + 1
    const parsed = splitNovelIntoChapters(text, file.name, nextChapterNo)
    novelHasHeadings.value = parsed.hasHeadings
    parsedNovelChapters.value = parsed.chapters
    analyzeAfterImport.value = true
    batchStarted.value = false
    batchTasks.value = []
    importDialogVisible.value = true
  } catch (error) {
    console.error('读取小说文件失败', error)
    notify.error('读取文件失败，请确认文件编码和内容格式')
  }
}

function splitNovelIntoChapters(text: string, fileName: string, fallbackChapterNo: number) {
  // 步骤 1：逐行识别中文“第 X 章/回”和英文“Chapter X”标题。
  const lines = text.split('\n')
  const headings: Array<{ chapterNo: number; title: string; start: number; bodyStart: number }> = []
  let offset = 0
  lines.forEach((line) => {
    const heading = parseNovelHeading(line)
    if (heading) {
      headings.push({
        chapterNo: heading.chapter_no,
        title: heading.title,
        start: offset,
        bodyStart: Math.min(text.length, offset + line.length + 1),
      })
    }
    offset += line.length + 1
  })

  // 步骤 2：没有识别到章标题时，把文件作为一个章节导入，并提示作者核对。
  if (!headings.length) {
    const title = fileName.replace(/\.(txt|md|markdown)$/i, '') || `第${fallbackChapterNo}章`
    return {
      hasHeadings: false,
      chapters: [{ key: `file-${Date.now()}-1`, chapter_no: fallbackChapterNo, title, content: text.trim() }],
    }
  }

  // 步骤 3：按标题切分正文；首章标题前的序言保留到首章，不丢弃原文。
  const preface = text.slice(0, headings[0].start).trim()
  const chapters = headings.map((heading, index) => {
    const nextStart = headings[index + 1]?.start ?? text.length
    let content = text.slice(heading.bodyStart, nextStart).trim()
    if (index === 0 && preface) content = `${preface}\n\n${content}`.trim()
    return {
      key: `file-${Date.now()}-${index + 1}`,
      chapter_no: heading.chapterNo,
      title: heading.title,
      content,
    }
  })
  return { hasHeadings: true, chapters }
}

function parseNovelHeading(line: string): { chapter_no: number; title: string } | null {
  // 步骤 1：移除 Markdown 标题符号；步骤 2：解析标题号并保留标题文本。
  const normalized = line.trim().replace(/^#{1,3}\s*/, '')
  const chineseMatch = normalized.match(/^第\s*([0-9０-９〇○零一二两三四五六七八九十百千万]+)\s*[章回](?:\s*[:：、.．\-—]?\s*(.*))?$/)
  if (chineseMatch) {
    const chapterNo = parseChineseChapterNumber(chineseMatch[1])
    if (chapterNo > 0) return { chapter_no: chapterNo, title: chineseMatch[2]?.trim() || `第${chapterNo}章` }
  }
  const englishMatch = normalized.match(/^(?:chapter|ch\.?)\s*([0-9０-９]+)(?:\s*[:：、.．\-—]?\s*(.*))?$/i)
  if (englishMatch) {
    const chapterNo = Number(englishMatch[1].replace(/[０-９]/g, (value) => String(value.charCodeAt(0) - 0xFF10)))
    if (chapterNo > 0) return { chapter_no: chapterNo, title: englishMatch[2]?.trim() || `Chapter ${chapterNo}` }
  }
  return null
}

function parseChineseChapterNumber(rawValue: string): number {
  // 步骤 1：兼容全角阿拉伯数字；步骤 2：把常见中文数词换算为章号。
  const value = rawValue.replace(/[０-９]/g, (digit) => String(digit.charCodeAt(0) - 0xFF10))
  if (/^\d+$/.test(value)) return Number(value)

  const digits: Record<string, number> = { '零': 0, '〇': 0, '○': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9 }
  if ([...value].every((char) => char in digits)) return Number([...value].map((char) => digits[char]).join(''))

  const smallUnits: Record<string, number> = { '十': 10, '百': 100, '千': 1000 }
  let total = 0
  let section = 0
  let current = 0
  for (const char of value) {
    if (char in digits) {
      current = digits[char]
    } else if (smallUnits[char]) {
      section += (current || 1) * smallUnits[char]
      current = 0
    } else if (char === '万') {
      total += (section + current || 1) * 10000
      section = 0
      current = 0
    } else {
      return 0
    }
  }
  return total + section + current
}

// 步骤 1：把内部任务状态映射为界面文案；步骤 2：供进度列表统一展示。
function batchTaskStateLabel(state: BatchTaskState) {
  const labels: Record<BatchTaskState, string> = {
    waiting: '等待', saving: '保存中', analyzing: '分析中', imported: '已导入',
    done: '已完成', skipped: '已跳过', failed: '失败', stopped: '未处理',
  }
  return labels[state]
}

function requestStopBatch() {
  // 步骤 1：标记停止意图；步骤 2：当前正在请求的章节结束后停止队列。
  batchStopRequested.value = true
}

function closeImportDialog() {
  // 步骤 1：只允许在处理结束后关闭；步骤 2：清理本次文件预览和任务状态。
  if (batchRunning.value) return
  importDialogVisible.value = false
  batchStarted.value = false
  novelFileName.value = ''
  parsedNovelChapters.value = []
  batchTasks.value = []
  batchStopRequested.value = false
}

async function startExistingBackfill() {
  // 步骤 1：重新读取章节正文和分析状态；步骤 2：把有正文且没有摘要的章节排入顺序队列。
  const projectId = projectStore.currentProject?.id
  if (!projectId || batchRunning.value) return
  batchRunning.value = true
  try {
    const [chapterList, statusList] = await Promise.all([
      listResource<ChapterItem>(projectId, 'chapters'),
      getChapterAnalysisStatus(projectId),
    ])
    chapters.value = chapterList
    analysisStatus.value = statusList
    const chaptersById = new Map(chapterList.map((chapter) => [chapter.id, chapter]))
    const tasks = statusList
      .filter((status) => status.has_content && !status.has_summary)
      .map((status) => {
        const chapter = chaptersById.get(status.chapter_id)
        return chapter ? {
          key: `chapter-${chapter.id}`,
          chapter_id: chapter.id,
          chapter_no: chapter.chapter_no,
          title: chapter.title,
          content: chapter.content,
          state: 'waiting' as BatchTaskState,
        } : null
      })
      .filter((task): task is MemoryBatchTask => task !== null)
    if (!tasks.length) {
      notify.info('没有待补充记忆的章节')
      return
    }
    batchLabel.value = '补充已有章节记忆'
    batchTasks.value = tasks
    batchStarted.value = true
    batchStopRequested.value = false
    importDialogVisible.value = true
    await runAnalysisQueue(tasks, projectId)
    await loadMemories(true)
  } catch (error) {
    console.error('准备章节记忆回填失败', error)
    notify.error('读取章节状态失败，请稍后重试')
  } finally {
    batchRunning.value = false
  }
}

async function startNovelImport() {
  // 步骤 1：校验项目和预览结果；步骤 2：逐章保存正文；步骤 3：按顺序分析并刷新记忆中心。
  const projectId = projectStore.currentProject?.id
  if (!projectId || !canStartImport.value || batchRunning.value) return

  const existingByNo = new Map<number, ChapterItem[]>()
  chapters.value.forEach((chapter) => {
    const items = existingByNo.get(chapter.chapter_no) || []
    items.push(chapter)
    existingByNo.set(chapter.chapter_no, items)
  })
  const statusById = new Map(analysisStatus.value.map((status) => [status.chapter_id, status]))
  const tasks: MemoryBatchTask[] = parsedNovelChapters.value.map((chapter, index) => {
    const existing = existingByNo.get(chapter.chapter_no)?.[0]
    return {
      key: chapter.key || `import-${index}`,
      chapter_no: chapter.chapter_no,
      title: chapter.title.trim() || `第${chapter.chapter_no}章`,
      content: chapter.content.trim(),
      existing_chapter_id: existing?.id,
      chapter_id: existing?.id,
      state: 'waiting',
    }
  })

  batchLabel.value = analyzeAfterImport.value ? '导入并补充记忆' : '导入小说章节'
  batchTasks.value = tasks
  batchStarted.value = true
  batchRunning.value = true
  batchStopRequested.value = false

  try {
    // 步骤 1：保留已有正文；步骤 2：只填充空章节；步骤 3：对缺少摘要的正文排队分析。
    for (const task of tasks) {
      if (batchStopRequested.value) {
        task.state = 'stopped'
        continue
      }
      const existing = task.existing_chapter_id
        ? existingByNo.get(task.chapter_no)?.find((chapter) => chapter.id === task.existing_chapter_id)
        : undefined
      if (existing && (existing.content.trim() || statusById.get(existing.id)?.has_summary)) {
        const status = statusById.get(existing.id)
        task.title = existing.title
        task.content = existing.content
        task.state = analyzeAfterImport.value && existing.content.trim() && !status?.has_summary ? 'waiting' : 'skipped'
        continue
      }

      task.state = 'saving'
      const payload = {
        project_id: projectId,
        outline_id: existing?.outline_id ?? null,
        chapter_no: task.chapter_no,
        title: task.title,
        content: task.content,
        status: existing?.status || 'draft',
      }
      try {
        const savedChapter = existing
          ? await updateResource<ChapterItem>('chapters', existing.id, payload)
          : await createResource<ChapterItem>('chapters', payload)
        task.chapter_id = savedChapter.id
        task.state = analyzeAfterImport.value ? 'waiting' : 'imported'
      } catch (error) {
        task.state = 'failed'
        task.error = requestErrorMessage(error)
      }
    }

    // 步骤 2：正文全部安全落库后，再按章号顺序分析，保证后章能读取前章摘要。
    if (analyzeAfterImport.value && !batchStopRequested.value) {
      await runAnalysisQueue(tasks.filter((task) => task.state === 'waiting' && task.chapter_id), projectId)
    } else if (batchStopRequested.value) {
      tasks.filter((task) => task.state === 'waiting').forEach((task) => { task.state = 'stopped' })
    }

    await loadMemories(true)
  } finally {
    batchRunning.value = false
    if (batchFailedCount.value) notify.warning(batchCompletionMessage.value)
    else notify.success(batchCompletionMessage.value)
  }
}

async function runAnalysisQueue(tasks: MemoryBatchTask[], projectId: number) {
  // 步骤 1：按章节号稳定排序；步骤 2：逐章分析，记录成功、失败或停止状态。
  const queue = [...tasks].sort((a, b) => a.chapter_no - b.chapter_no || a.key.localeCompare(b.key))
  for (let index = 0; index < queue.length; index += 1) {
    const task = queue[index]
    if (batchStopRequested.value) {
      queue.slice(index).forEach((pending) => { pending.state = 'stopped' })
      break
    }
    if (!task.chapter_id || !task.content.trim()) {
      task.state = 'failed'
      task.error = '章节正文为空或尚未保存'
      continue
    }

    task.state = 'analyzing'
    task.error = ''
    try {
      const result = await analyzeChapter({
        project_id: projectId,
        chapter_id: task.chapter_id,
        content: task.content,
      })
      if (result.analysis_status === 'unavailable') {
        throw new Error('模型暂不可用，章节正文已保留；请检查 API 配置后重试')
      }
      task.state = 'done'
    } catch (error) {
      task.state = 'failed'
      task.error = requestErrorMessage(error)
    }
  }
}

async function retryFailedTasks() {
  // 步骤 1：仅重试已经有章节 ID 的分析失败项；保存失败项可重新选择原文件续导。
  const failedTasks = batchTasks.value.filter((task) => task.state === 'failed' && task.chapter_id)
  if (!failedTasks.length) {
    notify.info('正文保存失败的章节可重新选择原文件；已导入正文会自动跳过')
    return
  }
  const projectId = projectStore.currentProject?.id
  if (!projectId || batchRunning.value) return
  failedTasks.forEach((task) => { task.state = 'waiting'; task.error = '' })
  batchStopRequested.value = false
  batchLabel.value = '重试失败章节记忆'
  batchRunning.value = true
  try {
    await runAnalysisQueue(failedTasks, projectId)
    await loadMemories(true)
  } finally {
    batchRunning.value = false
  }
}

function requestErrorMessage(error: unknown) {
  // 步骤 1：优先展示后端业务错误；步骤 2：无具体错误时给出可操作的通用提示。
  const responseData = (error as { response?: { data?: { detail?: unknown } } })?.response?.data
  if (typeof responseData?.detail === 'string') return responseData.detail
  if (error instanceof Error && error.message) return error.message.slice(0, 180)
  return '处理失败，请重试'
}

async function loadMemories(silent = false) {
  // 步骤 1：等待项目选择完成；步骤 2：并行读取章节、摘要和长期条目。
  const projectId = projectStore.currentProject?.id
  if (!projectId) return
  if (currentProjectId !== projectId) {
    // 步骤 1：切换项目时清除上一项目的选中项和分页状态。
    currentProjectId = projectId
    memoryPage.value = 1
    selectedSummary.value = null
    selectedMemoryItem.value = null
    hasLoadedMemories.value = false
    keyword.value = ''
    chapterFilter.value = null
    memoryTypeFilter.value = null
  }
  const requestSequence = ++memoryLoadSequence
  loading.value = true
  try {
    const offset = activeIndex.value === 'items' ? (memoryPage.value - 1) * memoryPageSize : 0
    const [chapterList, summaryList, memoryItemPage, statusList] = await Promise.all([
      listResource<ChapterItem>(projectId, 'chapters'),
      getChapterSummaries(projectId, 50),
      getLongTermMemoryItems(projectId, {
        limit: memoryPageSize,
        offset,
        keyword: activeIndex.value === 'items' ? keyword.value : '',
        memoryType: activeIndex.value === 'items' ? memoryTypeFilter.value : null,
      }),
      getChapterAnalysisStatus(projectId),
    ])
    if (requestSequence !== memoryLoadSequence || projectId !== projectStore.currentProject?.id) return
    const memoryItemList = memoryItemPage.items
    chapters.value = chapterList
    analysisStatus.value = statusList
    summaries.value = summaryList
    memoryItems.value = memoryItemList
    memoryItemTotal.value = memoryItemPage.all_total
    memoryPageTotal.value = memoryItemPage.total
    // 步骤 3：摘要为空但已有设定记忆时，首次进入直接展示有内容的索引。
    if (!hasLoadedMemories.value && summaryList.length === 0 && memoryItemList.length > 0) {
      activeIndex.value = 'items'
    }
    hasLoadedMemories.value = true
    if (!selectedSummary.value || !summaryList.some((item) => item.id === selectedSummary.value?.id)) {
      selectedSummary.value = summaryList[0] ?? null
    }
    if (!selectedMemoryItem.value || !memoryItemList.some((item) => item.memory_id === selectedMemoryItem.value?.memory_id)) {
      selectedMemoryItem.value = memoryItemList[0] ?? null
    }
    if (!silent) notify.success('长期记忆已刷新')
  } catch (error) {
    if (requestSequence !== memoryLoadSequence) return
    console.error('加载长期记忆失败', error)
    notify.error('长期记忆加载失败，请稍后重试')
  } finally {
    if (requestSequence === memoryLoadSequence) loading.value = false
  }
}

async function changeMemoryPage(page: number) {
  // 步骤 1：更新页码；步骤 2：静默加载当前页，避免翻页时弹出刷新提示。
  memoryPage.value = page
  await loadMemories(true)
}

useProjectDataLoader(loadMemories)
onBeforeUnmount(() => {
  if (memoryFilterTimer) clearTimeout(memoryFilterTimer)
})
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

.memory-pagination {
  display: flex;
  justify-content: center;
  padding: 10px 8px;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.memory-pagination {
  display: flex;
  justify-content: center;
  padding: 10px 8px;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
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

.hidden-file-input {
  display: none;
}

.memory-import-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
}

.novel-file-row,
.batch-progress-heading,
.preview-heading,
.memory-import-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.novel-file-row {
  padding: 12px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  background: var(--n-color-1, #1e2228);
}

.novel-file-name {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.novel-file-icon {
  font-size: 22px;
}

.novel-file-name div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.novel-file-name strong,
.novel-file-name span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.novel-file-name strong {
  color: var(--n-text-color-1, #e5e7eb);
  font-size: 13px;
}

.novel-file-name div span,
.preview-heading span {
  color: var(--n-text-color-3, #6b7280);
  font-size: 11px;
}

.import-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.import-option-hint {
  color: var(--n-text-color-3, #6b7280);
  font-size: 12px;
}

.import-option {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.option-label {
  width: 88px;
  flex: 0 0 auto;
  color: var(--n-text-color-2, #9ca3af);
  font-size: 12px;
}

.novel-preview,
.memory-batch-progress {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.preview-heading strong,
.batch-progress-heading strong {
  color: var(--n-text-color-1, #e5e7eb);
  font-size: 13px;
}

.preview-alert {
  margin: 0;
}

.novel-preview-scroll {
  height: min(42vh, 420px);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.novel-chapter-list,
.batch-task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
}

.novel-chapter-preview {
  padding: 10px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 7px;
  background: var(--n-color-1, #1e2228);
}

.novel-chapter-fields {
  display: grid;
  grid-template-columns: 145px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
}

.novel-chapter-excerpt {
  margin: 8px 0 0;
  color: var(--n-text-color-3, #6b7280);
  font-size: 11px;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.batch-progress-heading span {
  color: var(--n-text-color-3, #6b7280);
  font-size: 12px;
}

.batch-running-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--n-text-color-3, #6b7280);
  font-size: 11px;
}

.batch-task-scroll {
  height: min(46vh, 460px);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.batch-task-row {
  display: grid;
  grid-template-columns: 58px minmax(150px, 1fr) minmax(0, 1.4fr);
  align-items: center;
  gap: 10px;
  min-height: 36px;
  padding: 6px 8px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  font-size: 11px;
}

.batch-task-row strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--n-text-color-2, #9ca3af);
}

.batch-task-state {
  color: var(--n-text-color-3, #6b7280);
}

.batch-task-state.state-done,
.batch-task-state.state-imported {
  color: #36ad75;
}

.batch-task-state.state-analyzing,
.batch-task-state.state-saving {
  color: #63e2b7;
}

.batch-task-state.state-failed {
  color: #e88080;
}

.batch-task-error {
  overflow: hidden;
  color: #e88080;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.memory-import-actions {
  justify-content: flex-end;
  padding-top: 2px;
}

@media (max-width: 1100px) {
  .header-right {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .batch-task-row {
    grid-template-columns: 58px minmax(0, 1fr);
  }

  .batch-task-error {
    grid-column: 2;
    white-space: normal;
  }
}

@media (max-width: 700px) {
  .novel-chapter-fields {
    grid-template-columns: 1fr;
  }

  .import-option {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .batch-running-hint {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
