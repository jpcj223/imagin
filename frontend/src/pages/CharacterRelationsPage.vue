<template>
  <div class="page relations-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">🕸️</span>
          人物关系图谱
        </h1>
        <p class="page-subtitle">
          全局视角查看所有人物之间的关系网络，支持可视化编辑
        </p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ characterCount }}</span>
            <span class="stat-label">角色</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ relationCount }}</span>
            <span class="stat-label">关系</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ relationTypesCount }}</span>
            <span class="stat-label">关系类型</span>
          </div>
        </div>
        <n-button type="primary" @click="showAddModal = true">
          <template #icon>＋</template>
          新建关系
        </n-button>
      </div>
    </div>

    <!-- 筛选工具栏 -->
    <div class="filter-bar">
      <n-select v-model:value="filterRoleType" placeholder="按角色类型筛选" clearable :options="roleTypeOptions" style="width: 140px" />
      <n-select v-model:value="filterRelationType" placeholder="按关系类型筛选" clearable :options="relationTypeOptions" style="width: 140px" />
      <n-input v-model:value="searchKeyword" clearable placeholder="搜索角色名" style="width: 200px">
        <template #prefix>🔍</template>
      </n-input>
      <div class="filter-spacer"></div>
      <n-button text size="small" @click="refreshData">↻ 刷新</n-button>
    </div>

    <!-- 主体：左图谱 + 右列表 -->
    <div class="workbench">
      <!-- 左：Vue Flow 关系图谱 -->
      <section class="graph-panel">
        <div class="panel-head">
          <h2>关系图谱</h2>
          <div class="graph-tools">
            <n-button size="small" text @click="resetLayout">重置布局</n-button>
            <n-button size="small" text @click="fitView">适应视图</n-button>
          </div>
        </div>
        <div class="graph-container">
          <VueFlow
            ref="vueFlowRef"
            :nodes="nodes"
            :edges="edges"
            :min-zoom="0.2"
            :max-zoom="2"
            class="vue-flow-container"
            @node-click="onNodeClick"
            @edge-click="onEdgeClick"
            @pane-click="onPaneClick"
            @init="onVueFlowInit"
          >
            <Background :gap="20" :size="1" color="#1e2228" />
            <Controls :show-fit-view="true" :show-interactive="true" position="bottom-right" />
          </VueFlow>
        </div>

        <!-- 图例 -->
        <div class="graph-legend">
          <div class="legend-group">
            <span class="legend-title">角色类型</span>
            <span v-for="(color, type) in nodeColors" :key="type" class="legend-item">
              <span class="legend-dot" :style="{ background: color }"></span>
              {{ roleTypeLabelMap[type] || type }}
            </span>
          </div>
          <div class="legend-group">
            <span class="legend-title">关系类型</span>
            <span v-for="(color, type) in relationColorMap" :key="type" class="legend-item">
              <span class="legend-line" :style="{ background: color }"></span>
              {{ type }}
            </span>
          </div>
        </div>
      </section>

      <!-- 右：关系列表 + 详情编辑 -->
      <aside class="list-panel">
        <div class="panel-head">
          <h2>关系列表</h2>
          <n-tag size="tiny" type="default">{{ visibleEdges.length }} 条</n-tag>
        </div>

        <n-scrollbar class="list-scroll">
          <div v-if="visibleEdges.length === 0" class="list-empty">
            <div class="empty-icon">🔗</div>
            <p>暂无关系数据</p>
            <p class="empty-sub">点击右上角「新建关系」开始创建</p>
          </div>

          <template v-else>
            <div class="relation-list">
              <div
                v-for="edge in visibleEdges"
                :key="edge.id"
                class="relation-item"
                :class="{ active: selectedEdgeId === edge.id }"
                @click="selectEdgeById(edge.id)"
              >
                <div class="relation-line">
                  <span class="rel-name">{{ getCharName(edge.source) }}</span>
                  <span class="rel-arrow" :style="{ color: getRelationColor(edge.data?.relation_type) }">→</span>
                  <span class="rel-name">{{ getCharName(edge.target) }}</span>
                </div>
                <div class="relation-meta">
                  <n-tag size="small" :color="getRelationColor(edge.data?.relation_type)">
                    {{ edge.data?.relation_type || '其他' }}
                  </n-tag>
                  <span class="depth-dots" :title="`关系深度 ${edge.data?.depth || 5}/10`">
                    <span v-for="i in 10" :key="i" class="dot" :class="{ filled: i <= (edge.data?.depth || 5) }"></span>
                  </span>
                </div>
                <div v-if="edge.data?.effective_from || edge.data?.expires_at" class="relation-chapters">
                  <span v-if="edge.data?.effective_from" class="chapter-tag">第{{ edge.data.effective_from }}章起</span>
                  <span v-if="edge.data?.expires_at" class="chapter-tag danger">第{{ edge.data.expires_at }}章止</span>
                </div>
              </div>
            </div>
          </template>
        </n-scrollbar>

        <!-- 选中的关系详情编辑区 -->
        <div v-if="selectedEdgeData" class="edge-detail">
          <div class="panel-head inline-head">
            <h3>关系详情</h3>
            <n-button size="small" text @click="selectedEdgeId = null">关闭</n-button>
          </div>
          <n-form label-placement="top" size="small">
            <div class="form-grid-2">
              <n-form-item label="关系类型">
                <n-select v-model:value="editingEdge.relation_type" :options="relationTypeOptions" allow-input />
              </n-form-item>
              <n-form-item label="关系深度">
                <n-slider v-model:value="editingEdge.depth" :min="1" :max="10" :marks="{1:'浅',5:'中',10:'深'}" />
              </n-form-item>
            </div>
            <div class="form-grid-2">
              <n-form-item label="生效起始章节">
                <n-input-number v-model:value="editingEdge.effective_from" :min="0" placeholder="可选" style="width: 100%" />
              </n-form-item>
              <n-form-item label="失效章节">
                <n-input-number v-model:value="editingEdge.expires_at" :min="0" placeholder="可选" style="width: 100%" />
              </n-form-item>
            </div>
          </n-form>
          <div class="detail-actions">
            <n-button size="small" type="primary" @click="saveEdge">保存</n-button>
            <n-button size="small" @click="resetEdgeEdit">重置</n-button>
            <n-popconfirm positive-text="确认" negative-text="取消" @positive-click="deleteEdge">
              <template #trigger>
                <n-button size="small" type="error">删除</n-button>
              </template>
              确认删除这条关系？
            </n-popconfirm>
          </div>
        </div>
      </aside>
    </div>

    <!-- 新建关系弹窗 -->
    <n-modal v-model:show="showAddModal" preset="card" title="新建人物关系" style="width: 480px">
      <n-form label-placement="top">
        <div class="form-grid-2">
          <n-form-item label="源角色">
            <n-select v-model:value="newEdge.source_id" :options="characterOptions" placeholder="选择角色" filterable />
          </n-form-item>
          <n-form-item label="目标角色">
            <n-select v-model:value="newEdge.target_id" :options="characterOptions" placeholder="选择角色" filterable />
          </n-form-item>
        </div>
        <div class="form-grid-2">
          <n-form-item label="关系类型">
            <n-select v-model:value="newEdge.relation_type" :options="relationTypeOptions" allow-input placeholder="如：师徒" />
          </n-form-item>
          <n-form-item label="关系深度（1-10）">
            <n-slider v-model:value="newEdge.depth" :min="1" :max="10" :marks="{1:'浅',5:'中',10:'深'}" />
          </n-form-item>
        </div>
        <div class="form-grid-2">
          <n-form-item label="生效起始章节">
            <n-input-number v-model:value="newEdge.effective_from" :min="0" placeholder="可选" style="width: 100%" />
          </n-form-item>
          <n-form-item label="失效章节">
            <n-input-number v-model:value="newEdge.expires_at" :min="0" placeholder="可选" style="width: 100%" />
          </n-form-item>
        </div>
      </n-form>
      <template #footer>
        <n-button @click="showAddModal = false">取消</n-button>
        <n-button type="primary" :disabled="!canAddRelation" @click="addRelation">确认创建</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, nextTick } from 'vue'
