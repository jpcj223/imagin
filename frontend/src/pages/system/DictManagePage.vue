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

    <!-- 主体：左侧可排序字典，右侧以卡片管理字典标签 -->
    <div class="dict-layout">
      <aside class="dict-list-panel">
        <div class="dict-list-head">
          <div>
            <div class="panel-title">字典列表</div>
            <div class="panel-sub">{{ dictionaries.length }} 个字典 · 拖动排序</div>
          </div>
          <span class="dict-total-badge">{{ dictionaries.length }}</span>
        </div>

        <draggable
          v-model="dictionaries"
          item-key="id"
          handle=".dict-drag-handle"
          :animation="180"
          :disabled="dictionaryOrderSaving"
          ghost-class="dict-ghost"
          chosen-class="dict-chosen"
          class="dict-list"
          @end="saveDictionaryOrder"
        >
          <template #item="{ element: dict }">
            <div
              class="dict-item"
              :class="{ active: selectedDictId === dict.id, inactive: dict.status !== 'active' }"
              @click="selectDict(dict)"
            >
              <span class="dict-drag-handle" title="拖动调整字典顺序" aria-label="拖动排序">⠿</span>
              <div class="dict-main">
                <div class="dict-name">{{ dict.dict_name }}</div>
                <div class="dict-code">{{ dict.dict_code }}</div>
              </div>
              <span :class="['dict-status', dict.status]">
                {{ dict.status === 'active' ? '启用' : '停用' }}
              </span>
            </div>
          </template>
        </draggable>

        <div v-if="dictionaries.length === 0" class="list-empty">
          <div class="empty-icon">📚</div>
          <p>暂无字典</p>
          <p class="empty-sub">点击右上角「新增字典」创建</p>
        </div>
      </aside>

      <section class="dict-items-panel">
        <div class="panel-head">
          <div class="items-title-group">
            <div class="items-title-row">
              <div class="panel-title">{{ selectedDict?.dict_name || '字典标签' }}</div>
              <span v-if="selectedDict" class="item-total-badge">{{ dictItems.length }} 项</span>
            </div>
            <div class="panel-sub" v-if="selectedDict">
              {{ selectedDict.description || selectedDict.dict_code }} · 拖动标签卡片调整顺序
            </div>
          </div>
          <div v-if="selectedDict" class="panel-actions">
            <n-button size="small" @click="openDictEdit">编辑字典</n-button>
            <n-button size="small" type="primary" @click="openItemCreate">
              <template #icon>＋</template>
              新增标签
            </n-button>
          </div>
        </div>

        <div v-if="!selectedDict" class="items-empty">
          <div class="empty-icon">📖</div>
          <p>请选择左侧字典查看标签</p>
        </div>
        <div v-else-if="itemsLoading" class="items-loading">
          <n-spin size="medium" />
          <span>正在加载字典标签…</span>
        </div>
        <draggable
          v-else-if="dictItems.length > 0"
          v-model="dictItems"
          item-key="id"
          handle=".item-drag-handle"
          :animation="180"
          :disabled="itemOrderSaving"
          ghost-class="item-ghost"
          chosen-class="item-chosen"
          class="item-grid"
          @end="saveItemOrder"
        >
          <template #item="{ element: item, index }">
            <article class="item-card" :class="{ 'item-card-inactive': item.status !== 'active' }">
              <div class="item-card-head">
                <span class="item-drag-handle" title="拖动调整标签顺序" aria-label="拖动排序">⠿</span>
                <div class="item-card-title">{{ item.item_label }}</div>
                <span :class="['item-status', item.status]">{{ item.status === 'active' ? '启用' : '停用' }}</span>
              </div>
              <div class="item-value-row">
                <span class="item-field-label">枚举值</span>
                <code>{{ item.item_value }}</code>
              </div>
              <p class="item-remark" :class="{ empty: !item.remark }">
                {{ item.remark || '暂无备注' }}
              </p>
              <div class="item-card-footer">
                <span class="item-order">{{ String(index + 1).padStart(2, '0') }} <span>排序</span></span>
                <div class="item-actions">
                  <n-button size="tiny" text type="primary" @click.stop="openItemEdit(item)">编辑</n-button>
                  <n-popconfirm @positive-click="handleItemDelete(item.id)">
                    <template #trigger>
                      <n-button size="tiny" text type="error" @click.stop>删除</n-button>
                    </template>
                    确认删除这个字典标签？
                  </n-popconfirm>
                </div>
              </div>
            </article>
          </template>
        </draggable>
        <div v-else class="items-empty items-empty-card">
          <div class="empty-icon">🏷️</div>
          <p>这个字典还没有标签</p>
          <n-button size="small" type="primary" ghost @click="openItemCreate">新增第一个标签</n-button>
        </div>
      </section>
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
import { computed, onMounted, reactive, ref } from 'vue'
import draggable from 'vuedraggable'
import { useMessage } from 'naive-ui'
import {
  createDictItem,
  createDictionary,
  deleteDictItem,
  deleteDictionary,
  fetchDictionaries,
  fetchDictItems,
  reorderDictItems,
  reorderDictionaries,
  updateDictItem,
  updateDictionary,
  type DictItem,
  type Dictionary,
} from '@/api/core'

