<template>
  <div class="page page-wide">
    <div class="page-title">
      <div>
        <h1>🌍 设定档案库</h1>
        <p class="muted">按分类管理世界规则、地点、禁忌和名词，让章节生成有稳定依据。</p>
      </div>
      <div class="title-actions">
        <n-button @click="load">刷新</n-button>
        <n-button type="primary" @click="startCreate">新增设定</n-button>
      </div>
    </div>

    <div class="triple-workbench archive-workbench">
      <aside class="list-panel">
        <div class="panel-head">
          <h2>设定索引</h2>
          <span class="muted">{{ filteredWorlds.length }} / {{ worlds.length }}</span>
        </div>
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索标题、标签、规则" />
          <n-select v-model:value="categoryFilter" clearable :options="categoryOptions" placeholder="按分类筛选" />
          <div class="mini-list">
            <n-button v-for="template in templates" :key="template.name" size="small" @click="applyTemplate(template)">
              {{ template.icon }} {{ template.name }}
            </n-button>
          </div>
        </div>
        <div class="list-body">
          <n-empty v-if="filteredWorlds.length === 0" description="暂无匹配设定" />
          <template v-else>
            <button
              v-for="item in filteredWorlds"
              :key="item.id"
              class="list-item"
              :class="{ active: editingId === item.id }"
              @click="selectWorld(item)"
            >
              <div class="item-title">
                <span>{{ item.title || item.era || '未命名设定' }}</span>
                <span class="muted">{{ categoryLabel(item.category) }}</span>
              </div>
              <div class="item-meta">{{ item.tags || '暂无标签' }} · {{ importanceLabel(item.importance) }}</div>
              <div class="item-meta">{{ item.rules || item.geography || '尚未写入设定内容' }}</div>
            </button>
          </template>
        </div>
      </aside>

      <section class="detail-panel setting-editor">
        <div class="panel-head inline-head">
          <h2>{{ editingId ? '设定详情编辑' : '新设定档案' }}</h2>
          <span class="muted">{{ editingId ? `ID ${editingId}` : '等待保存' }}</span>
        </div>

        <n-form label-placement="top">
          <div class="grid-3">
            <n-form-item label="设定标题">
              <n-input v-model:value="form.title" placeholder="例如：灵能等级、旧城禁区" />
            </n-form-item>
            <n-form-item label="分类">
              <n-select v-model:value="form.category" :options="categoryOptions" />
            </n-form-item>
            <n-form-item label="重要性">
              <n-select v-model:value="form.importance" :options="importanceOptions" />
            </n-form-item>
          </div>

          <div class="grid-2">
            <n-form-item label="标签">
              <n-input v-model:value="form.tags" placeholder="逗号分隔，例如：灵能, 禁忌, 城市" />
            </n-form-item>
            <n-form-item label="关联章节">
              <n-input v-model:value="form.related_chapters" placeholder="例如：1-5, 12" />
            </n-form-item>
          </div>

          <n-form-item label="时代背景">
            <n-input v-model:value="form.era" type="textarea" :autosize="{ minRows: 3 }" />
          </n-form-item>
          <n-form-item label="地点 / 空间结构">
            <n-input v-model:value="form.geography" type="textarea" :autosize="{ minRows: 4 }" />
          </n-form-item>
          <div class="grid-2">
            <n-form-item label="氛围基调">
              <n-input v-model:value="form.atmosphere" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
            <n-form-item label="世界规则 / 禁忌">
              <n-input v-model:value="form.rules" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
          </div>
          <n-form-item label="补充信息">
            <n-input v-model:value="form.extra" type="textarea" :autosize="{ minRows: 4 }" />
          </n-form-item>
        </n-form>

        <div class="detail-actions">
          <n-button type="primary" @click="save">保存</n-button>
          <n-button @click="startCreate">新增</n-button>
          <n-button @click="resetCurrent">重置</n-button>
          <n-popconfirm v-if="editingId" positive-text="确认删除" negative-text="取消" @positive-click="remove">
            <template #trigger>
              <n-button type="error">删除</n-button>
            </template>
            删除后不可恢复，确认删除这条设定？
          </n-popconfirm>
        </div>
      </section>

      <aside class="side-panel setting-side">
        <div class="panel-head inline-head">
          <h2>设定体检</h2>
          <span class="muted">{{ currentCompletion }}%</span>
        </div>

        <div class="insight-card">
          <div class="insight-label">完整度</div>
          <div class="dossier-progress large">
            <span :style="{ width: `${currentCompletion}%` }"></span>
          </div>
          <p class="muted">{{ completionAdvice }}</p>
        </div>

        <n-form label-placement="top">
          <n-form-item label="关联人物">
            <n-select v-model:value="selectedCharacterIds" multiple clearable filterable :options="characterOptions" placeholder="选择受这条设定影响的人物" />
          </n-form-item>
          <n-form-item label="关联组织">
            <n-select v-model:value="selectedOrganizationIds" multiple clearable filterable :options="organizationOptions" placeholder="选择使用或约束这条设定的组织" />
          </n-form-item>
          <n-form-item label="关联伏笔">
            <n-select v-model:value="selectedForeshadowingIds" multiple clearable filterable :options="foreshadowingOptions" placeholder="选择和设定绑定的伏笔" />
          </n-form-item>
          <n-form-item label="冲突检查备注">
            <n-input v-model:value="form.conflict_notes" type="textarea" :autosize="{ minRows: 6 }" placeholder="记录可能和角色、组织、章节冲突的地方" />
          </n-form-item>
        </n-form>

        <div class="insight-card">
          <div class="insight-label">分类覆盖</div>
          <div class="tag-cloud">
            <span v-for="item in categoryStats" :key="item.value">
              {{ item.label }} {{ item.count }}
            </span>
          </div>
        </div>

        <div class="insight-card">
          <div class="insight-label">AI 补全建议</div>
          <div class="check-list">
            <div v-for="item in assistantHints" :key="item" class="check-row ready">
              <span>✓</span>
              <span>{{ item }}</span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { createResource, deleteResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import type { CharacterItem, ForeshadowingItem, OrganizationItem, WorldSetting } from '@/types/domain'

const message = useMessage()
const projectStore = useProjectStore()
const worlds = ref<WorldSetting[]>([])
const characters = ref<CharacterItem[]>([])
const organizations = ref<OrganizationItem[]>([])
const foreshadowings = ref<ForeshadowingItem[]>([])
const keyword = ref('')
const categoryFilter = ref<string | null>(null)
const editingId = ref<number | null>(null)

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
  { icon: '⚔️', name: '玄幻仙侠', title: '灵力与宗门体系', category: 'power', era: '古典架空，宗门林立。', geography: '九州、秘境、宗门山门。', atmosphere: '热血、宿命、强者为尊。', rules: '修为境界分明，灵力消耗必须自洽。', extra: '', tags: '修炼,宗门', importance: 'high', related_chapters: '', related_characters: '', related_organizations: '', related_foreshadowings: '', conflict_notes: '' },
  { icon: '🏙️', name: '都市异能', title: '城市异常管理', category: 'rule', era: '现代都市，异能隐藏于日常。', geography: '城市、地下组织、异能管理局。', atmosphere: '现实压迫与超常力量并存。', rules: '能力有代价，官方组织会追踪异常事件。', extra: '', tags: '异能,管理局', importance: 'high', related_chapters: '', related_characters: '', related_organizations: '', related_foreshadowings: '', conflict_notes: '' },
  { icon: '🚀', name: '星际科幻', title: '星际航行边界', category: 'rule', era: '远未来，星际航行成熟。', geography: '殖民星、空间站、边境航道。', atmosphere: '宏大、冷峻、文明冲突。', rules: '能源、航行距离和信息延迟需要保持一致。', extra: '', tags: '星舰,边境', importance: 'medium', related_chapters: '', related_characters: '', related_organizations: '', related_foreshadowings: '', conflict_notes: '' }
]