import { useMessage } from 'naive-ui'
import { useProjectStore } from '@/stores/project'
import { listResource, updateResource } from '@/api/resources'
import type { CharacterItem, CharacterRelation } from '@/types/domain'
import { notify } from '@/utils/notify'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

const message = useMessage()
const projectStore = useProjectStore()

const filterRoleType = ref<string | null>(null)
const filterRelationType = ref<string | null>(null)
const searchKeyword = ref('')

const characters = ref<CharacterItem[]>([])
const showAddModal = ref(false)

const vueFlowRef = ref<any>(null)

function fitView(options?: any) {
  vueFlowRef.value?.fitView?.(options)
}

const roleTypeOptions = [
  { label: '主角', value: 'protagonist' },
  { label: '配角', value: 'supporting' },
  { label: '反派', value: 'antagonist' }
]

const roleTypeLabelMap: Record<string, string> = {
  protagonist: '主角',
  supporting: '配角',
  antagonist: '反派'
}

const relationTypeOptions = [
  { label: '师徒', value: '师徒' },
  { label: '兄弟', value: '兄弟' },
  { label: '姐妹', value: '姐妹' },
  { label: '恋人', value: '恋人' },
  { label: '夫妻', value: '夫妻' },
  { label: '父子', value: '父子' },
  { label: '母女', value: '母女' },
  { label: '朋友', value: '朋友' },
  { label: '仇敌', value: '仇敌' },
  { label: '对手', value: '对手' },
  { label: '上下级', value: '上下级' },
  { label: '其他', value: '其他' }
]