const message = useMessage()
const loading = ref(false)
const itemsLoading = ref(false)
const dictionaryOrderSaving = ref(false)
const itemOrderSaving = ref(false)
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

async function loadDicts() {
  loading.value = true
  try {
    dictionaries.value = await fetchDictionaries()
    if (dictionaries.value.length > 0 && !selectedDictId.value) {
      selectDict(dictionaries.value[0])
    }
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '字典列表加载失败')
  } finally {
    loading.value = false
  }
}

async function selectDict(dict: Dictionary) {
  selectedDictId.value = dict.id
  itemsLoading.value = true
  try {
    // 管理页同时读取启用和停用标签，保证停用数据也能编辑与参与排序。
    dictItems.value = await fetchDictItems(dict.dict_code, true)
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '字典标签加载失败')
  } finally {
    itemsLoading.value = false
  }
}

// 字典列表拖动结束后，将完整顺序一次性保存到核心库。
async function saveDictionaryOrder() {
  if (dictionaryOrderSaving.value || dictionaries.value.length < 2) return
  dictionaryOrderSaving.value = true
  try {
    dictionaries.value = await reorderDictionaries(dictionaries.value.map((dict) => dict.id))
    message.success('字典顺序已保存')
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '字典排序保存失败，正在恢复原顺序')
    dictionaries.value = await fetchDictionaries()
  } finally {
    dictionaryOrderSaving.value = false
  }
}

// 当前字典的标签卡片拖动结束后，仅保存本字典内的完整顺序。
async function saveItemOrder() {
  const dict = selectedDict.value
  if (!dict || itemOrderSaving.value || dictItems.value.length < 2) return
  itemOrderSaving.value = true
  try {
    dictItems.value = await reorderDictItems(dict.id, dictItems.value.map((item) => item.id))
    message.success('标签顺序已保存')
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '标签排序保存失败，正在恢复原顺序')
    await selectDict(dict)
  } finally {
    itemOrderSaving.value = false
  }
}

// ---- 字典 CRUD ----

