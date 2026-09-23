<script setup lang="ts">
import { computed } from 'vue'

export interface StepInfo {
  id: string
  label: string
  icon: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  durationMs?: number
  errorMessage?: string
  canRestart?: boolean  // 是否可以从该步骤重跑
}

const props = defineProps<{
  steps: StepInfo[]
  currentStepId?: string | null
  overallProgress?: number
}>()

const emit = defineEmits<{
  (e: 'restart', stepId: string): void
}>()

const statusIcon = (status: string) => {
  switch (status) {
    case 'completed': return '✓'
    case 'running': return '▶'
    case 'failed': return '✕'
    case 'skipped': return '⊘'
    default: return '○'
  }
}

const statusClass = (status: string) => {
  return `step-${status}`
}

const formatDuration = (ms?: number) => {
  if (!ms) return ''
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}m${secs.toString().padStart(2, '0')}s`
}

function handleRestart(stepId: string) {
  emit('restart', stepId)
}
</script>

<template>
  <div class="workflow-progress">
    <!-- 总进度条 -->
    <div v-if="overallProgress !== undefined" class="overall-bar">
      <div class="bar-fill" :style="{ width: `${Math.min(100, overallProgress)}%` }"></div>
    </div>

    <!-- 步骤列表 -->
    <div class="step-list">
      <div
        v-for="(step, index) in steps"
        :key="step.id"
        :class="['step-item', statusClass(step.status)]"
      >
        <!-- 连接线 -->
        <div v-if="index < steps.length - 1" class="step-connector">
          <div class="connector-line" :class="{ filled: step.status === 'completed' }"></div>
        </div>

        <!-- 步骤图标 -->
        <div class="step-icon-wrapper">
          <div class="step-icon">{{ step.status === 'running' ? step.icon : statusIcon(step.status) }}</div>
          <div v-if="step.status === 'running'" class="step-pulse"></div>
        </div>

        <!-- 步骤信息 -->
        <div class="step-info">
          <div class="step-label">{{ step.label }}</div>
          <div class="step-meta">
            <span v-if="step.durationMs" class="step-duration">
              {{ formatDuration(step.durationMs) }}
            </span>
            <span v-if="step.status === 'failed' && step.errorMessage" class="step-error">
              {{ step.errorMessage }}
            </span>
          </div>
          <div v-if="step.status === 'completed' && step.canRestart !== false" class="step-restart">
            <button class="restart-btn" @click.stop="handleRestart(step.id)" title="从该步骤重跑">
              🔄 从这里重跑
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.workflow-progress {
  width: 100%;
}

.overall-bar {
  height: 4px;
  background: var(--n-border-color, #e0e0e0);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 20px;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.step-list {
  position: relative;
}

.step-item {
  display: flex;
  align-items: flex-start;
  position: relative;
  padding-bottom: 24px;
}

.step-item:last-child {
  padding-bottom: 0;
}

.step-connector {
  position: absolute;
  left: 18px;
  top: 40px;
  bottom: 0;
  width: 2px;
}

.connector-line {
  width: 100%;
  height: 100%;
  background: var(--n-border-color, #e0e0e0);
  transition: background 0.3s;
}

.connector-line.filled {
  background: linear-gradient(180deg, #6366f1, #8b5cf6);
}

.step-icon-wrapper {
  position: relative;
  z-index: 1;
  margin-right: 16px;
}

.step-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  background: var(--n-color, #fff);
  border: 2px solid var(--n-border-color, #e0e0e0);
  color: var(--n-text-color-3, #999);
  transition: all 0.3s ease;
}

.step-pulse {
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  border-radius: 50%;
  border: 2px solid #6366f1;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0; transform: scale(1.3); }
}

.step-pending .step-icon {
  border-color: var(--n-border-color, #e0e0e0);
  color: var(--n-text-color-3, #ccc);
}

.step-running .step-icon {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-color: #6366f1;
  color: #fff;
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15);
}

.step-completed .step-icon {
  background: #10b981;
  border-color: #10b981;
  color: #fff;
}

.step-failed .step-icon {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
}

.step-skipped .step-icon {
  background: #6b7280;
  border-color: #6b7280;
  color: #fff;
  opacity: 0.6;
}

.step-info {
  flex: 1;
  padding-top: 6px;
}

.step-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--n-text-color, #333);
  margin-bottom: 4px;
}

.step-pending .step-label {
  color: var(--n-text-color-3, #999);
}

.step-meta {
  font-size: 12px;
  color: var(--n-text-color-2, #666);
}

.step-duration {
  color: var(--n-text-color-3, #999);
}

.step-error {
  color: #ef4444;
  font-size: 11px;
}

.step-restart {
  margin-top: 6px;
}

.restart-btn {
  font-size: 11px;
  padding: 3px 10px;
  border: 1px solid var(--n-primary-color, #6366f1);
  color: var(--n-primary-color, #6366f1);
  background: transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.restart-btn:hover {
  background: var(--n-primary-color, #6366f1);
  color: #fff;
}
</style>
