<template>
  <section class="dialogue-panel">
    <header class="dialogue-heading">
      <div>
        <strong>对话改稿</strong>
        <p>先说明想法，AI 会结合当前正文讨论或给出候选稿。</p>
      </div>
      <n-tag v-if="chapterTitle" size="small" :bordered="false">{{ chapterTitle }}</n-tag>
    </header>

    <div class="scope-control">
      <span class="scope-label">改稿范围</span>
      <n-radio-group :value="scope" size="small" @update:value="emit('update:scope', $event)">
        <n-radio-button value="chapter">整章</n-radio-button>
        <n-radio-button value="selection" :disabled="!selectionText">选中片段</n-radio-button>
      </n-radio-group>
    </div>
    <div v-if="scope === 'selection'" class="selection-summary" :class="{ warning: !selectionText }">
      <template v-if="selectionText">已选 {{ selectionText.length }} 字：{{ selectionPreview }}</template>
      <template v-else>请先在中间正文中拖选要修改的文字</template>
    </div>
    <div v-else class="scope-note">整章模式会以当前正文为底稿，候选稿不会自动覆盖原文。</div>

    <div ref="messageList" class="dialogue-messages" aria-live="polite">
      <div v-if="messages.length === 0" class="dialogue-empty">
        <div class="empty-icon">💬</div>
        <strong>从你的写作意图开始</strong>
        <span>可以先讨论问题，也可以直接提出修改要求。</span>
        <div class="starter-prompts">
          <button v-for="prompt in starterPrompts" :key="prompt" type="button" @click="send(prompt)">
            {{ prompt }}
          </button>
        </div>
      </div>
      <article
        v-for="item in messages"
        :key="item.id"
        class="dialogue-message"
        :class="item.role"
      >
        <span class="message-author">{{ item.role === 'user' ? '你' : '章节编辑 Agent' }}</span>
        <p>{{ item.content }}</p>
        <small v-if="item.usageLabel">{{ item.usageLabel }}</small>
      </article>
      <div v-if="busy" class="assistant-thinking">
        <n-spin size="small" />
        <span>正在理解要求并处理正文…</span>
      </div>
    </div>

    <section v-if="candidate" class="candidate-card">
      <div class="candidate-heading">
        <div>
          <strong>候选稿已就绪</strong>
          <span>{{ candidate.scope === 'selection' ? '选中片段' : '整章' }} · {{ candidateWordCount }} 字</span>
        </div>
        <n-tag type="warning" size="tiny">待确认</n-tag>
      </div>
      <p class="candidate-note">原文仍保留。先查看对照，再决定是否应用。</p>
      <div class="candidate-actions">
        <n-button size="small" @click="previewVisible = true">查看差异</n-button>
        <n-button size="small" quaternary type="error" @click="emit('discard')">舍弃候选</n-button>
        <n-button size="small" type="primary" :loading="applying" :disabled="!canApply" @click="emit('apply')">
          应用并保存新版本
        </n-button>
      </div>
      <div v-if="!canApply" class="candidate-warning">正文已变化或切换了章节，请刷新改稿后再应用。</div>
    </section>

    <div class="dialogue-composer">
      <n-input
        v-model:value="draftMessage"
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 5 }"
        :disabled="busy || !canSend"
        placeholder="例如：把这段对话写得更克制，保留人物立场冲突…"
        @keydown.enter.exact.prevent="submit"
      />
      <div class="composer-footer">
        <span>{{ canSend ? 'Enter 发送 · Shift + Enter 换行' : '先选择或保存一章有正文的章节' }}</span>
        <n-button type="primary" :disabled="!draftMessage.trim() || !canSend" :loading="busy" @click="submit">
          发送
        </n-button>
      </div>
    </div>

    <n-modal v-model:show="previewVisible" preset="card" title="改稿差异预览" style="width: min(1080px, 94vw)">
      <div class="diff-summary">
        {{ originalWordCount }} 字 → {{ candidateWordCount }} 字
        <span v-if="firstDifference.before || firstDifference.after">· 首处差异</span>
      </div>
      <div v-if="firstDifference.before || firstDifference.after" class="first-difference">
        <div><span>原文变化</span><del>{{ firstDifference.before }}</del></div>
        <div><span>候选变化</span><ins>{{ firstDifference.after }}</ins></div>
      </div>
      <div class="compare-grid">
        <section>
          <h4>当前原文</h4>
          <pre>{{ sourceText }}</pre>
        </section>
        <section>
          <h4>候选正文</h4>
          <pre>{{ candidateText }}</pre>
        </section>
      </div>
      <template #footer>
        <div class="preview-footer">
          <n-button @click="previewVisible = false">返回修改</n-button>
          <n-button type="primary" :loading="applying" :disabled="!canApply" @click="emit('apply')">
            确认应用并保存版本
          </n-button>
        </div>
      </template>
    </n-modal>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { ChapterDialogueCandidate, ChapterDialogueMessage } from './chapterDialogueTypes'

