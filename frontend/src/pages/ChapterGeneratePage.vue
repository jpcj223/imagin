<template>
  <div class="page page-wide">
    <div class="page-title">
      <div>
        <h1>✨ 章节生成控制台</h1>
        <p class="muted">左侧选资料，中间写正文，右侧看 Agent 运行状态。</p>
      </div>
      <div class="title-actions">
        <n-button @click="loadResources">刷新资料</n-button>
        <n-button type="primary" :loading="loading" :disabled="loading" @click="requestGenerate('generateAndAnalyze')">
          {{ hasExistingDraft ? '重新生成并分析' : '生成并分析' }}
        </n-button>
      </div>
    </div>

    <div class="triple-workbench">
      <aside class="list-panel">
        <div class="panel-head">
          <h2>创作队列</h2>
          <span class="muted">{{ filteredOutlines.length }} 个大纲 / {{ filteredChapters.length }} 章</span>
        </div>
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索大纲或章节"/>
          <div class="context-brief">
            <div class="brief-row">
              <span>当前大纲</span>
              <strong>{{ selectedOutline?.title || '未选择' }}</strong>
            </div>
            <div class="brief-row">
              <span>当前章节</span>
              <strong>{{ selectedChapter?.title || `第${form.chapter_no}章` }}</strong>
            </div>
          </div>
        </div>

        <div class="queue-section">
          <div class="queue-title">大纲</div>
          <div class="list-body compact">
            <n-empty v-if="filteredOutlines.length === 0" description="暂无大纲"/>
            <template v-else>
              <button
                  v-for="item in filteredOutlines"
                  :key="item.id"
                  class="list-item"
                  :class="{ active: form.outline_id === item.id }"
                  @click="selectOutline(item)"
              >
                <div class="item-title">
                  <span>{{ item.title }}</span>
                  <span class="muted">#{{ item.chapter_no ?? item.sort_index }}</span>
                </div>
                <div class="item-meta">{{ item.description || '暂无章节目标' }}</div>
              </button>
            </template>
          </div>
        </div>

        <div class="queue-section">
          <div class="queue-title">章节草稿</div>
          <div class="list-body compact">
            <n-empty v-if="filteredChapters.length === 0" description="暂无章节草稿"/>
            <template v-else>
              <button
                  v-for="item in filteredChapters"
                  :key="item.id"
                  class="list-item"
                  :class="{ active: chapterId === item.id }"
                  @click="selectChapter(item)"
              >
                <div class="item-title">
                  <span>{{ item.title }}</span>
                  <span class="muted">第 {{ item.chapter_no }} 章</span>
                </div>
                <div class="item-meta">{{ shortText(item.content) }}</div>
              </button>
            </template>
          </div>
        </div>
      </aside>

      <section class="editor-panel">
        <div class="panel-head">
          <h2>正文编辑</h2>
          <div class="editor-stats">
            <span>{{ wordCount }} 字</span>
            <span>{{ chapterId ? `章节 ID ${chapterId}` : '未保存草稿' }}</span>
          </div>
        </div>
        <n-input v-model:value="draft" type="textarea" class="chapter-editor" :autosize="{ minRows: 31 }"
                 placeholder="生成或粘贴章节正文..."/>
        <div v-if="hasPolishHighlights" class="polish-highlight-panel">
          <div class="panel-head inline-head">
            <h2>精修高亮</h2>
            <span class="muted">高亮段落为精修后发生变化的内容</span>
          </div>
          <div class="polish-preview">
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

      <aside class="side-panel">
        <div class="panel-head">
          <h2>生成参数</h2>
          <span class="muted">Agent</span>
        </div>

        <n-form label-placement="top">
          <n-form-item label="章节号">
            <n-input-number v-model:value="form.chapter_no" :min="1"/>
          </n-form-item>
          <n-form-item label="节奏等级">
            <n-select v-model:value="form.rhythm_level" :options="rhythmOptions"/>
          </n-form-item>
          <n-form-item label="本章目标">
            <n-input v-model:value="form.instruction" type="textarea" :autosize="{ minRows: 5 }"
                     placeholder="选择大纲后会自动带入，也可以手动修改。"/>
          </n-form-item>
        </n-form>

        <div class="context-check">
          <div class="panel-head inline-head">
            <h2>上下文预检</h2>
            <span class="muted">{{ contextScore }}/{{ contextChecks.length }}</span>
          </div>
          <div class="check-list">
            <div v-for="item in contextChecks" :key="item.label" class="check-row" :class="{ ready: item.ready }">
              <span>{{ item.ready ? '✓' : '·' }}</span>
              <span>{{ item.label }}</span>
            </div>
          </div>
        </div>

        <div class="analysis-panel">
          <div class="panel-head inline-head">
            <h2>上下文包预览</h2>
            <n-button size="tiny" :loading="previewLoading" @click="refreshContextPreview">刷新</n-button>
          </div>
          <div class="preview-card">
            <strong>{{ contextPreview?.outline.title || '暂无大纲' }}</strong>
            <p>{{ contextPreview?.outline.description || '选择大纲后可查看本次生成目标。' }}</p>
          </div>
          <div class="preview-grid">
            <div class="preview-cell">
              <span>世界观</span>
              <strong>{{ contextPreview?.world.title || '0' }}</strong>
            </div>
            <div class="preview-cell">
              <span>角色</span>
              <strong>{{ contextPreview?.characters.length ?? 0 }}</strong>
            </div>
            <div class="preview-cell">
              <span>组织</span>
              <strong>{{ contextPreview?.organizations.length ?? 0 }}</strong>
            </div>
            <div class="preview-cell">
              <span>伏笔</span>
              <strong>{{ contextPreview?.foreshadowings.length ?? 0 }}</strong>
            </div>
          </div>
          <div class="mini-preview-list">
            <div v-for="item in previewLines" :key="item" class="item-meta">{{ item }}</div>
          </div>
        </div>

        <div class="detail-actions vertical-actions">
          <n-button :loading="loading" :disabled="loading" type="primary" block @click="requestGenerate('generate')">
            {{ hasExistingDraft ? '重新生成章节' : '开始生成章节' }}
          </n-button>

          <n-button :loading="loading" :disabled="loading" block @click="requestGenerate('generateAndAnalyze')">
            {{ hasExistingDraft ? '重新生成并分析' : '生成并分析' }}
          </n-button>
          <n-button :disabled="!draft" block @click="saveCurrentChapter">保存当前章节</n-button>
          <n-button :disabled="!draft" block @click="analyze">分析当前章节</n-button>
          <n-button :disabled="!draft" block @click="polish">精修当前章节</n-button>
          <n-button :disabled="!draft" block @click="runConsistencyCheck">检查一致性</n-button>
          <n-popconfirm v-if="chapterId" positive-text="确认删除" negative-text="取消"
                        @positive-click="removeChapter(chapterId)">
            <template #trigger>
              <n-button type="error" block>删除当前章节</n-button>
            </template>
            确认删除当前章节草稿？
          </n-popconfirm>
        </div>

        <div class="analysis-panel">
          <div class="panel-head inline-head">
            <h2>生成后沉淀</h2>
          </div>
          <div class="memory-grid">
            <div v-for="item in analysisCards" :key="item.label" class="memory-card">
              <strong>{{ item.label }}</strong>
              <p>{{ item.value || '暂无' }}</p>
            </div>
          </div>
          <pre class="analysis">{{ analysis || '暂无完整分析文本' }}</pre>
        </div>

        <div class="analysis-panel">
          <div class="panel-head inline-head">
            <h2>一致性检查</h2>
          </div>
          <div class="memory-card">
            <strong>{{ consistencyResult ? riskLabel(consistencyResult.risk_level) : '尚未检查' }}</strong>
            <p>{{ consistencyResult ? consistencyResult.suggestions.join('；') : '点击“检查一致性”后查看资料缺口。' }}</p>
          </div>
        </div>

        <div class="analysis-panel">
          <div class="panel-head inline-head">
            <h2>长期记忆</h2>
            <span class="muted">{{ summaries.length }} 条</span>
          </div>
          <div class="summary-list">
            <div v-for="item in summaries.slice(0, 5)" :key="item.id" class="summary-item">
              <strong>第 {{ item.chapter_no }} 章 · {{ item.title }}</strong>
              <p>{{ shortText(item.summary) }}</p>
            </div>
            <n-empty v-if="summaries.length === 0" size="small" description="暂无章节摘要"/>
          </div>
        </div>

        <div class="run-panel">
          <div class="panel-head inline-head">
            <h2>运行轨迹</h2>
            <n-button size="tiny" @click="loadAgentLogs">刷新</n-button>
          </div>
          <div class="timeline">
            <div v-for="event in visibleEvents" :key="event.id" class="timeline-item" :class="event.status">
              <div class="timeline-dot"></div>
              <div>
                <div class="timeline-title">{{ event.title }}</div>
                <div class="item-meta">{{ event.detail }}</div>
                <div class="item-meta">{{ event.time }}</div>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <n-modal v-model:show="regenerateConfirmVisible" :mask-closable="!loading">
      <div class="confirm-modal">
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
import {computed, onMounted, reactive, ref} from 'vue'
import {useMessage} from 'naive-ui'
import {
  analyzeChapter,
  checkConsistency,
  draftChapterStream,
  getAgentLogs,
  getChapterSummaries,
  getContextPreview,
  polishChapter
} from '@/api/agents'
import {createResource, deleteResource, listResource, updateResource} from '@/api/resources'
import {useProjectStore} from '@/stores/project'
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
  WorldSetting
} from '@/types/domain'

