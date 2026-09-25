<template>
  <div class="tab-content">

    <!-- 生成后沉淀 -->
    <div class="form-block">
      <div class="block-title">生成后沉淀</div>
      <n-alert v-if="props.analysisStatus === 'unavailable'" type="warning" :show-icon="true">
        {{ props.analysis || '模型服务不可用，本次未保存章节分析；配置模型后可重新分析。' }}
      </n-alert>
      <div v-else-if="!props.analysisSections.summary && !props.analysis" class="empty-analysis">
        <div class="empty-icon">📊</div>
        <p>生成并分析后，这里会展示章节摘要、人物变化、伏笔线索等</p>
      </div>
      <div v-else class="analysis-cards">
        <div class="analysis-card">
          <div class="card-label">📝 章节摘要</div>
          <p>{{ props.analysisSections.summary || '暂无' }}</p>
        </div>
        <div class="analysis-card">
          <div class="card-label">👤 人物变化</div>
          <p>{{ props.analysisSections.character_changes || '暂无' }}</p>
        </div>
        <div class="analysis-card">
          <div class="card-label">🌍 世界观变化</div>
          <p>{{ props.analysisSections.world_changes || '暂无' }}</p>
        </div>
        <div class="analysis-card">
          <div class="card-label">🎭 新增伏笔</div>
          <p>{{ props.analysisSections.new_foreshadowings || '暂无' }}</p>
        </div>
        <div class="analysis-card">
          <div class="card-label">⏱️ 时间线事件</div>
          <p>{{ props.analysisSections.timeline_events || '暂无' }}</p>
        </div>
      </div>
    </div>

    <!-- 章节分析只产生提案；作者确认后才写回人物、关系、组织等正式资料。 -->
    <div class="form-block">
      <div class="block-title">
        资料变化审核
        <n-tag size="tiny" :type="props.pendingProposalCount ? 'warning' : 'default'">
          {{ props.pendingProposalCount }} 条待审核
        </n-tag>
        <n-button
          size="tiny"
          quaternary
          :loading="props.proposalLoading"
          :disabled="!props.hasChapter"
          @click="emit('reloadProposals')"
        >
          刷新
        </n-button>
      </div>
      <n-spin :show="props.proposalLoading">
        <div v-if="props.changeProposals.length === 0" class="empty-proposals">
          分析章节后，人物、关系、组织、伏笔和时间线变化会出现在这里；确认后才会更新正式资料。
        </div>
        <div v-else class="proposal-list">
          <article
            v-for="proposal in props.changeProposals"
            :key="proposal.proposal_id"
            class="proposal-card"
            :class="'proposal-' + proposal.status"
          >
            <div class="proposal-heading">
              <div class="proposal-title">
                <strong>{{ proposalEntityLabel(proposal.entity_type) }} · {{ proposal.target_label || '未命名' }}</strong>
                <n-tag size="small" :type="proposalStatusType(proposal.status)">
                  {{ proposalStatusLabel(proposal.status) }}
                </n-tag>
                <n-tag v-if="proposal.operation === 'create'" size="small" type="info">新增</n-tag>
              </div>
              <span v-if="proposal.version_id" class="proposal-source">来源版本 {{ proposal.version_id.slice(0, 8) }}</span>
            </div>
            <p v-if="proposal.rationale" class="proposal-rationale">{{ proposal.rationale }}</p>
            <blockquote v-if="proposal.evidence" class="proposal-evidence">{{ proposal.evidence }}</blockquote>
            <div class="proposal-diff">
              <div v-for="change in proposalChanges(proposal)" :key="change.field" class="proposal-diff-row">
                <span class="proposal-field">{{ change.field }}</span>
                <span class="proposal-before">{{ change.before }}</span>
                <span class="proposal-arrow">→</span>
                <span class="proposal-after">{{ change.after }}</span>
              </div>
            </div>
            <p v-if="proposal.review_note" class="proposal-review-note">{{ proposal.review_note }}</p>
            <div v-if="proposal.status === 'pending'" class="proposal-actions">
              <n-button
                size="small"
                quaternary
                :disabled="props.proposalBusyIds.includes(proposal.proposal_id)"
                @click="emit('startProposalEdit', proposal)"
              >
                修改内容
              </n-button>
              <n-button
                size="small"
                type="error"
                quaternary
                :disabled="props.proposalBusyIds.includes(proposal.proposal_id)"
                @click="emit('reviewProposal', proposal, 'reject')"
              >
                拒绝
              </n-button>
              <n-button
                size="small"
                type="success"
                :loading="props.proposalBusyIds.includes(proposal.proposal_id)"
                @click="emit('reviewProposal', proposal, 'approve')"
              >
                确认并写回
              </n-button>
            </div>
            <div v-else-if="proposal.status === 'conflict'" class="proposal-actions">
              <n-button size="small" @click="emit('reanalyze')">按当前资料重新分析</n-button>
            </div>
          </article>
        </div>
      </n-spin>
    </div>

    <!-- 一致性检查 -->
    <div class="form-block">
      <div class="block-title">一致性检查</div>
      <div v-if="!props.consistencyResult" class="empty-consistency">
        点击「检查一致性」后查看资料缺口和潜在冲突
      </div>
      <div v-else class="consistency-result" :class="props.consistencyResult.risk_level">
        <div class="risk-header">
          <span class="risk-icon">
            {{ props.consistencyResult.risk_level === 'low' ? '✅' : props.consistencyResult.risk_level === 'medium' ? '⚠️' : '❌' }}
          </span>
          <span class="risk-label">{{ riskLabel(props.consistencyResult.risk_level) }}</span>
        </div>
        <ul class="suggestion-list">
          <li v-for="(s, i) in props.consistencyResult.suggestions" :key="i">{{ s }}</li>
        </ul>
      </div>
    </div>

    <!-- 长期记忆 -->
    <div class="form-block">
      <div class="block-title">
        长期记忆
        <n-tag size="tiny" type="info">{{ props.summaries.length }} 条</n-tag>
      </div>
      <div v-if="props.summaries.length === 0" class="empty-memory">
        暂无章节摘要，分析章节后会自动沉淀
      </div>
      <div v-else class="memory-list">
        <div v-for="item in props.summaries.slice(0, 5)" :key="item.id" class="memory-item">
          <div class="memory-chapter">第 {{ item.chapter_no }} 章 · {{ item.title }}</div>
          <p>{{ shortText(item.summary) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 章节分析标签的展示组件。
 * 步骤 1：接收分析结果、待审核提案和相关资料。
 * 步骤 2：把刷新、审核、编辑和重新分析动作发回工作台页面。
 */
import type {
  ChangeProposalEntityType,
  ChangeProposalStatus,
  ChapterChangeProposal,
} from '@/api/agentsV3'
import type { ChapterSummary, ConsistencyCheckResult, OrganizationItem } from '@/types/domain'

interface AnalysisSections {
  summary: string
  character_changes: string
  world_changes: string
  new_foreshadowings: string
  timeline_events: string
}

interface Props {
  analysis: string
  analysisStatus: string
  analysisSections: AnalysisSections
  pendingProposalCount: number
  proposalLoading: boolean
  proposalBusyIds: string[]
  changeProposals: ChapterChangeProposal[]
  hasChapter: boolean
  consistencyResult: ConsistencyCheckResult | null
  summaries: ChapterSummary[]
  organizations: OrganizationItem[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  reloadProposals: []
  startProposalEdit: [proposal: ChapterChangeProposal]
  reviewProposal: [proposal: ChapterChangeProposal, decision: 'approve' | 'reject']
  reanalyze: []
}>()

const proposalEntityLabels: Record<ChangeProposalEntityType, string> = {
  character: '人物',
  relationship: '人物关系',
  organization: '组织',
  organization_relation: '组织关系',
  foreshadowing: '伏笔',
  world_setting: '世界观',
  memory: '长期记忆',
}

function proposalEntityLabel(entityType: ChangeProposalEntityType): string {
  return proposalEntityLabels[entityType] ?? entityType
}

function proposalStatusLabel(status: ChangeProposalStatus): string {
  const labels: Record<ChangeProposalStatus, string> = {
    pending: '待审核',
    applied: '已写回',
    rejected: '已拒绝',
    conflict: '资料有变化',
  }
  return labels[status]
}

function proposalStatusType(status: ChangeProposalStatus): 'warning' | 'success' | 'error' | 'default' {
  if (status === 'pending') return 'warning'
  if (status === 'applied') return 'success'
  if (status === 'rejected') return 'default'
  return 'error'
}

function formatProposalValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'string') return value
  return JSON.stringify(value) ?? String(value)
}

/** 将提案字段格式化为“修改前 → 修改后”，并解析组织关系名称。 */
function proposalChanges(proposal: ChapterChangeProposal) {
  const fields = Object.entries(proposal.proposed_value ?? {})
  if (proposal.entity_type === 'organization_relation') {
    const summarize = (value: Record<string, unknown>) => {
      const sourceId = Number(value.source_org_id)
      const targetId = Number(value.target_org_id)
      const source = sourceId ? props.organizations.find((item) => item.id === sourceId)?.name : ''
      const target = targetId ? props.organizations.find((item) => item.id === targetId)?.name : ''
      const endpoints = source && target ? `${source} → ${target}` : proposal.target_label
      const relationType = value.relation_type === 'alliance'
        ? '同盟'
        : value.relation_type === 'hostility' ? '敌对' : ''
      const range: string[] = []
      if ('effective_from_chapter' in value) {
        range.push(value.effective_from_chapter == null ? '起始不限' : `第 ${String(value.effective_from_chapter)} 章起`)
      }
      if ('expires_at_chapter' in value) {
        range.push(value.expires_at_chapter == null ? '持续有效' : `至第 ${String(value.expires_at_chapter)} 章`)
      }
      return [endpoints, relationType, range.join('，'), value.description]
        .filter((part) => part !== '' && part !== undefined && part !== null)
        .join(' · ')
    }
    return [{
      field: proposal.operation === 'create' ? '新增组织关系' : '组织关系调整',
      before: proposal.operation === 'create' ? '无既有关系' : summarize(proposal.before_value),
      after: summarize(proposal.proposed_value),
    }]
  }

  if (proposal.entity_type === 'relationship') {
    const relationships = proposal.before_value.relationships
    const targetId = proposal.proposed_value.target_id
    const oldRelation = Array.isArray(relationships)
      ? relationships.find((item) => {
          if (!item || typeof item !== 'object') return false
          return (item as Record<string, unknown>).target_id === targetId
        }) as Record<string, unknown> | undefined
      : undefined
    const relationText = (value: Record<string, unknown> | undefined) => {
      if (!value) return '无既有关系'
      const depth = value.depth === undefined ? '' : ` · 深度 ${String(value.depth)}`
      return formatProposalValue(value.relation_type) + depth
    }
    return [{
      field: proposal.operation === 'update' ? '关系更新' : '新增关系',
      before: relationText(oldRelation),
      after: relationText(proposal.proposed_value),
    }]
  }

  if (proposal.operation === 'create') {
    return fields.map(([field, value]) => ({ field, before: '—', after: formatProposalValue(value) }))
  }
  return fields.map(([field, value]) => ({
    field,
    before: formatProposalValue(proposal.before_value[field]),
    after: formatProposalValue(value),
  }))
}

function riskLabel(value: string): string {
  const labels: Record<string, string> = { low: '低风险', medium: '中风险', high: '高风险' }
  return labels[value] ?? value
}

function shortText(value: string, max = 58): string {
  return value.length > max ? `${value.slice(0, max)}...` : value
}
</script>

<style scoped>
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
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border);
}

