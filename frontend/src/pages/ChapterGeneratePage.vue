<template>
  <div class="page chapter-generate-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">✨</span>
          章节生成工作台
        </h1>
        <p class="page-subtitle">
          选择大纲 → 调整参数 → 生成正文 → 分析沉淀
        </p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ outlines.length }}</span>
            <span class="stat-label">大纲</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ chapters.length }}</span>
            <span class="stat-label">章节草稿</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num success">{{ wordCount }}</span>
            <span class="stat-label">当前字数</span>
          </div>
        </div>
        <n-button size="small" @click="loadResources" :loading="loading">
          <template #icon>🔄</template>
          刷新资料
        </n-button>
      </div>
    </div>

    <!-- 三栏主体 -->
    <div class="workbench">
      <!-- ===== 左侧：大纲+章节队列 ===== -->
      <aside class="left-panel">
        <div class="panel-search">
          <n-input v-model:value="keyword" clearable placeholder="搜索大纲或章节...">
            <template #prefix>🔍</template>
          </n-input>
        </div>

        <!-- 上下文简报 -->
        <div class="context-brief-card">
          <div class="brief-row">
            <span class="brief-label">当前大纲</span>
            <span class="brief-value" :title="selectedOutline?.title">
              {{ selectedOutline?.title || '未选择' }}
            </span>
          </div>
          <div class="brief-row">
            <span class="brief-label">当前章节</span>
            <span class="brief-value" :title="selectedChapter?.title || `第${form.chapter_no}章`">
              {{ selectedChapter?.title || `第${form.chapter_no}章` }}
            </span>
          </div>
        </div>

        <!-- 大纲列表 -->
        <div class="list-section">
          <div class="list-section-header">
            <span class="section-label">📋 大纲</span>
            <n-tag size="tiny" type="info">{{ filteredOutlines.length }}</n-tag>
          </div>
          <n-scrollbar class="list-scroll">
            <div v-if="filteredOutlines.length === 0" class="list-empty">
              暂无大纲
            </div>
            <div
              v-for="item in filteredOutlines"
              :key="item.id"
              class="queue-item"
              :class="{ active: form.outline_id === item.id }"
              @click="selectOutline(item)"
            >
              <div class="item-main">
                <div class="item-title">{{ item.title }}</div>
                <div class="item-meta">
                  <span class="chapter-no-badge">#{{ item.chapter_no ?? item.sort_index }}</span>
                  {{ item.description || '暂无目标' }}
                </div>
              </div>
            </div>
          </n-scrollbar>
        </div>

        <!-- 章节列表 -->
        <div class="list-section">
          <div class="list-section-header">
            <span class="section-label">📝 章节草稿</span>
            <n-tag size="tiny" type="info">{{ filteredChapters.length }}</n-tag>
          </div>
          <n-scrollbar class="list-scroll">
            <div v-if="filteredChapters.length === 0" class="list-empty">
              暂无章节草稿
            </div>
            <div
              v-for="item in filteredChapters"
              :key="item.id"
              class="queue-item"
              :class="{ active: chapterId === item.id }"
              @click="selectChapter(item)"
            >
              <div class="item-main">
                <div class="item-title-row">
                  <span class="item-title">{{ item.title }}</span>
                  <n-tag size="tiny" :type="statusTagType(item.status)">
                    {{ statusLabel(item.status) }}
                  </n-tag>
                </div>
                <div class="item-meta">
                  第 {{ item.chapter_no }} 章 · {{ formatChars(item.content) }} 字
                </div>
              </div>
            </div>
          </n-scrollbar>
        </div>
      </aside>

      <!-- ===== 中间：正文编辑器 ===== -->
      <section class="editor-panel">
        <!-- 编辑器工具栏 -->
        <div class="editor-toolbar">
          <div class="toolbar-left">
            <n-input
              v-model:value="chapterTitle"
              class="title-input"
              placeholder="章节标题..."
              size="large"
              :bordered="false"
            />
          </div>
          <div class="toolbar-right">
            <div class="word-count">
              <span class="count-num">{{ wordCount }}</span>
              <span class="count-label">字</span>
            </div>
            <n-divider vertical />
            <span class="save-status" :class="{ saved: chapterId }">
              {{ chapterId ? '💾 已保存' : '📝 未保存' }}
            </span>
            <n-divider v-if="chapterId" vertical />
            <span v-if="chapterId" class="chapter-id">ID {{ chapterId }}</span>
          </div>
        </div>

        <!-- 正文编辑器 -->
        <div class="editor-container">
          <n-input
            v-model:value="draft"
            type="textarea"
            class="chapter-textarea"
            :autosize="{ minRows: 20 }"
            placeholder="在这里写你的小说正文...

