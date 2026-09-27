<template>
      <!-- ===== 中间：正文编辑器 ===== -->
      <section class="editor-panel">
        <!-- 编辑器工具栏 -->
        <div class="editor-toolbar">
          <div class="toolbar-left">
            <div v-if="outlineTitle" class="outline-context" :title="`${outlineLabel}：${outlineTitle}`">
              <span class="outline-context-label">{{ outlineLabel }}</span>
              <span class="outline-context-title">{{ outlineTitle }}</span>
            </div>
            <div class="title-row">
              <span class="chapter-number">第{{ chapterNo }}章</span>
              <n-input
                v-model:value="chapterTitle"
                class="title-input"
                aria-label="章节标题"
                :placeholder="chapterOutlineTitle || '输入章节标题...'"
                size="large"
                :bordered="false"
              />
            </div>
          </div>
          <div class="toolbar-right">
            <div class="word-count">
              <span class="count-num">{{ wordCount }}</span>
              <span class="count-label">字</span>
            </div>
            <n-divider vertical />
            <span class="save-status" :class="saveStatus">
              {{ saveStatusText }}
            </span>
            <n-divider v-if="chapterId" vertical />
            <span v-if="chapterId" class="chapter-id">ID {{ chapterId }}</span>
          </div>
        </div>

        <!-- 正文编辑器 -->
        <div class="editor-container">
          <n-input
            :style="{ '--chapter-editor-font-size': `${editorFontSize}px` }"
            v-model:value="draft"
            type="textarea"
            class="chapter-textarea"
            :autosize="{ minRows: 20 }"
            :bordered="false"
            ref="editorInput"
            @mouseup="captureSelection"
            @keyup="captureSelection"
            placeholder="在这里写你的小说正文...

提示：
1. 从左侧选择大纲，生成参数会自动填充
2. 调整右侧参数后点击「生成章节」
3. 生成后可进行分析、精修、一致性检查"
          />
        </div>

        <!-- 精修高亮对比面板 -->
        <div v-if="hasPolishHighlights" class="polish-panel">
          <div class="polish-header">
            <span class="polish-title">🎨 精修对比</span>
            <n-tag size="tiny" type="warning">高亮段落为精修后变化的内容</n-tag>
            <n-button size="tiny" text @click="closePolishComparison">关闭对比</n-button>
          </div>
          <div class="polish-content">
            <p
              v-for="(segment, index) in polishSegments"
              :key="`${index}-${segment.status}`"
              :class="['polish-segment', segment.status]"
            >
              {{ segment.text }}
            </p>
          </div>
        </div>
      </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

type PolishSegment = { text: string; status: 'same' | 'changed' }

const props = defineProps<{
  chapterTitle: string
  chapterNo: number
  outlineLabel: string
  outlineTitle: string
  chapterOutlineTitle: string
  draft: string
  wordCount: number
  chapterId: number | null
  editorFontSize: number
  saveStatus: 'saved' | 'unsaved' | 'saving' | 'error'
  hasPolishHighlights: boolean
  polishSegments: PolishSegment[]
}>()
const emit = defineEmits<{
  (event: 'update:chapterTitle', value: string): void
  (event: 'update:draft', value: string): void
  (event: 'close-polish-comparison'): void
  (event: 'selection-change', selection: { start: number; end: number; text: string } | null): void
}>()

const editorInput = ref<{ $el?: HTMLElement } | null>(null)

// 步骤 1：将编辑值作为受控输入回传页面，正文保存和生成仍由工作台统一协调。
const chapterTitle = computed({
  // 章节号由标题栏单独展示，避免把自动生成的“第 N 章”重复显示成正文标题。
  get: () => {
    const defaultNumber = props.chapterTitle.trim().match(/^第\s*(\d+)\s*章$/)?.[1]
    return Number(defaultNumber) === props.chapterNo ? '' : props.chapterTitle
  },
  set: (value: string) => emit('update:chapterTitle', value),
})
const draft = computed({
  get: () => props.draft,
  set: (value: string) => emit('update:draft', value),
})
const saveStatusText = computed(() => ({
  saved: '💾 已保存',
  unsaved: '📝 未保存',
  saving: '⏳ 保存中',
  error: '⚠️ 保存失败',
}[props.saveStatus]))
function closePolishComparison() {
  // 步骤 1：通知页面清空原稿快照，关闭精修前后对比。
  emit('close-polish-comparison')
}

