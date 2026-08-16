<template>
  <div class="page world-page">
    <!-- 世界观概览横幅 -->
    <div class="world-hero">
      <div class="hero-left">
        <div class="hero-badge">
          <span class="badge-icon">🌍</span>
          <span class="badge-text">{{ project?.name || '加载中' }} · 世界观</span>
        </div>
        <h1 class="hero-title">世界设定总览</h1>
        <p class="hero-desc">
          构建完整的世界规则、地理环境与势力格局，为创作提供稳定的设定支撑
        </p>
      </div>
      <div class="hero-right">
        <div class="hero-stat">
          <div class="hero-stat-value">{{ totalCount }}</div>
          <div class="hero-stat-label">设定条目</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-value">{{ coveredCategories }}</div>
          <div class="hero-stat-label">已覆盖分类</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-value">{{ highCount }}</div>
          <div class="hero-stat-label">高重要</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-value success">{{ completionRate }}%</div>
          <div class="hero-stat-label">完整度</div>
        </div>
      </div>
    </div>

    <!-- 世界观总览简易编辑 -->
    <div class="overview-card" :class="{ expanded: overviewExpanded }">
      <div class="overview-head" @click="overviewExpanded = !overviewExpanded">
        <div class="overview-title">
          <span class="ov-icon">📝</span>
          <span>世界观总览（简易编辑）</span>
        </div>
        <div class="overview-toggle">
          {{ overviewExpanded ? '收起' : '展开编辑' }}
          <span class="toggle-arrow">{{ overviewExpanded ? '▲' : '▼' }}</span>
        </div>
      </div>
      <div v-show="overviewExpanded" class="overview-body">
        <div class="overview-grid">
          <div class="ov-field">
            <label class="ov-label">世界观名称</label>
            <n-input v-model:value="overviewForm.title" placeholder="给你的世界起个名字" size="small" />
          </div>
          <div class="ov-field">
            <label class="ov-label">时代背景</label>
            <n-input v-model:value="overviewForm.era" placeholder="如：古典仙侠、末世废土、星际时代" size="small" />
          </div>
          <div class="ov-field">
            <label class="ov-label">核心力量体系</label>
            <n-input v-model:value="overviewForm.power_system" placeholder="如：修炼体系、异能、魔法" size="small" />
          </div>
          <div class="ov-field">
            <label class="ov-label">整体基调</label>
            <n-input v-model:value="overviewForm.atmosphere" placeholder="如：热血、暗黑、治愈" size="small" />
          </div>
        </div>
        <div class="ov-field ov-full">
          <label class="ov-label">世界观简介</label>
          <n-input
            v-model:value="overviewForm.synopsis"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }"
            placeholder="一句话介绍你的世界整体设定..."
          />
        </div>
        <div class="ov-field ov-full">
          <label class="ov-label">核心规则</label>
          <n-input
            v-model:value="overviewForm.core_rules"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }"
            placeholder="这个世界最重要的几条规则和禁忌..."
          />
        </div>
        <div class="ov-actions">
          <n-button size="small" @click="resetOverview">重置</n-button>
          <n-button type="primary" size="small" :loading="overviewSaving" @click="saveOverview">
            💾 保存总览
          </n-button>
        </div>
      </div>
    </div>

    <!-- 主体：三栏布局 -->
    <div class="workbench">
      <!-- 左侧：分类树 -->
      <aside class="category-panel">
        <div class="panel-title">设定分类</div>
        <div class="category-tree">
          <div
            v-for="cat in categoriesWithCount"
            :key="cat.value"
            class="cat-node"
            :class="{ active: activeCategory === cat.value }"
            @click="selectCategory(cat.value)"
          >
            <span class="cat-icon">{{ cat.icon }}</span>
            <span class="cat-name">{{ cat.label }}</span>
            <span class="cat-count">{{ cat.count }}</span>
          </div>
        </div>
      </aside>

      <!-- 中间：条目列表 -->
      <section class="list-panel">
        <div class="list-head">
          <div class="list-title">
            <span class="cur-cat-icon">{{ currentCategoryIcon }}</span>
            <span>{{ currentCategoryLabel }}</span>
            <span class="list-count">{{ filteredList.length }} 条</span>
          </div>
          <div class="list-tools">
            <n-input v-model:value="keyword" clearable placeholder="搜索..." size="small" style="width: 160px">
              <template #prefix>🔍</template>
            </n-input>
            <n-button type="primary" size="small" @click="startCreate">
              <template #icon>＋</template>
              新增
            </n-button>
          </div>
        </div>

        <n-scrollbar class="list-scroll">
          <div class="list-inner">
            <div v-if="loading" class="list-loading">
              <n-spin size="small" />
              <span>加载中...</span>
            </div>
            <div v-else-if="filteredList.length === 0" class="list-empty">
              <div class="empty-icon">📑</div>
              <p>暂无{{ currentCategoryLabel }}设定</p>
              <p class="empty-sub">点击「新增」添加第一条</p>
            </div>
            <div v-else class="setting-list">
              <div
                v-for="item in filteredList"
                :key="item.id"
                class="setting-item"
                :class="{ active: editingId === item.id }"
                @click="selectWorld(item)"
              >
                <div class="item-head">
                  <span class="item-title">{{ item.title || '未命名' }}</span>
                  <n-tag size="tiny" :type="importanceTagType(item.importance)">
                    {{ importanceLabel(item.importance) }}
                  </n-tag>
                </div>
                <div v-if="item.tags" class="item-tags">
                  <span v-for="tag in parseTagList(item.tags).slice(0, 3)" :key="tag" class="tag-chip">
                    {{ tag }}
                  </span>
                </div>
                <div class="item-desc">
                  {{ shortDesc(item) }}
                </div>
              </div>
            </div>
          </div>
        </n-scrollbar>
      </section>

      <!-- 右侧：详情编辑 -->
      <section class="detail-panel">
        <div class="detail-header">
          <div class="detail-title">
            <h2>{{ editingId ? '编辑设定' : (isCreating ? '新增设定' : '选择条目') }}</h2>
            <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
          </div>
          <div class="detail-actions" v-if="editingId || isCreating">
            <n-popconfirm v-if="editingId" positive-text="确认删除" negative-text="取消" @positive-click="remove">
              <template #trigger>
                <n-button type="error" text size="small">🗑️ 删除</n-button>
              </template>
              确认删除这条设定？
            </n-popconfirm>
            <n-button text size="small" @click="resetCurrent">↺ 重置</n-button>
            <n-button type="primary" size="small" :disabled="!canSave" @click="save">💾 保存</n-button>
          </div>
        </div>

        <div v-if="!editingId && !isCreating" class="detail-empty">
          <div class="empty-icon">✏️</div>
          <p>从左侧选择一条设定进行编辑</p>
          <p class="empty-sub">或点击「新增」创建</p>
        </div>

        <n-scrollbar v-else class="form-scroll">
          <n-form class="detail-form" label-placement="top" :show-label="true">
            <!-- 基本信息 -->
            <div class="form-section">
              <div class="section-title">基本信息</div>
              <n-form-item label="设定标题">
                <n-input v-model:value="form.title" placeholder="输入设定名称" size="large" />
              </n-form-item>
              <div class="form-grid-3">
                <n-form-item label="分类">
                  <n-select v-model:value="form.category" :options="categoryOptions" />
                </n-form-item>
                <n-form-item label="重要性">
                  <n-select v-model:value="form.importance" :options="importanceOptions" />
                </n-form-item>
                <n-form-item label="关联章节">
                  <n-input v-model:value="form.related_chapters" placeholder="如：1-5, 12" />
                </n-form-item>
              </div>
              <n-form-item label="标签">
                <n-input v-model:value="form.tags" placeholder="逗号分隔，如：灵能,禁忌,城市" />
              </n-form-item>
            </div>

            <!-- 设定内容 -->
            <div class="form-section">
              <div class="section-title">设定内容</div>
              <n-form-item label="详细描述">
                <n-input
                  v-model:value="form.rules"
                  type="textarea"
                  :autosize="{ minRows: 8, maxRows: 16 }"
                  placeholder="详细描述该设定的内容、规则、背景等"
                />
              </n-form-item>
              <div class="form-grid-2">
                <n-form-item label="时代背景">
                  <n-input v-model:value="form.era" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" placeholder="相关时代背景信息" />
                </n-form-item>
                <n-form-item label="地理环境">
                  <n-input v-model:value="form.geography" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" placeholder="相关地理信息" />
                </n-form-item>
              </div>
              <n-form-item label="氛围基调">
                <n-input v-model:value="form.atmosphere" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" placeholder="该设定带来的氛围感受" />
              </n-form-item>
            </div>

            <!-- 关联资料 -->
            <div class="form-section">
              <div class="section-title">关联资料</div>
              <div class="form-grid-2">
                <n-form-item label="关联人物">
                  <n-select v-model:value="selectedCharacterIds" multiple filterable :options="characterOptions" placeholder="选择相关人物" />
                </n-form-item>
                <n-form-item label="关联组织">
                  <n-select v-model:value="selectedOrganizationIds" multiple filterable :options="organizationOptions" placeholder="选择相关组织" />
                </n-form-item>
              </div>
              <n-form-item label="关联伏笔">
                <n-select v-model:value="selectedForeshadowingIds" multiple filterable :options="foreshadowingOptions" placeholder="选择相关伏笔" />
              </n-form-item>
              <n-form-item label="潜在冲突">
                <n-input v-model:value="form.conflict_notes" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" placeholder="该设定可能与哪些内容冲突" />
              </n-form-item>
            </div>
          </n-form>
        </n-scrollbar>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { createResource, deleteResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useDictStore } from '@/stores/dict'