const filteredWorlds = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return worlds.value.filter((item) => {
    const matchedText = !text || [item.title, item.category, item.era, item.geography, item.atmosphere, item.rules, item.extra, item.tags, item.conflict_notes].join(' ').toLowerCase().includes(text)
    const matchedCategory = !categoryFilter.value || item.category === categoryFilter.value
    return matchedText && matchedCategory
  })
})
const currentCompletion = computed(() => completionOf(form))
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
  form.rules ? '规则可用于生成前约束' : '缺少明确规则',
  form.related_chapters ? '已标记关联章节' : '可补充关联章节',
  form.related_characters || form.related_organizations ? '已建立资料关联' : '可关联人物或组织',
  form.conflict_notes ? '已记录潜在冲突' : '建议记录可能冲突'
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

function parseIds(value: string) {
  return value
    .split(',')
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isFinite(item) && item > 0)
}

function joinIds(value: number[]) {
  return value.join(',')
}

function completionOf(item: Partial<WorldSetting> | typeof form) {
  const fields = ['title', 'category', 'era', 'geography', 'atmosphere', 'rules', 'extra', 'tags', 'importance', 'related_chapters']
  const finished = fields.filter((field) => String(item[field as keyof typeof item] ?? '').trim()).length
  return Math.round((finished / fields.length) * 100)
}

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

