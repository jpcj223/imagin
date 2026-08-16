<template>
  <div class="page outline-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">📋</span>
          大纲规划
        </h1>
        <p class="page-subtitle">
          搭建卷章结构，规划每章剧情走向
        </p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ volumeCount }}</span>
            <span class="stat-label">卷</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ chapterCount }}</span>
            <span class="stat-label">章</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ confirmedCount }}</span>
            <span class="stat-label">已确认</span>
          </div>
        </div>
        <n-button type="primary" @click="startCreate('chapter')">
          <template #icon>＋</template>
          新增章节
        </n-button>
        <n-button @click="startCreate('volume')">
          <template #icon>📚</template>
          新增卷
        </n-button>
      </div>
    </div>

    <!-- 主体：左树 + 右详情 -->
    <div class="workbench">
      <!-- 左侧：大纲树 -->
      <aside class="tree-panel">
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索大纲...">
            <template #prefix>🔍</template>
          </n-input>
          <n-select
            v-model:value="statusFilter"
            clearable
            :options="statusOptions"
            placeholder="状态筛选"
            style="width: 120px"
          />
        </div>

        <n-scrollbar class="tree-scroll">
          <div v-if="loading" class="tree-loading">
            <n-spin size="small" />
            <span>加载中...</span>
          </div>

          <div v-else-if="treeData.length === 0" class="tree-empty">
            <div class="empty-icon">📑</div>
            <p>还没有大纲</p>
            <p class="empty-sub">点击右上角「新增章节」开始规划</p>
          </div>

          <div v-else class="outline-tree">
            <template v-for="group in treeData" :key="group.volumeId">
              <!-- 卷节点 -->
              <div
                v-if="group.volume"
                class="tree-node volume-node"
                :class="{ active: editingId === group.volume.id }"
                @click="selectOutline(group.volume)"
              >
                <div class="node-icon">📚</div>
                <div class="node-content">
                  <div class="node-title-row">
                    <span class="node-title">{{ group.volume.title }}</span>
                    <n-tag size="tiny" :type="statusTagType(group.volume.status)">
                      {{ statusLabel(group.volume.status) }}
                    </n-tag>
                  </div>
                  <div class="node-meta">
                    第 {{ group.volume.volume_no }} 卷 · {{ group.chapters.length }} 章
                  </div>
                </div>
              </div>

              <!-- 章节列表 -->
              <div class="chapter-group">
                <div
                  v-for="item in group.chapters"
                  :key="item.id"
                  class="tree-node chapter-node"
                  :class="{ active: editingId === item.id }"
                  @click="selectOutline(item)"
                >
                  <div class="chapter-indicator"></div>
                  <div class="node-icon ch-icon">📖</div>
                  <div class="node-content">
                    <div class="node-title-row">
                      <span class="node-title">{{ item.title }}</span>
                      <n-tag size="tiny" :type="statusTagType(item.status)">
                        {{ statusLabel(item.status) }}
                      </n-tag>
                    </div>
                    <div class="node-meta">
                      第 {{ item.chapter_no ?? item.sort_index }} 章
                    </div>
                    <div v-if="item.description" class="node-desc">
                      {{ shortText(item.description, 50) }}
                    </div>
                  </div>
                </div>

                <!-- 无章节时的占位 -->
                <div v-if="group.chapters.length === 0" class="empty-chapters">
                  本卷暂无章节
                </div>
              </div>
            </template>

            <!-- 未分组章节 -->
            <div v-if="ungroupedChapters.length > 0" class="ungrouped-section">
              <div class="ungrouped-title">📂 未分组章节</div>
              <div
                v-for="item in ungroupedChapters"
                :key="item.id"
                class="tree-node chapter-node"
                :class="{ active: editingId === item.id }"
                @click="selectOutline(item)"
              >
                <div class="chapter-indicator"></div>
                <div class="node-icon ch-icon">📖</div>
                <div class="node-content">
                  <div class="node-title-row">
                    <span class="node-title">{{ item.title }}</span>
                    <n-tag size="tiny" :type="statusTagType(item.status)">
                      {{ statusLabel(item.status) }}
                    </n-tag>
                  </div>
                  <div class="node-meta">
                    第 {{ item.chapter_no ?? item.sort_index }} 章
                  </div>
                  <div v-if="item.description" class="node-desc">
                    {{ shortText(item.description, 50) }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </n-scrollbar>
      </aside>

      <!-- 右侧：详情编辑 -->
      <section class="detail-panel">
        <div class="detail-header">
          <div class="detail-title">
            <h2>
              {{ editingId ? '编辑详情' : '新增' }}
              <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
            </h2>
            <span class="detail-sub">
              {{ editingId ? `ID ${editingId}` : '未保存' }}
            </span>
          </div>
          <div class="detail-actions">
            <n-popconfirm v-if="editingId" positive-text="确认删除" negative-text="取消" @positive-click="remove">
              <template #trigger>
                <n-button type="error" text>🗑️ 删除</n-button>
              </template>
              确认删除这个大纲节点？
            </n-popconfirm>
            <n-button @click="resetCurrent">↺ 重置</n-button>
            <n-button type="primary" :disabled="!canSave" @click="save">
              💾 保存
            </n-button>
          </div>
        </div>

        <div v-if="!editingId && !isCreating" class="detail-empty">
          <div class="empty-icon">✏️</div>
          <p>从左侧选择一个大纲节点进行编辑</p>
          <p class="empty-sub">或点击右上角新增</p>
        </div>

        <n-form v-else class="detail-form" label-placement="top" :show-label="true">
          <!-- 基本信息 -->
          <div class="form-section">
            <div class="section-title">基本信息</div>
            <n-form-item label="标题">
              <n-input
                v-model:value="form.title"
                placeholder="输入大纲标题"
                size="large"
              />
            </n-form-item>
            <div class="form-grid-3">
              <n-form-item label="节点类型">
                <n-select v-model:value="form.node_type" :options="nodeTypeOptions" />
              </n-form-item>
              <n-form-item label="状态">
                <n-select v-model:value="form.status" :options="statusOptions" />
              </n-form-item>
              <n-form-item v-if="form.node_type === 'volume'" label="卷号">
                <n-input-number v-model:value="form.volume_no" :min="1" style="width: 100%" />
              </n-form-item>
              <n-form-item v-else label="章节号">
                <n-input-number v-model:value="form.chapter_no" :min="1" style="width: 100%" />
              </n-form-item>
            </div>
            <div v-if="form.node_type === 'chapter'" class="form-grid-2">
              <n-form-item label="所属卷">
                <n-select
                  v-model:value="form.volume_id"
                  clearable
                  :options="volumeOptions"
                  placeholder="选择所属卷（可选）"
                />
              </n-form-item>
              <n-form-item label="排序索引">
                <n-input-number v-model:value="form.sort_index" :min="0" style="width: 100%" />
              </n-form-item>
            </div>
          </div>

          <!-- 内容描述 -->
          <div class="form-section">
            <div class="section-title">
              内容描述
              <span class="section-hint">
                描述本章的剧情目标、冲突点和关键场景
              </span>
            </div>
            <n-input
              v-model:value="form.description"
              type="textarea"
              :autosize="{ minRows: 10, maxRows: 20 }"
              placeholder="详细描述本卷/本章的剧情走向、主要冲突、关键事件、角色出场等..."
              class="description-textarea"
            />
            <div class="desc-footer">
              <span class="char-count">{{ form.description.length }} 字</span>
            </div>
          </div>

          <!-- 本章伏笔关联 -->
          <div class="form-section">
            <div class="section-title">
              关联伏笔
              <span class="section-hint">选择本章涉及的伏笔</span>
            </div>
            <n-select
              v-model:value="linkedForeshadowings"
              multiple
              filterable
              tag
              :options="foreshadowingOptions"
              placeholder="搜索并选择关联的伏笔"
            />
            <div v-if="linkedForeshadowings.length > 0" class="linked-tags">
              <n-tag
                v-for="id in linkedForeshadowings"
                :key="id"
                size="small"
                closable
                @close="removeForeshadowing(id)"
              >
                {{ getForeshadowKeyword(id) }}
              </n-tag>
            </div>
          </div>
        </n-form>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import { createResource, deleteResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import { useDirtySnapshot } from '@/composables/useDirtySnapshot'
import { notify } from '@/utils/notify'
import type { OutlineItem, ForeshadowingItem } from '@/types/domain'

const projectStore = useProjectStore()
const outlines = ref<OutlineItem[]>([])
const foreshadowings = ref<ForeshadowingItem[]>([])
const keyword = ref('')
const statusFilter = ref<string | null>(null)
const editingId = ref<number | null>(null)
const loading = ref(false)
const isCreating = ref(false)
const linkedForeshadowings = ref<number[]>([])

const form = reactive({
  title: '新章节',
  node_type: 'chapter',
  status: 'draft',
  volume_no: 1 as number | null,
  chapter_no: 1 as number | null,
  sort_index: 1,
  description: '',
  volume_id: null as number | null,
})

// 脏数据检测
const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(
  form,
  '当前大纲有未保存的修改，确定要离开吗？'
)

// ---- 选项 ----
const nodeTypeOptions = [
  { label: '章', value: 'chapter' },
  { label: '卷', value: 'volume' },
]

const statusOptions = [
  { label: '草稿', value: 'draft' },
  { label: '已确认', value: 'confirmed' },
]

// ---- 计算属性 ----
const filteredOutlines = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return outlines.value.filter((item) => {
    const matchedText =
      !text || [item.title, item.description].join(' ').toLowerCase().includes(text)
    const matchedStatus = !statusFilter.value || item.status === statusFilter.value
    return matchedText && matchedStatus
  })
})

