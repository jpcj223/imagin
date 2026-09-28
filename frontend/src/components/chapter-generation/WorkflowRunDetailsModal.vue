<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { WorkflowRunRecord, WorkflowStepRecord } from '@/api/agentsV3'
import type { StepInfo } from '@/components/WorkflowProgress.vue'

const props = defineProps<{
  visible: boolean
  runId: string | null
  runDetail: { run: WorkflowRunRecord; steps: WorkflowStepRecord[] } | null
  steps: StepInfo[]
  currentStepId: string | null
  progress: number
  clock: number
}>()

const emit = defineEmits<{ (event: 'update:visible', visible: boolean): void }>()
const selectedStepId = ref('')

type ModelPricingSnapshot = {
  input_price_per_million?: number | null
  output_price_per_million?: number | null
  cached_input_price_per_million?: number | null
  cached_input_uses_input_price?: boolean
}

function pricingForStep(step: { effectiveSettings?: Record<string, any> }): ModelPricingSnapshot | undefined {
  return step.effectiveSettings?.model?.pricing as ModelPricingSnapshot | undefined
}

function hasCompletePricing(pricing?: ModelPricingSnapshot) {
  return typeof pricing?.input_price_per_million === 'number'
    && typeof pricing.output_price_per_million === 'number'
}

function hasTokenUsage(usage?: WorkflowStepRecord['token_usage']) {
  return Boolean(usage && [usage.input_tokens, usage.output_tokens, usage.total_tokens].some(value => typeof value === 'number'))
}

const mergedSteps = computed(() => {
  const liveStepIds = new Set(props.steps.map(step => step.id))
  const backgroundAnalyzerRecord = [...(props.runDetail?.steps ?? [])]
    .reverse()
    .find(record => record.step_id === 'background_analyzer')
  const backgroundAnalyzerRecords = backgroundAnalyzerRecord && !liveStepIds.has(backgroundAnalyzerRecord.step_id)
    ? [{
        id: backgroundAnalyzerRecord.step_id,
        label: backgroundAnalyzerRecord.step_name || '后台分析沉淀',
        icon: '🔍',
        status: backgroundAnalyzerRecord.status,
        durationMs: backgroundAnalyzerRecord.duration_ms ?? undefined,
        tokenUsage: backgroundAnalyzerRecord.token_usage,
        llmCalls: backgroundAnalyzerRecord.llm_calls,
        outputSummary: String(backgroundAnalyzerRecord.output_snapshot?.summary ?? ''),
        contextSummary: backgroundAnalyzerRecord.input_snapshot?.context_summary as Record<string, unknown> | undefined,
        effectiveSettings: backgroundAnalyzerRecord.input_snapshot?.effective_settings as Record<string, unknown> | undefined,
        errorMessage: backgroundAnalyzerRecord.error_message ?? undefined,
        outputSnapshot: backgroundAnalyzerRecord.output_snapshot ?? {},
      }]
    : []
  return [...props.steps, ...backgroundAnalyzerRecords].map((liveStep) => {
    const record = [...(props.runDetail?.steps ?? [])].reverse().find(item => item.step_id === liveStep.id)
    const input = record?.input_snapshot
    const output = record?.output_snapshot ?? {}
    const contextSummary = input?.context_summary ?? liveStep.contextSummary
    const effectiveSettings = input?.effective_settings ?? liveStep.effectiveSettings
    const tokenUsage = hasTokenUsage(record?.token_usage) ? record?.token_usage : liveStep.tokenUsage
    const llmCalls = record?.llm_calls || liveStep.llmCalls || 0
    const durationMs = record?.duration_ms ?? liveStep.durationMs
    const outputContent = liveStep.id === 'planner'
      ? String(output.content ?? liveStep.outputContent ?? '')
      : liveStep.id === 'writer'
        ? String(output.writing_plan ?? '')
        : ''
    const outputSummary = liveStep.id === 'analyzer' || liveStep.id === 'background_analyzer'
      ? String(output.summary ?? liveStep.outputSummary ?? '')
      : liveStep.outputSummary
    return {
      ...liveStep,
      status: record?.status ?? liveStep.status,
      errorMessage: record?.error_message ?? liveStep.errorMessage,
      contextSummary,
      effectiveSettings,
      tokenUsage,
      llmCalls,
      durationMs,
      outputContent,
      outputSummary,
      outputSnapshot: output,
    }
  })
})

