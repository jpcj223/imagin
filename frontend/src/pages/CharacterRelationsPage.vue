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
      <!-- 视图模式切换 -->
      <div class="filter-group">
        <span class="filter-label">视图</span>
        <n-radio-group v-model:value="viewMode" size="small" @update:value="onViewModeChange">
          <n-radio-button value="all">全部展示</n-radio-button>
          <n-radio-button value="focus">聚焦模式</n-radio-button>
        </n-radio-group>
      </div>

      <!-- 聚焦模式下的角色选择 -->
      <div v-if="viewMode === 'focus'" class="filter-group">
        <span class="filter-label">聚焦角色</span>
        <n-select
          v-model:value="focusCharacterId"
          :options="characterOptions"
          placeholder="选择聚焦角色"
          filterable
          style="width: 160px"
          @update:value="onFocusCharacterChange"
        />
        <n-button size="small" text @click="viewMode = 'all'">
          ← 返回全局
        </n-button>
      </div>

      <div class="filter-divider"></div>

      <!-- 原有筛选 -->
      <n-select v-model:value="filterRoleType" placeholder="按角色类型筛选" clearable :options="roleTypeOptions" style="width: 140px" />
      <n-select v-model:value="filterRelationType" placeholder="按关系类型筛选" clearable :options="relationTypeOptions" style="width: 140px" />
      <n-select v-model:value="filterRelationStatus" placeholder="按关系状态筛选" clearable :options="relationStatusOptions" style="width: 130px" />
      <n-input v-model:value="searchKeyword" clearable placeholder="搜索角色名" style="width: 200px">
        <template #prefix>🔍</template>
      </n-input>

      <div class="filter-spacer"></div>
      <n-button size="small" text @click="toggleGroupPanel">
        {{ showGroupPanel ? '收起分组' : '展开分组' }}
      </n-button>
      <n-button size="small" text @click="refreshData">↻ 刷新</n-button>
    </div>

    <!-- 主体：左分组面板 + 中图谱 + 右列表 -->
    <div class="workbench" :class="{ 'no-group-panel': !showGroupPanel }">
      <!-- 左：连通分量分组面板 -->
      <aside v-if="showGroupPanel" class="group-panel">
        <div class="panel-head">
          <h2>关系分组</h2>
          <n-tag size="tiny" type="default">{{ connectedComponents.length }} 组</n-tag>
        </div>
        <n-scrollbar class="group-scroll">
          <div v-if="connectedComponents.length === 0" class="list-empty">
            <div class="empty-icon">🔗</div>
            <p>暂无分组</p>
          </div>
          <template v-else>
            <div
              v-for="(comp, idx) in connectedComponents"
              :key="idx"
              class="group-item"
              :class="{ active: activeComponentIndex === idx }"
              @click="focusOnComponent(idx)"
            >
              <div class="group-header">
                <span class="group-name">第 {{ idx + 1 }} 组</span>
                <span class="group-count">{{ comp.length }} 人</span>
              </div>
              <div class="group-members">
                <span
                  v-for="charId in comp.slice(0, 5)"
                  :key="charId"
                  class="member-tag"
                >
                  {{ getCharName(charId) }}
                </span>
                <span v-if="comp.length > 5" class="member-more">
                  +{{ comp.length - 5 }} 更多
                </span>
              </div>
            </div>
          </template>
        </n-scrollbar>
      </aside>

      <!-- 中：Vue Flow 关系图谱 -->
      <section class="graph-panel">
        <div class="panel-head">
          <h2>
            关系图谱
            <n-tag v-if="viewMode === 'focus'" size="tiny" type="info" style="margin-left: 8px">
              聚焦：{{ focusCharacterId ? getCharName(focusCharacterId) : '无' }}
            </n-tag>
            <n-tag v-if="connectMode" size="tiny" type="warning" style="margin-left: 8px">
              连线模式
            </n-tag>
          </h2>
          <div class="graph-tools">
            <n-button
              size="small"
              :type="connectMode ? 'warning' : 'default'"
              @click="toggleConnectMode"
            >
              {{ connectMode ? '退出连线' : '连线模式' }}
            </n-button>
            <n-button size="small" text @click="resetLayout">重置布局</n-button>
            <n-button size="small" text @click="fitView">适应视图</n-button>
          </div>
        </div>

        <!-- 连线模式提示条 -->
        <div v-if="connectMode" class="connect-hint-bar">
          <span class="hint-icon">💡</span>
          <span v-if="!connectSourceId">点击一个角色作为关系起点</span>
          <span v-else>
            已选起点：<strong>{{ getCharName(connectSourceId) }}</strong>，点击另一个角色建立关系
            <n-button size="tiny" text @click="cancelConnect">取消</n-button>
          </span>
        </div>

        <div class="graph-container">
          <VueFlow
            ref="vueFlowRef"
            :nodes="displayNodes"
            :edges="displayEdges"
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
          <div class="legend-group">
            <span class="legend-title">关系状态</span>
            <span class="legend-item">
              <span class="legend-line" style="background: #22c55e"></span>
              生效中
            </span>
            <span class="legend-item">
              <span class="legend-line" style="background: #64748b; background-image: repeating-linear-gradient(90deg, transparent, transparent 3px, #0f1115 3px, #0f1115 5px)"></span>
              已失效
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
                <!-- 双向关系标记 -->
                <div v-if="isBidirectional(edge)" class="relation-bidir">
                  <span class="bidir-tag">↔ 双向</span>
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

          <!-- 双向关系提示 -->
          <div v-if="bidirectionalInfo" class="bidir-notice">
            <span class="bidir-icon">↔</span>
            <span class="bidir-text">{{ bidirectionalInfo }}</span>
          </div>

          <n-form label-placement="top" size="small">
            <div class="form-grid-2">
              <n-form-item label="源角色">
                <n-input :value="getCharName(selectedEdgeData.source)" readonly />
              </n-form-item>
              <n-form-item label="目标角色">
                <n-input :value="getCharName(selectedEdgeData.target)" readonly />
              </n-form-item>
            </div>
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
            <n-select
              v-model:value="newEdge.source_id"
              :options="characterOptions"
              placeholder="选择角色"
              filterable
              @update:value="onSourceCharacterChange"
            />
          </n-form-item>
          <n-form-item label="目标角色">
            <n-select
              v-model:value="newEdge.target_id"
              :options="targetCharacterOptions"
              placeholder="选择角色"
              filterable
            />
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

    <!-- 快速建立关系弹窗（连线模式用） -->
    <n-modal v-model:show="showQuickAddModal" preset="card" title="快速建立关系" style="width: 400px">
      <div class="quick-add-preview">
        <div class="quick-add-names">
          <span class="quick-name">{{ quickAddEdge.source_name }}</span>
          <span class="quick-arrow">→</span>
          <span class="quick-name">{{ quickAddEdge.target_name }}</span>
        </div>
      </div>
      <n-form label-placement="top" size="small">
        <div class="form-grid-2">
          <n-form-item label="关系类型">
            <n-select v-model:value="quickAddEdge.relation_type" :options="relationTypeOptions" allow-input placeholder="如：师徒" />
          </n-form-item>
          <n-form-item label="关系深度">
            <n-slider v-model:value="quickAddEdge.depth" :min="1" :max="10" :marks="{1:'浅',5:'中',10:'深'}" />
          </n-form-item>
        </div>
      </n-form>
      <template #footer>
        <n-button @click="cancelQuickAdd">取消</n-button>
        <n-button type="primary" @click="confirmQuickAdd">确认创建</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, nextTick, watch, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useDictStore } from '@/stores/dict'
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
const dictStore = useDictStore()

