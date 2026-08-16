<template>
  <div class="page org-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">🏛️</span>
          势力管理台
        </h1>
        <p class="page-subtitle">
          管理组织结构、资源目标、阵营关系与剧情风险
        </p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ totalCount }}</span>
            <span class="stat-label">组织总数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ activeCount }}</span>
            <span class="stat-label">活跃中</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ avgPower }}</span>
            <span class="stat-label">平均实力</span>
          </div>
        </div>
        <n-button type="primary" @click="startCreate">
          <template #icon>＋</template>
          新增势力
        </n-button>
      </div>
    </div>

    <!-- 主体：三栏布局 -->
    <div class="workbench">
      <!-- 左侧：组织列表 -->
      <aside class="list-panel">
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索组织...">
            <template #prefix>🔍</template>
          </n-input>
          <n-select
            v-model:value="statusFilter"
            clearable
            :options="orgStatusOptions"
            placeholder="状态筛选"
            style="width: 120px"
          />
        </div>

        <n-scrollbar class="list-scroll">
          <div v-if="loading" class="list-loading">
            <n-spin size="small" />
            <span>加载中...</span>
          </div>

          <div v-else-if="filteredOrganizations.length === 0" class="list-empty">
            <div class="empty-icon">🏛️</div>
            <p>还没有组织</p>
            <p class="empty-sub">点击右上角「新增势力」开始创建</p>
          </div>

          <div v-else class="org-list">
            <div
              v-for="item in filteredOrganizations"
              :key="item.id"
              class="org-item"
              :class="{ active: editingId === item.id }"
              @click="selectOrganization(item)"
            >
              <div class="org-header">
                <span class="org-name">{{ item.name }}</span>
                <n-tag size="tiny" :type="statusTagType(item.status)">
                  {{ item.status || '未定义' }}
                </n-tag>
              </div>
              <div class="org-type">{{ item.org_type || '类型未定' }} · {{ item.location || '地点未定' }}</div>
              <div class="power-bar">
                <div class="power-fill" :style="{ width: `${item.power_level * 10}%` }"></div>
              </div>
              <div class="org-meta">
                <span>实力 {{ item.power_level }}/10</span>
                <span>层级 {{ item.level }}/10</span>
                <span>{{ item.member_count || 0 }} 人</span>
              </div>
              <div class="org-goal">{{ item.goal || item.description || '目标尚未填写' }}</div>
            </div>
          </div>
        </n-scrollbar>
      </aside>

      <!-- 中间：详情编辑 -->
      <section class="detail-panel">
        <div class="detail-header">
          <div class="detail-title">
            <h2>
              {{ editingId ? '势力详情编辑' : '新势力档案' }}
              <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
            </h2>
            <span class="detail-sub">
              {{ editingId ? `ID ${editingId}` : '等待保存' }}
            </span>
          </div>
          <div class="detail-actions">
            <n-popconfirm v-if="editingId" positive-text="确认删除" negative-text="取消" @positive-click="remove">
              <template #trigger>
                <n-button type="error" text>🗑️ 删除</n-button>
              </template>
              确认删除这个组织？
            </n-popconfirm>
            <n-button @click="resetCurrent">↺ 重置</n-button>
            <n-button type="primary" @click="save">💾 保存</n-button>
          </div>
        </div>

        <div v-if="!editingId && !isCreating" class="detail-empty">
          <div class="empty-icon">✏️</div>
          <p>从左侧选择一个组织进行编辑</p>
          <p class="empty-sub">或点击右上角新增</p>
        </div>

        <n-scrollbar v-else class="form-scroll">
          <n-form class="detail-form" label-placement="top">
            <!-- 基本信息 -->
            <div class="form-section">
              <div class="section-title">
                基本信息
                <span class="section-hint">组织的身份与定位</span>
              </div>
              <div class="form-grid-3">
                <n-form-item label="组织名称">
                  <n-input v-model:value="form.name" size="large" />
                </n-form-item>
                <n-form-item label="类型">
                  <n-input v-model:value="form.org_type" placeholder="宗门 / 公司 / 官方机构" />
                </n-form-item>
                <n-form-item label="状态">
                  <n-select v-model:value="form.status" :options="orgStatusOptions" placeholder="选择组织状态" clearable />
                </n-form-item>
              </div>
              <div class="form-grid-2">
                <n-form-item label="地点 / 势力范围">
                  <n-input v-model:value="form.location" />
                </n-form-item>
                <n-form-item label="宗旨 / 口号">
                  <n-input v-model:value="form.slogan" />
                </n-form-item>
              </div>
            </div>

            <!-- 势力属性 -->
            <div class="form-section">
              <div class="section-title">
                势力属性
                <span class="section-hint">组织的硬实力指标</span>
              </div>
              <div class="power-sliders">
                <div class="slider-row">
                  <div class="slider-label">
                    <span>组织层级</span>
                    <strong>{{ form.level }}/10</strong>
                  </div>
                  <n-slider v-model:value="form.level" :min="1" :max="10" :step="1" />
                </div>
                <div class="slider-row">
                  <div class="slider-label">
                    <span>实力等级</span>
                    <strong>{{ form.power_level }}/10</strong>
                  </div>
                  <n-slider v-model:value="form.power_level" :min="1" :max="10" :step="1" />
                </div>
                <div class="slider-row">
                  <div class="slider-label">
                    <span>成员总数</span>
                    <strong>{{ form.member_count }} 人</strong>
                  </div>
                  <n-input-number v-model:value="form.member_count" :min="0" />
                </div>
              </div>
            </div>

            <!-- 内部与资源 -->
            <div class="form-section">
              <div class="section-title">
                内部与资源
                <span class="section-hint">组织架构与核心资源</span>
              </div>
              <div class="form-grid-2">
                <n-form-item label="内部层级">
                  <n-input v-model:value="form.hierarchy" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
                </n-form-item>
                <n-form-item label="核心资源">
                  <n-input v-model:value="form.resources" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
                </n-form-item>
              </div>
              <div class="form-grid-2">
                <n-form-item label="组织目标">
                  <n-input v-model:value="form.goal" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
                </n-form-item>
                <n-form-item label="背景描述">
                  <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
                </n-form-item>
              </div>
            </div>

            <!-- 时间维度 -->
            <div class="form-section">
              <div class="section-title">
                时间维度
                <span class="section-hint">组织活跃的章节范围</span>
              </div>
              <div class="form-grid-2">
                <n-form-item label="主效起始章节">
                  <n-input-number v-model:value="form.active_from_chapter" :min="0" placeholder="组织主要活跃的起始章节" clearable style="width: 100%" />
                </n-form-item>
                <n-form-item label="覆灭/解散章节">
                  <n-input-number v-model:value="form.disbanded_chapter" :min="0" placeholder="可选，不填则一直有效" clearable style="width: 100%" />
                </n-form-item>
              </div>
            </div>

            <!-- 隐藏设定 -->
            <div class="form-section">
              <div class="section-title">
                隐藏设定
                <span class="section-hint">仅作者可见的暗线</span>
              </div>
              <n-input
                v-model:value="form.hidden_secrets"
                type="textarea"
                :autosize="{ minRows: 4, maxRows: 8 }"
                placeholder="组织的秘密、暗线、真实目的、不为人知的内幕..."
              />
            </div>
          </n-form>
        </n-scrollbar>
      </section>

      <!-- 右侧：关系与风险 -->
      <aside class="side-panel">
        <!-- 势力雷达 -->
        <div class="insight-card primary-card">
          <div class="card-header">
            <span class="card-icon">📊</span>
            <span class="card-title">势力雷达</span>
          </div>
          <div class="radar-list">
            <div class="radar-row">
              <span class="radar-label">组织层级</span>
              <div class="radar-bar">
                <div class="radar-fill" :style="{ width: `${form.level * 10}%` }"></div>
              </div>
              <span class="radar-value">{{ form.level }}/10</span>
            </div>
            <div class="radar-row">
              <span class="radar-label">实力等级</span>
              <div class="radar-bar">
                <div class="radar-fill power" :style="{ width: `${form.power_level * 10}%` }"></div>
              </div>
              <span class="radar-value">{{ form.power_level }}/10</span>
            </div>
            <div class="radar-row">
              <span class="radar-label">成员规模</span>
              <div class="radar-bar">
                <div class="radar-fill members" :style="{ width: `${Math.min(form.member_count / 100, 100)}%` }"></div>
              </div>
              <span class="radar-value">{{ form.member_count }}</span>
            </div>
          </div>
          <div class="risk-level">
            <span class="risk-label">风险等级</span>
            <n-tag :type="riskTagType" size="small">{{ riskLevel }}</n-tag>
          </div>
        </div>

        <!-- 关系管理 -->
        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">🔗</span>
            <span class="card-title">关系管理</span>
          </div>
          <n-form label-placement="top" size="small">
            <n-form-item label="核心成员">
              <n-select v-model:value="selectedCoreMembers" multiple filterable tag :options="characterOptions" placeholder="选择首领、骨干" />
            </n-form-item>
            <n-form-item label="盟友组织">
              <n-select v-model:value="selectedAllies" multiple filterable tag :options="organizationNameOptions" placeholder="选择盟友" />
            </n-form-item>
            <n-form-item label="敌对组织">
              <n-select v-model:value="selectedEnemies" multiple filterable tag :options="organizationNameOptions" placeholder="选择敌对" />
            </n-form-item>
          </n-form>
        </div>

        <!-- 剧情影响 -->
        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">💥</span>
            <span class="card-title">剧情影响</span>
          </div>
          <n-form label-placement="top" size="small">
            <n-form-item label="剧情影响">
              <n-input v-model:value="form.impact" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
            </n-form-item>
            <n-form-item label="风险提示">
              <n-input v-model:value="form.risk_notes" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
            </n-form-item>
          </n-form>
        </div>
      </aside>
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
import type { CharacterItem, OrganizationItem } from '@/types/domain'

