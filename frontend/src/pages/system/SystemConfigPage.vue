<template>
  <div class="page page-wide system-config-page">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title"><span class="title-icon">🔧</span>系统配置</h1>
        <p class="page-subtitle">维护应用默认值与全局运行参数，变更会立即写入系统配置。</p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ configs.length }}</span>
            <span class="stat-label">配置项</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num success">{{ categoryOptions.length }}</span>
            <span class="stat-label">配置分类</span>
          </div>
        </div>
        <n-button :loading="loading" @click="load">刷新</n-button>
        <n-button type="primary" @click="openCreate">
          <template #icon>＋</template>
          新增配置
        </n-button>
      </div>
    </div>

    <div class="config-toolbar">
      <n-input v-model:value="searchText" clearable placeholder="搜索配置名称、键名或说明" class="config-search">
        <template #prefix>🔎</template>
      </n-input>
      <n-select
        v-model:value="categoryFilter"
        :options="categoryOptions"
        clearable
        placeholder="全部分类"
        class="category-filter"
      />
      <span class="result-count">显示 {{ filteredConfigs.length }} / {{ configs.length }} 项</span>
    </div>

    <div v-if="loading && configs.length === 0" class="config-state">
      <n-spin size="medium" />
      <span>正在读取系统配置…</span>
    </div>
    <div v-else-if="loadFailed && configs.length === 0" class="config-state">
      <div class="empty-icon">⚠️</div>
      <strong>配置加载失败</strong>
      <span>请检查服务状态后重试。</span>
      <n-button @click="load">重新加载</n-button>
    </div>
    <div v-else-if="configs.length === 0" class="config-state">
      <div class="empty-icon">🔧</div>
      <strong>暂无配置项</strong>
      <span>创建第一条配置，集中维护系统默认值。</span>
      <n-button type="primary" @click="openCreate">新增配置</n-button>
    </div>
    <div v-else-if="filteredConfigs.length === 0" class="config-state compact">
      <strong>没有匹配的配置</strong>
      <span>换一个关键词或清除分类筛选后再试。</span>
    </div>
    <div v-else class="config-groups">
      <section v-for="group in groupedConfigs" :key="group.name" class="config-group">
        <header class="group-header">
          <div class="group-heading">
            <span class="group-mark"></span>
            <h2>{{ group.name }}</h2>
            <span class="group-count">{{ group.items.length }}</span>
          </div>
          <span class="group-description">{{ categoryDescriptions[group.name] || '其他系统参数' }}</span>
        </header>
        <div class="config-grid">
          <article v-for="cfg in group.items" :key="cfg.id" class="config-card">
            <div class="card-head">
              <div class="card-title" :title="cfg.config_name || cfg.config_key">
                <span class="card-icon">⚙️</span>
                <span>{{ cfg.config_name || cfg.config_key }}</span>
              </div>
              <n-button size="small" text type="primary" @click="openEdit(cfg)">编辑</n-button>
            </div>
            <div class="card-key">{{ cfg.config_key }}</div>
            <div class="card-value-wrap">
              <div
                class="card-value"
                :class="{ expanded: expandedKeys.has(cfg.config_key) }"
                :title="isSensitive(cfg.config_key) && !revealedKeys.has(cfg.config_key) ? '敏感配置已隐藏' : cfg.config_value"
              >{{ displayValue(cfg) }}</div>
              <div class="value-actions">
                <n-button v-if="isSensitive(cfg.config_key)" size="tiny" text @click="toggleReveal(cfg.config_key)">
                  {{ revealedKeys.has(cfg.config_key) ? '隐藏' : '显示' }}
                </n-button>
                <n-button v-if="isLongValue(cfg)" size="tiny" text @click="toggleExpand(cfg.config_key)">
                  {{ expandedKeys.has(cfg.config_key) ? '收起' : '展开' }}
                </n-button>
              </div>
            </div>
            <div v-if="cfg.description" class="card-desc">{{ cfg.description }}</div>
            <div class="card-meta">更新于 {{ formatTime(cfg.updated_at) }}</div>
          </article>
        </div>
      </section>
    </div>

    <n-modal v-model:show="showModal" preset="card" :title="isEdit ? '编辑配置' : '新增配置'" style="width: min(540px, 92vw)">
      <p class="modal-caption">配置值保存后会立即生效，请确认键名和内容符合预期。</p>
      <n-form :model="form" label-placement="top">
        <n-form-item label="配置键名">
          <n-input v-model:value="form.config_key" placeholder="如: site_name" :disabled="isEdit" maxlength="128" />
        </n-form-item>
        <n-form-item label="配置名称">
          <n-input v-model:value="form.config_name" placeholder="如: 站点名称" maxlength="128" />
        </n-form-item>
        <n-form-item label="配置值">
          <n-input
            v-model:value="form.config_value"
            :type="isSensitive(form.config_key) ? 'password' : 'textarea'"
            :show-password-on="isSensitive(form.config_key) ? 'click' : undefined"
            :rows="4"
            placeholder="请输入配置内容；允许留空以清除当前值"
          />
        </n-form-item>
        <n-form-item label="说明">
          <n-input v-model:value="form.description" type="textarea" :rows="2" placeholder="用途或生效范围（可选）" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="modal-actions">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSave">{{ isEdit ? '保存修改' : '创建配置' }}</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { fetchConfigs, updateConfig, type SysConfig } from '@/api/core'

