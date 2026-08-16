<template>
  <div class="page page-wide">
    <div class="page-title">
      <h1>📋 大纲管理</h1>
      <n-button type="primary" @click="startCreate">新增大纲</n-button>
    </div>

    <div class="split-workbench">
      <aside class="list-panel">
        <div class="panel-head">
          <h2>大纲节点</h2>
          <span class="muted">{{ filteredOutlines.length }} 条</span>
        </div>
        <div class="panel-tools">
          <n-input v-model:value="keyword" clearable placeholder="搜索标题或内容" />
          <n-select v-model:value="statusFilter" clearable :options="statuses" placeholder="筛选状态" />
        </div>
        <div class="list-body">
          <n-spin v-if="loading" description="加载中..." />
          <n-empty v-else-if="filteredOutlines.length === 0" :description="outlines.length === 0 ? '还没有大纲，点击右上角新增' : '暂无匹配大纲'" />
          <template v-else>
            <button
              v-for="item in filteredOutlines"
              :key="item.id"
              class="list-item"
              :class="{ active: editingId === item.id }"
              @click="selectOutline(item)"
            >
              <div class="item-title">
                <span>{{ item.title }}</span>
                <span class="muted">#{{ item.chapter_no ?? item.sort_index }}</span>
              </div>
              <div class="item-meta">{{ nodeTypeLabel(item.node_type) }} · {{ statusLabel(item.status) }}</div>
              <div class="item-meta">{{ item.description || '暂无内容描述' }}</div>
            </button>
          </template>
        </div>
      </aside>

      <section class="detail-panel">
        <div class="panel-head">
          <h2>
            {{ editingId ? '编辑大纲详情' : '新增大纲详情' }}
            <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
          </h2>
          <span class="muted">{{ editingId ? `ID ${editingId}` : '未保存' }}</span>
        </div>

        <n-form label-placement="top">
          <n-form-item label="标题">
            <n-input v-model:value="form.title" placeholder="新章节" />
          </n-form-item>
          <div class="grid-2">
            <n-form-item label="类型">
              <n-select v-model:value="form.node_type" :options="nodeTypes" />
            </n-form-item>
            <n-form-item label="状态">
              <n-select v-model:value="form.status" :options="statuses" />
            </n-form-item>
          </div>
          <div class="grid-2">
            <n-form-item label="章节号">
              <n-input-number v-model:value="form.chapter_no" :min="1" />
            </n-form-item>
            <n-form-item label="排序索引">
              <n-input-number v-model:value="form.sort_index" :min="0" />
            </n-form-item>
          </div>
          <n-form-item label="内容描述">
            <n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 12 }" />
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
            确认删除这个大纲节点？
          </n-popconfirm>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { createResource, deleteResource, listResource, updateResource } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import { useDirtySnapshot } from '@/composables/useDirtySnapshot'
import { notify } from '@/utils/notify'
import type { OutlineItem } from '@/types/domain'

const projectStore = useProjectStore()
const outlines = ref<OutlineItem[]>([])
const keyword = ref('')
const statusFilter = ref<string | null>(null)
const editingId = ref<number | null>(null)
const loading = ref(false)
const form = reactive({ title: '新章节', node_type: 'chapter', status: 'draft', chapter_no: 1 as number | null, sort_index: 1, description: '' })

// 脏数据检测：切换条目、新增、重置前检查是否有未保存修改。
const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form, '当前大纲有未保存的修改，确定要离开吗？')

const nodeTypes = [{ label: '章', value: 'chapter' }, { label: '卷', value: 'volume' }]
const statuses = [{ label: '草稿', value: 'draft' }, { label: '已确认', value: 'confirmed' }]

const filteredOutlines = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return outlines.value.filter((item) => {
    const matchedText = !text || [item.title, item.description].join(' ').toLowerCase().includes(text)
    const matchedStatus = !statusFilter.value || item.status === statusFilter.value
    return matchedText && matchedStatus
  })
})

function fillForm(item?: Partial<OutlineItem>) {
  Object.assign(form, {
    title: item?.title ?? '新章节',
    node_type: item?.node_type ?? 'chapter',
    status: item?.status ?? 'draft',
    chapter_no: item?.chapter_no ?? 1,
    sort_index: item?.sort_index ?? 1,
    description: item?.description ?? ''
  })
}

function nodeTypeLabel(value: string) {
  return nodeTypes.find((item) => item.value === value)?.label ?? value
}

function statusLabel(value: string) {
  return statuses.find((item) => item.value === value)?.label ?? value
}

async function startCreate() {
  // 新增前检查脏数据，避免丢失当前编辑内容。
  if (!(await confirmIfDirty())) return
  editingId.value = null
  fillForm()
  await nextTick()
  markClean()
}

async function selectOutline(item: OutlineItem) {
  // 选择逻辑只复制当前条目，避免未保存输入影响列表数据。
  if (editingId.value === item.id) return
  if (!(await confirmIfDirty())) return
  editingId.value = item.id
  fillForm(item)
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
    outlines.value = await listResource<OutlineItem>(projectId, 'outlines')
    // 首次加载时自动选中第一条，但只有在没有正在编辑的条目时才覆盖。
    if (!editingId.value && outlines.value[0]) {
      editingId.value = outlines.value[0].id
      fillForm(outlines.value[0])
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

  // 大纲保存后会被章节生成页读取，保存成功后保持右侧选中当前记录。
  if (editingId.value) {
    const updated = await updateResource<OutlineItem>('outlines', editingId.value, { ...form })
    notify.success('大纲已更新')
    await load()
    const fresh = outlines.value.find((item) => item.id === updated.id)
    if (fresh) {
      fillForm(fresh)
      await nextTick()
      markClean()
    }
  } else {
    const created = await createResource<OutlineItem>('outlines', { project_id: projectId, ...form })
    notify.success('大纲已新增')
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
  // 删除后自动选择下一条；如果是最后一条，选上一条；如果都没有，进入新建状态。
  const nextItem = outlines.value[currentIndex + 1] || outlines.value[currentIndex - 1]
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