const volumeCount = computed(() =>
  filteredOutlines.value.filter((i) => i.node_type === 'volume').length
)
const chapterCount = computed(() =>
  filteredOutlines.value.filter((i) => i.node_type === 'chapter').length
)
const confirmedCount = computed(() =>
  filteredOutlines.value.filter((i) => i.status === 'confirmed').length
)

// 伏笔选项
const foreshadowingOptions = computed(() =>
  foreshadowings.value.map((f) => ({
    label: `${f.keyword}（${statusLabel(f.status)}）`,
    value: f.id,
  }))
)

// 卷选项（用于章节归属）
const volumeOptions = computed(() =>
  outlines.value
    .filter((i) => i.node_type === 'volume')
    .sort((a, b) => (a.volume_no ?? 0) - (b.volume_no ?? 0))
    .map((v) => ({
      label: `第${v.volume_no}卷 · ${v.title}`,
      value: v.id,
    }))
)

// 树形数据：按卷分组
const treeData = computed(() => {
  const volumes = filteredOutlines.value
    .filter((i) => i.node_type === 'volume')
    .sort((a, b) => (a.volume_no ?? 0) - (b.volume_no ?? 0))

  const chapters = filteredOutlines.value
    .filter((i) => i.node_type === 'chapter')
    .sort((a, b) => (a.chapter_no ?? a.sort_index) - (b.chapter_no ?? b.sort_index))

  return volumes.map((vol) => ({
    volumeId: vol.id,
    volume: vol,
    chapters: chapters.filter((c) => {
      // 简单判断：用 volume_no 匹配（后续可优化为 parent_id）
      return c.volume_no === vol.volume_no
    }),
  }))
})