const props = defineProps<{
  chapterTitle: string
  messages: ChapterDialogueMessage[]
  candidate: ChapterDialogueCandidate | null
  scope: 'chapter' | 'selection'
  selectionText: string
  busy: boolean
  applying: boolean
  canSend: boolean
  canApply: boolean
}>()
const emit = defineEmits<{
  (event: 'send', instruction: string): void
  (event: 'apply'): void
  (event: 'discard'): void
  (event: 'update:scope', value: 'chapter' | 'selection'): void
}>()

const starterPrompts = ['先分析这一章的问题', '让节奏更紧凑', '强化人物对话的张力']
const draftMessage = ref('')
const previewVisible = ref(false)
const messageList = ref<HTMLElement | null>(null)
const selectionPreview = computed(() => props.selectionText.length > 180 ? `${props.selectionText.slice(0, 180)}…` : props.selectionText)
const sourceText = computed(() => {
  if (!props.candidate) return ''
  return props.candidate.scope === 'selection' ? props.candidate.originalSegment : props.candidate.expectedContent
})
const candidateText = computed(() => {
  if (!props.candidate) return ''
  return props.candidate.scope === 'selection' ? props.candidate.revisedSegment : props.candidate.proposedContent
})
const originalWordCount = computed(() => sourceText.value.replace(/\s/g, '').length)
const candidateWordCount = computed(() => candidateText.value.replace(/\s/g, '').length)
const firstDifference = computed(() => {
  const before = sourceText.value
  const after = candidateText.value
  let prefix = 0
  while (prefix < before.length && prefix < after.length && before[prefix] === after[prefix]) prefix++
  let suffix = 0
  while (suffix < before.length - prefix && suffix < after.length - prefix && before[before.length - 1 - suffix] === after[after.length - 1 - suffix]) suffix++
  const oldChange = before.slice(prefix, before.length - suffix)
  const newChange = after.slice(prefix, after.length - suffix)
  const cap = 700
  return {
    before: oldChange.length > cap ? `${oldChange.slice(0, cap)}…` : oldChange,
    after: newChange.length > cap ? `${newChange.slice(0, cap)}…` : newChange,
  }
})

function submit() {
  const instruction = draftMessage.value.trim()
  if (!instruction || !props.canSend || props.busy) return
  draftMessage.value = ''
  emit('send', instruction)
}

function send(instruction: string) {
  if (!props.canSend || props.busy) return
  emit('send', instruction)
}

watch(() => [props.messages.length, props.busy], async () => {
  await nextTick()
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight
})
watch(() => props.candidate, (candidate) => {
  if (!candidate) previewVisible.value = false
})
</script>