提示：
1. 从左侧选择大纲，生成参数会自动填充
2. 调整右侧参数后点击「生成章节」
3. 生成后可进行分析、精修、一致性检查"
          />
        </div>

        <!-- 精修高亮对比面板 -->
        <div v-if="hasPolishHighlights" class="polish-panel">
          <div class="polish-header">
            <span class="polish-title">🎨 精修对比</span>
            <n-tag size="tiny" type="warning">高亮段落为精修后变化的内容</n-tag>
            <n-button size="tiny" text @click="polishOriginal = ''">关闭对比</n-button>
          </div>
          <div class="polish-content">
            <p
              v-for="(segment, index) in polishSegments"
              :key="`${index}-${segment.status}`"
              :class="['polish-segment', segment.status]"
            >
              {{ segment.text }}
            </p>
          </div>
        </div>
      </section>

      <!-- ===== 右侧：Tab 面板 ===== -->
      <aside class="right-panel">
        <n-tabs v-model:value="activeTab" type="line" size="small" class="side-tabs">
          <!-- Tab: 生成参数 -->
          <n-tab-pane name="params" tab="参数">
            <div class="tab-content">
              <!-- 章节设置 -->
              <div class="form-block">
                <div class="block-title">章节设置</div>
                <n-form label-placement="top" :show-label="true">
                  <div class="form-row">
                    <n-form-item label="章节号" style="flex: 0 0 100px">
                      <n-input-number v-model:value="form.chapter_no" :min="1" style="width: 100%" />
                    </n-form-item>
                    <n-form-item label="节奏等级">
                      <n-select v-model:value="form.rhythm_level" :options="rhythmOptions" />
                    </n-form-item>
                  </div>
                  <n-form-item label="本章目标">
                    <n-input
                      v-model:value="form.instruction"
                      type="textarea"
                      :autosize="{ minRows: 4, maxRows: 6 }"
                      placeholder="选择大纲后会自动带入，也可以手动修改"
                    />
                  </n-form-item>
                  <n-form-item label="本章重点伏笔">
                    <n-select
                      v-model:value="selectedForeshadowingIds"
                      multiple
                      filterable
                      tag
                      :options="foreshadowingOptions"
                      placeholder="选择本章要埋设或回收的伏笔"
                    />
                    <div class="field-hint">
                      选中的伏笔会优先进入上下文包，帮助 AI 在本章精准推进剧情线。
                    </div>
                  </n-form-item>
                </n-form>
              </div>

              <!-- 生成操作 -->
              <div class="form-block">
                <div class="block-title">生成操作</div>
                <div class="action-buttons">
                  <n-button
                    type="primary"
                    block
                    size="large"
                    :loading="loading"
                    :disabled="loading"
                    @click="requestGenerate('generate')"
                  >
                    <template #icon>✨</template>
                    {{ hasExistingDraft ? '重新生成章节' : '生成章节' }}
                  </n-button>
                  <n-button
                    block
                    :loading="loading"
                    :disabled="loading"
                    @click="requestGenerate('generateAndAnalyze')"
                  >
                    <template #icon>🔄</template>
                    生成 + 分析沉淀
                  </n-button>
                </div>
              </div>

              <!-- 辅助操作 -->
              <div class="form-block">
                <div class="block-title">辅助操作</div>
                <div class="secondary-actions">
                  <n-button block :disabled="!draft" @click="saveCurrentChapter">
                    💾 保存当前章节
                  </n-button>
                  <n-button block :disabled="!draft" @click="analyze">
                    📊 分析当前章节
                  </n-button>
                  <n-button block :disabled="!draft" @click="openPolishMenu">
                    ✨ 精修当前章节
                  </n-button>
                  <n-button block :disabled="!draft" @click="runConsistencyCheck">
                    🔍 检查一致性
                  </n-button>
                  <n-popconfirm
                    v-if="chapterId"
                    positive-text="确认删除"
                    negative-text="取消"
                    @positive-click="removeChapter(chapterId)"
                  >
                    <template #trigger>
                      <n-button type="error" block>🗑️ 删除当前章节</n-button>
                    </template>
                    确认删除当前章节草稿？此操作不可恢复。
                  </n-popconfirm>
                </div>
              </div>

              <!-- 上下文预检 -->
              <div class="form-block">
                <div class="block-title">
                  上下文预检
                  <span class="score-badge" :class="{ good: contextScore >= 5 }">
                    {{ contextScore }}/{{ contextChecks.length }}
                  </span>
                </div>
                <div class="check-grid">
                  <div
                    v-for="item in contextChecks"
                    :key="item.label"
                    class="check-item"
                    :class="{ ready: item.ready }"
                  >
                    <span class="check-icon">{{ item.ready ? '✓' : '○' }}</span>
                    <span class="check-label">{{ item.label }}</span>
                  </div>
                </div>
              </div>
            </div>
          </n-tab-pane>

          <!-- Tab: 上下文包 -->
          <n-tab-pane name="context" tab="上下文">
            <div class="tab-content">
              <div class="context-header">
                <span class="block-title">AI 工作包预览</span>
                <n-button size="tiny" :loading="previewLoading" @click="refreshContextPreview">
                  刷新
                </n-button>
              </div>

              <!-- 当前大纲 -->
              <div class="context-outline">
                <div class="context-label">📌 当前大纲</div>
                <div v-if="contextPreview?.outline" class="outline-card">
                  <strong>{{ contextPreview.outline.title }}</strong>
                  <p>{{ contextPreview.outline.description }}</p>
                </div>
                <div v-else class="empty-context">
                  选择大纲后可查看本次生成目标
                </div>
              </div>

              <!-- 资料统计 -->
              <div class="context-stats">
                <div class="context-stat-card">
                  <span class="stat-icon">🌍</span>
                  <span class="stat-num">{{ contextPreview?.world ? 1 : 0 }}</span>
                  <span class="stat-name">世界观</span>
                </div>
                <div class="context-stat-card">
                  <span class="stat-icon">👤</span>
                  <span class="stat-num">{{ contextPreview?.characters.length ?? 0 }}</span>
                  <span class="stat-name">角色</span>
                </div>
                <div class="context-stat-card">
                  <span class="stat-icon">🏛️</span>
                  <span class="stat-num">{{ contextPreview?.organizations.length ?? 0 }}</span>
                  <span class="stat-name">组织</span>
                </div>
                <div class="context-stat-card">
                  <span class="stat-icon">🎭</span>
                  <span class="stat-num">{{ contextPreview?.foreshadowings.length ?? 0 }}</span>
                  <span class="stat-name">伏笔</span>
                </div>
              </div>

              <!-- 角色列表 -->
              <div v-if="contextPreview?.characters.length" class="context-list">
                <div class="context-list-title">👤 参与角色</div>
                <div
                  v-for="item in contextPreview.characters.slice(0, 5)"
                  :key="item.id"
                  class="context-list-item"
                >
                  <span class="item-name">{{ item.name }}</span>
                  <n-tag size="tiny">{{ item.role_type || '未分类' }}</n-tag>
                </div>
              </div>

              <!-- 伏笔列表 -->
              <div v-if="contextPreview?.foreshadowings.length" class="context-list">
                <div class="context-list-title">🎭 相关伏笔</div>
                <div
                  v-for="item in contextPreview.foreshadowings.slice(0, 4)"
                  :key="item.id"
                  class="context-list-item"
                >
                  <span class="item-name">{{ item.keyword }}</span>
                  <n-tag size="tiny" :type="foreshadowTagType(item.status)">
                    {{ item.status }}
                  </n-tag>
                </div>
              </div>

              <!-- 最近摘要 -->
              <div v-if="contextPreview?.recent_summaries.length" class="context-list">
                <div class="context-list-title">📜 最近摘要</div>
                <div
                  v-for="item in contextPreview.recent_summaries.slice(0, 3)"
                  :key="item.id"
                  class="context-summary-item"
                >
                  <strong>摘要 #{{ item.id }}</strong>
                  <p>{{ shortText(item.summary, 40) }}</p>
                </div>
              </div>
            </div>
          </n-tab-pane>

          <!-- Tab: 分析结果 -->
          <n-tab-pane name="analysis" tab="分析">
            <div class="tab-content">
              <!-- 生成后沉淀 -->
              <div class="form-block">
                <div class="block-title">生成后沉淀</div>
                <div v-if="!analysisSections.summary && !analysis" class="empty-analysis">
                  <div class="empty-icon">📊</div>
                  <p>生成并分析后，这里会展示章节摘要、人物变化、伏笔线索等</p>
                </div>
                <div v-else class="analysis-cards">
                  <div class="analysis-card">
                    <div class="card-label">📝 章节摘要</div>
                    <p>{{ analysisSections.summary || '暂无' }}</p>
                  </div>
                  <div class="analysis-card">
                    <div class="card-label">👤 人物变化</div>
                    <p>{{ analysisSections.character_changes || '暂无' }}</p>
                  </div>
                  <div class="analysis-card">
                    <div class="card-label">🌍 世界观变化</div>
                    <p>{{ analysisSections.world_changes || '暂无' }}</p>
                  </div>
                  <div class="analysis-card">
                    <div class="card-label">🎭 新增伏笔</div>
                    <p>{{ analysisSections.new_foreshadowings || '暂无' }}</p>
                  </div>
                  <div class="analysis-card">
                    <div class="card-label">⏱️ 时间线事件</div>
                    <p>{{ analysisSections.timeline_events || '暂无' }}</p>
                  </div>
                </div>
              </div>

              <!-- 一致性检查 -->
              <div class="form-block">
                <div class="block-title">一致性检查</div>
                <div v-if="!consistencyResult" class="empty-consistency">
                  点击「检查一致性」后查看资料缺口和潜在冲突
                </div>
                <div v-else class="consistency-result" :class="consistencyResult.risk_level">
                  <div class="risk-header">
                    <span class="risk-icon">
                      {{ consistencyResult.risk_level === 'low' ? '✅' : consistencyResult.risk_level === 'medium' ? '⚠️' : '❌' }}
                    </span>
                    <span class="risk-label">{{ riskLabel(consistencyResult.risk_level) }}</span>
                  </div>
                  <ul class="suggestion-list">
                    <li v-for="(s, i) in consistencyResult.suggestions" :key="i">{{ s }}</li>
                  </ul>
                </div>
              </div>

              <!-- 长期记忆 -->
              <div class="form-block">
                <div class="block-title">
                  长期记忆
                  <n-tag size="tiny" type="info">{{ summaries.length }} 条</n-tag>
                </div>
                <div v-if="summaries.length === 0" class="empty-memory">
                  暂无章节摘要，分析章节后会自动沉淀
                </div>
                <div v-else class="memory-list">
                  <div v-for="item in summaries.slice(0, 5)" :key="item.id" class="memory-item">
                    <div class="memory-chapter">第 {{ item.chapter_no }} 章 · {{ item.title }}</div>
                    <p>{{ shortText(item.summary) }}</p>
                  </div>
                </div>
              </div>
            </div>
          </n-tab-pane>

          <!-- Tab: 运行轨迹 -->
          <n-tab-pane name="logs" tab="轨迹">
            <div class="tab-content">
              <div class="logs-header">
                <span class="block-title">Agent 运行轨迹</span>
                <n-button size="tiny" @click="loadAgentLogs">刷新</n-button>
              </div>
              <div v-if="visibleEvents.length === 0" class="empty-logs">
                暂无运行记录
              </div>
              <div v-else class="timeline">
                <div
                  v-for="event in visibleEvents"
                  :key="event.id"
                  class="timeline-item"
                  :class="event.status"
                >
                  <div class="timeline-dot"></div>
                  <div class="timeline-content">
                    <div class="timeline-title">{{ event.title }}</div>
                    <div class="timeline-detail">{{ event.detail }}</div>
                    <div class="timeline-time">{{ event.time }}</div>
                  </div>
                </div>
              </div>
            </div>
          </n-tab-pane>
        </n-tabs>
      </aside>
    </div>

    <!-- 精修模式选择弹窗 -->
    <n-modal v-model:show="showPolishModal" preset="card" title="选择精修模式" style="width: 480px">
      <div class="polish-modes">
        <div
          v-for="mode in polishModes"
          :key="mode.value"
          class="polish-mode-card"
          :class="{ selected: selectedPolishMode === mode.value }"
          @click="selectedPolishMode = mode.value"
        >
          <div class="mode-icon">{{ mode.icon }}</div>
          <div class="mode-info">
            <div class="mode-name">{{ mode.name }}</div>
            <div class="mode-desc">{{ mode.desc }}</div>
          </div>
          <div v-if="selectedPolishMode === mode.value" class="mode-check">✓</div>
        </div>
      </div>
      <template #footer>
        <n-button @click="showPolishModal = false">取消</n-button>
        <n-button type="primary" :loading="loading" @click="doPolish">开始精修</n-button>
      </template>
    </n-modal>

    <!-- 重新生成确认弹窗 -->
    <n-modal v-model:show="regenerateConfirmVisible" :mask-closable="!loading">
      <div class="confirm-modal">
        <div class="confirm-icon">⚠️</div>
        <div class="confirm-title">{{ regenerateConfirmTitle }}</div>
        <p class="confirm-text">{{ regenerateConfirmText }}</p>
        <p class="confirm-note">{{ regenerateConfirmNote }}</p>
        <div class="confirm-actions">
          <n-button :disabled="loading" @click="cancelRegenerate">取消</n-button>
          <n-button type="primary" :loading="loading" @click="confirmRegenerate">
            {{ pendingGenerateMode === 'generateAndAnalyze' ? '确认重新生成并分析' : '确认重新生成' }}
          </n-button>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import {
  analyzeChapter,
  checkConsistency,
  draftChapterStream,
  getAgentLogs,
  getChapterSummaries,
  getContextPreview,
  polishChapter,
} from '@/api/agents'
import { createResource, deleteResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import type {
  ChapterItem,
  ChapterSummary,
  CharacterItem,
  ConsistencyCheckResult,
  ContextPreview,
  ForeshadowingItem,
  GenerationLog,
  OrganizationItem,
  OutlineItem,
  WorldSetting,
} from '@/types/domain'

const message = useMessage()
const projectStore = useProjectStore()

// ---- 基础状态 ----
const loading = ref(false)
const keyword = ref('')
const draft = ref('')
const chapterTitle = ref('')
const analysis = ref('')
const activeTab = ref('params')

// ---- 资料数据 ----
const outlines = ref<OutlineItem[]>([])
const chapters = ref<ChapterItem[]>([])
const worlds = ref<WorldSetting[]>([])
const characters = ref<CharacterItem[]>([])
const organizations = ref<OrganizationItem[]>([])
const foreshadowings = ref<ForeshadowingItem[]>([])
const summaries = ref<ChapterSummary[]>([])
const agentLogs = ref<GenerationLog[]>([])
const localEvents = ref<
  Array<{ id: string; title: string; detail: string; time: string; status: string }>
>([])
const contextPreview = ref<ContextPreview | null>(null)
const previewLoading = ref(false)
const chapterId = ref<number | null>(null)
const polishOriginal = ref('')
const regenerateConfirmVisible = ref(false)
const pendingGenerateMode = ref<'generate' | 'generateAndAnalyze' | null>(null)
const consistencyResult = ref<ConsistencyCheckResult | null>(null)

const analysisSections = reactive({
  summary: '',
  character_changes: '',
  world_changes: '',
  new_foreshadowings: '',
  timeline_events: '',
})

// ---- 生成表单 ----
const form = reactive({
  outline_id: null as number | null,
  chapter_id: null as number | null,
  chapter_no: 1,
  rhythm_level: '3 - 适中',
  instruction: '',
})

const rhythmOptions = [
  { label: '1 - 慢热', value: '1 - 慢热' },
  { label: '2 - 平稳', value: '2 - 平稳' },
  { label: '3 - 适中', value: '3 - 适中' },
  { label: '4 - 紧凑', value: '4 - 紧凑' },
  { label: '5 - 高燃', value: '5 - 高燃' },
]

// ---- 精修模式 ----
const showPolishModal = ref(false)
const selectedPolishMode = ref('conflict')
const polishModes = [
  {
    value: 'conflict',
    name: '增强冲突',
    icon: '⚔️',
    desc: '强化戏剧冲突、增加对白张力、提升结尾钩子',
  },
  {
    value: 'emotion',
    name: '情感深化',
    icon: '💖',
    desc: '丰富内心戏、增强角色情感表达和场景氛围',
  },
  {
    value: 'rhythm',
    name: '节奏优化',
    icon: '🎵',
    desc: '调整叙述节奏，让张弛更有度，读起来更流畅',
  },
  {
    value: 'polish',
    name: '文字润色',
    icon: '✨',
    desc: '优化措辞、句式和修辞，提升文笔质感',
  },
]

// ---- 伏笔选项 ----
const foreshadowingOptions = computed(() =>
  foreshadowings.value.map((item) => ({
    label: `${item.keyword}（埋${item.planted_chapter ?? '?'}）`,
    value: item.id,
  }))
)
const selectedForeshadowingIds = ref<number[]>([])

// ---- 计算属性 ----
const project = computed(() => projectStore.currentProject)

const filteredOutlines = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return outlines.value
  return outlines.value.filter((item) =>
    [item.title, item.description].join(' ').toLowerCase().includes(text)
  )
})

