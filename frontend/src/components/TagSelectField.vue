<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { NSelect, NButton, NInput, NIcon } from 'naive-ui'
import type { SelectOption } from 'naive-ui'

const props = defineProps<{
  modelValue: string
  options: SelectOption[]
  placeholder?: string
  allowCreate?: boolean
  filterable?: boolean
  maxTagCount?: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

// ===== 模式切换 =====
type Mode = 'tag' | 'text'
const mode = ref<Mode>('tag')
const isHovering = ref(false)

function enterTextMode() {
  textInput.value = props.modelValue
  mode.value = 'text'
  nextTick(() => {
    const textarea = textInputRef.value?.$el?.querySelector('textarea')
    if (textarea) {
      textarea.focus()
      // 光标移到末尾
      textarea.setSelectionRange(textarea.value.length, textarea.value.length)
    }
  })
}

function exitTextMode() {
  handleTextBlur()
  mode.value = 'tag'
}

// ===== 标签模式 =====
const tagSelect = ref<string[]>([])

// 只使用外部传入的字典 options，不追加用户自定义值
const displayOptions = computed(() => props.options)

// 重置
function handleReset() {
  tagSelect.value = []
}

// ===== 文本模式 =====
const textInput = ref('')
const textInputRef = ref<InstanceType<typeof NInput> | null>(null)

function handleTextKeydown(e: KeyboardEvent) {
  // ESC 退出编辑
  if (e.key === 'Escape') {
    e.preventDefault()
    exitTextMode()
  }
}

// ===== 通用工具 =====
function parseTags(str: string): string[] {
  if (!str.trim()) return []
  return str.split(/[、,，\n]/).map(s => s.trim()).filter(Boolean)
}

function joinTags(tags: string[]): string {
  return tags.join('、')
}

// ===== 外部值 → 内部同步 =====
watch(() => props.modelValue, (val) => {
  const parsed = parseTags(val)
  // 同步到标签模式
  const currentSet = new Set(tagSelect.value)
  const newSet = new Set(parsed)
  if (currentSet.size !== newSet.size || [...currentSet].some(t => !newSet.has(t))) {
    tagSelect.value = parsed
  }
  // 同步到文本模式
  if (mode.value === 'text') {
    textInput.value = val
  }
}, { immediate: true })

// ===== 内部值 → 外部同步 =====
// 标签模式变化
watch(tagSelect, (val) => {
  if (mode.value === 'tag') {
    emit('update:modelValue', joinTags(val))
  }
}, { deep: true })

// 文本模式变化时实时同步（不规范化，保证用户输入过程中数据也能保存）
watch(textInput, (val) => {
  if (mode.value === 'text') {
    emit('update:modelValue', val)
  }
})

// 文本模式失焦时规范化
function handleTextBlur() {
  const parsed = parseTags(textInput.value)
  const unique = [...new Set(parsed)]
  const result = joinTags(unique)
  textInput.value = result
  emit('update:modelValue', result)
  // 同步到标签模式
  tagSelect.value = unique
}
</script>

<template>
  <div
    class="tag-select-field"
    :class="{ 'is-hovering': isHovering }"
    @mouseenter="isHovering = true"
    @mouseleave="isHovering = false"
  >
    <!-- 标签模式 -->
    <div
      v-if="mode === 'tag'"
      class="tag-mode-wrapper"
      @dblclick="enterTextMode"
    >
      <NSelect
        v-model:value="tagSelect"
        multiple
        :filterable="filterable !== false"
        :allow-create="allowCreate !== false"
        :options="displayOptions"
        :placeholder="placeholder || '选择或输入...'"
        :max-tag-count="maxTagCount || 6"
        clearable
        class="tag-select-input"
      >
        <template #action>
          <div class="select-action-footer">
            <span class="select-action-hint">双击可自由编辑</span>
            <NButton
              text
              size="tiny"
              type="error"
              @click="handleReset"
              :disabled="tagSelect.length === 0"
            >
              重置
            </NButton>
          </div>
        </template>
      </NSelect>
    </div>

    <!-- 文本模式 -->
    <div v-else class="text-mode-wrapper">
      <NInput
        ref="textInputRef"
        v-model:value="textInput"
        type="textarea"
        :placeholder="placeholder || '输入内容，用顿号、逗号或换行分隔...'"
        class="text-input"
        @blur="exitTextMode"
        @keydown="handleTextKeydown"
        :autosize="{ minRows: 2, maxRows: 6 }"
      />
      <div class="text-mode-hint">
        失焦或按 ESC 返回
      </div>
    </div>
  </div>
</template>

<style scoped>
.tag-select-field {
  width: 100%;
  position: relative;
}

.tag-mode-wrapper {
  width: 100%;
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.tag-select-input {
  flex: 1;
  min-width: 0;
}

.text-mode-wrapper {
  width: 100%;
  position: relative;
}

.text-input {
  width: 100%;
}

.text-mode-hint {
  position: absolute;
  right: 8px;
  bottom: -18px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.select-action-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.select-action-hint {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

/* 去掉整个选择框的边框 */
:deep(.n-base-selection) {
  border: none !important;
  box-shadow: none !important;
}

:deep(.n-base-selection:hover) {
  border: none !important;
  box-shadow: none !important;
}

:deep(.n-base-selection--focused) {
  border: none !important;
  box-shadow: none !important;
}

/* 去掉文本输入框的边框 */
:deep(.n-input) {
  border: none !important;
  box-shadow: none !important;
}

:deep(.n-input:hover) {
  border: none !important;
  box-shadow: none !important;
}

:deep(.n-input--focus) {
  border: none !important;
  box-shadow: none !important;
}

/* 去掉选中标签的边框，背景透明与选择框融为一体 */
:deep(.n-base-selection .n-tag) {
  border: none !important;
  border-color: transparent !important;
  box-shadow: none !important;
  background-color: transparent !important;
  --n-border: none !important;
  --n-border-color: transparent !important;
  --n-color: transparent !important;
  --n-color-hover: transparent !important;
}

:deep(.n-base-selection .n-tag:hover) {
  border: none !important;
  border-color: transparent !important;
  box-shadow: none !important;
  background-color: rgba(255, 255, 255, 0.06) !important;
  --n-border: none !important;
  --n-border-color: transparent !important;
}

:deep(.n-base-selection .n-tag .n-tag__border) {
  display: none !important;
}

:deep(.n-base-selection .n-tag__close) {
  color: rgba(255, 255, 255, 0.6);
}

:deep(.n-base-selection .n-tag__close:hover) {
  color: rgba(255, 255, 255, 0.9);
}
</style>