watch(mergedSteps, (items) => {
  if (!items.some(item => item.id === selectedStepId.value)) {
    selectedStepId.value = props.currentStepId
      || items.find(item => item.status === 'running')?.id
      || items.find(item => item.status === 'completed')?.id
      || items[0]?.id
      || ''
  }
}, { immediate: true })

const selectedStep = computed(() => mergedSteps.value.find(item => item.id === selectedStepId.value) ?? null)
const usage = computed(() => {
  const attempts = props.runDetail?.steps ?? []
  const latestRecords = new Map<string, WorkflowStepRecord>()
  for (const attempt of attempts) latestRecords.set(attempt.step_id, attempt)
  let input = 0
  let output = 0
  let total = 0
  let requests = 0
  let elapsed = 0
  let measuredAttempts = 0
  let estimatedCost = 0
  let pricedAttempts = 0
  const addTokenUsage = (tokenUsage?: WorkflowStepRecord['token_usage']) => {
    if (!hasTokenUsage(tokenUsage)) return
    input += tokenUsage?.input_tokens ?? 0
    output += tokenUsage?.output_tokens ?? 0
    total += tokenUsage?.total_tokens ?? (tokenUsage?.input_tokens ?? 0) + (tokenUsage?.output_tokens ?? 0)
    measuredAttempts += 1
    if (typeof tokenUsage?.cost_cny === 'number') {
      estimatedCost += tokenUsage.cost_cny
      pricedAttempts += 1
    }
  }
  for (const attempt of attempts) {
    addTokenUsage(attempt.token_usage)
    requests += attempt.llm_calls ?? 0
    elapsed += attempt.duration_ms ?? 0
  }
  // 详情刷新前刚结束的步骤先使用 SSE 数值；已有持久化数据时不重复相加。
  for (const liveStep of props.steps) {
    const latest = latestRecords.get(liveStep.id)
    if (!hasTokenUsage(latest?.token_usage) && hasTokenUsage(liveStep.tokenUsage ?? undefined)) {
      addTokenUsage(liveStep.tokenUsage ?? undefined)
    }
    if (!latest?.llm_calls) requests += liveStep.llmCalls ?? 0
    if (latest?.duration_ms == null) {
      elapsed += liveStep.durationMs ?? (liveStep.startedAt ? props.clock - liveStep.startedAt : 0)
    }
  }
  const pricingSnapshots = mergedSteps.value
    .map(pricingForStep)
    .filter((pricing): pricing is ModelPricingSnapshot => Boolean(pricing))
  const hasPriceSnapshot = pricingSnapshots.length > 0
  const hasAnyPrice = pricingSnapshots.some((pricing) =>
    typeof pricing.input_price_per_million === 'number'
      || typeof pricing.output_price_per_million === 'number',
  )
  const hasCompletePrice = pricingSnapshots.some(hasCompletePricing)
  const isRunning = props.runDetail?.run.status === 'running'
    || mergedSteps.value.some((step) => step.status === 'running')
  const costLabel = pricedAttempts
    ? `${formatCurrency(estimatedCost)}${pricedAttempts < measuredAttempts ? ' *' : ''}`
    : !hasPriceSnapshot
      ? requests ? '无价格快照' : '—'
      : !hasAnyPrice
        ? '未配置单价'
        : !hasCompletePrice
          ? '单价未配全'
          : isRunning
            ? '等待用量'
            : measuredAttempts === 0
              ? '未返回用量'
              : '无法估算'
  const costNote = pricedAttempts
    ? '费用按调用时单价和服务商返回的 Token 用量估算；带 * 表示部分尝试缺少用量或单价。'
    : !hasPriceSnapshot
      ? '本次运行没有单价快照；新运行会记录当前模型配置。'
      : !hasAnyPrice
        ? '本次运行已保存模型配置，但当时没有填写输入和输出单价。'
        : !hasCompletePrice
          ? '输入和输出单价需要同时配置，才能估算费用。'
          : isRunning
            ? '单价已记录，等待模型返回 Token 用量后计算费用。'
            : '服务商未返回 Token 用量，暂时无法估算费用。'
  return {
    input,
    output,
    total,
    requests,
    elapsed,
    measuredAttempts,
    estimatedCost,
    pricedAttempts,
    costLabel,
    costNote,
    attempts: attempts.length || props.steps.filter(step => step.status !== 'pending').length,
  }
})