// 未分组章节
const ungroupedChapters = computed(() => {
  const chapters = filteredOutlines.value.filter((i) => i.node_type === 'chapter')
  const volumeNos = new Set(
    filteredOutlines.value
      .filter((i) => i.node_type === 'volume')
      .map((v) => v.volume_no)
  )
  return chapters
    .filter((c) => !c.volume_no || !volumeNos.has(c.volume_no))
    .sort((a, b) => (a.chapter_no ?? a.sort_index) - (b.chapter_no ?? b.sort_index))
})

const canSave = computed(() => form.title.trim().length > 0)

// ---- 工具函数 ----
function shortText(value: string, max = 50) {
  return value?.length > max ? `${value.slice(0, max)}...` : value || ''
}

function statusLabel(value: string) {
  return statusOptions.find((item) => item.value === value)?.label ?? value
}

function statusTagType(
  status: string
): 'default' | 'success' | 'info' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'success' | 'info' | 'warning' | 'error'> = {
    draft: 'default',
    confirmed: 'success',
  }
  return map[status] || 'default'
}

function getForeshadowKeyword(id: number): string {
  return foreshadowings.value.find((f) => f.id === id)?.keyword ?? ''
}

function removeForeshadowing(id: number) {
  linkedForeshadowings.value = linkedForeshadowings.value.filter((fid) => fid !== id)
}