function categoryLabel(value: string) {
  return categoryOptions.find((item) => item.value === value)?.label ?? '其他'
}

function importanceLabel(value: string) {
  return importanceOptions.find((item) => item.value === value)?.label ?? value
}

function startCreate() {
  // 新增设定时保持右侧体检面板联动，让用户能边写边看完整度。
  editingId.value = null
  fillForm()
}

function selectWorld(item: WorldSetting) {
  // 从设定索引切换时只同步表单，不直接写数据库。
  editingId.value = item.id
  fillForm(item)
}

function resetCurrent() {
  const current = worlds.value.find((item) => item.id === editingId.value)
  current ? selectWorld(current) : startCreate()
}

function applyTemplate(template: (typeof templates)[number]) {
  editingId.value = null
  Object.assign(form, template)
}

async function ensureProject() {
  if (!projectStore.currentProject) await projectStore.loadDefaultProject()
  return projectStore.currentProject?.id
}

async function load() {
  const projectId = await ensureProject()
  if (!projectId) return
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
  if (!editingId.value && worlds.value[0]) selectWorld(worlds.value[0])
}

async function save() {
  const projectId = await ensureProject()
  if (!projectId) return

  // 保存流程兼容旧数据：新增字段全部带默认值，旧库启动迁移后可直接写入。
  if (editingId.value) {
    const updated = await updateResource<WorldSetting>('world', editingId.value, { ...form })
    message.success('设定已更新')
    await load()
    selectWorld(updated)
  } else {
    const created = await createResource<WorldSetting>('world', { project_id: projectId, ...form })
    message.success('设定已新增')
    await load()
    selectWorld(created)
  }
}

async function remove() {
  if (!editingId.value) return
  await deleteResource('world', editingId.value)
  message.success('设定已删除')
  editingId.value = null
  fillForm()
  await load()
}

onMounted(load)
</script>

<style scoped>
.archive-workbench {
  grid-template-columns: 300px minmax(560px, 1fr) 320px;
}

.title-actions {
  display: flex;
  gap: 10px;
}

.setting-editor {
  background: linear-gradient(180deg, #24272d 0%, #202327 160px);
}

.setting-side {
  position: sticky;
  top: 16px;
}

.dossier-progress {
  height: 5px;
  margin: 8px 0;
  overflow: hidden;
  border-radius: 99px;
  background: #30343a;
}

.dossier-progress span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #63e2b7, #4f8cff);
}

.dossier-progress.large {
  height: 8px;
}

.insight-card {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid #30343a;
  border-radius: 8px;
  background: #181b1f;
}

.insight-label {
  margin-bottom: 8px;
  color: #e5e7eb;
  font-weight: 800;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-cloud span {
  padding: 4px 8px;
  border: 1px solid #34383d;
  border-radius: 999px;
  color: #cbd5e1;
  background: #202327;
}
</style>
