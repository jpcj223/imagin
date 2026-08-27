<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { NSelect, NButton, NInput, NIcon } from 'naive-ui'
import type { SelectOption } from 'naive-ui'

const props = defineProps<{
  modelValue?: string | null
  options: SelectOption[]
  placeholder?: string
  allowCreate?: boolean
  filterable?: boolean
  /** 自定义值是否保留在下拉列表中，默认 true。
   *  false 时：用户输入的自定义值不会加入下拉列表（但当前值仍会正常显示）
   */
  keepCustomOptions?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

// ===== 模式切换 =====
type Mode = 'select' | 'text'
const mode = ref<Mode>('select')
const isHovering = ref(false)

function enterTextMode() {
  textInput.value = props.modelValue ?? ''
  mode.value = 'text'
  nextTick(() => {
    const input = textInputRef.value?.$el?.querySelector('input')
    if (input) {
      input.focus()
      input.setSelectionRange(input.value.length, input.value.length)
    }
  })
}

function exitTextMode() {
  handleTextBlur()
  mode.value = 'select'
}

// ===== 选择模式 =====
const selectValue = ref(props.modelValue ?? '')

// 是否保留自定义选项在下拉列表中
const shouldKeepCustom = computed(() => props.keepCustomOptions !== false)

// 持久化的自定义选项（仅 keepCustomOptions=true 时使用）
const savedCustomOptions = ref<SelectOption[]>([])

// 最终展示的 options
// - 保留模式：外部 options + 所有自定义值
// - 不保留模式：仅外部 options（自定义值不出现在下拉列表中）
const displayOptions = computed<SelectOption[]>(() => {
  if (!shouldKeepCustom.value) {
    return props.options
  }
  // 保留模式：外部 + 所有持久化自定义值
  const externalValues = new Set(props.options.map(o => o.value))
  const custom = savedCustomOptions.value.filter(o => !externalValues.has(o.value))
  return [...props.options, ...custom]
})

// 初始化：保留模式下，如果当前值不在外部 options 里，加入持久化列表
const initVal = props.modelValue ?? ''
if (initVal && shouldKeepCustom.value && !props.options.find(o => o.value === initVal)) {
  savedCustomOptions.value.unshift({ label: initVal, value: initVal })
}

function handleCreate(val: string): SelectOption {
  const option = { label: val, value: val }
  if (shouldKeepCustom.value && !savedCustomOptions.value.find(o => o.value === val)) {
    savedCustomOptions.value.push(option)
  }
  return option
}

// 外部值 → 内部同步
watch(() => props.modelValue, (val) => {
  const strVal = val ?? ''
  if (mode.value === 'select') {
    selectValue.value = strVal
    // 保留模式下，如果新值不在外部 options 里，加入持久化列表确保显示
    if (strVal && shouldKeepCustom.value && !props.options.find(o => o.value === strVal)) {
      if (!savedCustomOptions.value.find(o => o.value === strVal)) {
        savedCustomOptions.value.unshift({ label: strVal, value: strVal })
      }
    }
  }
})

// 内部值 → 外部同步
watch(selectValue, (val) => {
  if (mode.value === 'select') {
    emit('update:modelValue', val ?? '')
  }
})

// ===== 文本模式 =====
const textInput = ref('')
const textInputRef = ref<InstanceType<typeof NInput> | null>(null)

function handleTextKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.preventDefault()
    exitTextMode()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    exitTextMode()
  }
}

function handleTextBlur() {
  const val = textInput.value.trim()
  emit('update:modelValue', val)
  selectValue.value = val
  // 保留模式下，新值加入持久化列表
  if (val && shouldKeepCustom.value && !props.options.find(o => o.value === val)) {
    if (!savedCustomOptions.value.find(o => o.value === val)) {
      savedCustomOptions.value.push({ label: val, value: val })
    }
  }
}
</script>

<template>
  <div
    class="single-select-field"
    :class="{ 'is-hovering': isHovering }"
    @mouseenter="isHovering = true"
    @mouseleave="isHovering = false"
  >
    <!-- 选择模式 -->
    <div
      v-if="mode === 'select'"
      class="select-mode-wrapper"
      @dblclick="enterTextMode"
    >
      <NSelect
        v-model:value="selectValue"
        :options="displayOptions"
        :filterable="filterable !== false"
        :allow-create="allowCreate !== false"
        :placeholder="placeholder || '请选择...'"
        clearable
        class="select-input"
        @create="handleCreate"
      />
      <!-- 编辑按钮：hover 时显示 -->
      <NButton
        v-if="isHovering"
        text
        size="tiny"
        class="edit-btn"
        @click="enterTextMode"
        title="自由编辑"
      >
        <template #icon>
          <NIcon size="14">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </NIcon>
        </template>
        编辑
      </NButton>
    </div>

    <!-- 文本模式 -->
    <div v-else class="text-mode-wrapper">
      <NInput
        ref="textInputRef"
        v-model:value="textInput"
        :placeholder="placeholder || '请输入...'"
        class="text-input"
        @blur="exitTextMode"
        @keydown="handleTextKeydown"
      />
    </div>
  </div>
</template>

<style scoped>
.single-select-field {
  width: 100%;
  position: relative;
}

.select-mode-wrapper {
  width: 100%;
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.select-input {
  flex: 1;
  min-width: 0;
}

.edit-btn {
  flex-shrink: 0;
  margin-top: 4px;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.edit-btn:hover {
  opacity: 1;
}

.text-mode-wrapper {
  width: 100%;
  position: relative;
}

.text-input {
  width: 100%;
}
</style>