function captureSelection() {
  // 步骤 1：读取正文编辑器的原生选区偏移；步骤 2：把稳定的正文范围交给对话改稿面板。
  const textarea = editorInput.value?.$el?.querySelector('textarea')
  if (!(textarea instanceof HTMLTextAreaElement)) return
  const { selectionStart: start, selectionEnd: end } = textarea
  if (start === end) {
    emit('selection-change', null)
    return
  }
  emit('selection-change', { start, end, text: textarea.value.slice(start, end) })
}
</script>
<style scoped>
/* ===== 中间编辑器 ===== */
.editor-panel {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  backdrop-filter: blur(10px);
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 18px 10px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.toolbar-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.title-input {
  flex: 1;
  min-width: 0;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
  background: transparent !important;
  transition: background-color 0.16s ease;
}

.title-input:hover,
.title-input:focus-within {
  background: rgba(255, 255, 255, 0.045) !important;
}

.title-input :deep(input) {
  font-size: 20px !important;
  font-weight: 600 !important;
  color: var(--text-primary) !important;
  background: transparent !important;
}

.title-input :deep(input::placeholder) {
  color: var(--text-secondary) !important;
  opacity: 0.8;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.chapter-number {
  flex: none;
  padding-left: 10px;
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 700;
  white-space: nowrap;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.word-count {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.count-num {
  font-size: 18px;
  font-weight: 700;
  background: var(--accent-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.count-label {
  font-size: 12px;
  color: var(--text-muted);
}

.save-status {
  font-size: 12px;
  color: var(--text-muted);
}

.save-status.saved {
  color: #6ee7b7;
}

.outline-context {
  display: flex;
  align-items: center;
  gap: 7px;
  overflow: hidden;
  padding: 2px 10px 0 12px;
  line-height: 20px;
  white-space: nowrap;
}

.outline-context-label {
  flex: none;
  padding: 1px 6px;
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 5px;
  color: #a5b4fc;
  background: rgba(99, 102, 241, 0.1);
  font-size: 11px;
}

.outline-context-title {
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 13px;
  text-overflow: ellipsis;
}

.save-status.saving {
  color: #93c5fd;
}

.save-status.error {
  color: #fca5a5;
}

.chapter-id {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

@media (max-width: 760px) {
  .editor-toolbar {
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    padding: 10px 12px;
  }

  .toolbar-left {
    flex: 1 1 220px;
  }

  .chapter-number {
    font-size: 18px;
  }

  .toolbar-right {
    gap: 6px;
    margin-left: auto;
  }

  .save-status {
    font-size: 11px;
    white-space: nowrap;
  }

  .chapter-id,
  .toolbar-right :deep(.n-divider) {
    display: none;
  }
}

.editor-container {
  flex: 1;
  min-height: 0;
  padding: 16px;
  overflow-x: hidden;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.18) transparent;
}

.editor-container::-webkit-scrollbar {
  width: 5px;
}

.editor-container::-webkit-scrollbar-track {
  background: transparent;
}

.editor-container::-webkit-scrollbar-thumb {
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.18);
}

.editor-container::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

.chapter-textarea {
  min-height: 100%;
  background: transparent !important;
}

.chapter-textarea :deep(textarea) {
  font-size: var(--chapter-editor-font-size, 16px);
}

.chapter-textarea :deep(textarea) {
  line-height: 1.9;
  font-size: 15px;
  padding: 16px !important;
  color: var(--text-primary) !important;
  background: transparent !important;
  overflow-y: hidden !important;
  scrollbar-width: none !important;
  -ms-overflow-style: none;
}

.chapter-textarea :deep(textarea)::-webkit-scrollbar {
  display: none !important;
  width: 0;
  height: 0;
}

.chapter-textarea :deep(.n-input__textarea-el) {
  overflow-y: hidden !important;
  scrollbar-width: none !important;
  -ms-overflow-style: none;
}

.chapter-textarea :deep(.n-input__textarea-el)::-webkit-scrollbar {
  display: none !important;
  width: 0;
  height: 0;
}

/* 精修对比面板 */
.polish-panel {
  border-top: 1px solid var(--border);
  max-height: 200px;
  overflow-y: auto;
  flex-shrink: 0;
}

.polish-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.02);
}

.polish-title {
  font-size: 13px;
  font-weight: 600;
  flex: 1;
  color: var(--text-primary);
}

.polish-content {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.polish-segment {
  margin: 0;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  line-height: 1.7;
  white-space: pre-wrap;
  background: rgba(255, 255, 255, 0.02);
  font-size: 13px;
  color: var(--text-secondary);
}

.polish-segment.changed {
  border-color: rgba(245, 158, 11, 0.4);
  color: #fef3c7;
  background: rgba(245, 158, 11, 0.1);
}


</style>