// ==================== 筛选状态 ====================
const filterRoleType = ref<string | null>(null)
const filterRelationType = ref<string | null>(null)
const filterRelationStatus = ref<string | null>(null) // 'active' | 'expired' | null
const searchKeyword = ref('')

// ==================== 视图模式 ====================
type ViewMode = 'all' | 'focus'
const viewMode = ref<ViewMode>('focus') // 默认聚焦模式
const focusCharacterId = ref<number | null>(null)
const activeComponentIndex = ref<number | null>(null)

// ==================== 连线模式 ====================
const connectMode = ref(false)
const connectSourceId = ref<number | null>(null)
const showQuickAddModal = ref(false)

// ==================== 分组面板 ====================
const showGroupPanel = ref(true)

// ==================== 数据 ====================
const characters = ref<CharacterItem[]>([])
const showAddModal = ref(false)
const vueFlowRef = ref<any>(null)

function fitView(options?: any) {
  vueFlowRef.value?.fitView?.(options)
}

// ==================== 字典 & 选项 ====================
const roleTypeOptions = computed(() => dictStore.options('character_role'))

const roleTypeLabelMap = computed(() => {
  const map: Record<string, string> = {}
  roleTypeOptions.value.forEach((item) => {
    map[item.value] = item.label
  })
  return map
})

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

