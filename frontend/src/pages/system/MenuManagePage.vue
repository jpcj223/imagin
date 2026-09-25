<template>
  <div class="page page-wide menu-manage-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">📋</span>
          菜单管理
        </h1>
        <p class="page-subtitle">管理系统菜单结构，支持多级嵌套</p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ totalCount }}</span>
            <span class="stat-label">菜单总数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num success">{{ visibleCount }}</span>
            <span class="stat-label">显示中</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num warning">{{ dirCount }}</span>
            <span class="stat-label">目录</span>
          </div>
        </div>
        <n-button type="primary" @click="openCreate(0)">
          <template #icon>＋</template>
          新增菜单
        </n-button>
      </div>
    </div>

    <div class="menu-toolbar">
      <n-input v-model:value="searchText" clearable placeholder="搜索菜单名称、路径或权限标识" class="menu-search">
        <template #prefix>🔎</template>
      </n-input>
      <n-select v-model:value="typeFilter" :options="typeFilterOptions" clearable placeholder="全部类型" class="menu-filter" />
      <n-select v-model:value="visibilityFilter" :options="visibilityFilterOptions" clearable placeholder="全部显示状态" class="menu-filter" />
      <span class="result-count">显示 {{ filteredCount }} / {{ totalCount }} 项</span>
      <div class="tree-actions">
        <n-button size="small" quaternary @click="expandAll">全部展开</n-button>
        <n-button size="small" quaternary @click="collapseAll">全部折叠</n-button>
        <n-button size="small" quaternary :loading="loading" @click="load">刷新</n-button>
      </div>
    </div>

    <!-- 树形表格 -->
    <div class="content-card menu-table-card">
      <n-data-table
        :columns="columns"
        :data="filteredMenuTree"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        striped
        :row-key="(row: MenuItem) => row.id"
        :expanded-row-keys="expandedRowKeys"
        @update:expanded-row-keys="expandedRowKeys = $event"
      />
      <div v-if="!loading && totalCount === 0" class="menu-empty-state">
        <div class="empty-icon">📋</div>
        <strong>还没有菜单</strong>
        <span>创建目录和菜单项，逐步搭建系统导航结构。</span>
        <n-button type="primary" @click="openCreate(0)">新增第一个菜单</n-button>
      </div>
      <div v-else-if="!loading && filteredCount === 0" class="menu-empty-state compact">
        <strong>没有匹配的菜单</strong>
        <span>调整搜索关键词或筛选条件后再试。</span>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <n-modal v-model:show="showModal" preset="card" :title="isEdit ? '编辑菜单' : '新增菜单'" style="width: min(560px, 92vw)">
      <n-form :model="form" label-placement="left" label-width="90px">
        <n-form-item label="上级目录">
          <n-select v-model:value="form.parent_id" :options="parentOptions" />
        </n-form-item>
        <n-form-item label="菜单名称">
          <n-input v-model:value="form.name" placeholder="请输入菜单名称" />
        </n-form-item>
        <n-form-item label="菜单类型">
          <n-select v-model:value="form.menu_type" :options="typeOptions" @update:value="onTypeChange" />
        </n-form-item>
        <n-form-item v-if="form.menu_type === 'menu'" label="路由路径">
          <n-input v-model:value="form.path" placeholder="如: /dashboard" />
        </n-form-item>
        <n-form-item v-if="form.menu_type === 'menu'" label="组件名">
          <n-input v-model:value="form.component" placeholder="如: Dashboard" />
        </n-form-item>
        <n-form-item label="图标">
          <n-input v-model:value="form.icon" placeholder="Emoji 图标，如: 🚀" />
        </n-form-item>
        <n-form-item label="排序">
          <n-input-number v-model:value="form.sort_order" :min="0" style="width: 100%" />
        </n-form-item>
        <n-form-item label="权限标识">
          <n-input v-model:value="form.permission" placeholder="如: system:user" />
        </n-form-item>
        <n-form-item label="是否显示">
          <n-switch v-model:value="form.is_visible" :checked-value="1" :unchecked-value="0" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="text-align: right">
          <n-button style="margin-right: 8px" @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSave">确定</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from 'vue'
import { NButton, NPopconfirm, NSpace, useMessage } from 'naive-ui'
import {
  createMenu,
  deleteMenu,
  fetchMenuTree,
  updateMenu,
  type MenuItem,
} from '@/api/core'

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const menuTree = ref<MenuItem[]>([])
const expandedRowKeys = ref<number[]>([])
const searchText = ref('')
const typeFilter = ref<string | null>(null)
const visibilityFilter = ref<number | null>(null)