const contextSummary = computed(() => selectedStep.value?.contextSummary as Record<string, unknown> | undefined)
const outlineSegments = computed(() => (contextSummary.value?.outline_segments ?? []) as Array<{ label: string; title: string; chapter_no?: number | null; summary?: string }>)
const sources = computed(() => (contextSummary.value?.sources ?? []) as Array<{ category: string; name: string; id?: number | null; source: string; summary?: string }>)
const projectSettings = computed(() => contextSummary.value?.project_settings as Record<string, string | number | null> | undefined)
const settings = computed(() => selectedStep.value?.effectiveSettings as Record<string, any> | undefined)
const modelSettings = computed(() => settings.value?.model as Record<string, any> | undefined)
const modelConfigLabel = computed(() => {
  if (settings.value?.model_called === false) return '本地结果，未调用模型'
  if (!modelSettings.value?.configured) return '无有效模型配置'
  return `${modelSettings.value.config_name || '当前配置'} · ${modelSettings.value.model || '模型未命名'}`
})

function formatNumber(value?: number | null) {
  return typeof value === 'number' ? new Intl.NumberFormat('zh-CN').format(value) : '—'
}

function formatCurrency(value?: number | null) {
  if (typeof value !== 'number') return '未配置'
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency', currency: 'CNY', minimumFractionDigits: 4, maximumFractionDigits: 6,
  }).format(value)
}

function stepCostLabel(step: NonNullable<typeof selectedStep.value>) {
  const tokenUsage = step.tokenUsage
  if (typeof tokenUsage?.cost_cny === 'number') return `费用约 ${formatCurrency(tokenUsage.cost_cny)}`
  const pricing = pricingForStep(step)
  if (!pricing) return '费用未估（无价格快照）'
  if (!hasCompletePricing(pricing)) return '费用未估（单价未配全）'
  if (hasTokenUsage(tokenUsage)) return '费用未估（服务商未返回单价用量）'
  return step.status === 'running' ? '单价已配置，等待用量' : '服务商未返回 Token 用量'
}

function formatPrice(value?: number | null) {
  return typeof value === 'number' ? `¥${value}/百万 Token` : '未配置'
}

function formatCachedInputPrice(pricing?: ModelPricingSnapshot) {
  if (typeof pricing?.cached_input_price_per_million === 'number') {
    return formatPrice(pricing.cached_input_price_per_million)
  }
  return pricing?.cached_input_uses_input_price ? '按输入单价' : '未配置'
}