const relationStatusOptions = [
  { label: '生效中', value: 'active' },
  { label: '已失效', value: 'expired' }
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

// ==================== 新建关系弹窗 ====================
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

/**
 * 所有角色选项（用于源角色选择、聚焦角色选择等）
 */
const characterOptions = computed(() =>
  characters.value.map((c) => ({ label: c.name, value: c.id }))
)

/**
 * 功能1：目标角色选项（动态计算，已关联的角色置灰）
 * - 源角色自身：disabled
 * - 已和源角色建立过关系的：disabled
 * - 其他：可选
 */
const targetCharacterOptions = computed<Array<{ label: string; value: number; disabled?: boolean }>>(() => {
  const sourceId = newEdge.source_id
  if (!sourceId) {
    return characters.value.map((c) => ({ label: c.name, value: c.id, disabled: false }))
  }

  // 获取源角色已关联的目标 ID 集合
  const relatedIds = getRelatedCharacterIds(sourceId)

  return characters.value.map((c) => {
    const isSelf = c.id === sourceId
    const isRelated = relatedIds.has(c.id)
    const disabled = isSelf || isRelated

    let label = c.name
    if (isSelf) {
      label = `${c.name}（自身）`
    } else if (isRelated) {
      label = `${c.name}（已关联）`
    }

    return {
      label,
      value: c.id,
      disabled
    }
  })
})

/**
 * 获取指定角色的所有直接关联角色 ID（从 character_relations 中解析）
 */
function getRelatedCharacterIds(characterId: number): Set<number> {
  const char = characters.value.find((c) => c.id === characterId)
  if (!char) return new Set()

  const relatedIds = new Set<number>()
  let relations: CharacterRelation[] = []
  try {
    if (typeof char.character_relations === 'string') {
      relations = JSON.parse(char.character_relations || '[]')
    } else if (Array.isArray(char.character_relations)) {
      relations = char.character_relations
    }
  } catch { /* ignore */ }

  relations.forEach((rel) => {
    relatedIds.add(rel.target_id)
  })

  return relatedIds
}

/**
 * 源角色变化时，清空已选的目标角色（如果目标角色不可选）
 */
function onSourceCharacterChange(): void {
  if (newEdge.target_id) {
    const targetOpt = targetCharacterOptions.value.find((o) => o.value === newEdge.target_id)
    if (targetOpt?.disabled) {
      newEdge.target_id = null
    }
  }
}

// ==================== 关系详情 ====================
const selectedEdgeId = ref<string | null>(null)
const editingEdge = reactive({
  relation_type: '',
  depth: 5,
  effective_from: null as number | null,
  expires_at: null as number | null
})

const selectedEdgeData = computed(() => {
  if (!selectedEdgeId.value) return null
  return allEdges.value.find((e) => e.id === selectedEdgeId.value) || null
})

/**
 * 功能6：检查关系是否为双向关系
 * 即：源→目标 和 目标→源 都存在关系记录
 */
function isBidirectional(edge: any): boolean {
  const sourceId = edge.source
  const targetId = edge.target
  // 检查是否存在反向边
  return allEdges.value.some(
    (e) => e.source === targetId && e.target === sourceId
  )
}

/**
 * 功能6：获取双向关系的描述信息
 */
const bidirectionalInfo = computed(() => {
  if (!selectedEdgeData.value) return null
  const edge = selectedEdgeData.value
  const sourceId = edge.source
  const targetId = edge.target

  // 查找反向边
  const reverseEdge = allEdges.value.find(
    (e) => e.source === targetId && e.target === sourceId
  )

  if (!reverseEdge) return null

  const sourceName = getCharName(sourceId)
  const targetName = getCharName(targetId)
  const reverseType = reverseEdge.data?.relation_type || '其他'
  const forwardType = edge.data?.relation_type || '其他'

  if (reverseType === forwardType) {
    return `${targetName} → ${sourceName} 也是「${forwardType}」关系`
  } else {
    return `${targetName} → ${sourceName} 是「${reverseType}」关系（与正向不同）`
  }
})

// ==================== 统计 ====================
const characterCount = computed(() => characters.value.length)
const relationCount = computed(() => allEdges.value.length)
const relationTypesCount = computed(() => new Set(allEdges.value.map((e) => e.data?.relation_type).filter(Boolean)).size)

// ==================== 工具函数 ====================
function getCharName(id: string | number): string {
  const numId = typeof id === 'string' ? parseInt(id) : id
  return characters.value.find((c) => c.id === numId)?.name || `角色${numId}`
}

// ==================== 全量节点和边（构建后不变，筛选基于此） ====================
const allNodes = ref<any[]>([])
const allEdges = ref<any[]>([])

// ==================== 连通分量计算（功能3） ====================
/**
 * 使用 BFS 算法计算图的连通分量
 * 将所有节点按连通性分成若干组，每组是一个连通分量
 * @returns 每个连通分量的节点 ID 数组（number 类型）
 */
const connectedComponents = computed<number[][]>(() => {
  const nodeIds = allNodes.value.map((n) => n.id)
  if (nodeIds.length === 0) return []

  // 构建无向邻接表
  const adj = new Map<string, Set<string>>()
  nodeIds.forEach((id) => adj.set(id, new Set()))

  allEdges.value.forEach((edge) => {
    adj.get(edge.source)?.add(edge.target)
    adj.get(edge.target)?.add(edge.source)
  })

  // BFS 遍历找所有连通分量
  const visited = new Set<string>()
  const components: number[][] = []

  nodeIds.forEach((id) => {
    if (visited.has(id)) return
    const component: number[] = []
    const queue: string[] = [id]
    visited.add(id)

    while (queue.length > 0) {
      const curr = queue.shift()!
      component.push(parseInt(curr))

      const neighbors = adj.get(curr)
      if (neighbors) {
        neighbors.forEach((neighbor) => {
          if (!visited.has(neighbor)) {
            visited.add(neighbor)
            queue.push(neighbor)
          }
        })
      }
    }

    // 按角色数量降序排序（大的组在前）
    components.push(component)
  })

  // 按组大小降序排列
  components.sort((a, b) => b.length - a.length)

  return components
})

// ==================== 聚焦子图计算（功能2） ====================
/**
 * 获取聚焦模式下应显示的节点 ID 集合
 * - 如果有聚焦角色：聚焦角色 + 其一阶邻居 + 邻居之间的边
 * - 如果没有聚焦角色：返回全部（等同于全部展示）
 */
const focusNodeIds = computed<Set<number>>(() => {
  if (viewMode.value !== 'focus') return new Set()

  // 如果是通过分组面板进入的聚焦，使用分组节点
  if (activeComponentIndex.value !== null && connectedComponents.value[activeComponentIndex.value]) {
    return new Set(connectedComponents.value[activeComponentIndex.value])
  }

  if (!focusCharacterId.value) {
    // 没有聚焦角色，返回所有节点
    return new Set(characters.value.map((c) => c.id))
  }

  // 计算一阶邻居子图
  const centerId = focusCharacterId.value
  const nodeIdSet = new Set<number>([centerId])

  // 添加中心角色的直接邻居
  const centerRelations = getRelatedCharacterIds(centerId)
  centerRelations.forEach((id) => nodeIdSet.add(id))

  // 也检查反向关系（其他角色指向中心角色的）
  characters.value.forEach((c) => {
    if (c.id === centerId) return
    const rels = getRelatedCharacterIds(c.id)
    if (rels.has(centerId)) {
      nodeIdSet.add(c.id)
    }
  })

  return nodeIdSet
})

/**
 * 功能2 & 功能5：经过视图模式 + 所有筛选后应显示的节点和边
 * 筛选优先级：视图模式(focus/all) → 角色类型 → 关键词 → 关系类型 → 关系状态
 */
const displayNodes = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  const roleFilter = filterRoleType.value
  const focusIds = focusNodeIds.value

  return allNodes.value.filter((node) => {
    const char = characters.value.find((c) => c.id === parseInt(node.id))
    if (!char) return false

    // 视图模式筛选
    if (viewMode.value === 'focus' && focusIds.size > 0) {
      if (!focusIds.has(char.id)) return false
    }

    // 角色类型筛选
    if (roleFilter && char.role_type !== roleFilter) return false

    // 关键词筛选
    if (keyword && !char.name.toLowerCase().includes(keyword)) return false

    return true
  })
})