const filteredChapters = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return chapters.value
  return chapters.value.filter((item) =>
    [item.title, item.content].join(' ').toLowerCase().includes(text)
  )
})

const selectedOutline = computed(
  () => outlines.value.find((item) => item.id === form.outline_id) ?? null
)
const selectedChapter = computed(
  () => chapters.value.find((item) => item.id === chapterId.value) ?? null
)
const wordCount = computed(() => draft.value.replace(/\s/g, '').length)
const hasExistingDraft = computed(() => Boolean(draft.value.trim()))

const regenerateConfirmTitle = computed(() =>
  pendingGenerateMode.value === 'generateAndAnalyze' ? '确认重新生成并分析？' : '确认重新生成？'
)
const regenerateConfirmText = computed(() =>
  `当前正文区已有 ${wordCount.value} 字，确认清空并重新生成第 ${form.chapter_no} 章？`
)
const regenerateConfirmNote = computed(() => {
  const instruction = form.instruction.trim()
  return instruction
    ? `本次会沿用当前本章目标：${shortText(instruction)}`
    : '当前没有本章目标，建议先选择大纲或填写目标后再重新生成。'
})

const polishSegments = computed(() => {
  const before = splitParagraphs(polishOriginal.value)
  return splitParagraphs(draft.value).map((text, index) => ({
    text,
    status: text.trim() !== (before[index] ?? '').trim() ? 'changed' : 'same',
  }))
})
const hasPolishHighlights = computed(
  () => polishOriginal.value.trim().length > 0 && polishSegments.value.length > 0
)

