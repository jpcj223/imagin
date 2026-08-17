<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { NSelect, NButton, NInput, NIcon } from 'naive-ui'
import type { SelectOption } from 'naive-ui'

const props = defineProps<{
  modelValue?: string | null
  options: SelectOption[]
  placeholder?: string
  allowCreate?: boolean
  filterable?: boolean
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

// 内部维护的 options（包含用户创建的）
const internalOptions = ref<SelectOption[]>([...props.options])

// 初始化：如果当前值不在 options 里，加入进去确保能正常显示
const initVal = props.modelValue ?? ''
if (initVal && !internalOptions.value.find(o => o.value === initVal)) {
  internalOptions.value.unshift({ label: initVal, value: initVal })
}

function handleCreate(val: string): SelectOption {
  const option = { label: val, value: val }
  if (!internalOptions.value.find(o => o.value === val)) {
    internalOptions.value.push(option)
  }
  return option
}

// 外部 options 变化时同步
watch(() => props.options, (val) => {
  // 合并外部 options + 内部自定义（去重）
  const externalValues = new Set(val.map(o => o.value))
  const custom = internalOptions.value.filter(o => !externalValues.has(o.value))
  internalOptions.value = [...val, ...custom]
}, { deep: true })

// 外部值 → 内部同步
watch(() => props.modelValue, (val) => {
  const strVal = val ?? ''
  if (mode.value === 'select') {
    selectValue.value = strVal
    // 如果新值不在 options 里，加入进去确保显示
    if (strVal && !internalOptions.value.find(o => o.value === strVal)) {
      internalOptions.value.unshift({ label: strVal, value: strVal })
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
  // 如果是新值，加入内部 options
  if (val && !internalOptions.value.find(o => o.value === val)) {
    internalOptions.value.push({ label: val, value: val })
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
        :options="internalOptions"
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