const displayEdges = computed(() => {
  const relFilter = filterRelationType.value
  const statusFilter = filterRelationStatus.value
  const displayNodeIds = new Set(displayNodes.value.map((n) => n.id))

  return allEdges.value.filter((edge) => {
    // 两端节点都必须在显示节点中
    if (!displayNodeIds.has(edge.source) || !displayNodeIds.has(edge.target)) return false

    // 关系类型筛选
    if (relFilter && edge.data?.relation_type !== relFilter) return false

    // 关系状态筛选
    if (statusFilter) {
      const isExpired = !!edge.data?.expires_at
      if (statusFilter === 'active' && isExpired) return false
      if (statusFilter === 'expired' && !isExpired) return false
    }

    return true
  })
})

// 右侧关系列表使用 displayEdges（与图中显示一致）
const visibleEdges = computed(() => displayEdges.value)

// ==================== 节点样式构建 ====================
function buildNodeStyle(roleType: string, isFocusCenter: boolean = false): Record<string, string> {
  const color = nodeColors[roleType] || '#475569'
  const style: Record<string, string> = {
    background: color,
    color: '#fff',
    border: isFocusCenter ? '3px solid #fbbf24' : '2px solid rgba(255,255,255,0.2)',
    borderRadius: '20px',
    padding: '6px 14px',
    fontSize: '13px',
    fontWeight: '500',
    boxShadow: isFocusCenter
      ? '0 0 16px rgba(251, 191, 36, 0.6), 0 2px 8px rgba(0,0,0,0.3)'
      : '0 2px 8px rgba(0,0,0,0.3)'
  }
  return style
}