import { useProjectDataLoader } from '@/composables/useProjectDataLoader'
import { useDirtySnapshot } from '@/composables/useDirtySnapshot'
import { notify } from '@/utils/notify'
import type { CharacterItem, ForeshadowingItem, OrganizationItem, WorldSetting } from '@/types/domain'

const projectStore = useProjectStore()
const dictStore = useDictStore()
const worlds = ref<WorldSetting[]>([])
const characters = ref<CharacterItem[]>([])
const organizations = ref<OrganizationItem[]>([])
const foreshadowings = ref<ForeshadowingItem[]>([])
const loading = ref(false)
const keyword = ref('')
const activeCategory = ref('geography')
const editingId = ref<number | null>(null)
const isCreating = ref(false)

// ===== 世界观总览 =====
const overviewExpanded = ref(false)
const overviewSaving = ref(false)
const overviewId = ref<number | null>(null)
const overviewForm = reactive({
  title: '',
  era: '',
  power_system: '',
  atmosphere: '',
  synopsis: '',
  core_rules: '',
})
const overviewOrigin = reactive({ ...overviewForm })

function findOverviewItem(): WorldSetting | undefined {
  return worlds.value.find((w) => w.category === 'overview' || w.title === '世界观总览')
}

function loadOverview() {
  const item = findOverviewItem()
  if (item) {
    overviewId.value = item.id
    overviewForm.title = item.title
    overviewForm.era = item.era
    overviewForm.atmosphere = item.atmosphere
    overviewForm.synopsis = item.rules
    overviewForm.core_rules = item.extra
    overviewForm.power_system = item.geography
  } else {
    overviewId.value = null
    overviewForm.title = '世界观总览'
    overviewForm.era = ''
    overviewForm.power_system = ''
    overviewForm.atmosphere = ''
    overviewForm.synopsis = ''
    overviewForm.core_rules = ''
  }
  Object.assign(overviewOrigin, overviewForm)
}

