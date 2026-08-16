<template>
  <div class="page page-wide dict-manage-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">📚</span>
          字典管理
        </h1>
        <p class="page-subtitle">管理系统枚举和字典数据</p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ dictionaries.length }}</span>
            <span class="stat-label">字典总数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num success">{{ activeDictCount }}</span>
            <span class="stat-label">启用中</span>
          </div>
        </div>
        <n-button type="primary" @click="openDictCreate">
          <template #icon>＋</template>
          新增字典
        </n-button>
      </div>
    </div>

    <!-- 字典列表 + 字典项详情 -->
    <div class="dict-layout">
      <!-- 左侧字典列表 -->
      <div class="dict-list-panel">
        <div class="panel-title">字典列表</div>
        <div class="dict-list">
          <div
            v-for="dict in dictionaries"
            :key="dict.id"
            class="dict-item"
            :class="{ active: selectedDictId === dict.id }"
            @click="selectDict(dict)"
          >
            <div class="dict-main">
              <div class="dict-name">{{ dict.dict_name }}</div>
              <div class="dict-code">{{ dict.dict_code }}</div>
            </div>
            <span :class="['dict-status', dict.status]" :title="dict.status">
              {{ dict.status === 'active' ? '●' : '○' }}
            </span>
          </div>
          <div v-if="dictionaries.length === 0" class="list-empty">
            <p>暂无字典</p>
          </div>
        </div>
      </div>

      <!-- 右侧字典项管理 -->
      <div class="dict-items-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">{{ selectedDict?.dict_name || '字典项' }}</div>
            <div class="panel-sub" v-if="selectedDict">{{ selectedDict.description }}</div>
          </div>
          <div v-if="selectedDict" style="display: flex; gap: 8px">
            <n-button size="small" @click="openDictEdit">编辑字典</n-button>
            <n-button size="small" type="primary" @click="openItemCreate">
              <template #icon>＋</template>
              新增字典项
            </n-button>
          </div>
        </div>

        <n-data-table
          v-if="selectedDict"
          :columns="itemColumns"
          :data="dictItems"
          :loading="itemsLoading"
          :bordered="false"
          size="small"
        />
        <div v-else class="items-empty">
          <div class="empty-icon">📖</div>
          <p>请选择左侧字典查看详情</p>
        </div>
      </div>
    </div>

    <!-- 字典编辑弹窗 -->
    <n-modal v-model:show="dictModal" preset="card" :title="isDictEdit ? '编辑字典' : '新增字典'" style="width: 460px">
      <n-form :model="dictForm" label-placement="left" label-width="90px">
        <n-form-item label="字典编码">
          <n-input v-model:value="dictForm.dict_code" placeholder="如: novel_type" :disabled="isDictEdit" />
        </n-form-item>
        <n-form-item label="字典名称">
          <n-input v-model:value="dictForm.dict_name" placeholder="如: 小说类型" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="dictForm.description" type="textarea" :rows="2" placeholder="字典说明" />
        </n-form-item>
        <n-form-item label="排序">
          <n-input-number v-model:value="dictForm.sort_order" :min="0" style="width: 100%" />
        </n-form-item>
        <n-form-item label="状态">
          <n-select v-model:value="dictForm.status" :options="statusOptions" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="text-align: right">
          <n-button v-if="isDictEdit" type="error" style="float: left" @click="handleDictDelete">删除字典</n-button>
          <n-button style="margin-right: 8px" @click="dictModal = false">取消</n-button>
          <n-button type="primary" :loading="dictSaving" @click="handleDictSave">确定</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 字典项编辑弹窗 -->
    <n-modal v-model:show="itemModal" preset="card" :title="isItemEdit ? '编辑字典项' : '新增字典项'" style="width: 460px">
      <n-form :model="itemForm" label-placement="left" label-width="90px">
        <n-form-item label="标签">
          <n-input v-model:value="itemForm.item_label" placeholder="显示名称" />
        </n-form-item>
        <n-form-item label="值">
          <n-input v-model:value="itemForm.item_value" placeholder="枚举值" />
        </n-form-item>
        <n-form-item label="排序">
          <n-input-number v-model:value="itemForm.sort_order" :min="0" style="width: 100%" />
        </n-form-item>
        <n-form-item label="状态">
          <n-select v-model:value="itemForm.status" :options="statusOptions" />
        </n-form-item>
        <n-form-item label="备注">
          <n-input v-model:value="itemForm.remark" type="textarea" :rows="2" placeholder="可选备注" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="text-align: right">
          <n-button style="margin-right: 8px" @click="itemModal = false">取消</n-button>
          <n-button type="primary" :loading="itemSaving" @click="handleItemSave">确定</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NPopconfirm, useMessage } from 'naive-ui'
