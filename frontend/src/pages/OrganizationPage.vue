<template>
  <div class="page page-wide">
    <div class="page-title">
      <div>
        <h1>🏛️ 势力管理台</h1>
        <p class="muted">管理组织结构、资源目标、阵营关系与剧情风险。</p>
      </div>
      <div class="title-actions">
        <n-button @click="load">刷新</n-button>
        <n-button type="primary" @click="startCreate">新增势力</n-button>
      </div>
    </div>

    <div class="triple-workbench archive-workbench">
      <aside class="list-panel">
        <div class="panel-head">
          <h2>组织库</h2>
          <span class="muted">{{ filteredOrganizations.length }} / {{ organizations.length }}</span>
        </div>
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索名称、目标、资源、成员" />
          <n-input v-model:value="typeFilter" clearable placeholder="按类型筛选" />
        </div>
        <div class="list-body">
          <n-spin v-if="loading" description="加载中..." />
          <n-empty v-else-if="filteredOrganizations.length === 0" :description="organizations.length === 0 ? '还没有组织，点击右上角新增' : '暂无匹配组织'" />
          <template v-else>
            <button
              v-for="item in filteredOrganizations"
              :key="item.id"
              class="list-item"
              :class="{ active: editingId === item.id }"
              @click="selectOrganization(item)"
            >
              <div class="item-title">
                <span>{{ item.name }}</span>
                <span class="muted">实力 {{ item.power_level }}</span>
              </div>
              <div class="power-bar">
                <span :style="{ width: `${item.power_level * 10}%` }"></span>
              </div>
              <div class="item-meta">{{ item.org_type || '类型未定' }} · {{ item.location || '地点未定' }}</div>
              <div class="item-meta">{{ item.goal || item.description || '目标尚未填写' }}</div>
            </button>
          </template>
        </div>
      </aside>

      <section class="detail-panel org-editor">
        <div class="panel-head inline-head">
          <h2>
            {{ editingId ? '势力详情编辑' : '新势力档案' }}
            <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
          </h2>
          <span class="muted">{{ editingId ? `ID ${editingId}` : '等待保存' }}</span>
        </div>

        <n-form label-placement="top">
          <div class="grid-3">
            <n-form-item label="组织名称">
              <n-input v-model:value="form.name" />
            </n-form-item>
            <n-form-item label="类型">
              <n-input v-model:value="form.org_type" placeholder="宗门 / 公司 / 官方机构" />
            </n-form-item>
            <n-form-item label="状态">
              <n-input v-model:value="form.status" placeholder="隐世 / 扩张 / 衰落" />
            </n-form-item>
          </div>

          <div class="grid-2">
            <n-form-item label="地点 / 势力范围">
              <n-input v-model:value="form.location" />
            </n-form-item>
            <n-form-item label="宗旨 / 口号">
              <n-input v-model:value="form.slogan" />
            </n-form-item>
          </div>

          <div class="grid-3">
            <n-form-item label="组织层级">
              <n-input-number v-model:value="form.level" :min="1" :max="10" />
            </n-form-item>
            <n-form-item label="实力等级">
              <n-input-number v-model:value="form.power_level" :min="1" :max="10" />
            </n-form-item>
            <n-form-item label="成员总数">
              <n-input-number v-model:value="form.member_count" :min="0" />
            </n-form-item>
          </div>

          <div class="grid-2">
            <n-form-item label="内部层级">
              <n-input v-model:value="form.hierarchy" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
            <n-form-item label="核心资源">
              <n-input v-model:value="form.resources" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
          </div>

          <div class="grid-2">
            <n-form-item label="组织目标">
              <n-input v-model:value="form.goal" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
            <n-form-item label="背景描述">
              <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 4 }" />
            </n-form-item>
          </div>
        </n-form>

        <div class="detail-actions">
          <n-button type="primary" @click="save">保存</n-button>
          <n-button @click="startCreate">新增</n-button>
          <n-button @click="resetCurrent">重置</n-button>
          <n-popconfirm v-if="editingId" positive-text="确认删除" negative-text="取消" @positive-click="remove">
            <template #trigger>
              <n-button type="error">删除</n-button>
            </template>
            确认删除这个组织？
          </n-popconfirm>
        </div>
      </section>

      <aside class="side-panel org-side">
        <div class="panel-head inline-head">
          <h2>关系与风险</h2>
          <span class="muted">{{ riskLevel }}</span>
        </div>

        <n-form label-placement="top">
          <n-form-item label="核心成员">
            <n-select v-model:value="selectedCoreMembers" multiple filterable tag :options="characterOptions" placeholder="选择或输入首领、骨干、卧底" />
          </n-form-item>
          <n-form-item label="盟友组织">
            <n-select v-model:value="selectedAllies" multiple filterable tag :options="organizationNameOptions" placeholder="选择或输入盟友组织" />
          </n-form-item>
          <n-form-item label="敌对组织">
            <n-select v-model:value="selectedEnemies" multiple filterable tag :options="organizationNameOptions" placeholder="选择或输入敌对组织" />
          </n-form-item>
          <n-form-item label="剧情影响">
            <n-input v-model:value="form.impact" type="textarea" :autosize="{ minRows: 4 }" />
          </n-form-item>
          <n-form-item label="风险提示">
            <n-input v-model:value="form.risk_notes" type="textarea" :autosize="{ minRows: 4 }" />
          </n-form-item>
        </n-form>

        <div class="insight-card">
          <div class="insight-label">势力雷达</div>
          <div class="metric-row">
            <span>层级</span>
            <strong>{{ form.level }}/10</strong>
          </div>
          <div class="metric-row">
            <span>实力</span>
            <strong>{{ form.power_level }}/10</strong>
          </div>
          <div class="metric-row">
            <span>成员</span>
            <strong>{{ form.member_count }}</strong>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { createResource, deleteResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useDirtySnapshot } from '@/composables/useDirtySnapshot'
