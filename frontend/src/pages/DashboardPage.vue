<template>
  <div class="page dashboard-page">
    <!-- 项目头部横幅 -->
    <div class="project-hero">
      <div class="hero-left">
        <div class="hero-badge">
          <span class="badge-icon">📖</span>
          <span class="badge-text">{{ project?.novel_type || '未设置类型' }}</span>
        </div>
        <h1 class="hero-title">{{ project?.name || '加载中...' }}</h1>
        <p class="hero-subtitle">
          <span v-if="project?.theme">主题：{{ project.theme }}</span>
          <span v-if="project?.view_point" class="hero-dot">·</span>
          <span v-if="project?.view_point">{{ project.view_point }}</span>
          <span v-if="project?.writing_style" class="hero-dot">·</span>
          <span v-if="project?.writing_style">{{ project.writing_style }}</span>
        </p>
      </div>
      <div class="hero-right">
        <div class="hero-stat">
          <div class="hero-stat-value">{{ formatNumber(dashboard.total_chars) }}</div>
          <div class="hero-stat-label">总字数</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-value">{{ dashboard.counts.chapters }}</div>
          <div class="hero-stat-label">章节</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-value">{{ progressPercent }}%</div>
          <div class="hero-stat-label">进度</div>
        </div>
      </div>
    </div>

    <!-- 快捷入口 -->
    <div class="quick-actions">
      <div
        v-for="action in quickActions"
        :key="action.path"
        class="action-card"
        @click="goTo(action.path)"
      >
        <div class="action-icon" :style="{ background: action.color }">{{ action.icon }}</div>
        <div class="action-info">
          <div class="action-title">{{ action.title }}</div>
          <div class="action-desc">{{ action.desc }}</div>
        </div>
        <div class="action-arrow">→</div>
      </div>
    </div>

    <!-- 主体：左数据概览 + 右最近章节 -->
    <div class="dashboard-main">
      <!-- 左侧：数据统计 -->
      <div class="stats-section">
        <div class="section-header">
          <h2 class="section-title">📊 资料概览</h2>
        </div>
        <div class="stat-grid">
          <div class="stat-card" @click="goTo('/characters')">
            <div class="stat-icon char">👥</div>
            <div class="stat-content">
              <div class="stat-value">{{ dashboard.counts.characters }}</div>
              <div class="stat-label">人物卡片</div>
            </div>
            <div class="stat-bar">
              <div
                class="stat-bar-fill"
                :style="{ width: charDistribution.protagonistPct + '%', background: '#f59e0b' }"
              ></div>
            </div>
            <div class="stat-meta">
              <span>主角 {{ charDistribution.protagonist }}</span>
              <span>配角 {{ charDistribution.supporting }}</span>
              <span>反派 {{ charDistribution.antagonist }}</span>
            </div>
          </div>

          <div class="stat-card" @click="goTo('/organizations')">
            <div class="stat-icon org">🏛️</div>
            <div class="stat-content">
              <div class="stat-value">{{ dashboard.counts.organizations }}</div>
              <div class="stat-label">组织势力</div>
            </div>
          </div>

          <div class="stat-card" @click="goTo('/world')">
            <div class="stat-icon world">🌍</div>
            <div class="stat-content">
              <div class="stat-value">{{ dashboard.counts.world_settings }}</div>
              <div class="stat-label">世界观设定</div>
            </div>
          </div>

          <div class="stat-card" @click="goTo('/foreshadowings')">
            <div class="stat-icon foreshadow">🎭</div>
            <div class="stat-content">
              <div class="stat-value">{{ dashboard.counts.foreshadowings }}</div>
              <div class="stat-label">伏笔看板</div>
            </div>
            <div class="foreshadow-pills">
              <n-tag size="tiny" type="warning">待埋 {{ foreshadowStats.pending }}</n-tag>
              <n-tag size="tiny" type="info">已埋下 {{ foreshadowStats.planted }}</n-tag>
              <n-tag size="tiny" type="success">已回收 {{ foreshadowStats.resolved }}</n-tag>
            </div>
          </div>

          <div class="stat-card" @click="goTo('/outline')">
            <div class="stat-icon outline">📋</div>
            <div class="stat-content">
              <div class="stat-value">{{ dashboard.counts.outlines }}</div>
              <div class="stat-label">大纲节点</div>
            </div>
          </div>

          <div class="stat-card" @click="goTo('/memory')">
            <div class="stat-icon memory">🧠</div>
            <div class="stat-content">
              <div class="stat-value">—</div>
              <div class="stat-label">长期记忆</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：最近章节 -->
      <div class="recent-section">
        <div class="section-header">
          <h2 class="section-title">📝 最近章节</h2>
          <n-button text size="small" @click="goTo('/chapter-generate')">去生成 →</n-button>
        </div>
        <div v-if="dashboard.recent_chapters.length === 0" class="empty-chapters">
          <div class="empty-icon">✍️</div>
          <p>还没有章节，开始你的第一章吧</p>
          <n-button type="primary" size="small" @click="goTo('/chapter-generate')">
            生成第一章
          </n-button>
        </div>
        <div v-else class="chapter-list">
          <div
            v-for="ch in dashboard.recent_chapters"
            :key="ch.id"
            class="chapter-item"
            @click="openChapter(ch)"
          >
            <div class="chapter-no">第{{ ch.chapter_no }}章</div>
            <div class="chapter-info">
              <div class="chapter-title">{{ ch.title }}</div>
              <div class="chapter-meta">
                <span>{{ formatNumber(ch.char_count) }} 字</span>
                <span class="dot">·</span>
                <n-tag size="tiny" :type="statusTagType(ch.status)">
                  {{ statusLabel(ch.status) }}
                </n-tag>
              </div>
            </div>
            <div class="chapter-arrow">→</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：创作流程步骤 -->
    <div class="workflow-section">
      <div class="section-header">
        <h2 class="section-title">🔄 创作流程</h2>
      </div>
      <n-steps :current="workflowStep" status="process" size="small">
        <n-step title="世界观设定" description="构建故事背景、规则和势力" />
        <n-step title="大纲规划" description="卷章结构、主线剧情节点" />
        <n-step title="管理人物" description="角色卡片、人物关系网络" />
        <n-step title="单章细纲" description="细化单章情节和场景" />
        <n-step title="生成文章" description="AI 辅助正文写作" />
      </n-steps>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboard } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import type { DashboardData } from '@/types/domain'