// ==================== 构建节点（同心圆环布局） ====================
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
      const isFocusCenter = focusCharacterId.value === c.id
      newNodes.push({
        id: String(c.id),
        type: 'default',
        position: {
          x: cx + Math.cos(angle) * radius + (Math.random() - 0.5) * 20,
          y: cy + Math.sin(angle) * radius + (Math.random() - 0.5) * 20
        },
        data: { label: c.name },
        style: buildNodeStyle(c.role_type, isFocusCenter),
        draggable: true,
        selectable: true
      })
    })
  })

  allNodes.value = newNodes
}

// ==================== 构建边 ====================
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

      // 注意：这里不再跳过反向边，保留所有方向的关系
      // 这样可以正确显示双向关系（两条边）
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

  allEdges.value = Array.from(edgeMap.values())
}

// ==================== 初始化图谱 ====================
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
  if (allNodes.value.length > 0) {
    nextTick(() => {
      fitView({ padding: 0.2, duration: 300 })
    })
  }
}

function resetLayout(): void {
  initGraph()
  message.success('布局已重置')
}

// ==================== 节点点击（功能2：切换聚焦 + 功能4：连线模式） ====================
function onNodeClick(event: any): void {
  const nodeId = parseInt(event.node.id)

  // 功能4：连线模式下的点击处理
  if (connectMode.value) {
    handleConnectClick(nodeId)
    return
  }

  // 功能2：单击节点切换为聚焦该节点
  if (viewMode.value === 'focus') {
    focusCharacterId.value = nodeId
    activeComponentIndex.value = null // 清除分组聚焦
    // 更新节点样式（聚焦高亮）
    updateNodeFocusStyle()
  } else {
    // 全部模式下点击节点不切换聚焦，仅清除边选中
    selectedEdgeId.value = null
  }

  selectedEdgeId.value = null
}