.form-block:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.block-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* ===== 分析 Tab ===== */
.empty-analysis,
.empty-consistency,
.empty-memory {
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

.empty-proposals {
  padding: 16px;
  color: var(--n-text-color-3, #6b7280);
  background: var(--n-color-1, #1e2228);
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
}

.proposal-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.proposal-card {
  padding: 12px;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.proposal-applied {
  border-color: rgba(16, 185, 129, 0.3);
}

.proposal-conflict {
  border-color: rgba(239, 68, 68, 0.45);
}

.proposal-heading,
.proposal-title,
.proposal-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.proposal-heading {
  justify-content: space-between;
  flex-wrap: wrap;
}

.proposal-title {
  flex-wrap: wrap;
}

.proposal-title strong {
  font-size: 13px;
}

.proposal-source {
  color: var(--n-text-color-3, #6b7280);
  font-size: 10px;
}

.proposal-rationale,
.proposal-review-note {
  margin: 8px 0;
  font-size: 12px;
  line-height: 1.5;
}

.proposal-evidence {
  margin: 8px 0;
  padding: 7px 9px;
  border-left: 2px solid #6366f1;
  background: rgba(99, 102, 241, 0.07);
  color: var(--n-text-color-2, #9ca3af);
  font-size: 11px;
  line-height: 1.5;
}

.proposal-diff {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 8px;
}

.proposal-diff-row {
  display: grid;
  grid-template-columns: minmax(72px, 0.7fr) minmax(0, 1fr) 20px minmax(0, 1fr);
  align-items: start;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.025);
  font-size: 11px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.proposal-field {
  color: var(--n-text-color-2, #9ca3af);
}

.proposal-before {
  color: #f59e0b;
}

.proposal-arrow {
  color: var(--n-text-color-3, #6b7280);
  text-align: center;
}

.proposal-after {
  color: #34d399;
}

.proposal-review-note {
  color: #f87171;
}


.proposal-actions {
  justify-content: flex-end;
  margin-top: 10px;
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

</style>
