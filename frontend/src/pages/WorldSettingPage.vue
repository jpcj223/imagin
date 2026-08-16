<template>
  <div class="page world-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">🌍</span>
          世界观设定
        </h1>
        <p class="page-subtitle">
          构建世界规则、地点与禁忌，为章节生成提供稳定依据
        </p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ totalCount }}</span>
            <span class="stat-label">设定总数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ highImportanceCount }}</span>
            <span class="stat-label">高重要</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ categoryCount }}</span>
            <span class="stat-label">分类数</span>
          </div>
        </div>
        <n-button type="primary" @click="startCreate">
          <template #icon>＋</template>
          新增设定
        </n-button>
      </div>
    </div>

    <!-- 主体：三栏布局 -->
    <div class="workbench">
      <!-- 左侧：设定索引 -->
      <aside class="list-panel">
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索设定...">
            <template #prefix>🔍</template>
          </n-input>
          <n-select
            v-model:value="categoryFilter"
            clearable
            :options="categoryOptions"
            placeholder="分类筛选"
            style="width: 120px"
          />
        </div>

        <!-- 快捷模板 -->
        <div class="template-bar">
          <span class="template-label">快捷模板</span>
          <div class="template-btns">
            <n-button
              v-for="tpl in templates"
              :key="tpl.name"
              size="tiny"
              quaternary
              @click="applyTemplate(tpl)"
            >
              {{ tpl.icon }} {{ tpl.name }}
            </n-button>
          </div>
        </div>

        <n-scrollbar class="list-scroll">
          <div v-if="loading" class="list-loading">
            <n-spin size="small" />
            <span>加载中...</span>
          </div>

          <div v-else-if="groupedWorlds.length === 0" class="list-empty">
            <div class="empty-icon">📑</div>
            <p>还没有设定</p>
            <p class="empty-sub">点击右上角「新增设定」开始构建世界</p>
          </div>

          <div v-else class="setting-groups">
            <template v-for="group in groupedWorlds" :key="group.category">
              <!-- 分类组头 -->
              <div class="group-header">
                <span class="group-icon">{{ categoryIcon(group.category) }}</span>
                <span class="group-name">{{ categoryLabel(group.category) }}</span>
                <n-tag size="tiny" type="default">{{ group.items.length }}</n-tag>
              </div>

              <!-- 设定列表 -->
              <div class="group-items">
                <div
                  v-for="item in group.items"
                  :key="item.id"
                  class="setting-item"
                  :class="{ active: editingId === item.id }"
                  @click="selectWorld(item)"
                >
                  <div class="item-icon">{{ categoryIcon(item.category) }}</div>
                  <div class="item-content">
                    <div class="item-title-row">
                      <span class="item-title">{{ item.title || '未命名设定' }}</span>
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
                      {{ shortText(item.rules || item.geography || item.era || '暂无描述', 60) }}
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </n-scrollbar>
      </aside>

      <!-- 中间：详情编辑 -->
      <section class="detail-panel">
        <div class="detail-header">
          <div class="detail-title">
            <h2>
              {{ editingId ? '编辑设定' : '新增设定' }}
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
              确认删除这条设定？
            </n-popconfirm>
            <n-button @click="resetCurrent">↺ 重置</n-button>
            <n-button type="primary" :disabled="!canSave" @click="save">
              💾 保存
            </n-button>
          </div>
        </div>

        <div v-if="!editingId && !isCreating" class="detail-empty">
          <div class="empty-icon">✏️</div>
          <p>从左侧选择一条设定进行编辑</p>
          <p class="empty-sub">或点击右上角新增</p>
        </div>

        <n-scrollbar v-else class="form-scroll">
          <n-form class="detail-form" label-placement="top" :show-label="true">
            <!-- 基本信息 -->
            <div class="form-section">
              <div class="section-title">
                基本信息
                <span class="section-hint">设定的标识和分类</span>
              </div>
              <n-form-item label="设定标题">
                <n-input
                  v-model:value="form.title"
                  placeholder="例如：灵能等级体系、旧城禁区"
                  size="large"
                />
              </n-form-item>
              <div class="form-grid-3">
                <n-form-item label="分类">
                  <n-select v-model:value="form.category" :options="categoryOptions" />
                </n-form-item>
                <n-form-item label="重要性">
                  <n-select v-model:value="form.importance" :options="importanceOptions" />
                </n-form-item>
                <n-form-item label="关联章节">
                  <n-input v-model:value="form.related_chapters" placeholder="例如：1-5, 12" />
                </n-form-item>
              </div>
              <n-form-item label="标签">
                <n-input v-model:value="form.tags" placeholder="逗号分隔，例如：灵能, 禁忌, 城市" />
              </n-form-item>
            </div>

            <!-- 世界设定内容 -->
            <div class="form-section">
              <div class="section-title">
                设定内容
                <span class="section-hint">描述世界的规则与细节</span>
              </div>
              <div class="form-grid-2">
                <n-form-item label="时代背景">
                  <n-input
                    v-model:value="form.era"
                    type="textarea"
                    :autosize="{ minRows: 4, maxRows: 8 }"
                    placeholder="描述故事发生的时代、历史背景、社会结构..."
                  />
                </n-form-item>
                <n-form-item label="地点 / 空间结构">
                  <n-input
                    v-model:value="form.geography"
                    type="textarea"
                    :autosize="{ minRows: 4, maxRows: 8 }"
                    placeholder="描述地理环境、重要地点、空间布局..."
                  />
                </n-form-item>
              </div>
              <div class="form-grid-2">
                <n-form-item label="氛围基调">
                  <n-input
                    v-model:value="form.atmosphere"
                    type="textarea"
                    :autosize="{ minRows: 4, maxRows: 8 }"
                    placeholder="描述整体叙事氛围、情感基调、美学风格..."
                  />
                </n-form-item>
                <n-form-item label="世界规则 / 禁忌">
                  <n-input
                    v-model:value="form.rules"
                    type="textarea"
                    :autosize="{ minRows: 4, maxRows: 8 }"
                    placeholder="描述世界运行规则、力量体系、禁忌事项..."
                  />
                </n-form-item>
              </div>
              <n-form-item label="补充信息">
                <n-input
                  v-model:value="form.extra"
                  type="textarea"
                  :autosize="{ minRows: 4, maxRows: 10 }"
                  placeholder="其他需要记录的补充设定..."
                />
                <div class="desc-footer">
                  <span class="char-count">{{ totalContentLength }} 字</span>
                </div>
              </n-form-item>
            </div>

            <!-- 关联数据 -->
            <div class="form-section">
              <div class="section-title">
                关联数据
                <span class="section-hint">与其他资料的关联关系</span>
              </div>
              <div class="form-grid-2">
                <n-form-item label="关联人物">
                  <n-select
                    v-model:value="selectedCharacterIds"
                    multiple
                    clearable
                    filterable
                    :options="characterOptions"
                    placeholder="选择受此设定影响的人物"
                  />
                </n-form-item>
                <n-form-item label="关联组织">
                  <n-select
                    v-model:value="selectedOrganizationIds"
                    multiple
                    clearable
                    filterable
                    :options="organizationOptions"
                    placeholder="选择相关的组织势力"
                  />
                </n-form-item>
              </div>
              <n-form-item label="关联伏笔">
                <n-select
                  v-model:value="selectedForeshadowingIds"
                  multiple
                  clearable
                  filterable
                  :options="foreshadowingOptions"
                  placeholder="选择与此设定绑定的伏笔"
                />
              </n-form-item>
              <n-form-item label="冲突检查备注">
                <n-input
                  v-model:value="form.conflict_notes"
                  type="textarea"
                  :autosize="{ minRows: 3, maxRows: 6 }"
                  placeholder="记录可能与角色、组织、章节冲突的地方..."
                />
              </n-form-item>
            </div>
          </n-form>
        </n-scrollbar>
      </section>

      <!-- 右侧：设定体检 -->
      <aside class="side-panel">
        <!-- 完整度卡片 -->
        <div class="insight-card primary-card">
          <div class="card-header">
            <span class="card-icon">📊</span>
            <span class="card-title">设定完整度</span>
          </div>
          <div class="completion-display">
            <div class="completion-ring">
              <svg viewBox="0 0 80 80" class="ring-svg">
                <circle cx="40" cy="40" r="34" class="ring-bg" />
                <circle
                  cx="40"
                  cy="40"
                  r="34"
                  class="ring-fill"
                  :style="{ strokeDasharray: `${currentCompletion * 2.136} 213.6` }"
                />
              </svg>
              <div class="ring-center">
                <span class="ring-num">{{ currentCompletion }}</span>
                <span class="ring-unit">%</span>
              </div>
            </div>
          </div>
          <p class="completion-advice">{{ completionAdvice }}</p>
        </div>

        <!-- 分类覆盖 -->
        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">🏷️</span>
            <span class="card-title">分类覆盖</span>
          </div>
          <div class="category-grid">
            <div
              v-for="item in categoryStats"
              :key="item.value"
              class="category-item"
              :class="{ active: item.count > 0 }"
            >
              <span class="cat-icon">{{ categoryIcon(item.value) }}</span>
              <span class="cat-name">{{ item.label }}</span>
              <span class="cat-count">{{ item.count }}</span>
            </div>
          </div>
        </div>

        <!-- 快速清单 -->
        <div class="insight-card">
          <div class="card-header">
            <span class="card-icon">💡</span>
            <span class="card-title">AI 补全建议</span>
          </div>
          <div class="check-list">
            <div v-for="(hint, idx) in assistantHints" :key="idx" class="check-row" :class="{ ready: hint.done }">
              <span class="check-icon">{{ hint.done ? '✓' : '○' }}</span>
              <span class="check-text">{{ hint.text }}</span>
            </div>
          </div>
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
import type { CharacterItem, ForeshadowingItem, OrganizationItem, WorldSetting } from '@/types/domain'

