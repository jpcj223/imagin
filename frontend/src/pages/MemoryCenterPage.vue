<template>
  <div class="page page-wide">
    <div class="page-title">
      <div>
        <h1>🧠 长期记忆中心</h1>
        <p class="muted">集中查看章节摘要、人物变化、世界观变化和时间线沉淀。</p>
      </div>
      <n-button @click="loadMemories">刷新记忆</n-button>
    </div>

    <div class="triple-workbench memory-workbench">
      <aside class="list-panel">
        <div class="panel-head">
          <h2>摘要索引</h2>
          <span class="muted">{{ filteredSummaries.length }} 条</span>
        </div>
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索章节、摘要或时间线" />
          <n-select v-model:value="chapterFilter" clearable :options="chapterOptions" placeholder="按章节筛选" />
        </div>
        <div class="list-body">
          <n-empty v-if="filteredSummaries.length === 0" description="暂无可用记忆" />
          <template v-else>
            <button
              v-for="item in filteredSummaries"
              :key="item.id"
              class="list-item"
              :class="{ active: selectedSummary?.id === item.id }"
              @click="selectSummary(item)"
            >
              <div class="item-title">
                <span>第 {{ item.chapter_no }} 章</span>
                <span class="muted">{{ item.created_at }}</span>
              </div>
              <div class="item-meta">{{ item.title }}</div>
              <p class="summary-excerpt">{{ shortText(item.summary, 72) }}</p>
            </button>
          </template>
        </div>
      </aside>

      <section class="editor-panel">
        <div class="panel-head inline-head">
          <h2>记忆详情</h2>
          <span class="muted">{{ selectedSummary ? `章节 ID ${selectedSummary.chapter_id}` : '未选择' }}</span>
        </div>

        <div v-if="selectedSummary" class="memory-detail">
          <div class="detail-hero">
            <span>第 {{ selectedSummary.chapter_no }} 章</span>
            <h2>{{ selectedSummary.title }}</h2>
            <p>{{ selectedSummary.summary || '暂无摘要' }}</p>
          </div>

          <div class="memory-grid">
            <div v-for="card in detailCards" :key="card.label" class="memory-card">
              <strong>{{ card.label }}</strong>
              <p>{{ card.value || '暂无记录' }}</p>
            </div>
          </div>
        </div>
        <div v-else class="detail-empty">从左侧选择一条章节摘要，查看沉淀后的长期记忆。</div>
      </section>

      <aside class="side-panel">
        <div class="panel-head inline-head">
          <h2>检索策略</h2>
          <span class="muted">v1</span>
        </div>
        <div class="strategy-list">
          <div class="strategy-item ready">
            <strong>最近摘要读取</strong>
            <p>章节生成会优先读取最近章节摘要，保障剧情连续性。</p>
          </div>
          <div class="strategy-item ready">
            <strong>关键词过滤</strong>
            <p>当前页面用 SQLite 普通查询结果做前端筛选，足够支撑第一版轻量创作。</p>
          </div>
          <div class="strategy-item">
            <strong>未来向量检索边界</strong>
            <p>后续只需要替换摘要检索接口，不影响章节生成页面和资料页。</p>
          </div>
        </div>

        <div class="analysis-panel">
          <div class="panel-head inline-head">
            <h2>资料统计</h2>
          </div>
          <div class="stat-grid">
            <div class="stat-cell">
              <span>章节草稿</span>
              <strong>{{ chapters.length }}</strong>
            </div>
            <div class="stat-cell">
              <span>摘要记忆</span>
              <strong>{{ summaries.length }}</strong>
            </div>
            <div class="stat-cell">
              <span>已分析比例</span>
              <strong>{{ coverageRate }}%</strong>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { getChapterSummaries } from '@/api/agents'
import { listResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import type { ChapterItem, ChapterSummary } from '@/types/domain'

const message = useMessage()
const projectStore = useProjectStore()
const keyword = ref('')
const chapterFilter = ref<number | null>(null)
const summaries = ref<ChapterSummary[]>([])
const chapters = ref<ChapterItem[]>([])
const selectedSummary = ref<ChapterSummary | null>(null)

const chapterOptions = computed(() =>
  chapters.value.map((item) => ({
    label: `第 ${item.chapter_no} 章 · ${item.title}`,
    value: item.chapter_no
  }))
)

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
    { label: '人物变化', value: item.character_changes },
    { label: '世界观变化', value: item.world_changes },
    { label: '新增伏笔', value: item.new_foreshadowings },
    { label: '时间线事件', value: item.timeline_events }
  ]
})

const coverageRate = computed(() => {
  if (chapters.value.length === 0) return 0
  return Math.round((summaries.value.length / chapters.value.length) * 100)
})

function shortText(value: string, max = 60) {
  return value?.length > max ? `${value.slice(0, max)}...` : value || '暂无摘要'
}

function selectSummary(item: ChapterSummary) {
  // 选择逻辑保持只读：记忆来自章节分析结果，不在此页面直接修改，避免和正文编辑产生冲突。
  selectedSummary.value = item
}

async function ensureProject() {
  if (!projectStore.currentProject) await projectStore.loadDefaultProject()
  return projectStore.currentProject?.id
}

async function loadMemories() {
  const projectId = await ensureProject()
  if (!projectId) return

  // 长期记忆第一版只依赖 SQLite 中的章节和摘要表，后续向量检索可在 API 层替换实现。
  const [chapterList, summaryList] = await Promise.all([
    listResource<ChapterItem>(projectId, 'chapters'),
    getChapterSummaries(projectId, 50)
  ])
  chapters.value = chapterList
  summaries.value = summaryList
  if (!selectedSummary.value || !summaryList.some((item) => item.id === selectedSummary.value?.id)) {
    selectedSummary.value = summaryList[0] ?? null
  }
  message.success('长期记忆已刷新')
}

onMounted(loadMemories)
</script>

<style scoped>
.memory-workbench {
  grid-template-columns: 330px minmax(440px, 1fr) 300px;
}

.summary-excerpt {
  margin: 8px 0 0;
  color: #cbd5e1;
  font-size: 12px;
  line-height: 1.6;
}

.memory-detail {
  display: grid;
  gap: 16px;
}

.detail-hero {
  padding: 18px;
  border: 1px solid #384151;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(79, 140, 255, 0.16), rgba(99, 226, 183, 0.08));
}

.detail-hero span {
  color: #93c5fd;
  font-size: 12px;
  font-weight: 700;
}

.detail-hero h2 {
  margin: 8px 0;
  font-size: 22px;
}

.detail-hero p {
  margin: 0;
  color: #d1d5db;
  line-height: 1.8;
}

.strategy-list {
  display: grid;
  gap: 10px;
}

.strategy-item {
  padding: 12px;
  border: 1px solid #30343a;
  border-radius: 6px;
  background: #181b1f;
}

.strategy-item.ready {
  border-color: rgba(99, 226, 183, 0.35);
}

.strategy-item strong {
  color: #e5e7eb;
}

.strategy-item p {
  margin: 6px 0 0;
  color: #9ca3af;
  line-height: 1.6;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.stat-cell {
  padding: 10px;
  border: 1px solid #30343a;
  border-radius: 6px;
  background: #181b1f;
}

.stat-cell span {
  display: block;
  color: #9ca3af;
  font-size: 12px;
}

.stat-cell strong {
  display: block;
  margin-top: 6px;
  color: #f8fafc;
  font-size: 20px;
}
</style>