const nodeColors: Record<string, string> = {
  protagonist: '#6366f1',
  supporting: '#22c55e',
  antagonist: '#ef4444'
}

const relationColorMap: Record<string, string> = {
  '师徒': '#f59e0b', '兄弟': '#3b82f6', '姐妹': '#ec4899',
  '恋人': '#ef4444', '夫妻': '#ef4444', '父子': '#8b5cf6',
  '母女': '#ec4899', '朋友': '#22c55e', '仇敌': '#dc2626',
  '对手': '#f97316', '上下级': '#64748b', '其他': '#64748b'
}

function getRelationColor(type?: string): string {
  if (!type) return '#64748b'
  return relationColorMap[type] || '#64748b'
}

const newEdge = reactive({
  source_id: null as number | null,
  target_id: null as number | null,
  relation_type: '朋友',
  depth: 5,
  effective_from: null as number | null,
  expires_at: null as number | null
})

const canAddRelation = computed(() => {
  return newEdge.source_id && newEdge.target_id && newEdge.source_id !== newEdge.target_id
})

const characterOptions = computed(() =>
  characters.value.map((c) => ({ label: c.name, value: c.id }))
)

const selectedEdgeId = ref<string | null>(null)
const editingEdge = reactive({
  relation_type: '',
  depth: 5,
  effective_from: null as number | null,
  expires_at: null as number | null
})

const selectedEdgeData = computed(() => {
  if (!selectedEdgeId.value) return null
  return edges.value.find((e) => e.id === selectedEdgeId.value) || null
})

const characterCount = computed(() => characters.value.length)
const relationCount = computed(() => edges.value.length)
const relationTypesCount = computed(() => new Set(edges.value.map((e) => e.data?.relation_type).filter(Boolean)).size)

function getCharName(id: string | number): string {
  const numId = typeof id === 'string' ? parseInt(id) : id
  return characters.value.find((c) => c.id === numId)?.name || `角色${numId}`
}

const nodes = ref<any[]>([])
const edges = ref<any[]>([])

const visibleEdges = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  const roleFilter = filterRoleType.value
  const relFilter = filterRelationType.value

  return edges.value.filter((edge) => {
    const source = characters.value.find((c) => c.id === parseInt(edge.source))
    const target = characters.value.find((c) => c.id === parseInt(edge.target))
    if (!source || !target) return false

    if (roleFilter) {
      if (source.role_type !== roleFilter && target.role_type !== roleFilter) return false
    }

    if (keyword) {
      if (!source.name.toLowerCase().includes(keyword) && !target.name.toLowerCase().includes(keyword)) return false
    }

    if (relFilter && edge.data?.relation_type !== relFilter) return false

    return true
  })
})