const projectStore = useProjectStore()
const worlds = ref<WorldSetting[]>([])
const characters = ref<CharacterItem[]>([])
const organizations = ref<OrganizationItem[]>([])
const foreshadowings = ref<ForeshadowingItem[]>([])
const keyword = ref('')
const categoryFilter = ref<string | null>(null)
const editingId = ref<number | null>(null)
const isCreating = ref(false)
const loading = ref(false)

const form = reactive({
  title: '',
  category: 'other',
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
  conflict_notes: ''
})

// 脏数据检测
const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form, '当前设定有未保存的修改，确定要离开吗？')

// ===== 选项配置 =====
const categoryOptions = [
  { label: '时代', value: 'era' },
  { label: '地点', value: 'location' },
  { label: '力量体系', value: 'power' },
  { label: '规则', value: 'rule' },
  { label: '禁忌', value: 'taboo' },
  { label: '名词', value: 'term' },
  { label: '其他', value: 'other' }
]

const importanceOptions = [
  { label: '低', value: 'low' },
  { label: '中', value: 'medium' },
  { label: '高', value: 'high' }
]

const templates = [
  {
    icon: '⚔️',
    name: '玄幻仙侠',
    title: '灵力与宗门体系',
    category: 'power',
    era: '古典架空，宗门林立。',
    geography: '九州、秘境、宗门山门。',
    atmosphere: '热血、宿命、强者为尊。',
    rules: '修为境界分明，灵力消耗必须自洽。',
    extra: '',
    tags: '修炼,宗门',
    importance: 'high',
    related_chapters: '',
    related_characters: '',
    related_organizations: '',
    related_foreshadowings: '',
    conflict_notes: ''
  },
  {
    icon: '🏙️',
    name: '都市异能',
    title: '城市异常管理',
    category: 'rule',
    era: '现代都市，异能隐藏于日常。',
    geography: '城市、地下组织、异能管理局。',
    atmosphere: '现实压迫与超常力量并存。',
    rules: '能力有代价，官方组织会追踪异常事件。',
    extra: '',
    tags: '异能,管理局',
    importance: 'high',
    related_chapters: '',
    related_characters: '',
    related_organizations: '',
    related_foreshadowings: '',
    conflict_notes: ''
  },
  {
    icon: '🚀',
    name: '星际科幻',
    title: '星际航行边界',
    category: 'rule',
    era: '远未来，星际航行成熟。',
    geography: '殖民星、空间站、边境航道。',
    atmosphere: '宏大、冷峻、文明冲突。',
    rules: '能源、航行距离和信息延迟需要保持一致。',
    extra: '',
    tags: '星舰,边境',
    importance: 'medium',
    related_chapters: '',
    related_characters: '',
    related_organizations: '',
    related_foreshadowings: '',
    conflict_notes: ''
  }
]