function formatDuration(value?: number | null) {
  if (typeof value !== 'number' || value <= 0) return '进行中'
  const seconds = Math.floor(value / 1000)
  if (seconds < 60) return `${seconds} 秒`
  return `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
}

function contentForStep(step: NonNullable<typeof selectedStep.value>) {
  if (step.id === 'planner') return step.outputContent
  if (step.id === 'writer') return step.outputContent ? `本章剧情节拍（与正文同次请求）\n${step.outputContent}` : ''
  if (step.id === 'analyzer' || step.id === 'background_analyzer') {
    const output = step.outputSnapshot as Record<string, unknown>
    return String(output.analysis_text ?? step.outputSummary ?? '')
  }
  return ''
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '等待中', running: '执行中', completed: '已完成', failed: '失败', paused: '已中断', skipped: '已跳过',
  }
  return labels[status] ?? status
}

function agentLabel(value: string) {
  const labels: Record<string, string> = { planner: '规划师', writer: '写作师', polisher: '精修师', analyzer: '分析师' }
  return labels[value] ?? value
}

function variantLabel(value: string) {
  const labels: Record<string, string> = {
    default: '默认', shuangwen: '爽文', wenqing: '文青', fast: '极速', detailed: '详细', deep: '深度', quick: '快速',
  }
  return labels[value] ?? value
}
</script>

<template>
  <n-modal :show="visible" @update:show="emit('update:visible', $event)">
    <section class="run-detail-modal" role="dialog" aria-modal="true" aria-label="本次章节生成详情">
      <header class="modal-header">
        <div>
          <div class="modal-kicker">章节生成记录</div>
          <h2>本次规划、资料与消耗</h2>
          <p>{{ runId ? `运行 ID：${runId}` : '生成任务已启动，正在收集本次记录' }}</p>
        </div>
        <button class="close-button" type="button" aria-label="关闭详情" @click="emit('update:visible', false)">×</button>
      </header>

      <div class="usage-grid">
        <article><strong>{{ Math.round(progress) }}%</strong><span>流程进度</span></article>
        <article><strong>{{ formatNumber(usage.requests) }}</strong><span>模型请求</span></article>
        <article><strong>{{ formatNumber(usage.input) }}</strong><span>输入 Token</span></article>
        <article><strong>{{ formatNumber(usage.output) }}</strong><span>输出 Token</span></article>
        <article><strong>{{ formatNumber(usage.total) }}</strong><span>合计 Token</span></article>
        <article><strong>{{ usage.costLabel }}</strong><span>估算费用</span></article>
        <article><strong>{{ formatDuration(usage.elapsed) }}</strong><span>步骤耗时</span></article>
      </div>
      <p class="usage-note">
        汇总包含本次运行的全部步骤尝试和重跑；{{ usage.attempts ? `${usage.measuredAttempts}/${usage.attempts} 次尝试已返回 Token。` : '' }}{{ usage.costNote }}缓存输入单价未填时按输入单价估算；服务商未返回缓存 Token 数时按普通输入计价。
      </p>

      <div class="step-layout">
        <nav class="step-nav" aria-label="生成步骤">
          <button
            v-for="step in mergedSteps"
            :key="step.id"
            type="button"
            :class="{ selected: selectedStepId === step.id }"
            @click="selectedStepId = step.id"
          >
            <span class="step-state" :class="step.status"></span>
            <span class="step-name">{{ step.label }}</span>
            <span class="step-status">{{ statusLabel(step.status) }}</span>
          </button>
        </nav>

        <main v-if="selectedStep" class="step-detail">
          <div class="detail-title-row">
            <div><h3>{{ selectedStep.label }}</h3><span>{{ formatDuration(selectedStep.durationMs) }} · {{ selectedStep.llmCalls || 0 }} 次模型请求 · {{ stepCostLabel(selectedStep) }}</span></div>
            <span class="status-pill" :class="selectedStep.status">{{ statusLabel(selectedStep.status) }}</span>
          </div>

          <section v-if="selectedStep.id === 'planner' || selectedStep.id === 'analyzer' || selectedStep.id === 'background_analyzer'" class="detail-section">
            <h4>{{ selectedStep.id === 'planner' ? '创作规划与判断摘要' : '章节分析结果' }}</h4>
            <p class="section-hint">这是 Agent 实际生成并传给后续步骤的规划/分析结果，不展示模型内部推理过程。</p>
            <pre v-if="contentForStep(selectedStep)" class="generated-content">{{ contentForStep(selectedStep) }}</pre>
            <p v-else class="empty-state">该步骤尚未返回内容。</p>
          </section>
          <section v-else class="detail-section">
            <h4>步骤结果</h4>
            <p class="result-summary">{{ selectedStep.outputSummary || (selectedStep.status === 'running' ? '正在执行，完成后会补齐结果与用量。' : '正文可在中央编辑区查看。') }}</p>
          </section>

          <section class="detail-section">
            <h4>实际装入上下文的资料</h4>
            <p class="section-hint">清单来自本步骤保存的上下文快照；展示装入模型输入的资料，不代表模型对每项资料的注意力权重。</p>
            <div v-if="outlineSegments.length" class="outline-list">
              <div v-for="item in outlineSegments" :key="`${item.label}-${item.title}`" class="outline-item">
                <span>{{ item.label }}</span>
                <div><strong>{{ item.title }}</strong><p v-if="item.summary">{{ item.summary }}</p></div>
              </div>
            </div>
            <div v-if="projectSettings && Object.values(projectSettings).some(Boolean)" class="project-settings-row">
              <span>项目写作设定</span>
              <strong>{{ [projectSettings.novel_type, projectSettings.writing_style, projectSettings.view_point, projectSettings.pace_level ? `节奏 ${projectSettings.pace_level}` : ''].filter(Boolean).join(' · ') }}</strong>
            </div>
            <div v-if="sources.length" class="source-list">
              <article v-for="(item, index) in sources" :key="`${item.category}-${item.id ?? item.name}-${index}`" class="source-item">
                <div class="source-heading"><span class="source-category">{{ item.category }}</span><strong>{{ item.name }}</strong><span class="source-origin">{{ item.source }}</span></div>
                <p v-if="item.summary">{{ item.summary }}</p>
              </article>
            </div>
            <p v-if="!outlineSegments.length && !sources.length" class="empty-state">本次没有保存上下文清单（可能是较早的运行记录）。</p>
          </section>

          <section class="detail-section">
            <h4>本步骤实际生效的配置</h4>
            <div v-if="settings" class="settings-grid">
              <div><span>Agent / 变体</span><strong>{{ agentLabel(settings.agent_type || '') }} / {{ variantLabel(settings.variant || '') }}</strong></div>
              <div><span>节奏等级</span><strong>{{ settings.rhythm_level || '模型默认' }}</strong></div>
              <div v-if="settings.target_word_count"><span>目标字数</span><strong>{{ formatNumber(settings.target_word_count) }} 字</strong></div>
              <div><span>模型配置</span><strong>{{ modelConfigLabel }}</strong></div>
              <div v-if="modelSettings?.configured"><span>采样参数</span><strong>温度 {{ modelSettings.temperature ?? '默认' }} · Top P {{ modelSettings.top_p ?? '默认' }}</strong></div>
              <div v-if="modelSettings?.configured"><span>最大输出</span><strong>{{ formatNumber(modelSettings.max_tokens) }} Token</strong></div>
              <div v-if="modelSettings?.configured"><span>频率 / 存在惩罚</span><strong>{{ modelSettings.frequency_penalty ?? '默认' }} / {{ modelSettings.presence_penalty ?? '默认' }}</strong></div>
              <div v-if="modelSettings?.pricing" class="wide-setting"><span>调用时单价（元/百万 Token）</span><strong>输入 {{ formatPrice(modelSettings.pricing.input_price_per_million) }} · 输出 {{ formatPrice(modelSettings.pricing.output_price_per_million) }} · 缓存输入 {{ formatCachedInputPrice(modelSettings.pricing) }}</strong></div>
              <div v-if="settings.agent_skills?.length" class="wide-setting"><span>Agent 已装配技能</span><div class="tag-list"><em v-for="skill in settings.agent_skills" :key="skill">{{ skill }}</em></div></div>
              <div v-if="settings.generation_skills?.length" class="wide-setting"><span>本次写作重点</span><div class="tag-list"><em v-for="skill in settings.generation_skills" :key="skill">{{ skill }}</em></div></div>
              <p v-if="settings.model_called === false" class="wide-setting setting-note">此步骤使用本地兜底结果，没有调用模型。</p>
            </div>
            <p v-else class="empty-state">本次设置尚未记录（可能是较早的运行记录）。</p>
          </section>
        </main>
      </div>
    </section>
  </n-modal>
</template>

<style scoped>
.run-detail-modal {
  --bg-primary: #0f1629;
  --bg-secondary: #182234;
  --bg-card: #1b2639;
  --border: rgba(148, 163, 184, .18);
  --text-primary: #e5e7eb;
  --text-secondary: #a5b0c2;
  --text-muted: #77849a;
  --accent-primary: #7168f5;
  width: min(1040px, calc(100vw - 36px));
  max-height: min(900px, calc(100vh - 36px));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: var(--text-primary);
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, .52);
}

.modal-header { display: flex; justify-content: space-between; align-items: flex-start; padding: 22px 24px 16px; border-bottom: 1px solid var(--border); }
.modal-kicker { color: #9b92ff; font-size: 12px; font-weight: 700; letter-spacing: .06em; }
.modal-header h2 { margin: 5px 0 4px; font-size: 20px; }
.modal-header p { margin: 0; color: var(--text-muted); font-size: 12px; }
.close-button { width: 32px; height: 32px; border: 1px solid var(--border); border-radius: 8px; color: var(--text-secondary); background: var(--bg-secondary); font-size: 22px; cursor: pointer; }
.usage-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 8px; padding: 14px 24px 0; }
.usage-grid article { min-width: 0; display: grid; gap: 3px; padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px; background: var(--bg-secondary); }
.usage-grid strong { overflow: hidden; color: #9b92ff; font-size: 18px; text-overflow: ellipsis; white-space: nowrap; }
.usage-grid span { color: var(--text-muted); font-size: 11px; }
.usage-note { margin: 8px 24px 14px; color: var(--text-muted); font-size: 11px; line-height: 1.5; }
.step-layout { min-height: 0; display: grid; grid-template-columns: 190px minmax(0, 1fr); flex: 1; border-top: 1px solid var(--border); }
.step-nav { display: flex; flex-direction: column; gap: 6px; padding: 14px 10px 16px 18px; overflow: auto; border-right: 1px solid var(--border); }
.step-nav button { display: grid; grid-template-columns: 9px minmax(0, 1fr); gap: 0 9px; align-items: center; padding: 10px; text-align: left; border: 1px solid transparent; border-radius: 9px; color: var(--text-primary); background: transparent; cursor: pointer; }
.step-nav button.selected { background: rgba(113, 104, 245, .13); border-color: rgba(113, 104, 245, .38); }
.step-state { grid-row: span 2; width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); }
.step-state.completed { background: #18b887; }.step-state.running { background: #6d72ff; box-shadow: 0 0 10px #6d72ff; }.step-state.failed { background: #ed6a77; }.step-state.paused { background: #e5a64b; }
.step-name { font-size: 13px; font-weight: 600; }.step-status { margin-top: 3px; color: var(--text-muted); font-size: 11px; }
.step-detail { min-height: 0; overflow: auto; padding: 18px 22px 22px; }
.detail-title-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.detail-title-row h3 { margin: 0 0 4px; font-size: 17px; }.detail-title-row span { color: var(--text-muted); font-size: 11px; }
.status-pill { padding: 4px 9px; border: 1px solid var(--border); border-radius: 99px; background: var(--bg-secondary); }.status-pill.completed { color: #35d5a4; }.status-pill.running { color: #a5a2ff; }.status-pill.failed { color: #ff8791; }
.detail-section { margin-top: 14px; padding: 14px; border: 1px solid var(--border); border-radius: 12px; background: var(--bg-secondary); }
.detail-section h4 { margin: 0 0 8px; font-size: 13px; }.section-hint { margin: 0 0 10px; color: var(--text-muted); font-size: 11px; line-height: 1.55; }
.generated-content { max-height: 280px; overflow: auto; margin: 0; padding: 12px; white-space: pre-wrap; overflow-wrap: anywhere; border-radius: 8px; color: var(--text-primary); background: rgba(9, 15, 27, .55); font: inherit; font-size: 12px; line-height: 1.75; }
.result-summary { margin: 0; color: var(--text-secondary); font-size: 12px; line-height: 1.65; }.empty-state { margin: 0; color: var(--text-muted); font-size: 12px; }
.outline-list { display: grid; gap: 6px; margin-bottom: 10px; }.outline-item { display: grid; grid-template-columns: 112px minmax(0, 1fr); gap: 10px; padding: 8px 10px; border-radius: 7px; background: rgba(113, 104, 245, .09); font-size: 11px; }.outline-item > span { color: #a59eff; }.outline-item strong { font-weight: 500; }.outline-item p { margin: 4px 0 0; color: var(--text-secondary); font-size: 11px; line-height: 1.55; white-space: pre-wrap; }
.project-settings-row { display: grid; grid-template-columns: 112px minmax(0, 1fr); gap: 10px; margin-bottom: 10px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 7px; color: var(--text-muted); font-size: 11px; }.project-settings-row strong { color: var(--text-secondary); font-weight: 500; }
.source-list { display: grid; gap: 7px; }.source-item { padding: 9px 10px; border: 1px solid rgba(148, 163, 184, .11); border-radius: 8px; background: rgba(10, 17, 30, .3); }.source-heading { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }.source-category { color: #a59eff; font-size: 10px; }.source-heading strong { font-size: 12px; }.source-origin { margin-left: auto; color: var(--text-muted); font-size: 10px; }.source-item p { margin: 6px 0 0; color: var(--text-secondary); font-size: 11px; line-height: 1.55; }
.settings-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }.settings-grid > div { min-width: 0; display: grid; gap: 4px; padding: 9px 10px; border-radius: 8px; background: rgba(10, 17, 30, .3); }.settings-grid > div > span { color: var(--text-muted); font-size: 10px; }.settings-grid strong { color: var(--text-primary); font-size: 11px; font-weight: 500; overflow-wrap: anywhere; }.wide-setting { grid-column: 1 / -1; }.tag-list { display: flex; flex-wrap: wrap; gap: 5px; }.tag-list em { padding: 3px 7px; border: 1px solid rgba(113, 104, 245, .32); border-radius: 99px; color: #c1bcff; font-size: 10px; font-style: normal; }.setting-note { margin: 0; color: var(--text-muted); font-size: 11px; }

@media (max-width: 700px) { .usage-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); padding-inline: 14px; }.usage-note { margin-inline: 14px; }.step-layout { grid-template-columns: 125px minmax(0, 1fr); }.step-nav { padding-left: 8px; }.step-detail { padding: 14px; }.modal-header { padding-inline: 14px; }.settings-grid { grid-template-columns: 1fr; } }
</style>