const projectStore = useProjectStore()
const organizations = ref<OrganizationItem[]>([])
const characters = ref<CharacterItem[]>([])
const keyword = ref('')
const statusFilter = ref<string | null>(null)
const editingId = ref<number | null>(null)
const isCreating = ref(false)
const loading = ref(false)

const form = reactive({
  name: '新组织',
  org_type: '',
  location: '',
  slogan: '',
  description: '',
  hierarchy: '',
  resources: '',
  goal: '',
  level: 1,
  power_level: 5,
  member_count: 0,
  status: '',
  core_members: '',
  allies: '',
  enemies: '',
  impact: '',
  risk_notes: '',
  active_from_chapter: null as number | null,
  disbanded_chapter: null as number | null,
  hidden_secrets: ''
})

const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form, '当前势力档案有未保存的修改，确定要离开吗？')

const orgStatusOptions = [
  { label: '隐世', value: '隐世' },
  { label: '扩张', value: '扩张' },
  { label: '鼎盛', value: '鼎盛' },
  { label: '衰落', value: '衰落' },
  { label: '覆灭', value: '覆灭' },
  { label: '蛰伏', value: '蛰伏' },
  { label: '转型中', value: '转型中' }
]

const filteredOrganizations = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return organizations.value.filter((item) => {
    const matchedText =
      !text ||
      [
        item.name,
        item.location,
        item.slogan,
        item.description,
        item.hierarchy,
        item.resources,
        item.goal,
        item.status,
        item.org_type,
        item.impact,
        item.risk_notes
      ]
        .join(' ')
        .toLowerCase()
        .includes(text)
    const matchedStatus = !statusFilter.value || item.status === statusFilter.value
    return matchedText && matchedStatus
  })
})

