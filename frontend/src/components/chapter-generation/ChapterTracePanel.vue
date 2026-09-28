<template>
  <div class="tab-content">
    <div class="logs-header">
      <div>
        <span class="block-title">运行记录</span>
        <small>按每次生成聚合执行步骤、耗时和真实用量</small>
      </div>
      <n-button size="tiny" :loading="loading" @click="refresh">刷新</n-button>
    </div>

    <div v-if="loading && runs.length === 0" class="empty-logs">正在读取运行记录…</div>
    <div v-else-if="runs.length === 0 && !loading" class="empty-logs">
      暂无运行记录；完成一次章节生成后，这里会显示每次运行的步骤详情。
    </div>
    <div v-if="runs.length" class="run-history-list">
      <div
        v-for="run in runs"
        :key="run.run_id"
        class="run-history-card"
        :class="{ selected: detail?.run.run_id === run.run_id }"
      >
        <div class="run-history-main">
          <strong>{{ templateLabel(run.template_name) }} · {{ chapterLabel(run.chapter_id) }}</strong>
          <n-tag size="tiny" :type="runStatusType(run.status)">{{ runStatusLabel(run.status) }}</n-tag>
          <small>{{ formatDate(run.created_at) }} · {{ run.word_count }} 字</small>
          <small v-if="run.error_message" class="run-error">{{ run.error_message }}</small>
        </div>
        <n-button size="tiny" text @click="showRunDetail(run)">
          {{ detail?.run.run_id === run.run_id ? '正在查看' : '查看步骤' }}
        </n-button>
      </div>
    </div>

    <div v-if="detail" class="run-detail-panel">
      <div class="run-detail-heading">
        <strong>{{ templateLabel(detail.run.template_name) }} · {{ runStatusLabel(detail.run.status) }}</strong>
        <small>{{ detail.run.run_id }}</small>
      </div>
      <div class="workflow-metrics-grid">
        <div><strong>{{ usage.llmCalls }}</strong><span>模型请求</span></div>
        <div><strong>{{ formatTokenCount(usage.totalTokens) }}</strong><span>已返回 Token</span></div>
        <div><strong>{{ usage.pricedSteps ? formatCurrency(usage.estimatedCost) : '未配置' }}</strong><span>费用估算（{{ usage.pricedSteps }}/{{ usage.measuredSteps }}）</span></div>
        <div><strong>{{ usage.measuredSteps }} / {{ usage.steps.length }}</strong><span>有用量记录的步骤</span></div>
        <div><strong>{{ formatDuration(usage.durationMs) }}</strong><span>累计步骤耗时</span></div>
      </div>
      <div class="workflow-step-usage">
        <div v-for="step in usage.steps" :key="step.id" class="workflow-step-usage-row">
          <div class="workflow-step-main">
            <span>{{ step.step_name || step.step_id }} · {{ runStatusLabel(step.status) }} · {{ stepSource(step) }}</span>
            <small>{{ stepContextSummary(step) }}</small>
            <small v-if="step.error_message" class="run-error">{{ step.error_message }}</small>
          </div>
          <span>{{ stepTokenUsage(step) }}<br>{{ step.duration_ms == null ? '耗时未记录' : formatDuration(step.duration_ms) }}</span>
        </div>
      </div>
      <p class="workflow-usage-note">Token 显示模型服务商实际返回的用量；费用使用调用时单价快照估算，缺少用量或单价时不推算。</p>
    </div>

    <div v-if="visibleEvents.length" class="local-events-section">
      <div class="block-title">本页操作</div>
      <div v-for="event in visibleEvents" :key="event.id" class="local-event-row">
        <span>{{ event.title }}</span><small>{{ event.detail }} · {{ event.time }}</small>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { getAgentLogs } from '@/api/agents'
import { getWorkflowRunDetail, getWorkflowRuns, type WorkflowRunRecord, type WorkflowStepRecord, type WorkflowTemplate } from '@/api/agentsV3'
import type { ChapterItem, GenerationLog } from '@/types/domain'

const props = defineProps<{
  projectId: number | null
  chapterId: number | null
  chapters: ChapterItem[]
  templates: WorkflowTemplate[]
  localEvents: Array<{ id: string; title: string; detail: string; time: string; status: string }>
}>()
const message = useMessage()
const logs = ref<GenerationLog[]>([])
const runs = ref<WorkflowRunRecord[]>([])
const loading = ref(false)
const detail = ref<{ run: WorkflowRunRecord; steps: WorkflowStepRecord[] } | null>(null)
let requestId = 0
let detailRequestId = 0

const visibleEvents = computed(() => {
  const persisted = logs.value.slice(0, 3).map((log) => ({
    id: `log-${log.id}`,
    title: taskTypeLabel(log.task_type),
    // 旧日志可能含整篇正文；仅显示摘要和错误状态，不把原始请求响应渲染到轨迹中。
    detail: log.error || (log.status === 'success' ? '已完成（旧记录没有分步详情）' : '运行失败'),
    time: formatDate(log.created_at),
    status: log.status,
  }))
  return [...props.localEvents].slice(0, 12).concat(persisted)
})

