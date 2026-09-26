<template>
      <!-- ===== 中间：正文编辑器 ===== -->
      <section class="editor-panel">
        <!-- 编辑器工具栏 -->
        <div class="editor-toolbar">
          <div class="toolbar-left">
            <n-input
              v-model:value="chapterTitle"
              class="title-input"
              placeholder="章节标题..."
              size="large"
              :bordered="false"
            />
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
  draft: string
  wordCount: number
  chapterId: number | null
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
  get: () => props.chapterTitle,
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
  padding: 12px 18px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.toolbar-left {
  flex: 1;
  min-width: 0;
}

.title-input {
  font-size: 16px;
  font-weight: 600;
}

.title-input :deep(input) {
  font-size: 16px !important;
  font-weight: 600 !important;
  color: var(--text-primary) !important;
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

.save-status.saving {
  color: #93c5fd;
}

.save-status.error {
  color: #fca5a5;
}

.chapter-id {
  font-size: 11px;
  color: var(--text-muted);
}

.editor-container {
  flex: 1;
  min-height: 0;
  padding: 16px;
  overflow-x: hidden;
  overflow-y: auto;
}

.editor-container::-webkit-scrollbar {
  width: 6px;
}

.editor-container::-webkit-scrollbar-track {
  background: transparent;
}

.editor-container::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 3px;
}

.editor-container::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

.chapter-textarea {
  min-height: 100%;
  background: transparent !important;
}

.chapter-textarea :deep(textarea) {
  line-height: 1.9;
  font-size: 15px;
  padding: 16px !important;
  color: var(--text-primary) !important;
  background: transparent !important;
  overflow-y: hidden !important;
  scrollbar-width: none;
}

.chapter-textarea :deep(textarea)::-webkit-scrollbar {
  display: none;
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