const contextChecks = computed(() => [
  { label: '已选择大纲', ready: Boolean(form.outline_id) },
  { label: '已有本章目标', ready: Boolean(form.instruction.trim()) },
  { label: '世界观可用', ready: worlds.value.length > 0 },
  { label: '角色资料可用', ready: characters.value.length > 0 },
  { label: '组织/伏笔上下文', ready: organizations.value.length + foreshadowings.value.length > 0 },
  { label: '最近摘要可检索', ready: summaries.value.length > 0 },
  { label: '正文可分析', ready: Boolean(draft.value.trim()) },
])
const contextScore = computed(() => contextChecks.value.filter((item) => item.ready).length)

const visibleEvents = computed(() => {
  const persisted = agentLogs.value.slice(0, 8).map((log) => ({
    id: `log-${log.id}`,
    title: taskTypeLabel(log.task_type),
    detail: log.error || log.response || log.request || '任务已记录',
    time: log.created_at,
    status: log.status === 'success' ? 'success' : 'error',
  }))
  return [...localEvents.value, ...persisted].slice(0, 15)
})

// ---- 工具函数 ----
function shortText(value: string, max = 58) {
  return value?.length > max ? `${value.slice(0, max)}...` : value || '暂无正文'
}

function formatChars(content: string): string {
  const len = content?.replace(/\s/g, '').length || 0
  if (len >= 10000) return (len / 10000).toFixed(1) + '万'
  return len.toString()
}