const message = useMessage()
const projectStore = useProjectStore()
const loading = ref(false)
const keyword = ref('')
const draft = ref('')
const analysis = ref('')
const outlines = ref<OutlineItem[]>([])
const chapters = ref<ChapterItem[]>([])
const worlds = ref<WorldSetting[]>([])
const characters = ref<CharacterItem[]>([])
const organizations = ref<OrganizationItem[]>([])
const foreshadowings = ref<ForeshadowingItem[]>([])
const summaries = ref<ChapterSummary[]>([])
const agentLogs = ref<GenerationLog[]>([])
const localEvents = ref<Array<{ id: string; title: string; detail: string; time: string; status: string }>>([])
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
  timeline_events: ''
})

const form = reactive({
  outline_id: null as number | null,
  chapter_id: null as number | null,
  chapter_no: 1,
  rhythm_level: '3 - 适中',
  instruction: ''
})

const rhythmOptions = [
  {label: '1 - 慢热', value: '1 - 慢热'},
  {label: '2 - 平稳', value: '2 - 平稳'},
  {label: '3 - 适中', value: '3 - 适中'},
  {label: '4 - 紧凑', value: '4 - 紧凑'},
  {label: '5 - 高燃', value: '5 - 高燃'}
]

const filteredOutlines = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return outlines.value
  return outlines.value.filter((item) => [item.title, item.description].join(' ').toLowerCase().includes(text))
})