// ===== 计算属性 =====
const filteredWorlds = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return worlds.value.filter((item) => {
    const matchedText =
      !text ||
      [item.title, item.category, item.era, item.geography, item.atmosphere, item.rules, item.extra, item.tags, item.conflict_notes]
        .join(' ')
        .toLowerCase()
        .includes(text)
    const matchedCategory = !categoryFilter.value || item.category === categoryFilter.value
    return matchedText && matchedCategory
  })
})

// 按分类分组
const groupedWorlds = computed(() => {
  const groups: { category: string; items: WorldSetting[] }[] = []
  const categoryOrder = categoryOptions.map((o) => o.value)

  for (const cat of categoryOrder) {
    const items = filteredWorlds.value.filter((w) => w.category === cat)
    if (items.length > 0) {
      groups.push({ category: cat, items })
    }
  }
  return groups
})

// 统计数据
const totalCount = computed(() => worlds.value.length)
const highImportanceCount = computed(() => worlds.value.filter((w) => w.importance === 'high').length)
const categoryCount = computed(() => new Set(worlds.value.map((w) => w.category)).size)

const canSave = computed(() => form.title.trim().length > 0)

const currentCompletion = computed(() => completionOf(form))

const totalContentLength = computed(() => {
  return form.era.length + form.geography.length + form.atmosphere.length + form.rules.length + form.extra.length
})