// ---- 表单操作 ----
function fillForm(item?: Partial<OutlineItem>) {
  Object.assign(form, {
    title: item?.title ?? '新章节',
    node_type: item?.node_type ?? 'chapter',
    status: item?.status ?? 'draft',
    volume_no: item?.volume_no ?? 1,
    chapter_no: item?.chapter_no ?? 1,
    sort_index: item?.sort_index ?? 1,
    description: item?.description ?? '',
    volume_id: null,
  })
}

async function startCreate(type: 'chapter' | 'volume' = 'chapter') {
  if (!(await confirmIfDirty())) return
  editingId.value = null
  isCreating.value = true
  fillForm({
    title: type === 'volume' ? '新卷' : '新章节',
    node_type: type,
    status: 'draft',
    volume_no: type === 'volume' ? volumeCount.value + 1 : 1,
    chapter_no: type === 'chapter' ? chapterCount.value + 1 : null,
    sort_index: outlines.value.length + 1,
    description: '',
  })
  linkedForeshadowings.value = []
  await nextTick()
  markClean()
}

async function selectOutline(item: OutlineItem) {
  if (editingId.value === item.id) return
  if (!(await confirmIfDirty())) return
  editingId.value = item.id
  isCreating.value = false
  fillForm(item)
  linkedForeshadowings.value = []
  await nextTick()
  markClean()
}

async function resetCurrent() {
  if (!(await confirmIfDirty('确定要重置当前大纲吗？'))) return
  const current = outlines.value.find((item) => item.id === editingId.value)
  if (current) {
    fillForm(current)
  } else {
    editingId.value = null
    isCreating.value = false
    fillForm()
  }
  linkedForeshadowings.value = []
  await nextTick()
  markClean()
}

// ---- 数据加载 ----
async function load() {
  const projectId = projectStore.currentProject!.id
  loading.value = true
  try {
    const [outlineList, foreshadowList] = await Promise.all([
      listResource<OutlineItem>(projectId, 'outlines'),
      listResource<ForeshadowingItem>(projectId, 'foreshadowings'),
    ])
    outlines.value = outlineList
    foreshadowings.value = foreshadowList

    // 首次加载自动选中第一条
    if (!editingId.value && !isCreating.value && outlines.value[0]) {
      editingId.value = outlines.value[0].id
      fillForm(outlines.value[0])
      await nextTick()
      markClean()
    }
  } finally {
    loading.value = false
  }
}

// ---- CRUD ----
async function save() {
  if (!canSave.value) return
  const projectId = projectStore.currentProject!.id

  if (editingId.value) {
    const updated = await updateResource<OutlineItem>('outlines', editingId.value, {
      ...form,
      project_id: projectId,
    })
    notify.success('大纲已更新')
    await load()
    const fresh = outlines.value.find((item) => item.id === updated.id)
    if (fresh) {
      fillForm(fresh)
      await nextTick()
      markClean()
    }
  } else {
    const created = await createResource<OutlineItem>('outlines', {
      ...form,
      project_id: projectId,
    })
    notify.success('大纲已新增')
    isCreating.value = false
    await load()
    const fresh = outlines.value.find((item) => item.id === created.id)
    if (fresh) {
      editingId.value = fresh.id
      fillForm(fresh)
      await nextTick()
      markClean()
    }
  }
}