const message = useMessage()
const loading = ref(false)
const loadFailed = ref(false)
const saving = ref(false)
const configs = ref<SysConfig[]>([])
const searchText = ref('')
const categoryFilter = ref<string | null>(null)
const revealedKeys = ref(new Set<string>())
const expandedKeys = ref(new Set<string>())

const showModal = ref(false)
const isEdit = ref(false)
const editKey = ref('')
const form = reactive({
  config_key: '',
  config_value: '',
  config_name: '',
  description: '',
})

const categoryDescriptions: Record<string, string> = {
  基础设置: '应用名称与通用显示信息',
  项目默认值: '创建项目和章节时使用的默认参数',
  编辑器: '写作编辑器行为与自动保存参数',
  模型服务: '模型接入与服务运行参数',
  其他配置: '尚未归类的系统参数',
}

const categorizedConfigs = computed(() => configs.value.map((config) => ({
  config,
  category: categoryFor(config.config_key),
})))
const categoryOptions = computed(() => {
  const categories = [...new Set(categorizedConfigs.value.map((item) => item.category))]
  return categories.map((name) => ({ label: name, value: name }))
})
const filteredConfigs = computed(() => {
  const keyword = searchText.value.trim().toLocaleLowerCase('zh-CN')
  return categorizedConfigs.value
    .filter(({ category }) => !categoryFilter.value || category === categoryFilter.value)
    .filter(({ config }) => !keyword || [config.config_name, config.config_key, config.description]
      .some((value) => String(value || '').toLocaleLowerCase('zh-CN').includes(keyword)))
    .map(({ config }) => config)
})
const groupedConfigs = computed(() => {
  const groups = new Map<string, SysConfig[]>()
  for (const config of filteredConfigs.value) {
    const category = categoryFor(config.config_key)
    if (!groups.has(category)) groups.set(category, [])
    groups.get(category)?.push(config)
  }
  const order = ['基础设置', '项目默认值', '编辑器', '模型服务', '其他配置']
  return [...groups.entries()]
    .sort(([left], [right]) => order.indexOf(left) - order.indexOf(right))
    .map(([name, items]) => ({ name, items }))
})

async function load() {
  // 步骤 1：拉取完整配置并保留当前搜索/分类条件。
  loading.value = true
  loadFailed.value = false
  try {
    configs.value = await fetchConfigs()
  } catch (e: any) {
    loadFailed.value = true
    message.error(e?.response?.data?.detail || '系统配置加载失败')
  } finally {
    loading.value = false
  }
}