function resetOverview() {
  Object.assign(overviewForm, overviewOrigin)
}

async function saveOverview() {
  const projectId = projectStore.currentProject?.id
  if (!projectId) return
  overviewSaving.value = true
  try {
    const payload = {
      title: overviewForm.title || '世界观总览',
      category: 'overview',
      era: overviewForm.era,
      geography: overviewForm.power_system,
      atmosphere: overviewForm.atmosphere,
      rules: overviewForm.synopsis,
      extra: overviewForm.core_rules,
      tags: '总览',
      importance: 'high',
      related_chapters: '',
      related_characters: '',
      related_organizations: '',
      related_foreshadowings: '',
      conflict_notes: '',
    }
    if (overviewId.value) {
      await updateResource('world', overviewId.value, payload)
    } else {
      const created = await createResource<WorldSetting>('world', payload)
      overviewId.value = created.id
    }
    Object.assign(overviewOrigin, overviewForm)
    notify.success('总览已保存')
    loadWorlds()
  } catch (e) {
    notify.error('保存失败')
  } finally {
    overviewSaving.value = false
  }
}

const form = reactive<Partial<WorldSetting>>({
  id: 0,
  title: '',
  category: 'geography',
  era: '',
  geography: '',
  atmosphere: '',
  rules: '',
  extra: '',
  tags: '',
  importance: 'medium',
  related_chapters: '',
  related_characters: '',
  related_organizations: '',
  related_foreshadowings: '',
  conflict_notes: '',
})