const usage = computed(() => {
  const steps = detail.value?.steps ?? []
  const measured = steps.filter((step) => {
    const tokens = step.token_usage
    return tokens && [tokens.input_tokens, tokens.output_tokens, tokens.total_tokens].some((value) => typeof value === 'number')
  })
  return {
    steps,
    measuredSteps: measured.length,
    totalTokens: measured.reduce((total, step) => {
      const tokens = step.token_usage
      return total + (tokens?.total_tokens ?? ((tokens?.input_tokens ?? 0) + (tokens?.output_tokens ?? 0)))
    }, 0),
    pricedSteps: steps.filter((step) => typeof step.token_usage?.cost_cny === 'number').length,
    estimatedCost: steps.reduce((total, step) => total + (step.token_usage?.cost_cny ?? 0), 0),
    llmCalls: steps.reduce((total, step) => total + (step.llm_calls || 0), 0),
    durationMs: steps.reduce((total, step) => total + (step.duration_ms || 0), 0),
  }
})

watch(() => [props.projectId, props.chapterId], () => {
  // 切项目或章节时立即废弃旧详情，避免新列表加载期间短暂显示上一章统计。
  detailRequestId += 1
  detail.value = null
  void refresh()
}, { immediate: true })

async function refresh() {
  const projectId = props.projectId
  if (!projectId) {
    requestId += 1
    detailRequestId += 1
    logs.value = []
    runs.value = []
    detail.value = null
    loading.value = false
    return
  }
  const currentRequestId = ++requestId
  loading.value = true
  try {
    const [logResult, runResult] = await Promise.all([
      getAgentLogs(projectId, 20),
      getWorkflowRuns(projectId, { chapter_id: props.chapterId ?? undefined, limit: 20 }),
    ])
    if (currentRequestId !== requestId || projectId !== props.projectId) return
    logs.value = logResult
    runs.value = runResult
    if (detail.value && !runResult.some((run) => run.run_id === detail.value?.run.run_id)) {
      detail.value = null
      detailRequestId += 1
    }
  } catch {
    if (currentRequestId === requestId) message.error('运行记录读取失败')
  } finally {
    if (currentRequestId === requestId) loading.value = false
  }
}

async function showRunDetail(run: WorkflowRunRecord) {
  const currentRequestId = ++detailRequestId
  try {
    const result = await getWorkflowRunDetail(run.run_id)
    if (currentRequestId === detailRequestId && result && run.run_id === runs.value.find((item) => item.run_id === run.run_id)?.run_id) {
      detail.value = result
    }
  } catch {
    if (currentRequestId === detailRequestId) message.error('运行详情读取失败')
  }
}

function taskTypeLabel(value: string) {
  const labels: Record<string, string> = {
    chapter_draft: '章节生成', chapter_analyze: '章节分析', chapter_polish: '章节精修', consistency_check: '一致性检查',
  }
  return labels[value] ?? value
}

function runStatusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '等待中', running: '运行中', paused: '已中断', completed: '已完成', failed: '失败', cancelled: '已取消', skipped: '已跳过',
  }
  return labels[status] ?? status
}

function runStatusType(status: string): 'success' | 'info' | 'warning' | 'error' | 'default' {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'paused' || status === 'cancelled') return 'warning'
  if (status === 'running') return 'info'
  return 'default'
}

function templateLabel(name: string) {
  return props.templates.find((template) => template.name === name)?.label ?? name
}

function chapterLabel(id: number | null) {
  if (id === null) return '未关联章节'
  return props.chapters.find((chapter) => chapter.id === id)?.title || `章节 ${id}`
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

function formatTokenCount(value: number) {
  return new Intl.NumberFormat('zh-CN').format(value)
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency', currency: 'CNY', minimumFractionDigits: 4, maximumFractionDigits: 6,
  }).format(value)
}