const filteredChapters = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return chapters.value
  return chapters.value.filter((item) => [item.title, item.content].join(' ').toLowerCase().includes(text))
})

const selectedOutline = computed(() => outlines.value.find((item) => item.id === form.outline_id) ?? null)
const selectedChapter = computed(() => chapters.value.find((item) => item.id === chapterId.value) ?? null)
const wordCount = computed(() => draft.value.replace(/\s/g, '').length)
const hasExistingDraft = computed(() => Boolean(draft.value.trim()))
const regenerateConfirmTitle = computed(() => (pendingGenerateMode.value === 'generateAndAnalyze' ? '确认重新生成并分析？' : '确认重新生成？'))
const regenerateConfirmText = computed(() => `当前正文区已有 ${wordCount.value} 字，确认清空并重新生成第 ${form.chapter_no} 章？`)
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
    status: text.trim() !== (before[index] ?? '').trim() ? 'changed' : 'same'
  }))
})
const hasPolishHighlights = computed(() => polishOriginal.value.trim().length > 0 && polishSegments.value.length > 0)
const analysisCards = computed(() => [
  {label: '章节摘要', value: analysisSections.summary},
  {label: '人物变化', value: analysisSections.character_changes},
  {label: '世界观变化', value: analysisSections.world_changes},
  {label: '新增伏笔', value: analysisSections.new_foreshadowings},
  {label: '时间线事件', value: analysisSections.timeline_events}
])