const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form, '当前设定有未保存的修改，确定要离开吗？')

const project = computed(() => projectStore.currentProject)

// ===== 分类配置（从字典加载）=====
const categoryOptions = computed(() => dictStore.options('world_category'))

const categoryIcons: Record<string, string> = {
  geography: '🗺️',
  era: '📜',
  power_system: '⚡',
  rules: '📏',
  items: '🎒',
  weapons: '⚔️',
  medicine: '💊',
  creatures: '🐉',
  organizations: '🏛️',
  other: '📦',
}

const categoriesWithCount = computed(() => {
  return categoryOptions.value.map((opt) => ({
    value: opt.value,
    label: opt.label,
    icon: categoryIcons[opt.value] || '📌',
    count: worlds.value.filter((w) => w.category === opt.value).length,
  }))
})

const importanceOptions = computed(() => dictStore.options('importance'))

const characterOptions = computed(() => characters.value.map((c) => ({ label: c.name, value: c.id })))
const organizationOptions = computed(() => organizations.value.map((o) => ({ label: o.name, value: o.id })))
const foreshadowingOptions = computed(() => foreshadowings.value.map((f) => ({ label: f.keyword, value: f.id })))

const selectedCharacterIds = computed({
  get: () => parseIds(form.related_characters || ''),
  set: (v: number[]) => { form.related_characters = joinIds(v) },
})
const selectedOrganizationIds = computed({
  get: () => parseIds(form.related_organizations || ''),
  set: (v: number[]) => { form.related_organizations = joinIds(v) },
})
const selectedForeshadowingIds = computed({
  get: () => parseIds(form.related_foreshadowings || ''),
  set: (v: number[]) => { form.related_foreshadowings = joinIds(v) },
})

// ===== 统计 =====
const totalCount = computed(() => worlds.value.filter((w) => w.category !== 'overview').length)
const highCount = computed(() => worlds.value.filter((w) => w.importance === 'high' && w.category !== 'overview').length)
const coveredCategories = computed(() => new Set(worlds.value.filter((w) => w.category !== 'overview').map((w) => w.category)).size)
const completionRate = computed(() => {
  const total = categoryOptions.value.length || 10
  return Math.round((coveredCategories.value / total) * 100)
})

const currentCategoryLabel = computed(() => {
  const opt = categoryOptions.value.find((o) => o.value === activeCategory.value)
  return opt?.label || '设定'
})
const currentCategoryIcon = computed(() => categoryIcons[activeCategory.value] || '📌')

// ===== 列表过滤 =====
const filteredList = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return worlds.value
    .filter((w) => w.category === activeCategory.value)
    .filter((w) => {
      if (!kw) return true
      return [w.title, w.rules, w.tags, w.era, w.geography].join(' ').toLowerCase().includes(kw)
    })
    .sort((a, b) => {
      if (a.importance === 'high' && b.importance !== 'high') return -1
      if (a.importance !== 'high' && b.importance === 'high') return 1
      return (b.id || 0) - (a.id || 0)
    })
})

const canSave = computed(() => (form.title || '').trim().length > 0)

// ===== 方法 =====
function selectCategory(cat: string) {
  activeCategory.value = cat
  editingId.value = null
  isCreating.value = false
}

function selectWorld(item: WorldSetting) {
  if (!confirmIfDirty()) return
  editingId.value = item.id
  isCreating.value = false
  Object.assign(form, { ...item })
  markClean()
}

function startCreate() {
  if (!confirmIfDirty()) return
  editingId.value = null
  isCreating.value = true
  Object.assign(form, {
    id: 0,
    title: '',
    category: activeCategory.value,
    era: '',
    geography: '',
    atmosphere: '',
    rules: '',
    extra: '',
    tags: '',
    importance: 'medium',
    related_chapters: '',
    related_characters: '',
    related_organizations: '',
    related_foreshadowings: '',
    conflict_notes: '',
  })
  markClean()
}

