<template>
  <div class="filter-tag-dropdown" ref="containerRef">
    <!-- 触发标签 -->
    <div
      class="filter-tag"
      :class="{ active: hasValue }"
      @click="toggle"
    >
      <span v-if="icon" class="tag-icon">{{ icon }}</span>
      <span class="tag-text">{{ displayLabel }}</span>
      <span v-if="hasValue" class="tag-close" @click.stop="clear">×</span>
    </div>

    <!-- 下拉面板 -->
    <Transition name="dropdown-fade">
      <div v-if="visible" class="dropdown-panel" :style="panelStyle">
        <div class="dropdown-list" ref="listRef">
          <div
            v-for="item in options"
            :key="item.value"
            class="dropdown-item"
            :class="{ selected: isSelected(item.value) }"
            @click="selectItem(item)"
          >
            <span class="item-label">{{ item.label }}</span>
            <span v-if="isSelected(item.value)" class="item-check">✓</span>
          </div>
          <div v-if="options.length === 0" class="dropdown-empty">
            暂无选项
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

interface DropdownOption {
  label: string
  value: string
}

const props = defineProps<{
  modelValue: string | string[] | null
  options: DropdownOption[]
  placeholder?: string
  icon?: string
  maxHeight?: number
  multiple?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | string[] | null): void
}>()

const visible = ref(false)
const containerRef = ref<HTMLElement | null>(null)
const listRef = ref<HTMLElement | null>(null)

const isMultiple = computed(() => props.multiple === true)

const selectedValues = computed(() => {
  if (!props.modelValue) return []
  return Array.isArray(props.modelValue) ? props.modelValue : [props.modelValue]
})

const hasValue = computed(() => selectedValues.value.length > 0)

const displayLabel = computed(() => {
  if (!hasValue.value) return props.placeholder || '筛选'
  const vals = selectedValues.value
  if (vals.length === 1) {
    const opt = props.options.find(o => o.value === vals[0])
    return opt?.label || props.placeholder || '筛选'
  }
  return `${props.placeholder || '筛选'}(${vals.length})`
})

const panelStyle = computed(() => ({
  maxHeight: `${props.maxHeight || 280}px`,
}))

function isSelected(value: string): boolean {
  return selectedValues.value.includes(value)
}

function toggle() {
  visible.value = !visible.value
}

function selectItem(item: DropdownOption) {
  if (isMultiple.value) {
    // 多选模式：点击切换选中状态，不关闭面板
    const current = [...selectedValues.value]
    const idx = current.indexOf(item.value)
    if (idx > -1) {
      current.splice(idx, 1)
    } else {
      current.push(item.value)
    }
    emit('update:modelValue', current.length > 0 ? current : null)
  } else {
    // 单选模式
    emit('update:modelValue', item.value === props.modelValue ? null : item.value)
    visible.value = false
  }
}

function clear() {
  emit('update:modelValue', null)
}

function handleClickOutside(e: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    visible.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.filter-tag-dropdown {
  position: relative;
  display: inline-block;
}

.filter-tag {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: var(--n-color-2, #262a33);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 16px;
  font-size: 12px;
  color: var(--n-text-color-3, #9ca3af);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.filter-tag:hover {
  background: var(--n-color-3, #2d313b);
  border-color: var(--n-border-color-hover, #3a3f4b);
  color: var(--n-text-color-2, #d1d5db);
}

.filter-tag.active {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.4);
  color: #60a5fa;
}

.tag-icon {
  font-size: 12px;
  line-height: 1;
}

.tag-text {
  line-height: 1;
  white-space: nowrap;
}

.tag-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  font-size: 12px;
  line-height: 1;
  margin-left: 2px;
  opacity: 0.7;
  transition: all 0.15s ease;
}

.tag-close:hover {
  background: rgba(255, 255, 255, 0.15);
  opacity: 1;
}

/* 下拉面板 */
.dropdown-panel {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 2000;
  background: var(--n-color-1, #1e2228);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.4);
  overflow: hidden;
  min-width: 140px;
}

.dropdown-list {
  max-height: inherit;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 4px 0;
}

/* 自定义滚动条 */
.dropdown-list::-webkit-scrollbar {
  width: 6px;
}

.dropdown-list::-webkit-scrollbar-track {
  background: var(--n-color-1, #1e2228);
}

.dropdown-list::-webkit-scrollbar-thumb {
  background: var(--n-border-color, #3a3f4b);
  border-radius: 3px;
}

.dropdown-list::-webkit-scrollbar-thumb:hover {
  background: var(--n-border-color-hover, #4b5060);
}

.dropdown-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  font-size: 12px;
  color: var(--n-text-color-2, #d1d5db);
  cursor: pointer;
  transition: background 0.15s ease;
}

.dropdown-item:hover {
  background: var(--n-color-2, #262a33);
}

.dropdown-item.selected {
  color: #60a5fa;
  background: rgba(59, 130, 246, 0.1);
}

.item-label {
  white-space: nowrap;
}

.item-check {
  font-size: 11px;
  font-weight: 600;
}

.dropdown-empty {
  padding: 20px 12px;
  text-align: center;
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
}

/* 动画 */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