const categoryStats = computed(() =>
  categoryOptions.map((option) => ({
    ...option,
    count: worlds.value.filter((item) => item.category === option.value).length
  }))
)

const completionAdvice = computed(() => {
  if (currentCompletion.value >= 80) return '设定已经较完整，适合进入章节生成上下文。'
  if (form.category === 'rule' || form.category === 'taboo') return '规则类设定建议写清触发条件、代价和例外。'
  return '建议补充标题、标签、规则和关联章节，方便后续检索。'
})

const assistantHints = computed(() => [
  { done: !!form.rules, text: form.rules ? '规则可用于生成前约束' : '缺少明确规则描述' },
  { done: !!form.related_chapters, text: form.related_chapters ? '已标记关联章节' : '可补充关联章节范围' },
  {
    done: !!(form.related_characters || form.related_organizations),
    text: form.related_characters || form.related_organizations ? '已建立资料关联' : '可关联人物或组织'
  },
  { done: !!form.conflict_notes, text: form.conflict_notes ? '已记录潜在冲突' : '建议记录可能的冲突点' }
])

const characterOptions = computed(() => characters.value.map((item) => ({ label: item.name, value: item.id })))
const organizationOptions = computed(() => organizations.value.map((item) => ({ label: item.name, value: item.id })))
const foreshadowingOptions = computed(() => foreshadowings.value.map((item) => ({ label: item.keyword, value: item.id })))

const selectedCharacterIds = computed({
  get: () => parseIds(form.related_characters),
  set: (value: number[]) => {
    form.related_characters = joinIds(value)
  }
})
const selectedOrganizationIds = computed({
  get: () => parseIds(form.related_organizations),
  set: (value: number[]) => {
    form.related_organizations = joinIds(value)
  }
})
const selectedForeshadowingIds = computed({
  get: () => parseIds(form.related_foreshadowings),
  set: (value: number[]) => {
    form.related_foreshadowings = joinIds(value)
  }
})

// ===== 工具函数 =====
function parseIds(value: string) {
  return value
    .split(',')
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isFinite(item) && item > 0)
}