const contextChecks = computed(() => [
  {label: '已选择大纲', ready: Boolean(form.outline_id)},
  {label: '已有本章目标', ready: Boolean(form.instruction.trim())},
  {label: '世界观可用', ready: worlds.value.length > 0},
  {label: '角色资料可用', ready: characters.value.length > 0},
  {label: '组织/伏笔上下文', ready: organizations.value.length + foreshadowings.value.length > 0},
  {label: '最近摘要可检索', ready: summaries.value.length > 0},
  {label: '正文可分析', ready: Boolean(draft.value.trim())}
])
const contextScore = computed(() => contextChecks.value.filter((item) => item.ready).length)

const previewLines = computed(() => {
  if (!contextPreview.value) return ['暂无上下文包，点击刷新后查看。']
  const preview = contextPreview.value
  const lines = [
    ...preview.characters.slice(0, 3).map((item) => `角色：${item.name} · ${item.role_type || '未分类'}`),
    ...preview.organizations.slice(0, 2).map((item) => `组织：${item.name} · 目标 ${shortText(item.goal, 18)}`),
    ...preview.foreshadowings.slice(0, 2).map((item) => `伏笔：${item.keyword} · ${item.status}`),
    ...preview.recent_summaries.slice(0, 2).map((item) => `摘要：${shortText(item.summary, 26)}`)
  ]
  return lines.length > 0 ? lines : ['上下文包为空，建议先补充设定资料。']
})

const visibleEvents = computed(() => {
  const persisted = agentLogs.value.slice(0, 8).map((log) => ({
    id: `log-${log.id}`,
    title: taskTypeLabel(log.task_type),
    detail: log.error || log.response || log.request || '任务已记录',
    time: log.created_at,
    status: log.status === 'success' ? 'success' : 'error'
  }))
  return [...localEvents.value, ...persisted].slice(0, 12)
})

function shortText(value: string, max = 58) {
  return value?.length > max ? `${value.slice(0, max)}...` : value || '暂无正文'
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
    consistency_check: '一致性检查'
  }
  return labels[value] ?? value
}

function riskLabel(value: string) {
  const labels: Record<string, string> = {
    low: '低风险',
    medium: '中风险',
    high: '高风险'
  }
  return labels[value] ?? value
}

function setAnalysisSections(result: Record<string, unknown>) {
  // 后端分析会同时返回完整文本和拆分小节，拆分结果用于右侧“生成后沉淀”卡片。
  analysisSections.summary = String(result.summary ?? '')
  analysisSections.character_changes = String(result.character_changes ?? '')
  analysisSections.world_changes = String(result.world_changes ?? '')
  analysisSections.new_foreshadowings = String(result.new_foreshadowings ?? '')
  analysisSections.timeline_events = String(result.timeline_events ?? '')
}

function clearAnalysisSections() {
  setAnalysisSections({})
}

function addEvent(title: string, detail: string, status = 'success') {
  // 本地运行轨迹用于即时反馈；后端日志刷新后会补充真实持久化记录。
  localEvents.value.unshift({
    id: `local-${Date.now()}-${localEvents.value.length}`,
    title,
    detail,
    status,
    time: new Date().toLocaleTimeString()
  })
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : '未知错误'
}

async function ensureProject() {
  if (!projectStore.currentProject) await projectStore.loadDefaultProject()
  return projectStore.currentProject?.id
}

async function loadAgentLogs() {
  const projectId = await ensureProject()
  if (!projectId) return
  agentLogs.value = await getAgentLogs(projectId, 20)
}