const totalCount = computed(() => organizations.value.length)
const activeCount = computed(() => organizations.value.filter((o) => o.status && o.status !== '覆灭').length)
const avgPower = computed(() => {
  if (organizations.value.length === 0) return 0
  const total = organizations.value.reduce((sum, o) => sum + (o.power_level || 0), 0)
  return Math.round(total / organizations.value.length)
})

const riskLevel = computed(() => {
  if (form.enemies && form.power_level <= 4) return '高风险'
  if (!form.goal || !form.resources) return '资料不足'
  return '稳定'
})

const riskTagType = computed<'default' | 'success' | 'warning' | 'error' | 'info'>(() => {
  if (riskLevel.value === '高风险') return 'error'
  if (riskLevel.value === '资料不足') return 'warning'
  return 'success'
})

function statusTagType(status: string): 'default' | 'success' | 'info' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'success' | 'info' | 'warning' | 'error'> = {
    '鼎盛': 'success',
    '扩张': 'info',
    '蛰伏': 'default',
    '衰落': 'warning',
    '覆灭': 'error',
    '隐世': 'default',
    '转型中': 'warning'
  }
  return map[status] || 'default'
}

const characterOptions = computed(() => characters.value.map((item) => ({ label: item.name, value: item.name })))

const organizationNameOptions = computed(() =>
  organizations.value
    .filter((item) => item.id !== editingId.value)
    .map((item) => ({ label: item.name, value: item.name }))
)