function joinIds(value: number[]) {
  return value.join(',')
}

function parseTagList(tags: string) {
  return tags
    .split(',')
    .map((t) => t.trim())
    .filter((t) => t.length > 0)
}

function completionOf(item: Partial<WorldSetting> | typeof form) {
  const fields = ['title', 'category', 'era', 'geography', 'atmosphere', 'rules', 'extra', 'tags', 'importance', 'related_chapters']
  const finished = fields.filter((field) => String(item[field as keyof typeof item] ?? '').trim()).length
  return Math.round((finished / fields.length) * 100)
}

function shortText(value: string, max = 50) {
  return value?.length > max ? `${value.slice(0, max)}...` : value || ''
}

function categoryLabel(value: string) {
  return categoryOptions.find((item) => item.value === value)?.label ?? '其他'
}

function categoryIcon(category: string): string {
  const icons: Record<string, string> = {
    era: '⏳',
    location: '📍',
    power: '⚡',
    rule: '📜',
    taboo: '⛔',
    term: '📖',
    other: '📁'
  }
  return icons[category] || '📁'
}

function importanceLabel(value: string) {
  return importanceOptions.find((item) => item.value === value)?.label ?? value
}

function importanceTagType(importance: string): 'default' | 'success' | 'info' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'success' | 'info' | 'warning' | 'error'> = {
    low: 'default',
    medium: 'info',
    high: 'warning'
  }
  return map[importance] || 'default'
}

