<template>
  <div class="page page-wide">
    <div class="page-title">
      <div>
        <h1>👥 角色档案工作台</h1>
        <p class="muted">把人物从“姓名表”推进到可持续写作的人设档案。</p>
      </div>
      <div class="title-actions">
        <n-button @click="load">刷新</n-button>
        <n-button type="primary" @click="startCreate">新建角色</n-button>
      </div>
    </div>

    <div class="triple-workbench archive-workbench">
      <aside class="list-panel">
        <div class="panel-head">
          <h2>角色库</h2>
          <span class="muted">{{ filteredCharacters.length }} / {{ characters.length }}</span>
        </div>
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索姓名、身份、动机、秘密" />
          <n-select v-model:value="roleFilter" clearable :options="roleTypes" placeholder="按角色类型筛选" />
        </div>
        <div class="list-body">
          <n-spin v-if="loading" description="加载中..." />
          <n-empty v-else-if="filteredCharacters.length === 0" :description="characters.length === 0 ? '还没有角色，点击右上角新增' : '暂无匹配角色'" />
          <template v-else>
            <button
              v-for="item in filteredCharacters"
              :key="item.id"
              class="list-item dossier-item"
              :class="{ active: editingId === item.id }"
              @click="selectCharacter(item)"
            >
              <div class="item-title">
                <span>{{ item.name }}</span>
                <span class="muted">{{ roleTypeLabel(item.role_type) }}</span>
              </div>
              <div class="item-meta">{{ item.identity || '身份未定' }} · {{ item.faction || '阵营未定' }}</div>
              <div class="dossier-progress">
                <span :style="{ width: `${completionOf(item)}%` }"></span>
              </div>
              <div class="item-meta">{{ item.motivation || item.personality || '尚未写入角色驱动力' }}</div>
            </button>
          </template>
        </div>
      </aside>

      <section class="detail-panel dossier-editor">
        <div class="panel-head inline-head">
          <h2>
            {{ editingId ? '角色档案编辑' : '新角色档案' }}
            <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
          </h2>
          <span class="muted">{{ editingId ? `ID ${editingId}` : '等待保存' }}</span>
        </div>

        <n-form label-placement="top">
          <div class="grid-3">
            <n-form-item label="角色名称">
              <n-input v-model:value="form.name" />
            </n-form-item>
            <n-form-item label="角色类型">
              <n-select v-model:value="form.role_type" :options="roleTypes" />
            </n-form-item>
            <n-form-item label="MBTI / 性格标签">
              <n-input v-model:value="form.mbti" placeholder="例如 INTJ / 外冷内热" />
            </n-form-item>
          </div>

          <div class="grid-2">
            <n-form-item label="身份 / 职业">
              <n-input v-model:value="form.identity" placeholder="表层身份、职业、江湖称号" />
            </n-form-item>
            <n-form-item label="阵营 / 所属势力">
              <n-input v-model:value="form.faction" placeholder="主角团、敌对组织、中立势力" />
            </n-form-item>
          </div>

          <div class="grid-2">
            <n-form-item label="外貌特征">
              <n-input v-model:value="form.appearance" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
            <n-form-item label="性格特征">
              <n-input v-model:value="form.personality" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
          </div>

          <div class="grid-2">
            <n-form-item label="核心动机">
              <n-input v-model:value="form.motivation" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
            <n-form-item label="弱点 / 缺陷">
              <n-input v-model:value="form.weakness" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
          </div>

          <n-form-item label="背景故事">
            <n-input v-model:value="form.background" type="textarea" :autosize="{ minRows: 5 }" />
          </n-form-item>

          <div class="grid-2">
            <n-form-item label="隐藏秘密">
              <n-input v-model:value="form.secret" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
            <n-form-item label="对白风格">
              <n-input v-model:value="form.dialogue_style" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
          </div>

          <n-form-item label="人物弧光">
            <n-input v-model:value="form.arc" type="textarea" :autosize="{ minRows: 4 }" placeholder="从什么状态走向什么状态，关键转折是什么" />
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
            确认删除这个角色？
          </n-popconfirm>
        </div>
      </section>

      <aside class="side-panel dossier-side">
        <div class="panel-head inline-head">
          <h2>角色辅助</h2>
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
          <n-form-item label="关系摘要">
            <n-input v-model:value="form.relationships" type="textarea" :autosize="{ minRows: 5 }" placeholder="师徒、亲族、宿敌、暧昧、亏欠..." />
          </n-form-item>
          <n-form-item label="关联组织">
            <n-select v-model:value="selectedOrganizationIds" multiple clearable filterable :options="organizationOptions" placeholder="选择角色所属或牵连的组织" />
          </n-form-item>
          <n-form-item label="关联人物">
            <n-select v-model:value="selectedCharacterIds" multiple clearable filterable :options="characterOptions" placeholder="选择重要关系人" />
          </n-form-item>
          <n-form-item label="出场章节">
            <n-input v-model:value="form.chapters" placeholder="例如：1, 3-5, 12" />
          </n-form-item>
          <n-form-item label="AI 建议 / 一致性备注">
            <n-input v-model:value="form.ai_notes" type="textarea" :autosize="{ minRows: 5 }" />
          </n-form-item>
        </n-form>

        <div class="insight-card">
          <div class="insight-label">一致性检查入口</div>
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
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useDirtySnapshot } from '@/composables/useDirtySnapshot'
import { createResource, deleteResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { notify } from '@/utils/notify'
import type { CharacterItem, OrganizationItem } from '@/types/domain'

const projectStore = useProjectStore()
const characters = ref<CharacterItem[]>([])
const organizations = ref<OrganizationItem[]>([])
const keyword = ref('')
const roleFilter = ref<string | null>(null)
const editingId = ref<number | null>(null)
const loading = ref(false)

const form = reactive({
  name: '新角色',
  role_type: 'supporting',
  identity: '',
  faction: '',
  mbti: '',
  appearance: '',
  personality: '',
  background: '',
  motivation: '',
  weakness: '',
  secret: '',
  dialogue_style: '',
  arc: '',
  relationships: '',
  chapters: '',
  organization_ids: '',
  related_character_ids: '',
  ai_notes: ''
})
const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form, '当前角色档案有未保存内容，继续切换会丢弃这些修改。')