function splitParagraphs(value: string) {
  return value
    .split(/\n{2,}/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function taskTypeLabel(value: string) {
  const labels: Record<string, string> = {
    chapter_draft: '章节生成',
    chapter_analyze: '章节分析',
    chapter_polish: '章节精修',
    consistency_check: '一致性检查',
  }
  return labels[value] ?? value
}

function riskLabel(value: string) {
  const labels: Record<string, string> = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
  }
  return labels[value] ?? value
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: '草稿',
    confirmed: '已确认',
    published: '已发布',
  }
  return map[status] || status
}

function statusTagType(status: string): 'default' | 'success' | 'info' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'success' | 'info' | 'warning' | 'error'> = {
    draft: 'default',
    confirmed: 'success',
    published: 'info',
  }
  return map[status] || 'default'
}

function foreshadowTagType(status: string): 'default' | 'success' | 'info' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'success' | 'info' | 'warning' | 'error'> = {
    pending: 'warning',
    planted: 'info',
    developing: 'info',
    resolved: 'success',
    abandoned: 'default',
  }
  return map[status] || 'default'
}

// ---- 分析结果处理 ----
function setAnalysisSections(result: Record<string, unknown>) {
  analysisSections.summary = String(result.summary ?? '')
  analysisSections.character_changes = String(result.character_changes ?? '')
  analysisSections.world_changes = String(result.world_changes ?? '')
  analysisSections.new_foreshadowings = String(result.new_foreshadowings ?? '')
  analysisSections.timeline_events = String(result.timeline_events ?? '')
}

function clearAnalysisSections() {
  setAnalysisSections({})
}

// ---- 运行轨迹 ----
function addEvent(title: string, detail: string, status = 'success') {
  localEvents.value.unshift({
    id: `local-${Date.now()}-${localEvents.value.length}`,
    title,
    detail,
    status,
    time: new Date().toLocaleTimeString(),
  })
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : '未知错误'
}

// ---- 项目相关 ----
async function ensureProject() {
  if (!projectStore.currentProject) await projectStore.loadDefaultProject()
  return projectStore.currentProject?.id
}

// ---- 数据加载 ----
async function loadAgentLogs() {
  const projectId = await ensureProject()
  if (!projectId) return
  agentLogs.value = await getAgentLogs(projectId, 20)
}

async function loadResources() {
  const projectId = projectStore.currentProject!.id
  const [
    outlineList,
    chapterList,
    worldList,
    characterList,
    organizationList,
    foreshadowingList,
    summaryList,
    logList,
  ] = await Promise.all([
    listResource<OutlineItem>(projectId, 'outlines'),
    listResource<ChapterItem>(projectId, 'chapters'),
    listResource<WorldSetting>(projectId, 'world'),
    listResource<CharacterItem>(projectId, 'characters'),
    listResource<OrganizationItem>(projectId, 'organizations'),
    listResource<ForeshadowingItem>(projectId, 'foreshadowings'),
    getChapterSummaries(projectId, 20),
    getAgentLogs(projectId, 20),
  ])
  outlines.value = outlineList
  chapters.value = chapterList
  worlds.value = worldList
  characters.value = characterList
  organizations.value = organizationList
  foreshadowings.value = foreshadowingList
  summaries.value = summaryList
  agentLogs.value = logList
  addEvent('读取资料', `大纲 ${outlineList.length}，角色 ${characterList.length}，摘要 ${summaryList.length}`)
  hydrateInstructionFromSelection()
  ensureActiveOutline()
  await refreshContextPreview({ silent: true })
}

async function refreshContextPreview(options: { silent?: boolean } = {}) {
  const projectId = await ensureProject()
  if (!projectId) return

  previewLoading.value = true
  try {
    contextPreview.value = await getContextPreview(projectId, form.chapter_no, form.outline_id)
    if (!options.silent)
      addEvent(
        '拼装上下文',
        `角色 ${contextPreview.value.characters.length}，组织 ${contextPreview.value.organizations.length}，伏笔 ${contextPreview.value.foreshadowings.length}`
      )
  } catch (error) {
    if (!options.silent) {
      addEvent('上下文预览失败', errorMessage(error), 'error')
      message.error('上下文预览失败')
    }
  } finally {
    previewLoading.value = false
  }
}

// ---- 生成相关 ----
function requestGenerate(mode: 'generate' | 'generateAndAnalyze') {
  if (loading.value) return
  hydrateInstructionFromSelection()
  ensureActiveOutline()
  if (!hasGenerationGoal()) {
    message.warning('请先选择大纲或填写本章目标')
    addEvent('生成拦截', '缺少大纲或本章目标，已取消生成', 'error')
    return
  }
  if (hasExistingDraft.value) {
    pendingGenerateMode.value = mode
    regenerateConfirmVisible.value = true
    return
  }
  void runGenerateMode(mode)
}

async function runGenerateMode(mode: 'generate' | 'generateAndAnalyze') {
  if (mode === 'generateAndAnalyze') {
    await generateAndAnalyze()
    return
  }
  await generate()
}

function cancelRegenerate() {
  pendingGenerateMode.value = null
  regenerateConfirmVisible.value = false
}

async function confirmRegenerate() {
  const mode = pendingGenerateMode.value
  pendingGenerateMode.value = null
  regenerateConfirmVisible.value = false
  if (!mode) return
  hydrateInstructionFromSelection()
  ensureActiveOutline()
  await runGenerateMode(mode)
}

function findOutlineForChapter(item: ChapterItem) {
  return (
    outlines.value.find((outline) => outline.id === item.outline_id) ??
    outlines.value.find((outline) => outline.chapter_no === item.chapter_no) ??
    null
  )
}

function hydrateInstructionFromSelection() {
  const currentChapter = selectedChapter.value
  if (!currentChapter) return

  const relatedOutline = findOutlineForChapter(currentChapter)
  if (relatedOutline) {
    form.outline_id = relatedOutline.id
    if (!form.instruction.trim() || form.instruction === currentChapter.title) {
      form.instruction = relatedOutline.description
    }
  } else if (!form.instruction.trim()) {
    form.instruction = currentChapter.title
  }
}