// ===== 表单操作 =====
function fillForm(item?: Partial<WorldSetting>) {
  Object.assign(form, {
    title: item?.title ?? '',
    category: item?.category ?? 'other',
    era: item?.era ?? '',
    geography: item?.geography ?? '',
    atmosphere: item?.atmosphere ?? '',
    rules: item?.rules ?? '',
    extra: item?.extra ?? '',
    tags: item?.tags ?? '',
    importance: item?.importance ?? 'medium',
    related_chapters: item?.related_chapters ?? '',
    related_characters: item?.related_characters ?? '',
    related_organizations: item?.related_organizations ?? '',
    related_foreshadowings: item?.related_foreshadowings ?? '',
    conflict_notes: item?.conflict_notes ?? ''
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

async function selectWorld(item: WorldSetting) {
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
  const current = worlds.value.find((item) => item.id === editingId.value)
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

async function applyTemplate(template: (typeof templates)[number]) {
  if (!(await confirmIfDirty())) return
  editingId.value = null
  isCreating.value = true
  Object.assign(form, template)
  await nextTick()
  markClean()
}

async function ensureProject() {
  if (!projectStore.currentProject) await projectStore.loadDefaultProject()
  return projectStore.currentProject?.id
}

// ===== 数据加载 =====
async function load() {
  const projectId = projectStore.currentProject!.id
  loading.value = true
  try {
    const [worldList, characterList, organizationList, foreshadowingList] = await Promise.all([
      listResource<WorldSetting>(projectId, 'world'),
      listResource<CharacterItem>(projectId, 'characters'),
      listResource<OrganizationItem>(projectId, 'organizations'),
      listResource<ForeshadowingItem>(projectId, 'foreshadowings')
    ])
    worlds.value = worldList
    characters.value = characterList
    organizations.value = organizationList
    foreshadowings.value = foreshadowingList

    if (!editingId.value && !isCreating.value && worlds.value[0]) {
      editingId.value = worlds.value[0].id
      fillForm(worlds.value[0])
      await nextTick()
      markClean()
    }
  } finally {
    loading.value = false
  }
}

// ===== CRUD =====
async function save() {
  if (!canSave.value) return
  const projectId = await ensureProject()
  if (!projectId) return

  if (editingId.value) {
    const updated = await updateResource<WorldSetting>('world', editingId.value, { ...form })
    notify.success('设定已更新')
    await load()
    const fresh = worlds.value.find((item) => item.id === updated.id)
    if (fresh) {
      fillForm(fresh)
      await nextTick()
      markClean()
    }
  } else {
    const created = await createResource<WorldSetting>('world', { project_id: projectId, ...form })
    notify.success('设定已新增')
    isCreating.value = false
    await load()
    const fresh = worlds.value.find((item) => item.id === created.id)
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
  const currentIndex = worlds.value.findIndex((item) => item.id === editingId.value)
  await deleteResource('world', editingId.value)
  notify.success('设定已删除')
  const nextItem = worlds.value[currentIndex + 1] || worlds.value[currentIndex - 1]
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
.world-page {
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
  min-width: 50px;
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
  grid-template-columns: 320px minmax(480px, 1fr) 280px;
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

/* ===== 左侧列表面板 ===== */
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

.template-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.template-label {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  font-weight: 600;
}

.template-btns {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
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
  padding: 60px 20px;
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

/* 设定分组 */
.setting-groups {
  padding: 8px 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 8px 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--n-text-color-2, #9ca3af);
  position: sticky;
  top: 0;
  background: var(--n-color-card, #1a1d21);
  z-index: 1;
}

.group-header:first-child {
  padding-top: 4px;
}

.group-icon {
  font-size: 14px;
}

.group-name {
  flex: 1;
}

.group-items {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.setting-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.setting-item:hover {
  background: var(--n-color-hover, #23272f);
}

.setting-item.active {
  background: var(--n-color-primary-1-suppl, #1e3a5f);
  border-color: var(--n-color-primary-3, #3b82f6);
}

.item-icon {
  font-size: 16px;
  flex-shrink: 0;
  width: 22px;
  text-align: center;
  margin-top: 1px;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.item-title {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 4px;
}

.tag-chip {
  padding: 1px 6px;
  font-size: 10px;
  border-radius: 4px;
  background: var(--n-color-1, #1e2228);
  color: var(--n-text-color-2, #9ca3af);
  border: 1px solid var(--n-border-color, #2a2f3a);
}

.item-desc {
  font-size: 11px;
  color: var(--n-text-color-2, #9ca3af);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ===== 中间详情面板 ===== */
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

.desc-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.char-count {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
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

/* 完整度圆环 */
.completion-display {
  display: flex;
  justify-content: center;
  margin-bottom: 12px;
}

.completion-ring {
  position: relative;
  width: 80px;
  height: 80px;
}

.ring-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-bg {
  fill: none;
  stroke: var(--n-border-color, #2a2f3a);
  stroke-width: 6;
}

.ring-fill {
  fill: none;
  stroke: url(#ringGradient);
  stroke: var(--n-color-primary, #3b82f6);
  stroke-width: 6;
  stroke-linecap: round;
  transition: stroke-dasharray 0.5s ease;
}

.ring-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: baseline;
  gap: 1px;
}

.ring-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--n-text-color-1, #e5e7eb);
  line-height: 1;
}

.ring-unit {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

.completion-advice {
  margin: 0;
  font-size: 11px;
  color: var(--n-text-color-2, #9ca3af);
  line-height: 1.6;
  text-align: center;
}

/* 分类网格 */
.category-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  font-size: 11px;
  transition: all 0.15s;
}

.category-item.active {
  border-color: var(--n-color-primary-3, #3b82f6);
  background: var(--n-color-primary-1-suppl, #1e3a5f);
}

.cat-icon {
  font-size: 13px;
}

.cat-name {
  flex: 1;
  color: var(--n-text-color-2, #9ca3af);
}

.category-item.active .cat-name {
  color: var(--n-text-color-1, #e5e7eb);
}

.cat-count {
  font-weight: 600;
  color: var(--n-text-color-3, #6b7280);
}

.category-item.active .cat-count {
  color: var(--n-color-primary, #3b82f6);
}

/* 检查清单 */
.check-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.check-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

.check-row.ready {
  color: var(--n-text-color-2, #9ca3af);
}

.check-icon {
  flex-shrink: 0;
  width: 16px;
  text-align: center;
  font-size: 11px;
}

.check-row.ready .check-icon {
  color: var(--n-color-success, #36d399);
}

.check-text {
  line-height: 1.5;
}
</style>
