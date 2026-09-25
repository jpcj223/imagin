<template>
  <div class="page config-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">⚙️</span>
          项目配置
          <span v-if="isDirty" class="dirty-dot" title="有未保存的修改">●</span>
        </h1>
        <p class="page-subtitle">
          管理项目基础信息、写作风格和全局参数
        </p>
        <!-- 项目切换器 -->
        <n-select
          :value="currentProjectId"
          :options="projectOptions"
          class="project-switcher"
          @update:value="onSwitchProject"
        />
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ projectStore.projects.length }}</span>
            <span class="stat-label">项目总数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ form.target_words }}</span>
            <span class="stat-label">目标字数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">Lv.{{ form.pace_level }}</span>
            <span class="stat-label">节奏等级</span>
          </div>
        </div>
        <n-button @click="openNewProject">
          <template #icon>＋</template>
          新建项目
        </n-button>
        <n-popconfirm
          v-if="projectStore.projects.length > 1"
          positive-text="确认删除"
          negative-text="取消"
          @positive-click="onDeleteCurrent"
        >
          <template #trigger>
            <n-button type="error" ghost :loading="deletingProject">删除项目</n-button>
          </template>
          <div class="delete-warn">
            <p>确定要删除「{{ form.name }}」吗？</p>
            <p class="warn-sub">此操作不可恢复，所有人物、组织、伏笔、章节等数据将被一并删除。</p>
          </div>
        </n-popconfirm>
        <n-button type="primary" :disabled="!canSave" :loading="saving" @click="save">保存配置</n-button>
      </div>
    </div>

    <n-form v-if="projectStore.currentProject" class="config-form" label-placement="top" :show-label="true">
      <div class="config-top-grid">
        <!-- 基本信息区 -->
        <div class="form-card">
          <div class="card-header-bar">
            <span class="card-icon">📖</span>
            <div>
              <span class="card-title">基本信息</span>
              <p class="card-caption">定义作品身份，供项目内各模块引用</p>
            </div>
          </div>
          <div class="card-body">
            <n-form-item label="书名（必填）">
              <n-input
                v-model:value="form.name"
                placeholder="给你的小说起个名字"
                :clearable="false"
                maxlength="50"
                show-count
                size="large"
              />
            </n-form-item>

            <div class="form-grid-2">
              <n-form-item label="主题">
                <n-input
                  v-model:value="form.theme"
                  placeholder="例如：成长、复仇、群像、救赎"
                  maxlength="30"
                  show-count
                />
              </n-form-item>
              <n-form-item label="小说类型">
                <n-select
                  v-model:value="form.novel_type"
                  :options="novelTypeOptions"
                  filterable
                  allow-input
                  placeholder="选择或输入类型"
                />
              </n-form-item>
            </div>

            <div class="form-grid-2">
              <n-form-item label="叙事视角">
                <n-select
                  v-model:value="form.view_point"
                  :options="viewPointOptions"
                  allow-input
                  placeholder="选择叙事视角"
                />
              </n-form-item>
              <n-form-item label="文风基调">
                <n-select
                  v-model:value="form.writing_style"
                  :options="writingStyleOptions"
                  allow-input
                  placeholder="选择文风基调"
                />
              </n-form-item>
            </div>
          </div>
        </div>

        <!-- 目标与节奏 -->
        <div class="form-card">
          <div class="card-header-bar">
            <span class="card-icon">🎯</span>
            <div>
              <span class="card-title">目标与节奏</span>
              <p class="card-caption">控制章节篇幅和剧情推进速度</p>
            </div>
          </div>
          <div class="card-body">
            <n-form-item label="单章目标字数">
              <div class="target-words-row">
                <n-input-number
                  v-model:value="form.target_words"
                  :min="500"
                  :max="100000"
                  :step="500"
                  style="width: 160px"
                />
                <n-slider
                  v-model:value="form.target_words"
                  :min="500"
                  :max="100000"
                  :step="500"
                  class="target-words-slider"
                />
              </div>
              <div class="field-hint">可以直接输入精确字数，也可以拖动滑块调整。</div>
            </n-form-item>

            <n-form-item label="默认节奏等级">
              <div class="pace-level-row">
                <n-slider
                  v-model:value="form.pace_level"
                  :min="1"
                  :max="5"
                  :marks="paceMarks"
                  class="pace-slider"
                />
              </div>
              <div class="field-hint">
                全局默认节奏，单章生成时可单独覆盖。等级越高，情节推进越快、冲突密度越大。
              </div>
            </n-form-item>
          </div>
        </div>
      </div>

      <!-- 项目简介区 -->
      <div class="form-card">
        <div class="card-header-bar">
          <span class="card-icon">📝</span>
          <span class="card-title">
            故事概述
            <span class="word-count">{{ form.synopsis.length }} / 5000</span>
          </span>
        </div>
        <div class="card-body">
          <n-form-item label="故事概述">
            <n-input
              v-model:value="form.synopsis"
              type="textarea"
              :autosize="{ minRows: 10, maxRows: 20 }"
              placeholder="整体故事概述、核心冲突、主要人物弧光、结局走向..."
              maxlength="5000"
              show-count
            />
          </n-form-item>
        </div>
      </div>

      <!-- 元信息区 -->
      <div class="meta-card">
        <div class="meta-item">
          <span class="meta-label">创建时间</span>
          <span class="meta-value">{{ formatDate(form.created_at) }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">最后更新</span>
          <span class="meta-value">{{ formatDate(form.updated_at) }}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">项目 ID</span>
          <span class="meta-value">#{{ form.id }}</span>
        </div>
      </div>
    </n-form>
    <div v-else class="config-empty-state">
      <div class="empty-icon">📚</div>
      <strong>还没有创作项目</strong>
      <span>新建一个项目后，就可以在这里配置作品资料和写作目标。</span>
      <n-button type="primary" @click="openNewProject">新建项目</n-button>
    </div>

    <!-- 新建项目弹窗 -->
    <n-modal v-model:show="showNewModal" preset="card" title="新建项目" style="width: 480px">
      <n-form label-placement="top">
        <n-form-item label="项目名称">
          <n-input
            v-model:value="newProjectName"
            placeholder="给新项目起个名字"
            maxlength="50"
            show-count
            @keyup.enter="confirmCreate"
          />
        </n-form-item>
        <n-form-item label="小说类型（可选）">
          <n-select
            v-model:value="newProjectType"
            :options="novelTypeOptions"
            filterable
            allow-input
            placeholder="选择或输入类型"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-button @click="showNewModal = false">取消</n-button>
        <n-button type="primary" :disabled="!newProjectName.trim()" :loading="creatingProject" @click="confirmCreate">
          创建并切换
        </n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { updateProject } from '@/api/projects'
import { useProjectStore } from '@/stores/project'
import type { Project } from '@/types/domain'
import { useDirtySnapshot } from '@/composables/useDirtySnapshot'
import { notify } from '@/utils/notify'
import { useDictStore } from '@/stores/dict'

const message = useMessage()
const projectStore = useProjectStore()
const dictStore = useDictStore()

// ---- 多项目切换 ----

const showNewModal = ref(false)
const newProjectName = ref('')
const newProjectType = ref('')
const creatingProject = ref(false)
const deletingProject = ref(false)
const saving = ref(false)

const projectOptions = computed(() =>
  projectStore.projects.map((p) => ({ label: p.name, value: p.id }))
)

const currentProjectId = computed<number | null>(() => projectStore.currentProject?.id ?? null)

async function onSwitchProject(projectId: number) {
  if (!projectId || projectId === projectStore.currentProject?.id) return
  if (isDirty.value) {
    const ok = await confirmIfDirty('当前项目有未保存的修改，切换后将丢失，确定要离开吗？')
    if (!ok) return
  }
  await projectStore.switchTo(projectId)
  loadFormFromCurrent()
  markClean()
}

function openNewProject() {
  newProjectName.value = ''
  newProjectType.value = ''
  showNewModal.value = true
}

async function confirmCreate() {
  const name = newProjectName.value.trim()
  if (!name || creatingProject.value) return
  creatingProject.value = true
  try {
    const newProj = await projectStore.createNew(name, newProjectType.value.trim())
    if (newProj) {
      showNewModal.value = false
      loadFormFromCurrent()
      markClean()
      message.success('新项目已创建，可以开始配置了')
    }
  } finally {
    creatingProject.value = false
  }
}

async function onDeleteCurrent() {
  if (!projectStore.currentProject || deletingProject.value) return
  deletingProject.value = true
  try {
    const ok = await projectStore.remove(projectStore.currentProject.id)
    if (ok) {
      loadFormFromCurrent()
      markClean()
    }
  } finally {
    deletingProject.value = false
  }
}

function loadFormFromCurrent() {
  const p = projectStore.currentProject
  if (!p) return
  Object.assign(form, {
    id: p.id,
    name: p.name || '',
    theme: p.theme || '',
    novel_type: p.novel_type || '',
    target_words: p.target_words || 2500,
    synopsis: p.synopsis || '',
    pace_level: (p as any).pace_level ?? 3,
    view_point: (p as any).view_point || '',
    writing_style: (p as any).writing_style || '',
    created_at: (p as any).created_at || '',
    updated_at: (p as any).updated_at || '',
  })
}

// ---- 选项配置（从字典动态获取）----

const novelTypeOptions = computed(() => dictStore.options('novel_type'))
const viewPointOptions = computed(() => dictStore.options('view_point'))
const writingStyleOptions = computed(() => dictStore.options('writing_style'))

const paceMarks = {
  1: '慢热',
  2: '渐入',
  3: '适中',
  4: '紧凑',
  5: '高燃',
}

// ---- 表单状态 ----

const form = reactive<Project>({
  id: 0,
  name: '',
  theme: '',
  novel_type: '',
  target_words: 2500,
  synopsis: '',
  pace_level: 3,
  view_point: '',
  writing_style: '',
  created_at: '',
  updated_at: '',
})

// ---- 脏状态检测 ----
const { isDirty, markClean, confirmIfDirty } = useDirtySnapshot(form)

const canSave = computed(() => form.name.trim().length > 0 && isDirty.value)

// ---- 工具函数 ----

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

// ---- 保存 ----

async function save() {
  if (!form.name.trim() || saving.value) {
    if (!form.name.trim()) notify.warning('请填写书名')
    return
  }
  saving.value = true
  try {
    await updateProject(form.id, {
      name: form.name.trim(),
      theme: form.theme.trim(),
      novel_type: form.novel_type,
      target_words: form.target_words,
      synopsis: form.synopsis,
      pace_level: form.pace_level,
      view_point: form.view_point,
      writing_style: form.writing_style,
    })
    await projectStore.refreshCurrent()
    markClean()
    message.success('项目配置已保存')
  } catch {
    notify.error('保存失败')
  } finally {
    saving.value = false
  }
}

// ---- 初始化 ----

onMounted(async () => {
  await dictStore.loadBatch(['novel_type', 'view_point', 'writing_style'])
  await projectStore.loadProjects()
  if (projectStore.currentProject) {
    loadFormFromCurrent()
    markClean()
  }
})
</script>

<style scoped>
.config-page {
  padding-bottom: 40px;
}

/* ===== 页头 ===== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 18px 20px;
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 14px;
  background: linear-gradient(115deg, rgba(30, 64, 120, 0.38), rgba(49, 46, 129, 0.22) 55%, rgba(19, 24, 34, 0.85));
  gap: 20px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
}

.title-icon {
  font-size: 18px;
  margin-right: -2px;
}

.page-subtitle {
  font-size: 13px;
  color: var(--n-text-color-3, #6b7280);
  margin: 0;
}

.project-switcher {
  width: min(320px, 100%);
  margin-top: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.header-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  background: rgba(15, 23, 42, 0.38);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 10px;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 56px;
}

.stat-num {
  font-size: 15px;
  font-weight: 700;
  color: var(--n-color-primary, #3b82f6);
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 3px;
}

.stat-divider {
  width: 1px;
  height: 24px;
  background: var(--n-border-color, #2a2f3a);
}

.dirty-dot {
  color: #f59e0b;
  font-size: 12px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ===== 表单卡片 ===== */
.config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-top-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-items: stretch;
}