function buildNodeStyle(roleType: string): Record<string, string> {
  const color = nodeColors[roleType] || '#475569'
  return {
    background: color,
    color: '#fff',
    border: '2px solid rgba(255,255,255,0.2)',
    borderRadius: '20px',
    padding: '6px 14px',
    fontSize: '13px',
    fontWeight: '500',
    boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
  }
}

function buildNodes(): void {
  const w = 800
  const h = 500
  const cx = w / 2
  const cy = h / 2

  const groups: Record<string, CharacterItem[]> = {
    protagonist: [],
    supporting: [],
    antagonist: []
  }
  characters.value.forEach((c) => {
    if (groups[c.role_type]) groups[c.role_type].push(c)
    else groups.supporting.push(c)
  })

  const radii: Record<string, number> = {
    protagonist: 80,
    supporting: 200,
    antagonist: 320
  }

  const newNodes: any[] = []
  Object.entries(groups).forEach(([type, list]) => {
    const radius = radii[type] || 150
    list.forEach((c, i) => {
      const angle = (i / Math.max(list.length, 1)) * Math.PI * 2 - Math.PI / 2
      newNodes.push({
        id: String(c.id),
        type: 'default',
        position: {
          x: cx + Math.cos(angle) * radius + (Math.random() - 0.5) * 20,
          y: cy + Math.sin(angle) * radius + (Math.random() - 0.5) * 20
        },
        data: { label: c.name },
        style: buildNodeStyle(c.role_type),
        draggable: true,
        selectable: true
      })
    })
  })

  nodes.value = newNodes
}

function buildEdges(): void {
  const edgeMap = new Map<string, any>()

  characters.value.forEach((c) => {
    let relations: CharacterRelation[] = []
    try {
      if (typeof c.character_relations === 'string') {
        relations = JSON.parse(c.character_relations || '[]')
      } else if (Array.isArray(c.character_relations)) {
        relations = c.character_relations
      }
    } catch { /* ignore */ }

    relations.forEach((rel) => {
      const sourceId = c.id
      const targetId = rel.target_id
      const key = `${sourceId}-${targetId}`
      const reverseKey = `${targetId}-${sourceId}`

      if (edgeMap.has(reverseKey)) return

      if (!edgeMap.has(key)) {
        const color = getRelationColor(rel.relation_type)
        const isExpired = !!rel.expires_at
        edgeMap.set(key, {
          id: key,
          source: String(sourceId),
          target: String(targetId),
          type: 'smoothstep',
          animated: false,
          style: {
            stroke: color,
            strokeWidth: rel.depth >= 7 ? 3 : rel.depth >= 4 ? 2 : 1.5,
            strokeDasharray: isExpired ? '6 4' : 'none'
          },
          data: {
            relation_type: rel.relation_type,
            depth: rel.depth,
            effective_from: rel.effective_from ?? null,
            expires_at: rel.expires_at ?? null
          },
          label: rel.relation_type,
          labelStyle: { fill: '#cbd5e1', fontSize: 11, fontWeight: 500 },
          labelBgPadding: [6, 3],
          labelBgBorderRadius: 4,
          labelBgStyle: { fill: '#1e2228', fillOpacity: 0.85 },
          markerEnd: 'arrowclosed'
        })
      }
    })
  })

  edges.value = Array.from(edgeMap.values())
}

function initGraph(): void {
  buildNodes()
  buildEdges()
  if (vueFlowRef.value) {
    nextTick(() => {
      fitView({ padding: 0.2, duration: 300 })
    })
  }
}

function onVueFlowInit(instance: any): void {
  vueFlowRef.value = instance
  if (nodes.value.length > 0) {
    nextTick(() => {
      fitView({ padding: 0.2, duration: 300 })
    })
  }
}

function resetLayout(): void {
  initGraph()
  message.success('布局已重置')
}

function onNodeClick(_event: any): void {
  selectedEdgeId.value = null
}

function onEdgeClick(event: any): void {
  selectEdgeById(event.edge.id)
}

function onPaneClick(): void {
  selectedEdgeId.value = null
}