const roleTypes = [
  { label: '主角', value: 'protagonist' },
  { label: '配角', value: 'supporting' },
  { label: '反派', value: 'antagonist' }
]

const searchableFields = computed(() => [
  'name',
  'role_type',
  'identity',
  'faction',
  'mbti',
  'appearance',
  'personality',
  'background',
  'motivation',
  'weakness',
  'secret',
  'dialogue_style',
  'arc',
  'relationships',
  'chapters',
  'ai_notes'
] as const)

const filteredCharacters = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return characters.value.filter((item) => {
    const matchedText =
      !text || searchableFields.value.map((field) => item[field] ?? '').join(' ').toLowerCase().includes(text)
    const matchedRole = !roleFilter.value || item.role_type === roleFilter.value
    return matchedText && matchedRole
  })
})

const currentCompletion = computed(() => completionOf(form))
const completionAdvice = computed(() => {
  if (currentCompletion.value >= 80) return '角色已经能支撑章节生成，可继续补充关系变化。'
  if (currentCompletion.value >= 50) return '建议补齐动机、弱点、秘密和人物弧光。'
  return '先写清身份、阵营、动机和背景，角色才不会在正文里漂移。'
})
const assistantHints = computed(() => [
  form.motivation ? '核心动机可进入章节目标' : '缺少核心动机',
  form.weakness ? '弱点可转化为冲突' : '缺少弱点',
  form.dialogue_style ? '对白风格可用于精修' : '缺少对白风格'
])
const organizationOptions = computed(() => organizations.value.map((item) => ({ label: item.name, value: item.id })))
const characterOptions = computed(() =>
  characters.value.filter((item) => item.id !== editingId.value).map((item) => ({ label: item.name, value: item.id }))
)
const selectedOrganizationIds = computed({
  get: () => parseIds(form.organization_ids),
  set: (value: number[]) => {
    form.organization_ids = joinIds(value)
  }
})
const selectedCharacterIds = computed({
  get: () => parseIds(form.related_character_ids),
  set: (value: number[]) => {
    form.related_character_ids = joinIds(value)
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

function completionOf(item: Partial<CharacterItem> | typeof form) {
  const fields = ['name', 'role_type', 'identity', 'faction', 'mbti', 'appearance', 'personality', 'background', 'motivation', 'weakness', 'secret', 'dialogue_style', 'arc']
  const finished = fields.filter((field) => String(item[field as keyof typeof item] ?? '').trim()).length
  return Math.round((finished / fields.length) * 100)
}

function fillForm(item?: Partial<CharacterItem>) {
  Object.assign(form, {
    name: item?.name ?? '新角色',
    role_type: item?.role_type ?? 'supporting',
    identity: item?.identity ?? '',
    faction: item?.faction ?? '',
    mbti: item?.mbti ?? '',
    appearance: item?.appearance ?? '',
    personality: item?.personality ?? '',
    background: item?.background ?? '',
    motivation: item?.motivation ?? '',
    weakness: item?.weakness ?? '',
    secret: item?.secret ?? '',
    dialogue_style: item?.dialogue_style ?? '',
    arc: item?.arc ?? '',
    relationships: item?.relationships ?? '',
    chapters: item?.chapters ?? '',
    organization_ids: item?.organization_ids ?? '',
    related_character_ids: item?.related_character_ids ?? '',
    ai_notes: item?.ai_notes ?? ''
  })
  markClean()
}

function roleTypeLabel(value: string) {
  return roleTypes.find((item) => item.value === value)?.label ?? value
}

async function startCreate() {
  // 新建档案前检查脏数据，避免丢失当前编辑内容。
  if (!(await confirmIfDirty())) return
  editingId.value = null
  fillForm()
  await nextTick()
  markClean()
}

async function selectCharacter(item: CharacterItem) {
  // 左侧点击只水合右侧表单；真正写库仍由保存按钮统一触发。
  if (editingId.value === item.id) return
  if (!(await confirmIfDirty())) return
  editingId.value = item.id
  fillForm(item)
  await nextTick()
  markClean()
}

async function resetCurrent() {
  if (!(await confirmIfDirty('确定要重置当前角色档案吗？'))) return
  const current = characters.value.find((item) => item.id === editingId.value)
  if (current) {
    fillForm(current)
  } else {
    editingId.value = null
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
  const projectId = await ensureProject()
  if (!projectId) return
  loading.value = true
  try {
    const [characterList, organizationList] = await Promise.all([
      listResource<CharacterItem>(projectId, 'characters'),
      listResource<OrganizationItem>(projectId, 'organizations')
    ])
    characters.value = characterList
    organizations.value = organizationList
    // 首次加载时自动选中第一条，但只有在没有正在编辑的条目时才覆盖。
    if (!editingId.value && characters.value[0]) {
      editingId.value = characters.value[0].id
      fillForm(characters.value[0])
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
  const payload = { ...form }

  // 保存后刷新列表并重新选中返回行，保证左侧摘要与右侧表单始终同源。
  if (editingId.value) {
    const updated = await updateResource<CharacterItem>('characters', editingId.value, payload)
    notify.success('角色档案已更新')
    await load()
    const fresh = characters.value.find((item) => item.id === updated.id)
    if (fresh) {
      fillForm(fresh)
      await nextTick()
      markClean()
    }
  } else {
    const created = await createResource<CharacterItem>('characters', { project_id: projectId, ...payload })
    notify.success('角色档案已新增')
    await load()
    const fresh = characters.value.find((item) => item.id === created.id)
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
  const currentIndex = characters.value.findIndex((item) => item.id === editingId.value)
  await deleteResource('characters', editingId.value)
  notify.success('角色档案已删除')
  // 删除后自动选择下一条；如果是最后一条，选上一条；如果都没有，进入新建状态。
  const nextItem = characters.value[currentIndex + 1] || characters.value[currentIndex - 1]
  if (nextItem) {
    editingId.value = nextItem.id
    fillForm(nextItem)
  } else {
    editingId.value = null
    fillForm()
  }
  await load()
  await nextTick()
  markClean()
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

.dossier-editor {
  background: linear-gradient(180deg, #24272d 0%, #202327 160px);
}

.dossier-side {
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

.dirty-dot {
  margin-left: 6px;
  color: #f59e0b;
  font-size: 12px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.list-body {
  position: relative;
  min-height: 200px;
  display: flex;
  flex-direction: column;
}
</style>