const router = useRouter()
const projectStore = useProjectStore()

// ---- 数据 ----
const dashboard = ref<DashboardData>({
  counts: {
    characters: 0,
    outlines: 0,
    chapters: 0,
    foreshadowings: 0,
    organizations: 0,
    world_settings: 0,
  },
  total_chars: 0,
  recent_chapters: [],
  foreshadowing_by_status: {},
  characters_by_type: {},
})

const project = computed(() => projectStore.currentProject)

// ---- 快捷入口 ----
const quickActions = [
  {
    title: '世界观设定',
    desc: '构建故事背景和规则体系',
    icon: '🌍',
    path: '/world',
    color: 'linear-gradient(135deg, #3b82f6, #06b6d4)',
  },
  {
    title: '大纲规划',
    desc: '搭建卷章结构和剧情节点',
    icon: '📑',
    path: '/outline',
    color: 'linear-gradient(135deg, #10b981, #059669)',
  },
  {
    title: '管理人物',
    desc: '维护角色卡和人物关系',
    icon: '👤',
    path: '/characters',
    color: 'linear-gradient(135deg, #f59e0b, #ef4444)',
  },
  {
    title: '单章细纲',
    desc: '细化单章情节和场景',
    icon: '📝',
    path: '/outline',
    color: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
  },
  {
    title: '生成文章',
    desc: 'AI 辅助快速创作正文',
    icon: '✨',
    path: '/chapter-generate',
    color: 'linear-gradient(135deg, #ec4899, #f43f5e)',
  },
]

// ---- 计算属性 ----

/** 目标总字数（用于进度展示）。 */
const targetTotalWords = computed(() => {
  const targetPerChapter = project.value?.target_words || 2500
  const chapterCount = dashboard.value.counts.chapters || 1
  // 简单估算：假设目标是写 30 章
  return targetPerChapter * 30
})

/** 写作进度百分比。 */
const progressPercent = computed(() => {
  const target = targetTotalWords.value
  if (target <= 0) return 0
  const pct = Math.round((dashboard.value.total_chars / target) * 100)
  return Math.min(pct, 99)
})

/** 角色类型分布。 */
const charDistribution = computed(() => {
  const byType = dashboard.value.characters_by_type || {}
  const protagonist = byType['protagonist'] || 0
  const supporting = byType['supporting'] || 0
  const antagonist = byType['antagonist'] || 0
  const total = dashboard.value.counts.characters || 1
  return {
    protagonist,
    supporting,
    antagonist,
    protagonistPct: Math.round((protagonist / total) * 100),
  }
})

/** 伏笔状态统计。 */
const foreshadowStats = computed(() => {
  const s = dashboard.value.foreshadowing_by_status || {}
  return {
    pending: s['pending'] || 0,
    planted: s['planted'] || s['developing'] || 0,
    developing: s['developing'] || 0,
    resolved: s['resolved'] || 0,
    abandoned: s['abandoned'] || 0,
  }
})

/** 创作流程步骤进度（根据有数据的模块估算）。 */
const workflowStep = computed(() => {
  const c = dashboard.value.counts
  let step = 0
  // 有世界观设定 → 步骤 1
  if (c.world_settings > 0) step = 1
  // 有大纲 → 步骤 2
  if (c.outlines > 0) step = 2
  // 有人物 → 步骤 3
  if (c.characters > 0) step = 3
  // 有章节 → 步骤 4（单章细纲和章节关联）
  if (c.chapters > 0) step = 4
  // 有章节正文 → 步骤 5
  if (dashboard.value.total_chars > 0) step = 5
  return step
})

// ---- 方法 ----

async function load() {
  if (!projectStore.currentProject) return
  const data = await getDashboard(projectStore.currentProject.id)
  dashboard.value = data
}