.form-card {
  min-width: 0;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 12px;
  overflow: hidden;
}

.card-header-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  background: var(--n-color-1, #1e2228);
}

.card-icon {
  font-size: 18px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
}

.card-caption {
  margin: 3px 0 0;
  color: var(--n-text-color-3, #6b7280);
  font-size: 11px;
}

.word-count {
  font-size: 12px;
  font-weight: 400;
  color: var(--n-text-color-3, #6b7280);
}

.card-body {
  padding: 18px;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

/* ===== 目标字数 ===== */
.target-words-row {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.target-words-slider {
  flex: 1;
  min-width: 80px;
}

/* ===== 节奏等级 ===== */
.pace-level-row {
  padding: 8px 4px 0;
}

.pace-slider {
  margin-top: 4px;
}

.field-hint {
  font-size: 12px;
  color: var(--n-text-color-3, #64748b);
  margin-top: 8px;
  line-height: 1.6;
}

/* ===== 元信息卡片 ===== */
.meta-card {
  display: flex;
  gap: 32px;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.06), rgba(168, 85, 247, 0.04));
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 10px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 11px;
  color: var(--n-text-color-3, #64748b);
}

.meta-value {
  font-size: 13px;
  color: var(--n-text-color-2, #cbd5e1);
  font-family: 'JetBrains Mono', monospace;
}

.config-empty-state {
  display: flex;
  min-height: 320px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  text-align: center;
  color: var(--n-text-color-2, #cbd5e1);
  background: var(--n-color-card, #1a1d21);
  border: 1px dashed var(--n-border-color, #2a2f3a);
  border-radius: 14px;
}

.config-empty-state span {
  max-width: 420px;
  color: var(--n-text-color-3, #6b7280);
  font-size: 13px;
  line-height: 1.6;
}

.empty-icon {
  font-size: 38px;
}

/* ===== 删除确认弹窗 ===== */
.delete-warn p {
  margin: 0 0 6px;
  font-size: 13px;
}

.delete-warn .warn-sub {
  font-size: 12px;
  color: #f59e0b;
  line-height: 1.5;
}

/* ===== 响应式 ===== */
@media (max-width: 1180px) {
  .config-top-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-right {
    justify-content: flex-start;
  }

  .form-grid-2 {
    grid-template-columns: 1fr;
  }

  .project-switcher {
    width: 100%;
  }
}
</style>