function applyOutlineToForm(item: OutlineItem, options: { forceInstruction?: boolean } = {}) {
  form.outline_id = item.id
  form.chapter_no = item.chapter_no ?? item.sort_index
  if (options.forceInstruction || !form.instruction.trim()) {
    form.instruction = item.description
  }
}

function ensureActiveOutline() {
  if (form.outline_id && outlines.value.some((item) => item.id === form.outline_id)) return
  if (selectedChapter.value) return

  const firstOutline = outlines.value[0]
  if (!firstOutline) return
  applyOutlineToForm(firstOutline)
}

function hasGenerationGoal() {
  return Boolean(form.outline_id || form.instruction.trim())
}

function selectOutline(item: OutlineItem) {
  applyOutlineToForm(item, { forceInstruction: true })
  addEvent('选择大纲', `${item.title} 已进入生成上下文`)
  void refreshContextPreview({ silent: true })
}

function selectChapter(item: ChapterItem) {
  const relatedOutline = findOutlineForChapter(item)
  chapterId.value = item.id
  form.chapter_id = item.id
  form.outline_id = relatedOutline?.id ?? item.outline_id
  form.chapter_no = item.chapter_no
  form.instruction = relatedOutline?.description || form.instruction || item.title
  draft.value = item.content
  chapterTitle.value = item.title
  analysis.value = ''
  polishOriginal.value = ''
  consistencyResult.value = null
  addEvent(
    '载入章节',
    relatedOutline ? `${item.title} 已载入，并恢复章纲目标` : `${item.title} 已进入正文编辑区`
  )
  void refreshContextPreview({ silent: true })
}

// ---- 生成章节 ----
async function generate(options: { showToast?: boolean } = {}) {
  const { showToast = true } = options
  if (loading.value) return false

  const projectId = await ensureProject()
  if (!projectId) return false

  loading.value = true
  hydrateInstructionFromSelection()
  ensureActiveOutline()
  if (!hasGenerationGoal()) {
    loading.value = false
    message.warning('请先选择大纲或填写本章目标')
    addEvent('生成拦截', '缺少大纲或本章目标，已取消生成', 'error')
    return false
  }
  await refreshContextPreview()
  const previousDraft = draft.value
  const previousAnalysis = analysis.value
  const previousPolishOriginal = polishOriginal.value
  addEvent('生成启动', `第 ${form.chapter_no} 章，节奏 ${form.rhythm_level}`, 'running')
  draft.value = ''
  analysis.value = ''
  polishOriginal.value = ''
  consistencyResult.value = null
  clearAnalysisSections()
  try {
    const result = await draftChapterStream(
      {
        project_id: projectId,
        outline_id: form.outline_id,
        chapter_id: form.chapter_id,
        chapter_no: form.chapter_no,
        instruction: form.instruction,
        rhythm_level: form.rhythm_level,
      },
      {
        onStart: (detail, startedChapterId) => {
          if (startedChapterId) {
            chapterId.value = startedChapterId
            form.chapter_id = startedChapterId
          }
          addEvent('流式生成', detail, 'running')
        },
        onDelta: (content) => {
          draft.value += content
        },
        onError: (detail) => addEvent('生成中断', detail, 'error'),
      }
    )
    if (!result) throw new Error('流式生成未返回完成事件')
    chapterId.value = result.chapter_id
    form.chapter_id = result.chapter_id
    // 自动生成标题
    if (!chapterTitle.value) {
      chapterTitle.value = `第${form.chapter_no}章`
    }
    addEvent('保存章节', `章节 ID ${result.chapter_id} 已写入草稿库`)
    await loadResources()
    addEvent('生成完成', result.source === 'llm' ? '真实模型已返回正文' : result.source, 'success')
    if (showToast) message.success(result.source === 'llm' ? '章节已生成' : '已生成开发模式草稿')
    // 生成完成后自动切到分析 Tab
    activeTab.value = 'analysis'
    return true
  } catch (error) {
    if (!draft.value.trim()) draft.value = previousDraft
    analysis.value = previousAnalysis
    polishOriginal.value = previousPolishOriginal
    addEvent('生成失败', errorMessage(error), 'error')
    message.error(draft.value.trim() ? '生成中断，已保留当前输出' : '章节生成失败')
    return false
  } finally {
    loading.value = false
  }
}

async function generateAndAnalyze() {
  const generated = await generate({ showToast: false })
  if (generated) {
    const analyzed = await analyze({ showToast: false })
    message.success(analyzed ? '章节已生成并分析完成' : '章节已生成，分析未完成')
  }
}

// ---- 保存章节 ----
async function saveCurrentChapter() {
  const projectId = await ensureProject()
  if (!projectId) return

  const payload = {
    project_id: projectId,
    outline_id: form.outline_id,
    chapter_no: form.chapter_no,
    title: chapterTitle.value || `第${form.chapter_no}章`,
    content: draft.value,
    status: 'draft',
  }

  if (chapterId.value) {
    await updateResource<ChapterItem>('chapters', chapterId.value, payload)
    addEvent('保存章节', `章节 ID ${chapterId.value} 已更新`)
    message.success('章节草稿已更新')
  } else {
    const created = await createResource<ChapterItem>('chapters', payload)
    chapterId.value = created.id
    form.chapter_id = created.id
    addEvent('保存章节', `新章节 ID ${created.id} 已创建`)
    message.success('章节草稿已保存')
  }
  await loadResources()
}

// ---- 分析章节 ----
async function analyze(options: { showToast?: boolean } = {}) {
  const { showToast = true } = options
  if (!chapterId.value || !projectStore.currentProject) {
    message.warning('请先生成或保存章节后再分析')
    return false
  }
  addEvent('分析启动', `章节 ID ${chapterId.value} 正在沉淀摘要`, 'running')
  activeTab.value = 'analysis'
  try {
    const result = await analyzeChapter({
      project_id: projectStore.currentProject.id,
      chapter_id: chapterId.value,
      content: draft.value,
    })
    analysis.value = result.analysis
    setAnalysisSections(result)
    await loadAgentLogs()
    await loadResources()
    addEvent('分析完成', '摘要、人物变化、伏笔线索已生成')
    if (showToast) message.success('章节分析已完成')
    return true
  } catch (error) {
    addEvent('分析失败', errorMessage(error), 'error')
    message.error('章节分析失败')
    return false
  }
}

