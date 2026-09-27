<template>
  <div class="tab-content">
    <div class="prefs-header">
      <span class="block-title">写作偏好记忆</span>
      <n-button size="tiny" :loading="loading" @click="emit('refresh')">刷新</n-button>
    </div>
    <div class="prefs-desc">
      Agent 会记住你的偏好，下次生成时自动应用，无需重复设置。
    </div>

    <n-form label-placement="top" :show-label="true" class="prefs-form">
      <n-form-item label="默认生成模式">
        <n-select
          :value="preferences.default_template"
          :options="templateOptions"
          @update:value="update('default_template', $event)"
        />
      </n-form-item>
      <n-form-item label="默认写作风格">
        <n-select
          :value="preferences.default_writer_variant"
          :options="writerVariantOptions"
          @update:value="update('default_writer_variant', $event)"
        />
      </n-form-item>
      <n-form-item label="模型创造性">
        <n-slider
          :value="preferences.default_temperature"
          :min="0"
          :max="200"
          :step="10"
          @update:value="update('default_temperature', $event)"
        />
        <div class="slider-labels">
          <span>严谨</span>
          <span>{{ (preferences.default_temperature / 100).toFixed(1) }}</span>
          <span>创意</span>
        </div>
      </n-form-item>
      <n-form-item label="目标字数">
        <n-input-number
          :value="preferences.default_target_word_count"
          :min="500"
          :max="10000"
          :step="500"
          style="width: 100%"
          @update:value="update('default_target_word_count', $event)"
        />
      </n-form-item>
      <n-form-item label="自动沉淀等级">
        <n-select
          :value="preferences.auto_sync_level"
          :options="autoSyncOptions"
          @update:value="update('auto_sync_level', $event)"
        />
      </n-form-item>
    </n-form>

    <div class="prefs-actions">
      <n-button type="primary" block :loading="saving" @click="emit('save')">
        保存本项目写作偏好
      </n-button>
    </div>

    <div class="editor-preference">
      <div class="block-title">个人编辑器设置</div>
      <p>字号作用于你的所有项目，不会改变项目写作偏好。</p>
      <n-input-number
        :value="preferences.editor_font_size"
        :min="12"
        :max="24"
        style="width: 100%"
        @update:value="update('editor_font_size', $event)"
      />
      <n-button block :loading="editorSaving" @click="emit('save-editor')">保存个人字号</n-button>
    </div>

    <div class="prefs-stats">
      <div class="prefs-stat-card">
        <span class="stat-num">{{ preferences.total_generations ?? 0 }}</span>
        <span class="stat-label">累计生成</span>
      </div>
      <div class="prefs-stat-card">
        <span class="stat-num">{{ formatWordCount(preferences.total_words_generated) }}</span>
        <span class="stat-label">累计字数</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface PreferenceSettings {
  default_template: string
  default_writer_variant: string
  default_temperature: number
  default_target_word_count: number
  auto_sync_level: string
  editor_font_size: number
  total_generations?: number
  total_words_generated?: number
}

const props = defineProps<{
  preferences: PreferenceSettings
  templateOptions: Array<{ label: string; value: string }>
  writerVariantOptions: Array<{ label: string; value: string }>
  autoSyncOptions: Array<{ label: string; value: string }>
  loading: boolean
  saving: boolean
  editorSaving: boolean
}>()

const emit = defineEmits<{
  'update:preferences': [value: PreferenceSettings]
  refresh: []
  save: []
  'save-editor': []
}>()

// 通过整份设置的更新事件回传，保持偏好面板和页面状态之间的单向数据流。
function update<K extends keyof PreferenceSettings>(key: K, value: PreferenceSettings[K] | null) {
  if (value === null) return
  emit('update:preferences', { ...props.preferences, [key]: value })
}

function formatWordCount(count?: number): string {
  if (!count) return '0'
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`
  return String(count)
}
</script>

<style scoped>
.tab-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 14px 16px;
}

.block-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-primary, #e5e7eb);
  font-size: 12px;
  font-weight: 600;
}

.prefs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: -8px;
}

.prefs-desc {
  padding: 8px 12px;
  border-left: 3px solid var(--n-primary-color, #6366f1);
  border-radius: 8px;
  background: var(--n-color-info, #eef2ff);
  color: var(--n-text-color-2, #9ca3af);
  font-size: 12px;
}

.prefs-form {
  margin-bottom: -8px;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: -4px;
  color: var(--n-text-color-3, #9ca3af);
  font-size: 11px;
}

.prefs-actions {
  margin-bottom: 4px;
}

.editor-preference {
  display: grid;
  gap: 9px;
  margin: 4px 0;
  padding: 12px;
  border: 1px solid var(--n-border-color, rgba(148, 163, 184, 0.2));
  border-radius: 9px;
  background: rgba(148, 163, 184, 0.04);
}

.editor-preference p {
  margin: 0;
  color: var(--n-text-color-3, #7b8494);
  font-size: 12px;
  line-height: 1.5;
}

.prefs-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.prefs-stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14px 8px;
  border: 1px solid var(--n-border-color, #e0e7ff);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(148, 163, 184, 0.04));
}

.stat-num {
  margin-bottom: 4px;
  color: var(--n-primary-color, #818cf8);
  font-size: 20px;
  font-weight: 700;
}

.stat-label {
  color: var(--n-text-color-2, #9ca3af);
  font-size: 11px;
}
</style>