function resetCurrent() {
  if (editingId.value) {
    const item = worlds.value.find((w) => w.id === editingId.value)
    if (item) Object.assign(form, { ...item })
  } else {
    Object.assign(form, {
      id: 0,
      title: '',
      category: activeCategory.value,
      era: '',
      geography: '',
      atmosphere: '',
      rules: '',
      extra: '',
      tags: '',
      importance: 'medium',
      related_chapters: '',
      related_characters: '',
      related_organizations: '',
      related_foreshadowings: '',
      conflict_notes: '',
    })
  }
  markClean()
}

async function save() {
  if (!canSave.value) return
  const projectId = projectStore.currentProject?.id
  if (!projectId) return

  try {
    if (editingId.value) {
      await updateResource('world', editingId.value, { ...form })
      notify.success('已保存')
    } else {
      const created = await createResource<WorldSetting>('world', { ...form })
      editingId.value = created.id
      isCreating.value = false
      notify.success('已创建')
    }
    markClean()
    loadWorlds()
  } catch (e) {
    notify.error('保存失败')
  }
}

async function remove() {
  const projectId = projectStore.currentProject?.id
  if (!projectId || !editingId.value) return
  try {
    await deleteResource('world', editingId.value)
    editingId.value = null
    isCreating.value = false
    notify.success('已删除')
    loadWorlds()
  } catch (e) {
    notify.error('删除失败')
  }
}

function parseIds(str: string): number[] {
  if (!str) return []
  return str.split(',').map((s) => parseInt(s.trim())).filter((n) => !isNaN(n))
}
function joinIds(ids: number[]): string {
  return ids.join(',')
}

function parseTagList(str: string): string[] {
  if (!str) return []
  return str.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
}

function shortDesc(item: WorldSetting): string {
  const text = item.rules || item.geography || item.era || '暂无描述'
  return text.length > 60 ? text.substring(0, 60) + '...' : text
}

function importanceLabel(val: string): string {
  return dictStore.label('importance', val) || val
}

function importanceTagType(val: string): 'default' | 'success' | 'warning' | 'info' | 'error' {
  if (val === 'high') return 'error'
  if (val === 'medium') return 'warning'
  return 'default'
}

async function loadWorlds() {
  const projectId = projectStore.currentProject?.id
  if (!projectId) return
  loading.value = true
  try {
    worlds.value = await listResource<WorldSetting>(projectId, 'world')
  } finally {
    loading.value = false
  }
}

async function load() {
  const projectId = projectStore.currentProject?.id
  if (!projectId) return
  loading.value = true
  try {
    const [wList, cList, oList, fList] = await Promise.all([
      listResource<WorldSetting>(projectId, 'world'),
      listResource<CharacterItem>(projectId, 'characters'),
      listResource<OrganizationItem>(projectId, 'organizations'),
      listResource<ForeshadowingItem>(projectId, 'foreshadowings'),
      dictStore.loadBatch(['world_category', 'importance']),
    ])
    worlds.value = wList
    characters.value = cList
    organizations.value = oList
    foreshadowings.value = fList

    // 默认选中第一个有数据的分类，否则第一个分类
    const firstWithData = categoriesWithCount.value.find((c) => c.count > 0)
    if (firstWithData) {
      activeCategory.value = firstWithData.value
    } else if (categoryOptions.value.length > 0) {
      activeCategory.value = categoryOptions.value[0].value
    }

    // 加载世界观总览
    loadOverview()
  } finally {
    loading.value = false
  }
}

useProjectDataLoader(load)
</script>

<style scoped>
.world-page {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

/* ===== 世界观概览横幅 ===== */
.world-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding: 20px 24px;
  background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
  border: 1px solid #2c4a6e;
  border-radius: 10px;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(59, 130, 246, 0.2);
  border-radius: 20px;
  font-size: 12px;
  color: #60a5fa;
  margin-bottom: 10px;
}
.badge-icon { font-size: 14px; }

.hero-title {
  font-size: 22px;
  font-weight: 700;
  color: #f3f4f6;
  margin: 0 0 6px 0;
}

.hero-desc {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
}