// ---- 一致性检查 ----
async function runConsistencyCheck() {
  if (!projectStore.currentProject) {
    message.warning('请先加载项目')
    return
  }
  addEvent('一致性检查', '正在核对大纲、世界观、角色、组织和伏笔', 'running')
  activeTab.value = 'analysis'
  try {
    consistencyResult.value = await checkConsistency({
      project_id: projectStore.currentProject.id,
      chapter_id: chapterId.value,
      content: draft.value,
    })
    await loadAgentLogs()
    addEvent(
      '检查完成',
      `${riskLabel(consistencyResult.value.risk_level)}，${consistencyResult.value.suggestions[0]}`
    )
    message.success('一致性检查完成')
  } catch (error) {
    addEvent('检查失败', errorMessage(error), 'error')
    message.error('一致性检查失败')
  }
}

// ---- 精修 ----
function openPolishMenu() {
  if (!chapterId.value || !projectStore.currentProject) {
    message.warning('请先生成或保存章节后再精修')
    return
  }
  showPolishModal.value = true
}

async function doPolish() {
  if (!chapterId.value || !projectStore.currentProject) return
  const mode = polishModes.find((m) => m.value === selectedPolishMode.value)
  if (!mode) return

  showPolishModal.value = false
  addEvent('精修启动', `模式：${mode.name}`, 'running')
  try {
    const beforePolish = draft.value
    const result = await polishChapter({
      project_id: projectStore.currentProject.id,
      chapter_id: chapterId.value,
      mode: mode.name,
      instruction: mode.desc,
    })
    polishOriginal.value = beforePolish
    draft.value = result.content
    await loadResources()
    addEvent('精修完成', '正文已覆盖为精修版本，变化段落已高亮')
    message.success('章节已精修')
  } catch (error) {
    addEvent('精修失败', errorMessage(error), 'error')
    message.error('章节精修失败')
  }
}

// ---- 删除章节 ----
async function removeChapter(id: number) {
  await deleteResource('chapters', id)
  if (chapterId.value === id) {
    chapterId.value = null
    form.chapter_id = null
    draft.value = ''
    chapterTitle.value = ''
    analysis.value = ''
    polishOriginal.value = ''
    consistencyResult.value = null
    clearAnalysisSections()
  }
  addEvent('删除章节', `章节 ID ${id} 已删除`)
  message.success('章节已删除')
  await loadResources()
}

// ---- 初始化 ----
useProjectDataLoader(loadResources)
</script>

<style scoped>
.chapter-generate-page {
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

.header-stats .stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 50px;
}

.header-stats .stat-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--n-color-primary, #3b82f6);
  line-height: 1.2;
}

.header-stats .stat-num.success {
  color: #10b981;
}

.header-stats .stat-label {
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 2px;
}