async function remove() {
  if (!editingId.value) return
  const currentIndex = outlines.value.findIndex((item) => item.id === editingId.value)
  await deleteResource('outlines', editingId.value)
  notify.success('大纲已删除')
  const nextItem = outlines.value[currentIndex + 1] || outlines.value[currentIndex - 1]
  if (nextItem) {
    editingId.value = nextItem.id
    fillForm(nextItem)
  } else {
    editingId.value = null
    isCreating.value = false
    fillForm()
  }
  await load()
  await nextTick()
  markClean()
}

useProjectDataLoader(load)
</script>

<style scoped>
.outline-page {
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
  min-width: 40px;
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

/* ===== 工作区 ===== */
.workbench {
  flex: 1;
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 12px;
  min-height: 0;
}

/* ===== 左侧树面板 ===== */
.tree-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-tools {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.panel-tools > :first-child {
  flex: 1;
}

.tree-scroll {
  flex: 1;
  min-height: 0;
  padding: 8px 10px 12px;
}

.tree-loading,
.tree-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 10px;
  color: var(--n-text-color-3, #6b7280);
  font-size: 13px;
}

.empty-icon {
  font-size: 36px;
}

.tree-empty p {
  margin: 0;
}

.empty-sub {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

/* 大纲树 */
.outline-tree {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tree-node {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.tree-node:hover {
  background: var(--n-color-hover, #23272f);
}

.tree-node.active {
  background: var(--n-color-primary-1-suppl, #1e3a5f);
  border-color: var(--n-color-primary-3, #3b82f6);
}

.node-icon {
  font-size: 18px;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
  margin-top: 1px;
}

.ch-icon {
  font-size: 14px;
  width: 20px;
}

.node-content {
  flex: 1;
  min-width: 0;
}

.node-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.node-title {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-meta {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
}

.node-desc {
  font-size: 11px;
  color: var(--n-text-color-2, #9ca3af);
  margin-top: 4px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 卷节点 */
.volume-node {
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  margin-top: 10px;
}

.volume-node:first-child {
  margin-top: 0;
}

.volume-node .node-title {
  font-size: 14px;
}

/* 章节组 */
.chapter-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 16px;
  margin-top: 2px;
}

.chapter-node {
  position: relative;
  padding: 8px 10px 8px 8px;
}

.chapter-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 60%;
  background: var(--n-border-color, #2a2f3a);
  border-radius: 1px;
}

.chapter-node.active .chapter-indicator {
  background: var(--n-color-primary, #3b82f6);
}

.empty-chapters {
  padding: 8px 12px;
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  font-style: italic;
}

/* 未分组 */
.ungrouped-section {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px dashed var(--n-border-color, #2a2f3a);
}

.ungrouped-title {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  margin-bottom: 6px;
  padding: 0 4px;
}

/* ===== 右侧详情 ===== */
.detail-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.detail-title h2 {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-sub {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 2px;
}

.dirty-dot {
  color: #f59e0b;
  font-size: 12px;
  animation: dirtyPulse 1.5s ease-in-out infinite;
}

@keyframes dirtyPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.detail-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--n-text-color-3, #6b7280);
  padding: 40px;
  text-align: center;
}

.detail-empty .empty-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.detail-empty p {
  margin: 0;
  font-size: 14px;
}

.detail-empty .empty-sub {
  font-size: 12px;
}

.detail-form {
  flex: 1;
  overflow-y: auto;
  padding: 20px 28px 28px;
}

.form-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 14px;
  padding-left: 10px;
  border-left: 3px solid #6366f1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--n-text-color-3, #6b7280);
  border-left: none;
  padding-left: 0;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 16px;
}

.form-grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px 16px;
}

.description-textarea :deep(textarea) {
  line-height: 1.8;
  font-size: 14px;
}

.desc-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.char-count {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
}

.linked-tags {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* ===== 响应式 ===== */
@media (max-width: 1200px) {
  .workbench {
    grid-template-columns: 300px 1fr;
  }
  .form-grid-3 {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