.hero-right {
  display: flex;
  gap: 24px;
}
.hero-stat {
  text-align: center;
}
.hero-stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #f3f4f6;
  line-height: 1.2;
}
.hero-stat-value.success { color: #4ade80; }
.hero-stat-label {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}

/* ===== 世界观总览卡片 ===== */
.overview-card {
  background: #1c1f23;
  border: 1px solid #2c3035;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
}
.overview-card.expanded {
  border-color: #3b82f6;
}

.overview-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}
.overview-head:hover {
  background: #202328;
}

.overview-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #e5e7eb;
}
.ov-icon { font-size: 16px; }

.overview-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
}
.toggle-arrow { font-size: 10px; }

.overview-body {
  padding: 0 16px 16px;
  border-top: 1px solid #2c3035;
  padding-top: 14px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.ov-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ov-field.ov-full {
  margin-bottom: 12px;
}

.ov-label {
  font-size: 12px;
  color: #9ca3af;
  font-weight: 500;
}

.ov-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

/* ===== 工作台 ===== */
.workbench {
  display: grid;
  grid-template-columns: 200px 280px 1fr;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

/* ===== 分类面板 ===== */
.category-panel {
  background: #1c1f23;
  border: 1px solid #2c3035;
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #e5e7eb;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #2c3035;
}

.category-tree {
  flex: 1;
  overflow-y: auto;
}

.cat-node {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 2px;
  transition: background 0.15s;
}
.cat-node:hover { background: #24282d; }
.cat-node.active {
  background: #22262b;
  border-left: 3px solid #3b82f6;
  padding-left: 7px;
}

.cat-icon { font-size: 16px; flex-shrink: 0; }
.cat-name { flex: 1; font-size: 13px; color: #d1d5db; }
.cat-count {
  font-size: 11px;
  color: #6b7280;
  background: #24282d;
  padding: 1px 7px;
  border-radius: 10px;
}

/* ===== 列表面板 ===== */
.list-panel {
  background: #1c1f23;
  border: 1px solid #2c3035;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.list-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-bottom: 1px solid #2c3035;
  flex-shrink: 0;
}

.list-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #e5e7eb;
}
.cur-cat-icon { font-size: 16px; }
.list-count {
  font-size: 12px;
  color: #6b7280;
  font-weight: 400;
  margin-left: 4px;
}

.list-tools {
  display: flex;
  gap: 8px;
}

.list-scroll {
  flex: 1;
  min-height: 0;
}

.setting-list {
  padding: 8px;
}

.setting-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 8px;
  border: 1px solid #2c3035;
  background: #1a1d21;
  transition: all 0.15s;
}
.setting-item:hover {
  background: #202429;
  border-color: #3a3f46;
  transform: translateX(2px);
}
.setting-item.active {
  background: #1e293b;
  border-color: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
}

.item-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
  gap: 8px;
}
.item-title {
  font-size: 13px;
  font-weight: 600;
  color: #f3f4f6;
  flex: 1;
  line-height: 1.4;
  word-break: break-all;
}

.item-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}
.tag-chip {
  font-size: 11px;
  padding: 2px 8px;
  background: #24282d;
  color: #9ca3af;
  border-radius: 10px;
  border: 1px solid #2c3035;
}

.item-desc {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.list-loading, .list-empty, .detail-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #6b7280;
  gap: 8px;
}
.empty-icon { font-size: 36px; margin-bottom: 4px; }
.empty-sub { font-size: 12px; color: #4b5563; }

/* ===== 详情面板 ===== */
.detail-panel {
  background: #1c1f23;
  border: 1px solid #2c3035;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #2c3035;
  flex-shrink: 0;
}

.detail-title h2 {
  font-size: 15px;
  font-weight: 600;
  color: #f3f4f6;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}
.dirty-dot { color: #f59e0b; font-size: 10px; }

.detail-actions {
  display: flex;
  gap: 8px;
}

.form-scroll {
  flex: 1;
  min-height: 0;
  padding: 16px;
}

.form-section {
  margin-bottom: 20px;
}
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #d1d5db;
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid #2c3035;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.form-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}

/* ===== 响应式 ===== */
@media (max-width: 1400px) {
  .workbench {
    grid-template-columns: 180px 260px 1fr;
  }
  .form-grid-3 {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 1100px) {
  .workbench {
    grid-template-columns: 180px 1fr;
  }
  .detail-panel { display: none; }
  .form-grid-2, .form-grid-3 {
    grid-template-columns: 1fr;
  }
}
</style>