useProjectDataLoader(load)

function goTo(path: string) {
  router.push(path)
}

function openChapter(ch: { id: number; chapter_no: number }) {
  // 跳到章节生成页并定位到对应章节
  router.push({ path: '/chapter-generate', query: { chapter: ch.chapter_no } })
}

function formatNumber(n: number): string {
  if (n >= 10000) {
    return (n / 10000).toFixed(1) + '万'
  }
  return n.toLocaleString()
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: '草稿',
    confirmed: '已确认',
    published: '已发布',
  }
  return map[status] || status
}

function statusTagType(status: string): 'default' | 'success' | 'warning' | 'info' | 'error' {
  const map: Record<string, 'default' | 'success' | 'warning' | 'info' | 'error'> = {
    draft: 'default',
    confirmed: 'success',
    published: 'info',
  }
  return map[status] || 'default'
}
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ===== 项目头部横幅 ===== */
.project-hero {
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4c1d95 100%);
  border-radius: 16px;
  padding: 28px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
}

.project-hero::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -10%;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.3) 0%, transparent 70%);
  pointer-events: none;
}

.hero-left {
  position: relative;
  z-index: 1;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(4px);
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  color: #c7d2fe;
  margin-bottom: 12px;
}

.badge-icon {
  font-size: 14px;
}

.hero-title {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 8px 0;
}

.hero-subtitle {
  color: #a5b4fc;
  font-size: 14px;
  margin: 0;
}

.hero-dot {
  margin: 0 6px;
  opacity: 0.5;
}

.hero-right {
  display: flex;
  gap: 40px;
  position: relative;
  z-index: 1;
}

.hero-stat {
  text-align: center;
}

.hero-stat-value {
  font-size: 32px;
  font-weight: 800;
  color: #fff;
  line-height: 1;
  margin-bottom: 6px;
}

.hero-stat-label {
  font-size: 13px;
  color: #a5b4fc;
}

/* ===== 快捷入口 ===== */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
}

.action-card {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 12px;
  padding: 16px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-card:hover {
  border-color: var(--n-color-primary-3, #3b82f6);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}

.action-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.action-info {
  flex: 1;
  min-width: 0;
}

.action-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 2px;
}

.action-desc {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.action-arrow {
  color: var(--n-text-color-3, #6b7280);
  font-size: 16px;
  transition: transform 0.2s;
}

.action-card:hover .action-arrow {
  transform: translateX(4px);
  color: var(--n-color-primary, #3b82f6);
}

/* ===== 主体两栏 ===== */
.dashboard-main {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
}

/* ===== 统计卡片网格 ===== */
.stats-section {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 12px;
  padding: 20px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-card {
  background: var(--n-color-1, #1e2228);
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stat-card:hover {
  border-color: var(--n-color-primary-3, #3b82f6);
  background: var(--n-color-hover, #23272f);
}

.stat-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: rgba(99, 102, 241, 0.15);
}

.stat-icon.char {
  background: rgba(245, 158, 11, 0.15);
}
.stat-icon.org {
  background: rgba(239, 68, 68, 0.15);
}
.stat-icon.world {
  background: rgba(59, 130, 246, 0.15);
}
.stat-icon.foreshadow {
  background: rgba(168, 85, 247, 0.15);
}
.stat-icon.outline {
  background: rgba(16, 185, 129, 0.15);
}
.stat-icon.memory {
  background: rgba(6, 182, 212, 0.15);
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 4px;
}

.stat-bar {
  height: 4px;
  background: var(--n-color-2, #2a2f3a);
  border-radius: 2px;
  overflow: hidden;
}

.stat-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.stat-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
}

.foreshadow-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* ===== 最近章节 ===== */
.recent-section {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.empty-chapters {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--n-text-color-3, #6b7280);
  padding: 40px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 40px;
}

.empty-chapters p {
  margin: 0;
  font-size: 13px;
}

.chapter-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.chapter-item:hover {
  background: var(--n-color-hover, #23272f);
}

.chapter-no {
  font-size: 12px;
  color: var(--n-color-primary, #3b82f6);
  font-weight: 600;
  flex-shrink: 0;
  width: 52px;
}

.chapter-info {
  flex: 1;
  min-width: 0;
}

.chapter-title {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.chapter-meta {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  display: flex;
  align-items: center;
  gap: 4px;
}

.chapter-meta .dot {
  opacity: 0.5;
}

.chapter-arrow {
  color: var(--n-text-color-3, #6b7280);
  font-size: 14px;
  flex-shrink: 0;
}

/* ===== 创作流程 ===== */
.workflow-section {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 12px;
  padding: 20px 24px;
}

/* ===== 响应式 ===== */
@media (max-width: 1200px) {
  .quick-actions {
    grid-template-columns: repeat(3, 1fr);
  }
  .dashboard-main {
    grid-template-columns: 1fr;
  }
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .project-hero {
    flex-direction: column;
    gap: 20px;
    text-align: center;
  }
  .hero-right {
    gap: 24px;
  }
  .quick-actions {
    grid-template-columns: 1fr;
  }
  .stat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