import {
  createDictItem,
  createDictionary,
  deleteDictItem,
  deleteDictionary,
  fetchDictionaries,
  fetchDictItems,
  updateDictItem,
  updateDictionary,
  type DictItem,
  type Dictionary,
} from '@/api/core'

const message = useMessage()
const loading = ref(false)
const itemsLoading = ref(false)
const dictionaries = ref<Dictionary[]>([])
const dictItems = ref<DictItem[]>([])
const selectedDictId = ref(0)

const dictModal = ref(false)
const dictSaving = ref(false)
const isDictEdit = ref(false)
const dictForm = reactive({
  dict_code: '',
  dict_name: '',
  description: '',
  sort_order: 1,
  status: 'active',
})

const itemModal = ref(false)
const itemSaving = ref(false)
const isItemEdit = ref(false)
const editItemId = ref(0)
const itemForm = reactive({
  item_label: '',
  item_value: '',
  sort_order: 1,
  status: 'active',
  remark: '',
})

const statusOptions = [
  { label: '启用', value: 'active' },
  { label: '停用', value: 'inactive' },
]

const selectedDict = computed(() => dictionaries.value.find((d) => d.id === selectedDictId.value))
const activeDictCount = computed(() => dictionaries.value.filter((d) => d.status === 'active').length)

const itemColumns = [
  { title: '标签', key: 'item_label', width: 140 },
  { title: '值', key: 'item_value', width: 140 },
  { title: '排序', key: 'sort_order', width: 70 },
  {
    title: '状态',
    key: 'status',
    width: 80,
    render: (row: DictItem) =>
      h(
        'span',
        { class: row.status === 'active' ? 'item-status active' : 'item-status inactive' },
        row.status === 'active' ? '启用' : '停用'
      ),
  },
  { title: '备注', key: 'remark' },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: (row: DictItem) =>
      h('div', { style: 'display: flex; gap: 8px' }, [
        h(NButton, { size: 'small', text: true, onClick: () => openItemEdit(row) }, () => '编辑'),
        h(
          NPopconfirm,
          { onPositiveClick: () => handleItemDelete(row.id) },
          { default: () => '确认删除？', trigger: () => h(NButton, { size: 'small', text: true, type: 'error' }, () => '删除') }
        ),
      ]),
  },
]

async function loadDicts() {
  loading.value = true
  try {
    dictionaries.value = await fetchDictionaries()
    if (dictionaries.value.length > 0 && !selectedDictId.value) {
      selectDict(dictionaries.value[0])
    }
  } finally {
    loading.value = false
  }
}

async function selectDict(dict: Dictionary) {
  selectedDictId.value = dict.id
  itemsLoading.value = true
  try {
    dictItems.value = await fetchDictItems(dict.dict_code)
  } finally {
    itemsLoading.value = false
  }
}

// ---- 字典 CRUD ----

function openDictCreate() {
  isDictEdit.value = false
  Object.assign(dictForm, {
    dict_code: '',
    dict_name: '',
    description: '',
    sort_order: 1,
    status: 'active',
  })
  dictModal.value = true
}