function categoryFor(key: string): string {
  // 步骤 1：按配置键前缀归类，未知键保留在“其他配置”中。
  const normalized = key.toLocaleLowerCase('en-US')
  if (/^(site|app|ui)_/.test(normalized)) return '基础设置'
  if (/^default_/.test(normalized)) return '项目默认值'
  if (/(^auto_save|^editor_)/.test(normalized)) return '编辑器'
  if (/(model|llm|api|provider|token|secret|credential)/.test(normalized)) return '模型服务'
  return '其他配置'
}

function isSensitive(key: string): boolean {
  // 步骤 1：识别常见凭据键，卡片默认隐藏原始值。
  return /(password|secret|token|api[_-]?key|credential|private[_-]?key)/i.test(key)
}

function displayValue(config: SysConfig): string {
  // 步骤 1：对敏感值默认打码，只有用户主动点击“显示”才展示明文。
  if (isSensitive(config.config_key) && !revealedKeys.value.has(config.config_key)) return '••••••••'
  return config.config_value || '（空值）'
}

function isLongValue(config: SysConfig): boolean {
  return !isSensitive(config.config_key) && (config.config_value || '').length > 160
}

function toggleReveal(key: string) {
  // 步骤 1：复制 Set 后更新，确保 Vue 能检测集合变化。
  const next = new Set(revealedKeys.value)
  next.has(key) ? next.delete(key) : next.add(key)
  revealedKeys.value = next
}

function toggleExpand(key: string) {
  // 步骤 1：只切换当前配置项的长文本展示状态。
  const next = new Set(expandedKeys.value)
  next.has(key) ? next.delete(key) : next.add(key)
  expandedKeys.value = next
}

function openCreate() {
  // 步骤 1：重置编辑态和表单，避免沿用上次打开的内容。
  isEdit.value = false
  editKey.value = ''
  Object.assign(form, { config_key: '', config_value: '', config_name: '', description: '' })
  showModal.value = true
}

function openEdit(config: SysConfig) {
  // 步骤 1：保留键名作为更新定位键，并装载现有配置值。
  isEdit.value = true
  editKey.value = config.config_key
  Object.assign(form, {
    config_key: config.config_key,
    config_value: config.config_value,
    config_name: config.config_name,
    description: config.description,
  })
  showModal.value = true
}

async function handleSave() {
  // 步骤 1：校验键名格式，兼容系统配置键的常见命名约定。
  const key = form.config_key.trim()
  if (!/^[a-zA-Z][a-zA-Z0-9_.-]{0,127}$/.test(key)) {
    message.warning('键名需以字母开头，只能包含字母、数字、下划线、点和短横线')
    return
  }
  if (!form.config_name.trim()) {
    message.warning('请输入配置名称')
    return
  }

  // 步骤 2：调用统一的新增/更新接口并等待列表同步完成。
  saving.value = true
  try {
    await updateConfig(isEdit.value ? editKey.value : key, {
      config_value: form.config_value,
      config_name: form.config_name.trim(),
      description: form.description.trim(),
    })
    message.success(isEdit.value ? '配置已更新' : '配置已创建')
    showModal.value = false
    await load()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '配置保存失败')
  } finally {
    saving.value = false
  }
}

function formatTime(value: string): string {
  // 步骤 1：优先按本地时间格式化，遇到无法解析的数据则保留原文。
  if (!value) return '暂无记录'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value.replace('T', ' ').substring(0, 16)
    : date.toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })
}

onMounted(load)
</script>