function formatDuration(value: number) {
  const seconds = Math.floor(value / 1000)
  return seconds < 60 ? `${seconds} 秒` : `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
}

function stepSource(step: WorkflowStepRecord) {
  const source = step.output_snapshot?.source
  if (typeof source !== 'string') return '来源未记录'
  return source.startsWith('fallback:') ? '兜底内容' : source === 'llm' ? '模型生成' : source
}

function stepTokenUsage(step: WorkflowStepRecord) {
  const tokens = step.token_usage
  if (!tokens || ![tokens.input_tokens, tokens.output_tokens, tokens.total_tokens].some((value) => typeof value === 'number')) {
    if (step.llm_calls) return '服务商未返回用量'
    return stepSource(step) === '兜底内容' ? '兜底 / 无 Token 记录' : '未调用模型'
  }
  const parts = [
    tokens.input_tokens != null ? `输入 ${formatTokenCount(tokens.input_tokens)}` : '',
    tokens.cached_input_tokens != null ? `缓存输入 ${formatTokenCount(tokens.cached_input_tokens)}` : '',
    tokens.output_tokens != null ? `输出 ${formatTokenCount(tokens.output_tokens)}` : '',
    tokens.total_tokens != null ? `合计 ${formatTokenCount(tokens.total_tokens)}` : '',
  ].filter(Boolean)
  const cost = typeof tokens.cost_cny === 'number' ? ` · 约 ${formatCurrency(tokens.cost_cny)}` : ''
  return `${parts.join(' / ')} tokens${cost}`
}

function stepContextSummary(step: WorkflowStepRecord) {
  const summary = step.input_snapshot?.context_summary
  if (!summary) return '资料清单未记录（旧运行）'
  const previewNames = (label: string, values?: string[]) => {
    if (!values?.length) return ''
    const visible = values.slice(0, 3).join('、')
    const remaining = values.length - Math.min(values.length, 3)
    return `${label}：${visible}${remaining > 0 ? `等 ${values.length} 项` : ''}`
  }
  const items = [
    summary.outline_title ? `大纲：${summary.outline_title}` : '',
    previewNames('人物', summary.characters),
    previewNames('组织', summary.organizations),
    previewNames('世界观', summary.world_settings),
    previewNames('伏笔', summary.foreshadowings),
    summary.recent_chapters?.length ? `前情：第 ${summary.recent_chapters.join('、')} 章` : '',
    previewNames('长期记忆', summary.long_term_memories),
  ].filter(Boolean)
  return items.length ? items.join(' · ') : '本步骤未匹配到项目资料'
}

defineExpose({ refresh })
</script>

<style scoped>
.tab-content { display: grid; gap: 10px; }
.block-title { color: var(--n-text-color, #e2e8f0); font-size: 13px; font-weight: 600; }
.logs-header { display: flex; align-items: center; justify-content: space-between; }
.logs-header > div { display: grid; gap: 3px; }
.logs-header small { color: var(--n-text-color-3, #7b8494); font-size: 11px; }
.empty-logs { padding: 24px 16px; text-align: center; color: var(--n-text-color-3, #6b7280); font-size: 12px; background: var(--n-color-1, #1e2228); border-radius: 8px; }
.run-history-list { display: grid; gap: 8px; }
.run-history-card { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; padding: 11px; border: 1px solid var(--n-border-color, rgba(148, 163, 184, .2)); border-radius: 9px; background: rgba(148, 163, 184, .04); }
.run-history-card.selected { border-color: var(--n-primary-color, #6366f1); background: rgba(99, 102, 241, .08); }
.run-history-main { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 5px 8px; min-width: 0; }
.run-history-main strong, .run-history-main small, .run-detail-heading small { min-width: 0; overflow-wrap: anywhere; }
.run-history-main small { grid-column: 1 / -1; color: var(--n-text-color-3, #7b8494); font-size: 11px; }
.run-detail-panel { display: grid; gap: 10px; margin-top: 12px; padding: 12px; border: 1px solid var(--n-border-color, rgba(148, 163, 184, .2)); border-radius: 10px; background: rgba(15, 23, 42, .28); }
.run-detail-heading { display: grid; gap: 4px; }
.run-detail-heading small { color: var(--n-text-color-3, #7b8494); font-size: 10px; }
.run-error { color: #f87171 !important; }
.workflow-metrics-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.workflow-metrics-grid > div { display: flex; flex-direction: column; gap: 3px; min-width: 0; padding: 8px; border-radius: 8px; background: rgba(99, 102, 241, .07); }
.workflow-metrics-grid strong { overflow: hidden; color: var(--n-primary-color, #6366f1); font-size: 15px; text-overflow: ellipsis; white-space: nowrap; }
.workflow-metrics-grid span, .workflow-step-usage-row span:last-child, .workflow-usage-note { color: var(--n-text-color-3, #7b8494); font-size: 12px; }
.workflow-step-usage { display: grid; gap: 6px; margin-top: 10px; }
.workflow-step-usage-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; font-size: 12px; }
.workflow-step-main { display: grid; gap: 3px; min-width: 0; }
.workflow-step-main > span { color: var(--n-text-color, #333); }
.workflow-step-main small { overflow-wrap: anywhere; color: var(--n-text-color-3, #7b8494); font-size: 11px; line-height: 1.45; }
.workflow-usage-note { margin: 8px 0 0; line-height: 1.5; }
.local-events-section { display: grid; gap: 7px; margin-top: 18px; padding-top: 12px; border-top: 1px solid var(--n-border-color, rgba(148, 163, 184, .2)); }
.local-event-row { display: grid; gap: 3px; padding: 8px; border-radius: 7px; background: rgba(148, 163, 184, .04); font-size: 12px; }
.local-event-row small { color: var(--n-text-color-3, #7b8494); font-size: 11px; }
@media (max-width: 760px) { .run-history-card { flex-direction: column; } }
</style>