const showModal = ref(false)
const isEdit = ref(false)
const editId = ref(0)
const form = reactive({
  parent_id: 0,
  name: '',
  path: '',
  icon: '',
  component: '',
  sort_order: 1,
  menu_type: 'menu' as 'menu' | 'dir' | 'button',
  permission: '',
  is_visible: 1,
})

const typeOptions = [
  { label: '目录', value: 'dir' },
  { label: '菜单', value: 'menu' },
  { label: '按钮', value: 'button' },
]

const typeFilterOptions = [
  { label: '目录', value: 'dir' },
  { label: '菜单', value: 'menu' },
  { label: '按钮', value: 'button' },
]

const visibilityFilterOptions = [
  { label: '显示', value: 1 },
  { label: '隐藏', value: 0 },
]

function flatten(items: MenuItem[]): MenuItem[] {
  const result: MenuItem[] = []
  for (const item of items) {
    result.push(item)
    if (item.children && item.children.length > 0) {
      result.push(...flatten(item.children))
    }
  }
  return result
}

const flatList = computed(() => flatten(menuTree.value))
const totalCount = computed(() => flatList.value.length)
const visibleCount = computed(() => flatList.value.filter((m) => m.is_visible === 1).length)
const dirCount = computed(() => flatList.value.filter((m) => m.menu_type === 'dir').length)
const expandableKeys = computed(() => flatList.value.filter((item) => item.children?.length).map((item) => item.id))
const filteredMenuTree = computed(() => {
  const keyword = searchText.value.trim().toLocaleLowerCase('zh-CN')
  const filterNodes = (items: MenuItem[]): MenuItem[] => items.flatMap((item) => {
    const children = item.children ? filterNodes(item.children) : []
    const matchesKeyword = !keyword || [item.name, item.path, item.permission]
      .some((value) => String(value || '').toLocaleLowerCase('zh-CN').includes(keyword))
    const matchesType = !typeFilter.value || item.menu_type === typeFilter.value
    const matchesVisibility = visibilityFilter.value === null || item.is_visible === visibilityFilter.value
    if (matchesKeyword && matchesType && matchesVisibility) {
      return [{ ...item, children: item.children ? (keyword || typeFilter.value || visibilityFilter.value !== null ? children : item.children) : [] }]
    }
    return children.length ? [{ ...item, children }] : []
  })
  return filterNodes(menuTree.value)
})
const filteredCount = computed(() => flatten(filteredMenuTree.value).length)

watch([searchText, typeFilter, visibilityFilter], () => {
  // 步骤 1：筛选时自动展开命中的父级，避免结果藏在折叠节点里。
  expandedRowKeys.value = searchText.value || typeFilter.value || visibilityFilter.value !== null
    ? flatten(filteredMenuTree.value).filter((item) => item.children?.length).map((item) => item.id)
    : []
})

const parentOptions = computed(() => {
  const options = [{ label: '顶级菜单', value: 0 }]
  const excludedIds = new Set<number>()
  if (isEdit.value) collectDescendantIds(menuTree.value, editId.value, excludedIds)
  for (const m of flatList.value) {
    if (m.menu_type === 'dir' && !excludedIds.has(m.id)) {
      const depth = getMenuDepth(menuTree.value, m.id)
      options.push({ label: `${'　'.repeat(depth)}${depth ? '└ ' : ''}${m.name}`, value: m.id })
    }
  }
  return options
})

const columns = [
  { title: '名称', key: 'name', width: 200 },
  {
    title: '图标',
    key: 'icon',
    width: 60,
    render: (row: MenuItem) => h('span', { style: 'font-size: 16px' }, row.icon),
  },
  { title: '路径', key: 'path', width: 200 },
  {
    title: '类型',
    key: 'menu_type',
    width: 80,
    render: (row: MenuItem) => {
      const map: Record<string, { text: string; cls: string }> = {
        dir: { text: '目录', cls: 'type-dir' },
        menu: { text: '菜单', cls: 'type-menu' },
        button: { text: '按钮', cls: 'type-btn' },
      }
      const info = map[row.menu_type] || map.menu
      return h('span', { class: `type-tag ${info.cls}` }, info.text)
    },
  },
  { title: '排序', key: 'sort_order', width: 70 },
  {
    title: '显示',
    key: 'is_visible',
    width: 70,
    render: (row: MenuItem) =>
      h(
        'span',
        { class: row.is_visible === 1 ? 'vis-tag show' : 'vis-tag hide' },
        row.is_visible === 1 ? '显示' : '隐藏'
      ),
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    render: (row: MenuItem) =>
      h(NSpace, { size: 'small' }, () => [
        ...(row.menu_type === 'button' ? [] : [h(NButton, { size: 'small', text: true, onClick: () => openCreate(row.id) }, () => '添加子菜单')]),
        h(NButton, { size: 'small', text: true, onClick: () => openEdit(row) }, () => '编辑'),
        h(
          NPopconfirm,
          { onPositiveClick: () => handleDelete(row.id) },
          { default: () => '确认删除？子菜单也会被删除', trigger: () => h(NButton, { size: 'small', text: true, type: 'error' }, () => '删除') }
        ),
      ]),
  },
]