<style scoped>
.dialogue-panel { display: flex; flex-direction: column; gap: 12px; min-height: 100%; height: 100%; box-sizing: border-box; padding: 12px; color: #e5e7eb; }
.dialogue-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.dialogue-heading strong { font-size: 15px; }
.dialogue-heading p { margin: 5px 0 0; color: #8492a8; font-size: 12px; line-height: 1.6; }
.scope-control { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 9px; border: 1px solid rgba(255,255,255,.08); border-radius: 8px; background: rgba(255,255,255,.025); }
.scope-label { color: #aab4c4; font-size: 12px; }
.selection-summary, .scope-note { padding: 9px 10px; border-radius: 7px; background: rgba(99,102,241,.1); color: #abb7ff; font-size: 12px; line-height: 1.6; overflow-wrap: anywhere; }
.selection-summary.warning { color: #fbbf24; background: rgba(245,158,11,.08); }
.dialogue-messages { display: flex; flex: 1; flex-direction: column; gap: 12px; min-height: 180px; max-height: min(38vh, 420px); overflow-y: auto; padding: 4px 2px; }
.dialogue-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; min-height: 180px; text-align: center; color: #91a0b6; }
.empty-icon { display: grid; place-items: center; width: 42px; height: 42px; margin-bottom: 3px; border-radius: 14px; background: rgba(99,102,241,.15); font-size: 21px; }
.dialogue-empty strong { color: #dbe4f2; font-size: 13px; }
.dialogue-empty > span { max-width: 260px; font-size: 12px; line-height: 1.5; }
.starter-prompts { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px; margin-top: 6px; }
.starter-prompts button { padding: 5px 8px; border: 1px solid rgba(255,255,255,.1); border-radius: 14px; background: rgba(255,255,255,.04); color: #abb7c8; font-size: 11px; cursor: pointer; }
.starter-prompts button:hover { border-color: #6366f1; color: #c7d2fe; }
.dialogue-message { max-width: 96%; padding: 9px 11px; border: 1px solid rgba(255,255,255,.07); border-radius: 10px; background: rgba(255,255,255,.035); }
.dialogue-message.user { align-self: flex-end; border-color: rgba(99,102,241,.25); background: rgba(99,102,241,.16); }
.dialogue-message.assistant { align-self: flex-start; }
.message-author { color: #a5b4fc; font-size: 11px; font-weight: 600; }
.dialogue-message p { margin: 5px 0 0; color: #e2e8f0; font-size: 12px; line-height: 1.7; white-space: pre-wrap; overflow-wrap: anywhere; }
.dialogue-message small { display: block; margin-top: 6px; color: #77859a; font-size: 10px; }
.assistant-thinking { display: flex; align-items: center; gap: 8px; color: #a5b4fc; font-size: 12px; }
.candidate-card { padding: 11px; border: 1px solid rgba(245,158,11,.3); border-radius: 9px; background: rgba(245,158,11,.055); }
.candidate-heading, .candidate-actions { display: flex; align-items: center; justify-content: space-between; gap: 7px; }
.candidate-heading > div { display: flex; flex-direction: column; gap: 4px; }
.candidate-heading strong { color: #fde68a; font-size: 13px; }
.candidate-heading span, .candidate-note { color: #a7a9af; font-size: 11px; }
.candidate-note { margin: 8px 0; line-height: 1.5; }
.candidate-actions { justify-content: flex-start; flex-wrap: wrap; }
.candidate-actions :deep(.n-button:last-child) { margin-left: auto; }
.candidate-warning { margin-top: 7px; color: #fbbf24; font-size: 11px; }
.dialogue-composer { padding-top: 10px; border-top: 1px solid rgba(255,255,255,.08); }
.composer-footer { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding-top: 8px; color: #77859a; font-size: 10px; }
.preview-modal { width: min(1080px, 94vw); }
.diff-summary { margin-bottom: 10px; color: #9ca3af; font-size: 12px; }
.first-difference { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
.first-difference > div { min-width: 0; padding: 9px; border-radius: 7px; background: rgba(255,255,255,.04); white-space: pre-wrap; overflow-wrap: anywhere; font-size: 12px; line-height: 1.7; }
.first-difference span { display: block; margin-bottom: 5px; color: #94a3b8; font-size: 10px; }
.first-difference del { color: #fca5a5; text-decoration-color: #ef4444; }
.first-difference ins { color: #86efac; text-decoration: none; }
.compare-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.compare-grid section { min-width: 0; overflow: hidden; border: 1px solid rgba(255,255,255,.08); border-radius: 8px; }
.compare-grid h4 { margin: 0; padding: 9px 11px; border-bottom: 1px solid rgba(255,255,255,.08); color: #cbd5e1; font-size: 12px; }
.compare-grid pre { max-height: 58vh; overflow: auto; margin: 0; padding: 12px; color: #cbd5e1; font: inherit; font-size: 12px; line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }
.preview-footer { display: flex; justify-content: flex-end; gap: 8px; }
@media (max-width: 900px) { .first-difference, .compare-grid { grid-template-columns: 1fr; } .dialogue-messages { max-height: 32vh; } }
</style>