function selectEdgeById(edgeId: string): void {
  selectedEdgeId.value = edgeId
  const edge = edges.value.find((e) => e.id === edgeId)
  if (edge) {
    Object.assign(editingEdge, {
      relation_type: edge.data?.relation_type || '其他',
      depth: edge.data?.depth || 5,
      effective_from: edge.data?.effective_from,
      expires_at: edge.data?.expires_at
    })
  }
}

function resetEdgeEdit(): void {
  if (!selectedEdgeData.value) return
  const edge = selectedEdgeData.value
  Object.assign(editingEdge, {
    relation_type: edge.data?.relation_type || '其他',
    depth: edge.data?.depth || 5,
    effective_from: edge.data?.effective_from,
    expires_at: edge.data?.expires_at
  })
}

async function saveEdge(): Promise<void> {
  if (!selectedEdgeId.value) return
  const edge = edges.value.find((e) => e.id === selectedEdgeId.value)
  if (!edge) return

  const sourceId = parseInt(edge.source)
  const targetId = parseInt(edge.target)
  const source = characters.value.find((c) => c.id === sourceId)
  if (!source) {
    notify.error('找不到源角色')
    return
  }

  let relations: CharacterRelation[] = []
  try {
    if (typeof source.character_relations === 'string') {
      relations = JSON.parse(source.character_relations || '[]')
    } else if (Array.isArray(source.character_relations)) {
      relations = [...source.character_relations]
    }
  } catch { /* ignore */ }

  const idx = relations.findIndex((r) => r.target_id === targetId)
  if (idx >= 0) {
    relations[idx] = {
      ...relations[idx],
      relation_type: editingEdge.relation_type,
      depth: editingEdge.depth,
      effective_from: editingEdge.effective_from,
      expires_at: editingEdge.expires_at
    }
  }

  try {
    await updateResource<CharacterItem>('characters', sourceId, {
      character_relations: JSON.stringify(relations)
    })
    ;(source.character_relations as any) = JSON.stringify(relations)

    const color = getRelationColor(editingEdge.relation_type)
    const isExpired = !!editingEdge.expires_at
    edge.data = {
      relation_type: editingEdge.relation_type,
      depth: editingEdge.depth,
      effective_from: editingEdge.effective_from,
      expires_at: editingEdge.expires_at
    }
    edge.style = {
      stroke: color,
      strokeWidth: editingEdge.depth >= 7 ? 3 : editingEdge.depth >= 4 ? 2 : 1.5,
      strokeDasharray: isExpired ? '6 4' : 'none'
    }
    edge.label = editingEdge.relation_type

    message.success('关系已更新')
  } catch {
    notify.error('保存失败')
  }
}

async function deleteEdge(): Promise<void> {
  if (!selectedEdgeId.value) return
  const edge = edges.value.find((e) => e.id === selectedEdgeId.value)
  if (!edge) return

  const sourceId = parseInt(edge.source)
  const targetId = parseInt(edge.target)
  const source = characters.value.find((c) => c.id === sourceId)
  if (!source) return

  let relations: CharacterRelation[] = []
  try {
    if (typeof source.character_relations === 'string') {
      relations = JSON.parse(source.character_relations || '[]')
    } else if (Array.isArray(source.character_relations)) {
      relations = [...source.character_relations]
    }
  } catch { /* ignore */ }

  const filtered = relations.filter((r) => r.target_id !== targetId)

  try {
    await updateResource<CharacterItem>('characters', sourceId, {
      character_relations: JSON.stringify(filtered)
    })
    ;(source.character_relations as any) = JSON.stringify(filtered)
    edges.value = edges.value.filter((e) => e.id !== selectedEdgeId.value)
    selectedEdgeId.value = null
    message.success('关系已删除')
  } catch {
    notify.error('删除失败')
  }
}