.header-stats .stat-divider {
  width: 1px;
  height: 24px;
  background: var(--n-border-color, #2a2f3a);
}

/* ===== 三栏工作台 ===== */
.workbench {
  flex: 1;
  display: grid;
  grid-template-columns: 260px 1fr 360px;
  gap: 12px;
  min-height: 0;
}

/* ===== 左侧面板 ===== */
.left-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-search {
  padding: 12px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
}

.context-brief-card {
  margin: 12px;
  padding: 10px 12px;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.brief-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.brief-label {
  color: var(--n-text-color-3, #6b7280);
  flex-shrink: 0;
  width: 60px;
}

.brief-value {
  flex: 1;
  color: var(--n-text-color-1, #e5e7eb);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.list-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
}

.list-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
}

.section-label {
  color: var(--n-text-color-2, #9ca3af);
}

.list-scroll {
  flex: 1;
  min-height: 0;
  padding: 0 8px 8px;
}

.list-empty {
  text-align: center;
  color: var(--n-text-color-3, #6b7280);
  font-size: 12px;
  padding: 30px 10px;
}

.queue-item {
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.15s;
  border: 1px solid transparent;
}

.queue-item:hover {
  background: var(--n-color-hover, #23272f);
}

.queue-item.active {
  background: var(--n-color-primary-1-suppl, #1e3a5f);
  border-color: var(--n-color-primary-3, #3b82f6);
}

.item-main {
  min-width: 0;
}

.item-title {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.item-meta {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 6px;
}

.chapter-no-badge {
  color: var(--n-color-primary, #3b82f6);
  font-weight: 600;
}

/* ===== 中间编辑器 ===== */
.editor-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.toolbar-left {
  flex: 1;
  min-width: 0;
}

.title-input {
  font-size: 16px;
  font-weight: 600;
}

.title-input :deep(input) {
  font-size: 16px !important;
  font-weight: 600 !important;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.word-count {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.count-num {
  font-size: 18px;
  font-weight: 700;
  color: var(--n-color-primary, #3b82f6);
}

.count-label {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

.save-status {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

.save-status.saved {
  color: #10b981;
}

.chapter-id {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
}

.editor-container {
  flex: 1;
  min-height: 0;
  padding: 16px;
  overflow: hidden;
}

.chapter-textarea {
  height: 100%;
}

.chapter-textarea :deep(textarea) {
  min-height: 100% !important;
  height: 100% !important;
  line-height: 1.9;
  font-size: 15px;
  padding: 16px !important;
}

/* 精修对比面板 */
.polish-panel {
  border-top: 1px solid var(--n-border-color, #2a2f3a);
  max-height: 200px;
  overflow-y: auto;
  flex-shrink: 0;
}

.polish-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  background: var(--n-color-1, #1e2228);
}

.polish-title {
  font-size: 13px;
  font-weight: 600;
  flex: 1;
}

.polish-content {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.polish-segment {
  margin: 0;
  padding: 8px 10px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 6px;
  line-height: 1.7;
  white-space: pre-wrap;
  background: var(--n-color-1, #1e2228);
  font-size: 13px;
}

.polish-segment.changed {
  border-color: rgba(242, 201, 125, 0.5);
  color: #fff7db;
  background: rgba(242, 201, 125, 0.1);
}

/* ===== 右侧面板 ===== */
.right-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.side-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.side-tabs :deep(.n-tabs-nav) {
  padding: 0 8px;
  flex-shrink: 0;
}

.side-tabs :deep(.n-tabs-tab) {
  padding: 10px 14px;
  font-size: 13px;
}

.side-tabs :deep(.n-tabs-panels) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.side-tabs :deep(.n-tabs-panel) {
  height: 100%;
  overflow-y: auto;
  padding: 0 !important;
}

.tab-content {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.block-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-hint {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 6px;
  line-height: 1.5;
}

.form-row {
  display: flex;
  gap: 10px;
}

/* 生成按钮组 */
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.secondary-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.secondary-actions > :nth-child(5),
.secondary-actions > :nth-child(6) {
  grid-column: span 2;
}

/* 上下文预检 */
.score-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--n-color-2, #2a2f3a);
  color: var(--n-text-color-2, #9ca3af);
  font-weight: 500;
}

.score-badge.good {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.check-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 6px;
  background: var(--n-color-1, #1e2228);
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
}

.check-item.ready {
  border-color: rgba(16, 185, 129, 0.3);
  color: #6ee7b7;
  background: rgba(16, 185, 129, 0.08);
}

.check-icon {
  font-size: 12px;
  width: 14px;
  text-align: center;
}

.check-label {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ===== 上下文 Tab ===== */
.context-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.context-outline {
  margin-bottom: 4px;
}

.context-label {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  margin-bottom: 6px;
}

.outline-card {
  padding: 10px 12px;
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.08);
}

.outline-card strong {
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
}

.outline-card p {
  margin: 0;
  font-size: 12px;
  color: var(--n-text-color-2, #9ca3af);
  line-height: 1.6;
}

.empty-context {
  padding: 12px;
  text-align: center;
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  background: var(--n-color-1, #1e2228);
  border-radius: 6px;
}

.context-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.context-stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 6px;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  gap: 4px;
}

.stat-icon {
  font-size: 18px;
}

.stat-num {
  font-size: 16px;
  font-weight: 700;
}

.stat-name {
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
}

.context-list {
  margin-top: 4px;
}

.context-list-title {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  margin-bottom: 8px;
}

.context-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: var(--n-color-1, #1e2228);
  border-radius: 6px;
  margin-bottom: 4px;
  font-size: 12px;
}

.context-summary-item {
  padding: 8px 10px;
  background: var(--n-color-1, #1e2228);
  border-radius: 6px;
  margin-bottom: 6px;
}

.context-summary-item strong {
  font-size: 12px;
  display: block;
  margin-bottom: 4px;
}

.context-summary-item p {
  margin: 0;
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  line-height: 1.5;
}

/* ===== 分析 Tab ===== */
.empty-analysis,
.empty-consistency,
.empty-memory,
.empty-logs {
  padding: 24px 16px;
  text-align: center;
  color: var(--n-text-color-3, #6b7280);
  font-size: 12px;
  background: var(--n-color-1, #1e2228);
  border-radius: 8px;
}

.empty-icon {
  font-size: 28px;
  margin-bottom: 8px;
}

.analysis-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.analysis-card {
  padding: 10px 12px;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.card-label {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--n-text-color-2, #9ca3af);
}

.analysis-card p {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--n-text-color-1, #e5e7eb);
}

.consistency-result {
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  background: var(--n-color-1, #1e2228);
}

.consistency-result.low {
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.05);
}

.consistency-result.medium {
  border-color: rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.05);
}

.consistency-result.high {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.05);
}

.risk-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  margin-bottom: 10px;
  font-size: 14px;
}

.risk-icon {
  font-size: 18px;
}

.suggestion-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.8;
  color: var(--n-text-color-2, #9ca3af);
}

.memory-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.memory-item {
  padding: 8px 10px;
  background: var(--n-color-1, #1e2228);
  border-radius: 6px;
}

.memory-chapter {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
}

.memory-item p {
  margin: 0;
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  line-height: 1.5;
}

/* ===== 运行轨迹 ===== */
.logs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.timeline-item {
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr);
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  background: var(--n-color-1, #1e2228);
}

.timeline-dot {
  width: 10px;
  height: 10px;
  margin-top: 5px;
  border-radius: 50%;
  background: #64748b;
}

.timeline-item.success .timeline-dot {
  background: #10b981;
}

.timeline-item.running .timeline-dot {
  background: #f59e0b;
  animation: pulse 1.5s ease-in-out infinite;
}

.timeline-item.error .timeline-dot {
  background: #ef4444;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.timeline-content {
  min-width: 0;
}

.timeline-title {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 3px;
}

.timeline-detail {
  font-size: 11px;
  color: var(--n-text-color-2, #9ca3af);
  line-height: 1.5;
  word-break: break-all;
}

.timeline-time {
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 3px;
}

/* ===== 精修模式弹窗 ===== */
.polish-modes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.polish-mode-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  background: var(--n-color-1, #1e2228);
}

.polish-mode-card:hover {
  border-color: var(--n-color-primary-3, #3b82f6);
}

.polish-mode-card.selected {
  border-color: var(--n-color-primary, #3b82f6);
  background: rgba(59, 130, 246, 0.1);
}

.mode-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.mode-info {
  flex: 1;
  min-width: 0;
}

.mode-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 2px;
}

.mode-desc {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

.mode-check {
  color: var(--n-color-primary, #3b82f6);
  font-weight: bold;
  font-size: 16px;
}

/* ===== 重新生成确认弹窗 ===== */
.confirm-modal {
  width: min(480px, calc(100vw - 40px));
  padding: 24px;
  border-radius: 12px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  text-align: center;
}

.confirm-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.confirm-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 10px;
}

.confirm-text {
  margin: 0 0 8px 0;
  line-height: 1.6;
  color: var(--n-text-color-1, #e5e7eb);
}

.confirm-note {
  margin: 0;
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  line-height: 1.6;
}

.confirm-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 20px;
}

/* ===== 响应式 ===== */
@media (max-width: 1400px) {
  .workbench {
    grid-template-columns: 240px 1fr 320px;
  }
}
</style>