const selectedCoreMembers = computed({
  get: () => splitList(form.core_members),
  set: (value: string[]) => {
    form.core_members = value.join('，')
  }
})

const selectedAllies = computed({
  get: () => splitList(form.allies),
  set: (value: string[]) => {
    form.allies = value.join('，')
  }
})

const selectedEnemies = computed({
  get: () => splitList(form.enemies),
  set: (value: string[]) => {
    form.enemies = value.join('，')
  }
})

function splitList(value: string) {
  return value
    .split(/[，,\n]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function fillForm(item?: Partial<OrganizationItem>) {
  Object.assign(form, {
    name: item?.name ?? '新组织',
    org_type: item?.org_type ?? '',
    location: item?.location ?? '',
    slogan: item?.slogan ?? '',
    description: item?.description ?? '',
    hierarchy: item?.hierarchy ?? '',
    resources: item?.resources ?? '',
    goal: item?.goal ?? '',
    level: item?.level ?? 1,
    power_level: item?.power_level ?? 5,
    member_count: item?.member_count ?? 0,
    status: item?.status ?? '',
    core_members: item?.core_members ?? '',
    allies: item?.allies ?? '',
    enemies: item?.enemies ?? '',
    impact: item?.impact ?? '',
    risk_notes: item?.risk_notes ?? '',
    active_from_chapter: item?.active_from_chapter ?? null,
    disbanded_chapter: item?.disbanded_chapter ?? null,
    hidden_secrets: item?.hidden_secrets ?? ''
  })
}

async function startCreate() {
  if (!(await confirmIfDirty())) return
  editingId.value = null
  isCreating.value = true
  fillForm()
  await nextTick()
  markClean()
}

async function selectOrganization(item: OrganizationItem) {
  if (editingId.value === item.id) return
  if (!(await confirmIfDirty())) return
  editingId.value = item.id
  isCreating.value = false
  fillForm(item)
  await nextTick()
  markClean()
}

async function resetCurrent() {
  if (!(await confirmIfDirty('确定要重置当前编辑内容吗？'))) return
  const current = organizations.value.find((item) => item.id === editingId.value)
  if (current) {
    fillForm(current)
  } else {
    editingId.value = null
    isCreating.value = false
    fillForm()
  }
  await nextTick()
  markClean()
}

async function ensureProject() {
  if (!projectStore.currentProject) await projectStore.loadDefaultProject()
  return projectStore.currentProject?.id
}

async function load() {
  const projectId = projectStore.currentProject!.id
  loading.value = true
  try {
    const [organizationList, characterList] = await Promise.all([
      listResource<OrganizationItem>(projectId, 'organizations'),
      listResource<CharacterItem>(projectId, 'characters')
    ])
    organizations.value = organizationList
    characters.value = characterList
    if (!editingId.value && !isCreating.value && organizations.value[0]) {
      editingId.value = organizations.value[0].id
      fillForm(organizations.value[0])
      await nextTick()
      markClean()
    }
  } finally {
    loading.value = false
  }
}

async function save() {
  const projectId = await ensureProject()
  if (!projectId) return

  if (editingId.value) {
    const updated = await updateResource<OrganizationItem>('organizations', editingId.value, { ...form })
    notify.success('势力档案已更新')
    await load()
    const fresh = organizations.value.find((item) => item.id === updated.id)
    if (fresh) {
      fillForm(fresh)
      await nextTick()
      markClean()
    }
  } else {
    const created = await createResource<OrganizationItem>('organizations', { project_id: projectId, ...form })
    notify.success('势力档案已新增')
    isCreating.value = false
    await load()
    const fresh = organizations.value.find((item) => item.id === created.id)
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
  const currentIndex = organizations.value.findIndex((item) => item.id === editingId.value)
  await deleteResource('organizations', editingId.value)
  notify.success('势力档案已删除')
  const nextItem = organizations.value[currentIndex + 1] || organizations.value[currentIndex - 1]
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
.org-page {
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
  min-width: 60px;
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
  grid-template-columns: 300px minmax(480px, 1fr) 280px;
  gap: 12px;
  min-height: 0;
}

/* ===== 通用面板 ===== */
.list-panel,
.detail-panel,
.side-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ===== 左侧列表 ===== */
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

.list-scroll {
  flex: 1;
  min-height: 0;
}

.list-loading,
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

.empty-icon {
  font-size: 36px;
}

.list-empty p {
  margin: 0;
}

.empty-sub {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

.org-list {
  padding: 8px 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.org-item {
  padding: 12px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  background: var(--n-color-1, #1e2228);
}

.org-item:hover {
  border-color: #6366f1;
}

.org-item.active {
  border-color: #6366f1;
  background: rgba(99, 102, 241, 0.08);
}

.org-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.org-name {
  font-size: 13px;
  font-weight: 600;
}

.org-type {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  margin-bottom: 8px;
}

.power-bar {
  height: 5px;
  margin-bottom: 6px;
  overflow: hidden;
  border-radius: 99px;
  background: var(--n-border-color, #2a2f3a);
}

.power-fill {
  height: 100%;
  background: linear-gradient(90deg, #4f8cff, #f2c97d);
  border-radius: 99px;
  transition: width 0.3s;
}

.org-meta {
  display: flex;
  gap: 10px;
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  margin-bottom: 6px;
}

.org-goal {
  font-size: 11px;
  color: var(--n-text-color-2, #9ca3af);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ===== 中间详情 ===== */
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

.form-scroll {
  flex: 1;
  min-height: 0;
}

.detail-form {
  padding: 20px 28px 28px;
}

.form-section {
  margin-bottom: 24px;
}

.form-section:last-child {
  margin-bottom: 0;
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

/* 势力滑块 */
.power-sliders {
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
  padding: 16px 20px;
}

.slider-row {
  margin-bottom: 16px;
}

.slider-row:last-child {
  margin-bottom: 0;
}

.slider-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}

.slider-label strong {
  font-size: 14px;
  color: #a5b4fc;
}

/* ===== 右侧面板 ===== */
.side-panel {
  padding: 12px;
  gap: 12px;
  overflow-y: auto;
}

.insight-card {
  padding: 14px;
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  background: var(--n-color-1, #1e2228);
}

.primary-card {
  background: linear-gradient(135deg, var(--n-color-primary-1-suppl, #1e3a5f) 0%, var(--n-color-1, #1e2228) 100%);
  border-color: var(--n-color-primary-3, #3b82f6);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.card-icon {
  font-size: 16px;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
}

/* 势力雷达 */
.radar-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.radar-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.radar-label {
  width: 56px;
  color: var(--n-text-color-2, #9ca3af);
  flex-shrink: 0;
}

.radar-bar {
  flex: 1;
  height: 6px;
  background: var(--n-border-color, #2a2f3a);
  border-radius: 3px;
  overflow: hidden;
}

.radar-fill {
  height: 100%;
  background: var(--n-color-primary, #3b82f6);
  border-radius: 3px;
  transition: width 0.3s;
}

.radar-fill.power {
  background: linear-gradient(90deg, #f59e0b, #ef4444);
}

.radar-fill.members {
  background: linear-gradient(90deg, #22c55e, #10b981);
}

.radar-value {
  width: 42px;
  text-align: right;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
  flex-shrink: 0;
}

.risk-level {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
}

.risk-label {
  font-size: 12px;
  color: var(--n-text-color-2, #9ca3af);
}
</style>