import { notify } from '@/utils/notify'
import type { CharacterItem, OrganizationItem } from '@/types/domain'

const projectStore = useProjectStore()
const organizations = ref<OrganizationItem[]>([])
const characters = ref<CharacterItem[]>([])
const keyword = ref('')
const typeFilter = ref('')
const editingId = ref<number | null>(null)
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
  risk_notes: ''
})

// 脏数据检测：切换条目、新增、重置前检查是否有未保存修改。
const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form, '当前势力档案有未保存的修改，确定要离开吗？')

const filteredOrganizations = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  const type = typeFilter.value.trim().toLowerCase()
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
        item.core_members,
        item.allies,
        item.enemies,
        item.impact,
        item.risk_notes
      ]
        .join(' ')
        .toLowerCase()
        .includes(text)
    const matchedType = !type || item.org_type.toLowerCase().includes(type)
    return matchedText && matchedType
  })
})
const riskLevel = computed(() => {
  if (form.enemies && form.power_level <= 4) return '高风险'
  if (!form.goal || !form.resources) return '资料不足'
  return '稳定'
})

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
  // 旧数据可能用中文逗号、英文逗号或换行保存，这里统一转成选择控件可识别的数组。
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
    risk_notes: item?.risk_notes ?? ''
  })
}

async function startCreate() {
  // 新增势力前检查脏数据，避免丢失当前编辑内容。
  if (!(await confirmIfDirty())) return
  editingId.value = null
  fillForm()
  await nextTick()
  markClean()
}

async function selectOrganization(item: OrganizationItem) {
  // 列表选择前检查脏数据；同一条目重复点击直接跳过。
  if (editingId.value === item.id) return
  if (!(await confirmIfDirty())) return
  editingId.value = item.id
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
    const [organizationList, characterList] = await Promise.all([
      listResource<OrganizationItem>(projectId, 'organizations'),
      listResource<CharacterItem>(projectId, 'characters')
    ])
    organizations.value = organizationList
    characters.value = characterList
    // 首次加载时自动选中第一条，但只有在没有正在编辑的条目时才覆盖。
    if (!editingId.value && organizations.value[0]) {
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

  // 组织字段会被章节上下文直接读取，因此保存后刷新列表并保留当前选择。
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
  // 删除后自动选择下一条；如果是最后一条，选上一条；如果都没有，进入新建状态。
  const nextItem = organizations.value[currentIndex + 1] || organizations.value[currentIndex - 1]
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

.org-editor {
  background: linear-gradient(180deg, #24272d 0%, #202327 160px);
}

.org-side {
  position: sticky;
  top: 16px;
}

.power-bar {
  height: 5px;
  margin: 8px 0;
  overflow: hidden;
  border-radius: 99px;
  background: #30343a;
}

.power-bar span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #4f8cff, #f2c97d);
}

.insight-card {
  margin-top: 10px;
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

.metric-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #30343a;
  color: #cbd5e1;
}

.metric-row:last-child {
  border-bottom: 0;
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