function openDictEdit() {
  if (!selectedDict.value) return
  isDictEdit.value = true
  Object.assign(dictForm, {
    dict_code: selectedDict.value.dict_code,
    dict_name: selectedDict.value.dict_name,
    description: selectedDict.value.description,
    sort_order: selectedDict.value.sort_order,
    status: selectedDict.value.status,
  })
  dictModal.value = true
}

async function handleDictSave() {
  if (!dictForm.dict_code.trim() || !dictForm.dict_name.trim()) {
    message.warning('请填写字典编码和名称')
    return
  }
  dictSaving.value = true
  try {
    if (isDictEdit.value && selectedDict.value) {
      await updateDictionary(selectedDict.value.id, { ...dictForm })
      message.success('更新成功')
    } else {
      await createDictionary({ ...dictForm })
      message.success('创建成功')
    }
    dictModal.value = false
    loadDicts()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '操作失败')
  } finally {
    dictSaving.value = false
  }
}

async function handleDictDelete() {
  if (!selectedDict.value) return
  try {
    await deleteDictionary(selectedDict.value.id)
    message.success('删除成功')
    selectedDictId.value = 0
    dictItems.value = []
    dictModal.value = false
    loadDicts()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '删除失败')
  }
}

// ---- 字典项 CRUD ----

function openItemCreate() {
  isItemEdit.value = false
  editItemId.value = 0
  Object.assign(itemForm, {
    item_label: '',
    item_value: '',
    sort_order: 1,
    status: 'active',
    remark: '',
  })
  itemModal.value = true
}

function openItemEdit(row: DictItem) {
  isItemEdit.value = true
  editItemId.value = row.id
  Object.assign(itemForm, {
    item_label: row.item_label,
    item_value: row.item_value,
    sort_order: row.sort_order,
    status: row.status,
    remark: row.remark,
  })
  itemModal.value = true
}

async function handleItemSave() {
  if (!itemForm.item_label.trim() || !itemForm.item_value.trim()) {
    message.warning('请填写标签和值')
    return
  }
  itemSaving.value = true
  try {
    if (isItemEdit.value) {
      await updateDictItem(editItemId.value, { ...itemForm })
      message.success('更新成功')
    } else if (selectedDict.value) {
      await createDictItem(selectedDict.value.id, { ...itemForm })
      message.success('创建成功')
    }
    itemModal.value = false
    if (selectedDict.value) selectDict(selectedDict.value)
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '操作失败')
  } finally {
    itemSaving.value = false
  }
}

async function handleItemDelete(id: number) {
  try {
    await deleteDictItem(id)
    message.success('删除成功')
    if (selectedDict.value) selectDict(selectedDict.value)
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(loadDicts)
</script>

<style scoped>
.dict-manage-page {
  padding: 28px 32px;
}

.dict-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
}

.dict-list-panel {
  background: #1c1f23;
  border: 1px solid #2c3035;
  border-radius: 8px;
  padding: 16px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #e5e7eb;
  margin-bottom: 4px;
}

.panel-sub {
  font-size: 12px;
  color: #9ca3af;
}

.dict-list {
  margin-top: 12px;
}

.dict-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.15s;
}
.dict-item:hover {
  background: #24282d;
}
.dict-item.active {
  background: #22262b;
  border-left: 3px solid #3b82f6;
  padding-left: 9px;
}

.dict-name {
  font-size: 13px;
  color: #e5e7eb;
}
.dict-code {
  font-size: 11px;
  color: #6b7280;
  margin-top: 2px;
  font-family: monospace;
}

.dict-status {
  font-size: 10px;
}
.dict-status.active {
  color: #4ade80;
}
.dict-status.inactive {
  color: #6b7280;
}

.dict-items-panel {
  background: #1c1f23;
  border: 1px solid #2c3035;
  border-radius: 8px;
  padding: 16px;
  min-height: 400px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.items-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #6b7280;
}
.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.item-status {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
}
.item-status.active {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}
.item-status.inactive {
  background: rgba(156, 163, 175, 0.15);
  color: #9ca3af;
}

.list-empty {
  text-align: center;
  color: #6b7280;
  padding: 40px 0;
  font-size: 13px;
}
</style>