async function loadResources() {
  const projectId = await ensureProject()
  if (!projectId) return
  // 章节 Agent 预检需要同时看大纲、正文草稿、资料库、伏笔和长期摘要。
  const [outlineList, chapterList, worldList, characterList, organizationList, foreshadowingList, summaryList, logList] = await Promise.all([
    listResource<OutlineItem>(projectId, 'outlines'),
    listResource<ChapterItem>(projectId, 'chapters'),
    listResource<WorldSetting>(projectId, 'world'),
    listResource<CharacterItem>(projectId, 'characters'),
    listResource<OrganizationItem>(projectId, 'organizations'),
    listResource<ForeshadowingItem>(projectId, 'foreshadowings'),
    getChapterSummaries(projectId, 20),
    getAgentLogs(projectId, 20)
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
  await refreshContextPreview({silent: true})
}

async function refreshContextPreview(options: { silent?: boolean } = {}) {
  const projectId = await ensureProject()
  if (!projectId) return

  previewLoading.value = true
  try {
    // 上下文预览与真实生成共用同一批资料来源，让用户能在生成前看到 Agent 的“工作包”。
    contextPreview.value = await getContextPreview(projectId, form.chapter_no, form.outline_id)
    if (!options.silent) addEvent('拼装上下文', `角色 ${contextPreview.value.characters.length}，组织 ${contextPreview.value.organizations.length}，伏笔 ${contextPreview.value.foreshadowings.length}`)
  } catch (error) {
    if (!options.silent) {
      addEvent('上下文预览失败', errorMessage(error), 'error')
      message.error('上下文预览失败')
    }
  } finally {
    previewLoading.value = false
  }
}

function requestGenerate(mode: 'generate' | 'generateAndAnalyze') {
  // 重新生成是破坏性操作：有正文时先进入自控弹窗，确认按钮会明确回到对应生成流程。
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
  // 章节可能有关联大纲，也可能只有章节号；两种情况都尝试找回本章目标。
  return (
      outlines.value.find((outline) => outline.id === item.outline_id) ??
      outlines.value.find((outline) => outline.chapter_no === item.chapter_no) ??
      null
  )
}

function hydrateInstructionFromSelection() {
  // 重新生成依赖明确的本章目标；当用户只点选章节时，也要把关联章纲补回参数区。
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
  // 大纲进入生成参数时只负责同步“目标”和“章节号”，正文是否覆盖由章节选择逻辑决定。
  form.outline_id = item.id
  form.chapter_no = item.chapter_no ?? item.sort_index
  if (options.forceInstruction || !form.instruction.trim()) {
    form.instruction = item.description
  }
}

function ensureActiveOutline() {
  // 视频里的问题就是“看起来有大纲，实际 form 没选中”；这里把首个可用大纲水合成真实生成上下文。
  if (form.outline_id && outlines.value.some((item) => item.id === form.outline_id)) return
  if (selectedChapter.value) return

  const firstOutline = outlines.value[0]
  if (!firstOutline) return
  applyOutlineToForm(firstOutline)
}

function hasGenerationGoal() {
  // 防止空目标生成把已有章节覆盖成“暂无要求”的草稿。
  return Boolean(form.outline_id || form.instruction.trim())
}

function selectOutline(item: OutlineItem) {
  // 选择大纲只改变生成参数，不覆盖中间正文，方便用户用同一正文参考不同章纲。
  applyOutlineToForm(item, {forceInstruction: true})
  addEvent('选择大纲', `${item.title} 已进入生成上下文`)
  void refreshContextPreview({silent: true})
}

function selectChapter(item: ChapterItem) {
  // 选择章节会载入正文并同步生成参数，后续保存会更新这条章节。
  const relatedOutline = findOutlineForChapter(item)
  chapterId.value = item.id
  form.chapter_id = item.id
  form.outline_id = relatedOutline?.id ?? item.outline_id
  form.chapter_no = item.chapter_no
  form.instruction = relatedOutline?.description || form.instruction || item.title
  draft.value = item.content
  analysis.value = ''
  polishOriginal.value = ''
  addEvent('载入章节', relatedOutline ? `${item.title} 已载入，并恢复章纲目标` : `${item.title} 已进入正文编辑区`)
  void refreshContextPreview({silent: true})
}

async function generate(options: { showToast?: boolean } = {}) {
  const {showToast = true} = options
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
    // 稳定版流式生成：delta 直接写入正文，done 后再刷新章节列表；中途失败时保留已输出内容。
    const result = await draftChapterStream(
        {
          project_id: projectId,
          outline_id: form.outline_id,
          chapter_id: form.chapter_id,
          chapter_no: form.chapter_no,
          instruction: form.instruction,
          rhythm_level: form.rhythm_level
        },
        {
          onStart: (detail, startedChapterId) => {
            // 后端在开始流式输出时已经创建草稿；提前记录 ID，关闭标签后也能在章节草稿中找回。
            if (startedChapterId) {
              chapterId.value = startedChapterId
              form.chapter_id = startedChapterId
            }
            addEvent('流式生成', detail, 'running')
          },
          onDelta: (content) => {
            draft.value += content
          },
          onError: (detail) => addEvent('生成中断', detail, 'error')
        }
    )
    if (!result) throw new Error('流式生成未返回完成事件')
    chapterId.value = result.chapter_id
    form.chapter_id = result.chapter_id
    addEvent('保存章节', `章节 ID ${result.chapter_id} 已写入草稿库`)
    await loadResources()
    addEvent('生成完成', result.source === 'llm' ? '真实模型已返回正文' : result.source, 'success')
    if (showToast) message.success(result.source === 'llm' ? '章节已生成' : '已生成开发模式草稿')
    return true
  } catch (error) {
    // 已经输出的正文不回滚，方便用户保存半截结果；完全没输出时才恢复旧正文。
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
  // 一键流程串联生成和分析，让用户能看到 agent 从产出到沉淀的完整闭环。
  const generated = await generate({showToast: false})
  if (generated) {
    const analyzed = await analyze({showToast: false})
    message.success(analyzed ? '章节已生成并分析完成' : '章节已生成，分析未完成')
  }
}

async function saveCurrentChapter() {
  const projectId = await ensureProject()
  if (!projectId) return

  const payload = {
    project_id: projectId,
    outline_id: form.outline_id,
    chapter_no: form.chapter_no,
    title: `第${form.chapter_no}章`,
    content: draft.value,
    status: 'draft'
  }

  // 保存流程以 chapterId 为准：有 ID 更新，无 ID 创建，成功后刷新左侧章节列表。
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

async function analyze(options: { showToast?: boolean } = {}) {
  const {showToast = true} = options
  if (!chapterId.value || !projectStore.currentProject) {
    message.warning('请先生成或保存章节后再分析')
    return false
  }
  addEvent('分析启动', `章节 ID ${chapterId.value} 正在沉淀摘要`, 'running')
  try {
    const result = await analyzeChapter({
      project_id: projectStore.currentProject.id,
      chapter_id: chapterId.value,
      content: draft.value
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

async function runConsistencyCheck() {
  if (!projectStore.currentProject) {
    message.warning('请先加载项目')
    return
  }
  addEvent('一致性检查', '正在核对大纲、世界观、角色、组织和伏笔', 'running')
  try {
    consistencyResult.value = await checkConsistency({
      project_id: projectStore.currentProject.id,
      chapter_id: chapterId.value,
      content: draft.value
    })
    await loadAgentLogs()
    addEvent('检查完成', `${riskLabel(consistencyResult.value.risk_level)}，${consistencyResult.value.suggestions[0]}`)
    message.success('一致性检查完成')
  } catch (error) {
    addEvent('检查失败', errorMessage(error), 'error')
    message.error('一致性检查失败')
  }
}

async function polish() {
  if (!chapterId.value || !projectStore.currentProject) {
    message.warning('请先生成或保存章节后再精修')
    return
  }
  addEvent('精修启动', '模式：增强冲突', 'running')
  try {
    const beforePolish = draft.value
    const result = await polishChapter({
      project_id: projectStore.currentProject.id,
      chapter_id: chapterId.value,
      mode: '增强冲突',
      instruction: '保持原剧情事实，增强对白与章节结尾钩子'
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

async function removeChapter(id: number) {
  await deleteResource('chapters', id)
  if (chapterId.value === id) {
    chapterId.value = null
    form.chapter_id = null
    draft.value = ''
    analysis.value = ''
    polishOriginal.value = ''
    consistencyResult.value = null
    clearAnalysisSections()
  }
  addEvent('删除章节', `章节 ID ${id} 已删除`)
  message.success('章节已删除')
  await loadResources()
}

onMounted(loadResources)
</script>

<style scoped>
.title-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.context-brief {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid #31363c;
  border-radius: 6px;
  background: #181b1f;
}

.brief-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 8px;
  color: #9ca3af;
  font-size: 12px;
}

.brief-row strong {
  overflow: hidden;
  color: #e5e7eb;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-section {
  border-top: 1px solid #32363c;
}

.queue-title {
  padding: 10px 14px 0;
  color: #cbd5e1;
  font-weight: 700;
}

.compact {
  max-height: 260px;
}

.editor-stats {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #9ca3af;
  font-size: 12px;
}

.chapter-editor :deep(textarea) {
  min-height: calc(100vh - 205px) !important;
  line-height: 1.8;
}

.polish-highlight-panel {
  margin-top: 14px;
  border-top: 1px solid #34383d;
}

.polish-preview {
  display: grid;
  gap: 10px;
}

.polish-segment {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid #30343a;
  border-radius: 6px;
  color: #cbd5e1;
  line-height: 1.8;
  white-space: pre-wrap;
  background: #181b1f;
}

.polish-segment.changed {
  border-color: rgba(242, 201, 125, 0.55);
  color: #fff7db;
  background: rgba(242, 201, 125, 0.12);
}

.context-check,
.analysis-panel,
.run-panel {
  margin-top: 18px;
  border-top: 1px solid #34383d;
}

.inline-head {
  padding-left: 0;
  padding-right: 0;
}

.check-list {
  display: grid;
  gap: 8px;
}

.check-row {
  display: grid;
  grid-template-columns: 18px 1fr;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid #30343a;
  border-radius: 6px;
  color: #9ca3af;
  background: #181b1f;
}

.check-row.ready {
  border-color: rgba(99, 226, 183, 0.35);
  color: #d1fae5;
}

.vertical-actions {
  display: grid;
  align-items: stretch;
}

.analysis {
  min-height: 120px;
  margin: 0;
  padding: 12px;
  white-space: pre-wrap;
  color: #d1d5db;
  background: #151719;
  border-radius: 6px;
}

.preview-card {
  padding: 12px;
  border: 1px solid rgba(79, 140, 255, 0.35);
  border-radius: 6px;
  background: rgba(79, 140, 255, 0.1);
}

.preview-card strong {
  display: block;
  margin-bottom: 6px;
  color: #e5e7eb;
}

.preview-card p {
  margin: 0;
  color: #aab4c3;
  line-height: 1.6;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 10px 0;
}

.preview-cell {
  min-width: 0;
  padding: 8px;
  border: 1px solid #30343a;
  border-radius: 6px;
  background: #181b1f;
}

.preview-cell span {
  display: block;
  color: #9ca3af;
  font-size: 12px;
}

.preview-cell strong {
  display: block;
  overflow: hidden;
  margin-top: 4px;
  color: #f8fafc;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mini-preview-list {
  display: grid;
  gap: 6px;
}

.memory-grid,
.summary-list {
  display: grid;
  gap: 10px;
  margin-bottom: 10px;
}

.memory-card,
.summary-item {
  padding: 10px;
  border: 1px solid #30343a;
  border-radius: 6px;
  background: #181b1f;
}

.memory-card strong,
.summary-item strong {
  display: block;
  margin-bottom: 6px;
  color: #e5e7eb;
}

.memory-card p,
.summary-item p {
  margin: 0;
  color: #9ca3af;
  line-height: 1.6;
}

.timeline {
  display: grid;
  gap: 10px;
}

.timeline-item {
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr);
  gap: 10px;
  padding: 10px;
  border: 1px solid #30343a;
  border-radius: 6px;
  background: #181b1f;
}

.timeline-dot {
  width: 10px;
  height: 10px;
  margin-top: 5px;
  border-radius: 50%;
  background: #64748b;
}

.timeline-item.success .timeline-dot {
  background: #63e2b7;
}

.timeline-item.running .timeline-dot {
  background: #f2c97d;
}

.timeline-item.error .timeline-dot {
  background: #e88080;
}

.timeline-title {
  margin-bottom: 4px;
  color: #e5e7eb;
  font-weight: 700;
}

.confirm-modal {
  width: min(520px, calc(100vw - 40px));
  padding: 22px;
  border: 1px solid #3a4048;
  border-radius: 8px;
  color: #e5e7eb;
  background: #1d2025;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
}

.confirm-title {
  margin-bottom: 10px;
  font-size: 20px;
  font-weight: 800;
}

.confirm-text {
  margin: 0;
  color: #f8fafc;
  line-height: 1.7;
}

.confirm-note {
  margin: 8px 0 0;
  color: #9ca3af;
  line-height: 1.7;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
</style>