/**
 * 更新节点的聚焦高亮样式
 */
function updateNodeFocusStyle(): void {
  allNodes.value.forEach((node) => {
    const char = characters.value.find((c) => c.id === parseInt(node.id))
    if (char) {
      const isFocusCenter = focusCharacterId.value === char.id
      node.style = buildNodeStyle(char.role_type, isFocusCenter)
    }
  })
}

// 监听聚焦角色变化，更新节点样式
watch(focusCharacterId, () => {
  updateNodeFocusStyle()
  nextTick(() => {
    fitView({ padding: 0.3, duration: 300 })
  })
})

// ==================== 边点击 ====================
function onEdgeClick(event: any): void {
  selectEdgeById(event.edge.id)
}

function onPaneClick(): void {
  selectedEdgeId.value = null
  // 连线模式下点击空白处取消
  if (connectMode.value) {
    cancelConnect()
  }
}

function selectEdgeById(edgeId: string): void {
  selectedEdgeId.value = edgeId
  const edge = allEdges.value.find((e) => e.id === edgeId)
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

// ==================== 保存边 ====================
async function saveEdge(): Promise<void> {
  if (!selectedEdgeId.value) return
  const edge = allEdges.value.find((e) => e.id === selectedEdgeId.value)
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

// ==================== 删除边 ====================
async function deleteEdge(): Promise<void> {
  if (!selectedEdgeId.value) return
  const edge = allEdges.value.find((e) => e.id === selectedEdgeId.value)
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
    allEdges.value = allEdges.value.filter((e) => e.id !== selectedEdgeId.value)
    selectedEdgeId.value = null
    message.success('关系已删除')
  } catch {
    notify.error('删除失败')
  }
}

// ==================== 新建关系 ====================
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

// ==================== 功能4：连线模式 ====================
/**
 * 切换连线模式
 */
function toggleConnectMode(): void {
  connectMode.value = !connectMode.value
  if (!connectMode.value) {
    connectSourceId.value = null
    showQuickAddModal.value = false
  }
}

/**
 * 连线模式下的节点点击处理
 * 第一次点击选择源角色，第二次点击选择目标角色并弹出快速创建弹窗
 */
function handleConnectClick(nodeId: number): void {
  if (!connectSourceId.value) {
    // 第一次点击：选择源角色
    connectSourceId.value = nodeId
    message.info(`已选择 ${getCharName(nodeId)} 作为起点，点击另一个角色建立关系`)
  } else {
    // 第二次点击：选择目标角色
    const sourceId = connectSourceId.value
    const targetId = nodeId

    // 检查：不能连到自己
    if (sourceId === targetId) {
      notify.warning('不能和自己建立关系')
      return
    }

    // 检查：已存在关系
    const relatedIds = getRelatedCharacterIds(sourceId)
    if (relatedIds.has(targetId)) {
      notify.warning(`${getCharName(sourceId)} 和 ${getCharName(targetId)} 已存在关系`)
      connectSourceId.value = null
      return
    }

    // 打开快速建立关系弹窗
    openQuickAddModal(sourceId, targetId)
  }
}

/**
 * 取消连线
 */
function cancelConnect(): void {
  connectSourceId.value = null
  connectMode.value = false
}

// ==================== 功能4：快速建立关系弹窗 ====================
const quickAddEdge = reactive({
  source_id: null as number | null,
  target_id: null as number | null,
  source_name: '',
  target_name: '',
  relation_type: '朋友',
  depth: 5
})

/**
 * 打开快速建立关系弹窗
 */
function openQuickAddModal(sourceId: number, targetId: number): void {
  quickAddEdge.source_id = sourceId
  quickAddEdge.target_id = targetId
  quickAddEdge.source_name = getCharName(sourceId)
  quickAddEdge.target_name = getCharName(targetId)
  quickAddEdge.relation_type = '朋友'
  quickAddEdge.depth = 5
  showQuickAddModal.value = true
}

/**
 * 取消快速添加
 */
function cancelQuickAdd(): void {
  showQuickAddModal.value = false
  connectSourceId.value = null
  connectMode.value = false
}

/**
 * 确认快速添加关系
 */
async function confirmQuickAdd(): Promise<void> {
  if (!quickAddEdge.source_id || !quickAddEdge.target_id) return

  const source = characters.value.find((c) => c.id === quickAddEdge.source_id)
  if (!source) return

  let relations: CharacterRelation[] = []
  try {
    if (typeof source.character_relations === 'string') {
      relations = JSON.parse(source.character_relations || '[]')
    } else if (Array.isArray(source.character_relations)) {
      relations = [...source.character_relations]
    }
  } catch { /* ignore */ }

  if (relations.some((r) => r.target_id === quickAddEdge.target_id)) {
    notify.warning('该关系已存在')
    return
  }

  relations.push({
    target_id: quickAddEdge.target_id,
    relation_type: quickAddEdge.relation_type,
    depth: quickAddEdge.depth,
    effective_from: null,
    expires_at: null
  })

  try {
    await updateResource<CharacterItem>('characters', source.id, {
      character_relations: JSON.stringify(relations)
    })
    ;(source.character_relations as any) = JSON.stringify(relations)
    message.success('关系已创建')
    showQuickAddModal.value = false
    connectSourceId.value = null
    connectMode.value = false
    initGraph()
  } catch {
    notify.error('创建失败')
  }
}

// ==================== 功能2：视图模式切换 ====================
function onViewModeChange(mode: ViewMode): void {
  if (mode === 'focus') {
    // 切换到聚焦模式时，如果没有聚焦角色，自动找主角
    if (!focusCharacterId.value) {
      const protagonist = characters.value.find((c) => c.role_type === 'protagonist')
      if (protagonist) {
        focusCharacterId.value = protagonist.id
      }
    }
    activeComponentIndex.value = null
  } else {
    // 切换到全部模式时，清除聚焦相关状态
    activeComponentIndex.value = null
  }
  nextTick(() => {
    fitView({ padding: 0.2, duration: 300 })
  })
}

function onFocusCharacterChange(): void {
  activeComponentIndex.value = null // 手动选择角色时清除分组聚焦
  nextTick(() => {
    fitView({ padding: 0.3, duration: 300 })
  })
}

// ==================== 功能3：分组面板操作 ====================
/**
 * 聚焦到某个连通分量分组
 */
function focusOnComponent(index: number): void {
  activeComponentIndex.value = index
  viewMode.value = 'focus'
  focusCharacterId.value = null // 清除单角色聚焦
  nextTick(() => {
    fitView({ padding: 0.3, duration: 300 })
  })
}

/**
 * 切换分组面板显示
 */
function toggleGroupPanel(): void {
  showGroupPanel.value = !showGroupPanel.value
}

// ==================== 数据加载 ====================
async function loadCharacters(): Promise<void> {
  const pid = projectStore.currentProject?.id
  if (!pid) return
  try {
    await dictStore.load('character_role')
    const list = await listResource<CharacterItem>(pid, 'characters')
    characters.value = list
    initGraph()

    // 功能2：默认聚焦主角
    const protagonist = characters.value.find((c) => c.role_type === 'protagonist')
    if (protagonist) {
      focusCharacterId.value = protagonist.id
      viewMode.value = 'focus'
      updateNodeFocusStyle()
    } else {
      // 没有主角，使用全部展示
      viewMode.value = 'all'
    }
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
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  white-space: nowrap;
}

.filter-divider {
  width: 1px;
  height: 24px;
  background: var(--n-border-color, #2a2f3a);
  margin: 0 4px;
}

.filter-spacer {
  flex: 1;
}

/* ===== 工作区 ===== */
.workbench {
  flex: 1;
  display: grid;
  grid-template-columns: 220px minmax(500px, 1fr) 340px;
  gap: 12px;
  min-height: 0;
}

.workbench.no-group-panel {
  grid-template-columns: minmax(500px, 1fr) 340px;
}

/* ===== 通用面板 ===== */
.graph-panel,
.list-panel,
.group-panel {
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
  display: flex;
  align-items: center;
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

/* ===== 连线模式提示条 ===== */
.connect-hint-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(251, 191, 36, 0.1);
  border-bottom: 1px solid rgba(251, 191, 36, 0.3);
  font-size: 12px;
  color: #fbbf24;
  flex-shrink: 0;
}

.connect-hint-bar .hint-icon {
  font-size: 14px;
}

.connect-hint-bar strong {
  color: #fbbf24;
  font-weight: 600;
}

/* ===== 分组面板 ===== */
.group-panel {
  min-width: 0;
}

.group-scroll {
  flex: 1;
  min-height: 0;
}

.group-item {
  padding: 10px 12px;
  margin: 8px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  background: var(--n-color-1, #1e2228);
}

.group-item:hover {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.05);
}

.group-item.active {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.12);
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.group-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
}

.group-count {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  background: var(--n-color-2, #262a33);
  padding: 1px 6px;
  border-radius: 4px;
}

.group-members {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.member-tag {
  font-size: 11px;
  padding: 2px 6px;
  background: var(--n-color-2, #262a33);
  color: var(--n-text-color-2, #94a3b8);
  border-radius: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80px;
}

.member-more {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  padding: 2px 4px;
}

/* ===== 图谱面板 ===== */
.graph-panel {
  min-width: 0;
}

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
  position: relative;
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

/* 双向关系标记 */
.relation-bidir {
  margin-top: 6px;
}

.bidir-tag {
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border-radius: 4px;
  font-weight: 500;
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

/* 双向关系提示 */
.bidir-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 12px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 6px;
}

.bidir-icon {
  font-size: 16px;
  color: #4ade80;
  font-weight: bold;
}

.bidir-text {
  font-size: 12px;
  color: #86efac;
  line-height: 1.4;
}

/* ===== 快速建立关系弹窗 ===== */
.quick-add-preview {
  margin-bottom: 16px;
  padding: 16px;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  text-align: center;
}

.quick-add-names {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.quick-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
  padding: 6px 16px;
  background: var(--n-color-2, #262a33);
  border-radius: 20px;
}

.quick-arrow {
  font-size: 20px;
  font-weight: bold;
  color: var(--n-color-primary, #3b82f6);
}
</style>