function openDictCreate() {
  isDictEdit.value = false
  Object.assign(dictForm, {
    dict_code: '',
    dict_name: '',
    description: '',
    sort_order: Math.max(0, ...dictionaries.value.map((dict) => dict.sort_order)) + 10,
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
    sort_order: Math.max(0, ...dictItems.value.map((item) => item.sort_order)) + 10,
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
  /* 左侧固定管理字典，右侧将当前字典项按卡片网格展开。 */
  display: grid;
  grid-template-columns: minmax(270px, 310px) minmax(0, 1fr);
  gap: 16px;
  align-items: stretch;
  min-height: 560px;
}

.dict-list-panel,
.dict-items-panel {
  min-width: 0;
  min-height: 560px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 12px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--n-text-color-1, #e5e7eb);
}

.panel-sub {
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 4px;
}

.dict-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.dict-total-badge,
.item-total-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 30px;
  height: 26px;
  padding: 0 8px;
  box-sizing: border-box;
  border-radius: 999px;
  background: var(--n-color, #23272f);
  color: var(--n-text-color-2, #9ca3af);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.dict-list {
  /* 让大量字典在左栏内部滚动，不挤压右侧标签卡片区域。 */
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
}

.dict-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 64px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, transform 0.15s;
  box-sizing: border-box;
}

.dict-item:hover {
  background: var(--n-color-hover, #23272f);
  border-color: var(--n-border-color, #2a2f3a);
}

.dict-item.active {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.35);
  box-shadow: inset 3px 0 0 var(--n-primary-color, #3b82f6);
}

.dict-item.inactive .dict-main {
  opacity: 0.65;
}

.dict-drag-handle,
.item-drag-handle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 22px;
  width: 22px;
  height: 26px;
  color: var(--n-text-color-3, #6b7280);
  font-size: 19px;
  line-height: 1;
  letter-spacing: -3px;
  cursor: grab;
  user-select: none;
}

.dict-drag-handle:hover,
.item-drag-handle:hover {
  color: var(--n-primary-color, #3b82f6);
}

.dict-drag-handle:active,
.item-drag-handle:active {
  cursor: grabbing;
}

.dict-name {
  font-size: 13px;
  color: var(--n-text-color-1, #e5e7eb);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dict-code {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 2px;
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dict-status {
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
}

.dict-status.active {
  color: #4ade80;
  background: rgba(34, 197, 94, 0.12);
}

.dict-status.inactive {
  color: #6b7280;
  background: rgba(107, 114, 128, 0.14);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.items-title-group {
  min-width: 0;
}

.items-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.item-total-badge {
  min-width: 48px;
  height: 24px;
  background: rgba(59, 130, 246, 0.14);
  color: var(--n-primary-color, #60a5fa);
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.item-grid {
  /* 卡片自动适配可用宽度，拖动时保持网格布局。 */
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 250px), 1fr));
  align-content: start;
  gap: 12px;
  padding: 18px;
}

.item-card {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px;
  background: var(--n-color, #202329);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 12px;
  transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}

.item-card:hover {
  transform: translateY(-2px);
  border-color: rgba(99, 102, 241, 0.45);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
}

.item-card-inactive {
  opacity: 0.72;
}

.item-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.item-drag-handle {
  flex-basis: 20px;
  width: 20px;
  height: 24px;
}

.item-card-title {
  min-width: 0;
  flex: 1;
  color: var(--n-text-color-1, #e5e7eb);
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-status {
  flex-shrink: 0;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  white-space: nowrap;
}

.item-status.active {
  background: rgba(34, 197, 94, 0.12);
  color: #4ade80;
}

.item-status.inactive {
  background: rgba(156, 163, 175, 0.14);
  color: #9ca3af;
}

.item-value-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.item-field-label {
  flex-shrink: 0;
  color: var(--n-text-color-3, #6b7280);
  font-size: 11px;
}

.item-value-row code {
  min-width: 0;
  padding: 4px 7px;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.12);
  border-radius: 5px;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-remark {
  min-height: 38px;
  margin: 0;
  color: var(--n-text-color-2, #9ca3af);
  font-size: 12px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.item-remark.empty {
  color: var(--n-text-color-3, #6b7280);
}

.item-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--n-border-color, #2a2f3a);
}

.item-order {
  color: var(--n-primary-color, #60a5fa);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.item-order span {
  color: var(--n-text-color-3, #6b7280);
  margin-left: 4px;
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.items-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 300px;
  gap: 8px;
  color: var(--n-text-color-3, #6b7280);
}

.items-empty-card {
  margin: 18px;
  border: 1px dashed var(--n-border-color, #2a2f3a);
  border-radius: 12px;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.items-loading {
  display: flex;
  flex: 1;
  min-height: 300px;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--n-text-color-3, #6b7280);
}

.list-empty {
  text-align: center;
  color: var(--n-text-color-3, #6b7280);
  padding: 40px 0;
  font-size: 13px;
}

.list-empty .empty-icon {
  margin: 0 0 8px;
}

.list-empty p {
  margin: 0;
}

.list-empty .empty-sub {
  margin-top: 5px;
  font-size: 12px;
}

.dict-ghost,
.item-ghost {
  opacity: 0.4;
  background: rgba(59, 130, 246, 0.12) !important;
  border: 1px dashed var(--n-primary-color, #3b82f6) !important;
}

.dict-chosen,
.item-chosen {
  cursor: grabbing;
}

@media (max-width: 1000px) {
  .dict-manage-page {
    padding: 20px;
  }

  .dict-layout {
    grid-template-columns: minmax(230px, 280px) minmax(0, 1fr);
  }

  .item-grid {
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr));
    padding: 14px;
  }
}

@media (max-width: 760px) {
  .dict-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .dict-list-panel {
    min-height: 0;
    max-height: 360px;
  }

  .dict-items-panel {
    min-height: 480px;
  }

  .panel-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .panel-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