<style scoped>
.system-config-page {
  padding: 24px 28px 40px;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 0;
  color: var(--n-text-color-1, #f3f4f6);
  font-size: 22px;
  font-weight: 700;
}

.page-subtitle {
  margin: 7px 0 0;
  color: var(--n-text-color-3, #8490a3);
  font-size: 13px;
}

.header-right,
.header-stats {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-stats {
  gap: 0;
  padding: 7px 10px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
}

.stat {
  display: flex;
  min-width: 76px;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-num {
  color: var(--n-primary-color, #60a5fa);
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}

.stat-num.success {
  color: #34d399;
}

.stat-label {
  color: var(--n-text-color-3, #8490a3);
  font-size: 11px;
  white-space: nowrap;
}

.stat-divider {
  width: 1px;
  height: 28px;
  margin: 0 8px;
  background: var(--n-border-color, #2a2f3a);
}

.config-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 18px;
  padding: 12px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
}

.config-search {
  width: min(420px, 52vw);
}

.category-filter {
  width: 190px;
}

.result-count {
  margin-left: auto;
  color: var(--n-text-color-3, #8490a3);
  font-size: 12px;
  white-space: nowrap;
}

.config-groups {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.config-group {
  min-width: 0;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.group-heading {
  display: flex;
  align-items: center;
  gap: 9px;
}

.group-mark {
  width: 3px;
  height: 18px;
  border-radius: 2px;
  background: var(--n-primary-color, #3b82f6);
}

.group-heading h2 {
  margin: 0;
  color: var(--n-text-color-1, #e5e7eb);
  font-size: 15px;
  font-weight: 650;
}

.group-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 23px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--n-color, #23272f);
  color: var(--n-text-color-3, #8490a3);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.group-description {
  color: var(--n-text-color-3, #8490a3);
  font-size: 12px;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 330px), 1fr));
  gap: 12px;
}

.config-card {
  display: flex;
  min-width: 0;
  min-height: 188px;
  flex-direction: column;
  padding: 16px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 11px;
  transition: border-color 0.18s ease, transform 0.18s ease;
}

.config-card:hover {
  transform: translateY(-1px);
  border-color: rgba(59, 130, 246, 0.55);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.card-title {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
  color: var(--n-text-color-1, #f3f4f6);
  font-size: 14px;
  font-weight: 600;
}

.card-title span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-icon {
  flex: 0 0 auto;
  font-size: 16px;
}

.card-key {
  margin: 5px 0 10px 24px;
  color: var(--n-text-color-3, #8490a3);
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 11px;
  overflow-wrap: anywhere;
}

.card-value-wrap {
  position: relative;
  min-width: 0;
  padding: 10px 11px;
  background: var(--n-color, #151719);
  border: 1px solid var(--n-border-color, #292e37);
  border-radius: 7px;
}

.card-value {
  max-height: 4.8em;
  overflow: hidden;
  color: var(--n-text-color-2, #c7cbd1);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.card-value.expanded {
  max-height: none;
}

.value-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  min-height: 16px;
  margin-top: 4px;
}

.card-desc {
  margin-top: 9px;
  color: var(--n-text-color-3, #8490a3);
  font-size: 12px;
  line-height: 1.5;
}

.card-meta {
  margin-top: auto;
  padding-top: 12px;
  color: var(--n-text-color-3, #6b7280);
  font-size: 11px;
}

.config-state {
  display: flex;
  min-height: 320px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--n-text-color-3, #8490a3);
  text-align: center;
  background: var(--n-color-card, #1a1d21);
  border: 1px dashed var(--n-border-color, #2a2f3a);
  border-radius: 12px;
}

.config-state strong {
  color: var(--n-text-color-1, #e5e7eb);
  font-size: 15px;
}

.config-state span {
  font-size: 12px;
}

.config-state.compact {
  min-height: 220px;
}

.empty-icon {
  font-size: 38px;
}

.modal-caption {
  margin: 0 0 16px;
  color: var(--n-text-color-3, #8490a3);
  font-size: 12px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 900px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .header-right {
    width: 100%;
    flex-wrap: wrap;
  }

  .config-toolbar {
    flex-wrap: wrap;
  }

  .config-search {
    width: 100%;
  }

  .result-count {
    width: 100%;
    margin: 2px 0 0;
  }
}

@media (max-width: 600px) {
  .system-config-page {
    padding: 18px 14px 28px;
  }

  .header-stats {
    width: 100%;
    justify-content: space-around;
  }

  .category-filter {
    flex: 1;
    min-width: 145px;
  }

  .group-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 5px;
  }
}
</style>