async function load() {
  loading.value = true
  try {
    menuTree.value = await fetchMenuTree()
    expandedRowKeys.value = expandableKeys.value
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '菜单列表加载失败')
  } finally {
    loading.value = false
  }
}

function onTypeChange(val: string) {
  if (val !== 'menu') {
    form.path = ''
    form.component = ''
  }
}

function expandAll() {
  expandedRowKeys.value = [...expandableKeys.value]
}

function collapseAll() {
  expandedRowKeys.value = []
}

function collectDescendantIds(items: MenuItem[], targetId: number, result: Set<number>, found = false) {
  for (const item of items) {
    const isTarget = found || item.id === targetId
    if (isTarget) result.add(item.id)
    if (item.children?.length) collectDescendantIds(item.children, targetId, result, isTarget)
  }
}

function getMenuDepth(items: MenuItem[], targetId: number, depth = 0): number {
  for (const item of items) {
    if (item.id === targetId) return depth
    if (item.children?.length) {
      const found = getMenuDepth(item.children, targetId, depth + 1)
      if (found >= 0) return found
    }
  }
  return -1
}

function openCreate(parentId: number) {
  isEdit.value = false
  editId.value = 0
  Object.assign(form, {
    parent_id: parentId,
    name: '',
    path: '',
    icon: '',
    component: '',
    sort_order: 1,
    menu_type: 'menu' as const,
    permission: '',
    is_visible: 1,
  })
  showModal.value = true
}

function openEdit(row: MenuItem) {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    parent_id: row.parent_id,
    name: row.name,
    path: row.path,
    icon: row.icon,
    component: row.component,
    sort_order: row.sort_order,
    menu_type: row.menu_type,
    permission: row.permission,
    is_visible: row.is_visible,
  })
  showModal.value = true
}

async function handleSave() {
  if (!form.name.trim()) {
    message.warning('请输入菜单名称')
    return
  }
  if (form.menu_type === 'menu' && !form.path.trim()) {
    message.warning('菜单类型需要填写路由路径')
    return
  }
  if (isEdit.value && form.parent_id === editId.value) {
    message.warning('上级目录不能选择当前菜单')
    return
  }

  saving.value = true
  try {
    const payload = {
      ...form,
      name: form.name.trim(),
      path: form.path.trim(),
      component: form.component.trim(),
      permission: form.permission.trim(),
      icon: form.icon.trim(),
    }
    if (isEdit.value) {
      await updateMenu(editId.value, payload)
      message.success('更新成功')
    } else {
      await createMenu(payload)
      message.success('创建成功')
    }
    showModal.value = false
    await load()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await deleteMenu(id)
    message.success('删除成功')
    await load()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.menu-manage-page {
  padding: 24px 28px 40px;
}

.menu-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
  padding: 12px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
}

.menu-search {
  width: min(360px, 42vw);
}

.menu-filter {
  width: 150px;
}

.result-count {
  color: var(--n-text-color-3, #8490a3);
  font-size: 12px;
  white-space: nowrap;
}

.tree-actions {
  display: flex;
  gap: 2px;
  margin-left: auto;
}

.menu-table-card {
  min-height: 360px;
  padding: 8px 14px 14px;
  overflow: hidden;
}

.menu-empty-state {
  display: flex;
  min-height: 300px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: var(--n-text-color-3, #8490a3);
  text-align: center;
}

.menu-empty-state strong {
  color: var(--n-text-color-1, #e5e7eb);
}

.menu-empty-state span {
  margin-bottom: 5px;
  font-size: 12px;
}

.menu-empty-state.compact {
  min-height: 220px;
}

.empty-icon {
  font-size: 38px;
}

.type-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
}
.type-dir {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
}
.type-menu {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}
.type-btn {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}

.vis-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
}
.vis-tag.show {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}
.vis-tag.hide {
  background: rgba(156, 163, 175, 0.15);
  color: #9ca3af;
}

@media (max-width: 760px) {
  .menu-manage-page {
    padding: 18px 14px 28px;
  }

  .menu-search {
    width: 100%;
  }

  .menu-filter {
    flex: 1;
    min-width: 125px;
  }

  .tree-actions {
    width: 100%;
    margin-left: 0;
    justify-content: flex-end;
  }
}
</style>