async function addRelation(): Promise<void> {
  if (!newEdge.source_id || !newEdge.target_id) return
  if (newEdge.source_id === newEdge.target_id) {
    notify.warning('不能和自己建立关系')
    return
  }

  const source = characters.value.find((c) => c.id === newEdge.source_id)
  if (!source) return

  let relations: CharacterRelation[] = []
  try {
    if (typeof source.character_relations === 'string') {
      relations = JSON.parse(source.character_relations || '[]')
    } else if (Array.isArray(source.character_relations)) {
      relations = [...source.character_relations]
    }
  } catch { /* ignore */ }

  if (relations.some((r) => r.target_id === newEdge.target_id)) {
    notify.warning('该关系已存在')
    return
  }

  relations.push({
    target_id: newEdge.target_id,
    relation_type: newEdge.relation_type,
    depth: newEdge.depth,
    effective_from: newEdge.effective_from,
    expires_at: newEdge.expires_at
  })

  try {
    await updateResource<CharacterItem>('characters', source.id, {
      character_relations: JSON.stringify(relations)
    })
    ;(source.character_relations as any) = JSON.stringify(relations)
    message.success('关系已创建')
    showAddModal.value = false
    initGraph()
  } catch {
    notify.error('创建失败')
  }
}

async function loadCharacters(): Promise<void> {
  const pid = projectStore.currentProject?.id
  if (!pid) return
  try {
    const list = await listResource<CharacterItem>(pid, 'characters')
    characters.value = list
    initGraph()
  } catch {
    notify.error('加载角色列表失败')
  }
}

function refreshData(): void {
  loadCharacters()
  message.success('已刷新')
}

const { loading } = useProjectDataLoader(loadCharacters)
</script>

<style scoped>
.relations-page {
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
  display: flex;
  align-items: center;
  gap: 0px;
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
  min-width: 55px;
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
}

.stat-divider {
  width: 1px;
  height: 24px;
  background: var(--n-border-color, #2a2f3a);
}

/* ===== 筛选栏 ===== */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  flex-shrink: 0;
}

.filter-spacer {
  flex: 1;
}

/* ===== 工作区 ===== */
.workbench {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(500px, 1fr) 340px;
  gap: 12px;
  min-height: 0;
}

/* ===== 通用面板 ===== */
.graph-panel,
.list-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.panel-head h2 {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
}

.panel-head h3 {
  font-size: 13px;
  font-weight: 600;
  margin: 0;
}

.inline-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.graph-tools {
  display: flex;
  gap: 4px;
}

/* ===== 图谱面板 ===== */
.graph-container {
  flex: 1;
  position: relative;
  min-height: 300px;
}

.vue-flow-container {
  width: 100%;
  height: 100%;
  background: #0f1115;
}

.graph-legend {
  display: flex;
  gap: 24px;
  padding: 10px 16px;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
  background: rgba(0, 0, 0, 0.2);
  flex-wrap: wrap;
}

.legend-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.legend-title {
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #94a3b8;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-line {
  width: 16px;
  height: 2px;
  border-radius: 1px;
}

/* ===== 右侧列表面板 ===== */
.list-scroll {
  flex: 1;
  min-height: 0;
}

.list-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 50px 20px;
  gap: 10px;
  color: var(--n-text-color-3, #6b7280);
  font-size: 13px;
}

.list-empty .empty-icon {
  font-size: 36px;
}

.list-empty p {
  margin: 0;
}

.empty-sub {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

.relation-list {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.relation-item {
  padding: 12px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  background: var(--n-color-1, #1e2228);
}

.relation-item:hover {
  border-color: #6366f1;
}

.relation-item.active {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
}

.relation-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 8px;
}

.rel-name {
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
}

.rel-arrow {
  font-size: 16px;
  font-weight: bold;
}

.relation-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.depth-dots {
  display: flex;
  gap: 2px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #334155;
}

.dot.filled {
  background: #22c55e;
}

.relation-chapters {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--n-border-color, #2a2f3a);
}

.chapter-tag {
  padding: 2px 6px;
  background: rgba(34, 211, 238, 0.15);
  color: #67e8f9;
  border-radius: 4px;
  font-size: 10px;
}

.chapter-tag.danger {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
}

/* ===== 关系详情 ===== */
.edge-detail {
  margin: 0 12px 12px;
  padding: 12px;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.edge-detail .panel-head {
  padding: 0 0 10px 0;
  margin-bottom: 10px;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 16px;
}

.detail-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
}
</style>
