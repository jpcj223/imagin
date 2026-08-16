<template>
  <div class="page page-wide api-config-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">🔌</span>
          API 配置
        </h1>
        <p class="page-subtitle">
          管理 AI 模型连接，配置创作辅助参数
        </p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ configs.length }}</span>
            <span class="stat-label">配置总数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num success">{{ activeCount }}</span>
            <span class="stat-label">当前启用</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ servicePresets.length }}</span>
            <span class="stat-label">服务预设</span>
          </div>
        </div>
        <n-button @click="testConnection" :loading="testing">
          <template #icon>🧪</template>
          测试连接
        </n-button>
      </div>
    </div>

    <!-- 主体：左侧配置列表 + 右侧编辑表单 -->
    <div class="workbench">
      <!-- 左侧：配置列表 -->
      <div class="list-panel">
        <div class="panel-head">
          <h2>配置列表</h2>
          <n-button size="small" type="primary" @click="createNew">
            <template #icon>＋</template>
            新建
          </n-button>
        </div>
        <n-scrollbar class="list-scroll">
          <div v-if="configs.length === 0" class="list-empty">
            <div class="empty-icon">🔧</div>
            <p>暂无配置</p>
            <p class="empty-sub">点击右上角「新建」添加</p>
          </div>
          <div class="config-list">
            <div
              v-for="cfg in configs"
              :key="cfg.id"
              class="config-item"
              :class="{ active: selectedId === cfg.id, 'is-active': cfg.is_active === 1 }"
              @click="selectConfig(cfg)"
            >
              <div class="item-main">
                <div class="item-name">
                  <span v-if="cfg.is_active === 1" class="active-badge" title="当前启用">●</span>
                  {{ cfg.name }}
                </div>
                <div class="item-sub">{{ cfg.model }}</div>
              </div>
              <n-dropdown
                @select="(key: string) => onItemAction(key, cfg)"
                :options="itemMenuOptions(cfg)"
                trigger="click"
              >
                <n-button size="tiny" text @click.stop>⋯</n-button>
              </n-dropdown>
            </div>
          </div>
        </n-scrollbar>
      </div>

      <!-- 右侧：编辑表单 -->
      <div class="detail-panel">
        <div v-if="!selectedId && !isNewMode" class="detail-empty">
          <div class="empty-icon">📝</div>
          <p>从左侧选择一个配置进行编辑</p>
          <p class="empty-sub">或点击左上角新建</p>
        </div>

        <n-scrollbar v-else class="form-scroll">
          <!-- 顶部操作栏 -->
          <div class="form-toolbar">
            <div class="form-title">
              {{ isEditing ? '编辑配置' : '新建配置' }}
              <n-tag v-if="form.is_active" type="success" size="small">
                当前启用
              </n-tag>
            </div>
            <div class="form-actions">
              <n-button
                v-if="isEditing && !form.is_active"
                @click="setActive"
                :loading="activating"
              >
                设为启用
              </n-button>
              <n-button type="primary" @click="save" :loading="saving" :disabled="!canSave">
                💾 保存配置
              </n-button>
            </div>
          </div>

          <!-- 服务预设快捷应用 -->
          <div class="preset-card">
            <div class="preset-header">
              <span class="preset-icon">⚡</span>
              <span class="preset-title">快速应用服务预设</span>
            </div>
            <div class="preset-buttons">
              <n-button
                v-for="preset in servicePresets"
                :key="preset.name"
                size="small"
                secondary
                @click="applyPreset(preset)"
              >
                {{ preset.name }}
              </n-button>
            </div>
            <p class="preset-hint">
              预设仅填入地址和推荐模型，API Key 需要你手动粘贴。
            </p>
          </div>

          <n-form class="config-form" label-placement="top" :show-label="true">
            <!-- 基本信息 -->
            <div class="form-section">
              <div class="section-title">
                基本信息
                <span class="section-hint">连接配置的核心参数</span>
              </div>
              <n-form-item label="配置名称">
                <n-input
                  v-model:value="form.name"
                  placeholder="例如：硅基流动 DeepSeek V4 Pro"
                  maxlength="50"
                  size="large"
                />
              </n-form-item>
              <n-form-item label="API 地址">
                <n-input
                  v-model:value="form.base_url"
                  placeholder="https://api.siliconflow.cn/v1"
                />
              </n-form-item>
              <n-alert
                v-if="isAnthropicUrl"
                class="compat-alert"
                type="warning"
                :bordered="false"
              >
                检测到 Anthropic 地址。当前后端调用 /chat/completions，请改用 OpenAI-compatible 地址。
              </n-alert>
              <n-form-item label="API Key">
                <n-input
                  v-model:value="form.api_key"
                  type="password"
                  show-password-on="click"
                  placeholder="sk-..."
                />
              </n-form-item>
              <n-form-item label="模型名称">
                <n-input
                  v-model:value="form.model"
                  placeholder="例如：deepseek-ai/DeepSeek-V4-Pro"
                />
              </n-form-item>
            </div>

            <!-- 模型参数 -->
            <div class="form-section">
              <div class="section-title">
                模型参数
                <span class="section-hint">调整生成效果的精细控制</span>
              </div>
              <div class="param-grid">
                <n-form-item label="采样温度 (temperature)">
                  <div class="slider-row">
                    <n-slider
                      v-model:value="form.temperature"
                      :min="0"
                      :max="2"
                      :step="0.1"
                      class="param-slider"
                    />
                    <n-input-number
                      v-model:value="form.temperature"
                      :min="0"
                      :max="2"
                      :step="0.1"
                      style="width: 80px"
                    />
                  </div>
                  <div class="field-hint">0=确定，0.7=均衡，2=极具创意</div>
                </n-form-item>
                <n-form-item label="最大输出 Token">
                  <n-input-number
                    v-model:value="form.max_tokens"
                    :min="128"
                    :max="32000"
                    :step="128"
                    placeholder="模型默认"
                    style="width: 100%"
                  />
                  <div class="field-hint">留空使用模型默认值</div>
                </n-form-item>
                <n-form-item label="Top P (核采样)">
                  <div class="slider-row">
                    <n-slider
                      v-model:value="form.top_p"
                      :min="0"
                      :max="1"
                      :step="0.05"
                      class="param-slider"
                    />
                    <n-input-number
                      v-model:value="form.top_p"
                      :min="0"
                      :max="1"
                      :step="0.05"
                      style="width: 80px"
                    />
                  </div>
                </n-form-item>
                <n-form-item label="频率惩罚">
                  <div class="slider-row">
                    <n-slider
                      v-model:value="form.frequency_penalty"
                      :min="-2"
                      :max="2"
                      :step="0.1"
                      class="param-slider"
                    />
                    <n-input-number
                      v-model:value="form.frequency_penalty"
                      :min="-2"
                      :max="2"
                      :step="0.1"
                      style="width: 80px"
                    />
                  </div>
                </n-form-item>
                <n-form-item label="存在惩罚">
                  <div class="slider-row">
                    <n-slider
                      v-model:value="form.presence_penalty"
                      :min="-2"
                      :max="2"
                      :step="0.1"
                      class="param-slider"
                    />
                    <n-input-number
                      v-model:value="form.presence_penalty"
                      :min="-2"
                      :max="2"
                      :step="0.1"
                      style="width: 80px"
                    />
                  </div>
                </n-form-item>
              </div>
            </div>

            <!-- 网络代理 -->
            <div class="form-section">
              <div class="section-title">
                网络代理
                <span class="section-hint">可选的代理配置</span>
              </div>
              <n-form-item label="代理地址（可选）">
                <n-input
                  v-model:value="form.proxy_url"
                  placeholder="http://127.0.0.1:7890"
                />
              </n-form-item>
              <div class="field-hint">
                留空则直连。支持 HTTP/HTTPS 代理，格式如 http://host:port
              </div>
            </div>
          </n-form>
        </n-scrollbar>
      </div>
    </div>

    <!-- 测试结果弹窗 -->
    <n-modal v-model:show="showTestResult" preset="card" title="连接测试结果" style="width: 520px">
      <div class="test-result">
        <div v-if="testResult" class="result-status" :class="testResult.ok ? 'ok' : 'fail'">
          <span class="result-icon">{{ testResult.ok ? '✅' : '❌' }}</span>
          <span>{{ testResult.ok ? '连接成功' : '连接失败' }}</span>
        </div>
        <div class="result-content">
          <div class="result-label">模型返回：</div>
          <n-alert v-if="testResult" :type="testResult.ok ? 'success' : 'error'" :bordered="false">
            {{ testResult.message }}
          </n-alert>
        </div>
      </div>
      <template #footer>
        <n-button type="primary" @click="showTestResult = false">知道了</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import {
  listModelConfigs,
  createModelConfig,
  updateModelConfig,
  activateModelConfig,
  deleteModelConfig,
  testModelConnection,
  type ModelConfig,
  type ModelConfigPayload,
} from '@/api/models'
import { notify } from '@/utils/notify'

const message = useMessage()

// ---- 数据状态 ----
const configs = ref<ModelConfig[]>([])
const selectedId = ref<number | null>(null)
const loading = ref(false)
const saving = ref(false)
const activating = ref(false)
const testing = ref(false)

// ---- 表单数据 ----
const form = reactive<{
  name: string
  base_url: string
  api_key: string
  model: string
  is_active: boolean
  temperature: number | null
  max_tokens: number | null
  top_p: number | null
  frequency_penalty: number | null
  presence_penalty: number | null
  proxy_url: string
}>({
  name: '',
  base_url: '',
  api_key: '',
  model: '',
  is_active: false,
  temperature: 0.7,
  max_tokens: null,
  top_p: 0.9,
  frequency_penalty: 0,
  presence_penalty: 0,
  proxy_url: '',
})

const isNewMode = ref(false)
const isEditing = computed(() => selectedId.value !== null && !isNewMode.value)

// ---- 服务预设 ----
const servicePresets = [
  {
    name: '硅基流动',
    base_url: 'https://api.siliconflow.cn/v1',
    model: 'deepseek-ai/DeepSeek-V4-Pro',
  },
  {
    name: 'DeepSeek 官方',
    base_url: 'https://api.deepseek.com/v1',
    model: 'deepseek-chat',
  },
  {
    name: '月之暗面 Kimi',
    base_url: 'https://api.moonshot.cn/v1',
    model: 'moonshot-v1-8k',
  },
  {
    name: '通义千问',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'qwen-plus',
  },
  {
    name: '智谱 GLM',
    base_url: 'https://open.bigmodel.cn/api/paas/v4',
    model: 'glm-4-plus',
  },
  {
    name: 'OpenAI 官方',
    base_url: 'https://api.openai.com/v1',
    model: 'gpt-4o',
  },
  {
    name: 'Ollama 本地',
    base_url: 'http://localhost:11434/v1',
    model: 'qwen2.5:7b',
  },
]

const activeCount = computed(() => configs.value.filter((c) => c.is_active === 1).length)

// ---- 计算属性 ----
const isAnthropicUrl = computed(() =>
  form.base_url.toLowerCase().includes('/anthropic')
)

const canSave = computed(() => {
  return form.name.trim() && form.base_url.trim() && form.api_key.trim() && form.model.trim()
})

// ---- 测试结果 ----
const showTestResult = ref(false)
const testResult = ref<{ ok: boolean; message: string } | null>(null)

// ---- 方法 ----

async function loadConfigs() {
  loading.value = true
  try {
    configs.value = await listModelConfigs()
    if (!selectedId.value && configs.value.length > 0) {
      const active = configs.value.find((c) => c.is_active === 1)
      selectedId.value = active ? active.id : configs.value[0].id
      fillFormFromSelected()
    }
  } catch {
    notify.error('加载配置列表失败')
  } finally {
    loading.value = false
  }
}

function selectConfig(cfg: ModelConfig) {
  selectedId.value = cfg.id
  isNewMode.value = false
  fillFormFromSelected()
}

function fillFormFromSelected() {
  const cfg = configs.value.find((c) => c.id === selectedId.value)
  if (!cfg) return
  form.name = cfg.name
  form.base_url = cfg.base_url
  form.api_key = cfg.api_key
  form.model = cfg.model
  form.is_active = cfg.is_active === 1
  form.temperature = cfg.temperature ?? 0.7
  form.max_tokens = cfg.max_tokens ?? null
  form.top_p = cfg.top_p ?? 0.9
  form.frequency_penalty = cfg.frequency_penalty ?? 0
  form.presence_penalty = cfg.presence_penalty ?? 0
  form.proxy_url = cfg.proxy_url ?? ''
}

function createNew() {
  isNewMode.value = true
  selectedId.value = null
  form.name = '新配置'
  form.base_url = ''
  form.api_key = ''
  form.model = ''
  form.is_active = false
  form.temperature = 0.7
  form.max_tokens = null
  form.top_p = 0.9
  form.frequency_penalty = 0
  form.presence_penalty = 0
  form.proxy_url = ''
}

function applyPreset(preset: { name: string; base_url: string; model: string }) {
  form.name = `${preset.name} - ${preset.model.split('/').pop() || preset.model}`
  form.base_url = preset.base_url
  form.model = preset.model
  message.info(`已应用 ${preset.name} 预设`)
}

function itemMenuOptions(cfg: ModelConfig) {
  return [
    {
      label: cfg.is_active === 1 ? '✅ 当前启用' : '设为启用',
      key: 'activate',
      disabled: cfg.is_active === 1,
    },
    {
      label: '复制配置',
      key: 'duplicate',
    },
    {
      type: 'divider' as const,
      key: 'divider',
    },
    {
      label: '删除',
      key: 'delete',
      disabled: configs.value.length <= 1,
      props: { style: 'color: #ef4444;' },
    },
  ]
}

async function onItemAction(key: string, cfg: ModelConfig) {
  switch (key) {
    case 'activate':
      await doActivate(cfg.id)
      break
    case 'duplicate':
      await doDuplicate(cfg)
      break
    case 'delete':
      await doDelete(cfg.id)
      break
  }
}

async function doActivate(id: number) {
  activating.value = true
  try {
    await activateModelConfig(id)
    notify.success('已切换启用配置')
    await loadConfigs()
    selectedId.value = id
    fillFormFromSelected()
  } catch {
    notify.error('切换失败')
  } finally {
    activating.value = false
  }
}

async function setActive() {
  if (selectedId.value) {
    await doActivate(selectedId.value)
  }
}

async function doDuplicate(cfg: ModelConfig) {
  try {
    const newCfg = await createModelConfig({
      name: `${cfg.name} (副本)`,
      base_url: cfg.base_url,
      api_key: cfg.api_key,
      model: cfg.model,
      is_active: false,
      temperature: cfg.temperature ?? undefined,
      max_tokens: cfg.max_tokens ?? undefined,
      top_p: cfg.top_p ?? undefined,
      frequency_penalty: cfg.frequency_penalty ?? undefined,
      presence_penalty: cfg.presence_penalty ?? undefined,
      proxy_url: cfg.proxy_url ?? undefined,
    })
    notify.success('已复制配置')
    await loadConfigs()
    selectedId.value = newCfg.id
    isNewMode.value = false
    fillFormFromSelected()
  } catch {
    notify.error('复制失败')
  }
}

async function doDelete(id: number) {
  if (configs.value.length <= 1) {
    notify.warning('至少保留一个配置')
    return
  }
  try {
    await deleteModelConfig(id)
    notify.success('已删除配置')
    if (selectedId.value === id) {
      selectedId.value = null
      isNewMode.value = false
    }
    await loadConfigs()
  } catch {
    notify.error('删除失败')
  }
}

function buildPayload(): ModelConfigPayload {
  return {
    name: form.name.trim(),
    base_url: form.base_url.trim().replace(/\/+$/, ''),
    api_key: form.api_key.trim(),
    model: form.model.trim().replace(/^openai:/, ''),
    is_active: form.is_active,
    temperature: form.temperature,
    max_tokens: form.max_tokens,
    top_p: form.top_p,
    frequency_penalty: form.frequency_penalty,
    presence_penalty: form.presence_penalty,
    proxy_url: form.proxy_url.trim() || undefined,
  }
}

async function save() {
  if (!canSave.value) return
  if (isAnthropicUrl.value) {
    message.error('当前应用内模型配置请使用 OpenAI-compatible /v1 地址')
    return
  }
  saving.value = true
  try {
    const payload = buildPayload()
    if (isNewMode.value) {
      const created = await createModelConfig(payload)
      notify.success('配置已创建')
      isNewMode.value = false
      await loadConfigs()
      selectedId.value = created.id
      fillFormFromSelected()
    } else if (selectedId.value) {
      await updateModelConfig(selectedId.value, payload)
      notify.success('配置已保存')
      await loadConfigs()
      fillFormFromSelected()
    }
  } catch {
    notify.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  if (selectedId.value && canSave.value) {
    try {
      const payload = buildPayload()
      await updateModelConfig(selectedId.value, payload)
    } catch {
      // 保存失败也可以继续测（用上次保存的配置）
    }
  }

  testing.value = true
  try {
    const result = await testModelConnection()
    testResult.value = result
    showTestResult.value = true
  } catch {
    testResult.value = { ok: false, message: '测试请求失败，请检查网络或配置' }
    showTestResult.value = true
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.api-config-page {
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 12px;
}

/* ===== 页头 ===== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
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
  font-size: 12px;
  color: var(--n-text-color-3, #6b7280);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 14px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 8px;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 50px;
}

.stat-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--n-color-primary, #3b82f6);
  line-height: 1.2;
}

.stat-num.success {
  color: #10b981;
}

.stat-label {
  font-size: 10px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 2px;
}

.stat-divider {
  width: 1px;
  height: 24px;
  background: var(--n-border-color, #2a2f3a);
}

/* ===== 工作区 ===== */
.workbench {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 12px;
  min-height: 0;
}

/* ===== 通用面板 ===== */
.list-panel,
.detail-panel {
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  flex-shrink: 0;
}

.panel-head h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.list-scroll {
  flex: 1;
  min-height: 0;
}

.list-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 60px 20px;
  color: var(--n-text-color-3, #6b7280);
  text-align: center;
}

.list-empty .empty-icon {
  font-size: 36px;
}

.list-empty p {
  margin: 0;
  font-size: 13px;
}

.list-empty .empty-sub {
  font-size: 12px;
  opacity: 0.7;
}

.config-list {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.config-item:hover {
  background: var(--n-color-hover, #23272f);
}

.config-item.active {
  background: rgba(59, 130, 246, 0.08);
  border-color: var(--n-color-primary, #3b82f6);
}

.config-item.is-active .item-name {
  color: #10b981;
}

.item-main {
  min-width: 0;
  flex: 1;
}

.item-name {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 6px;
}

.active-badge {
  font-size: 8px;
  color: #10b981;
}

.item-sub {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ===== 详情面板 ===== */
.detail-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--n-text-color-3, #6b7280);
}

.detail-empty .empty-icon {
  font-size: 40px;
}

.detail-empty p {
  margin: 0;
  font-size: 13px;
}

.detail-empty .empty-sub {
  font-size: 12px;
  opacity: 0.7;
}

.form-scroll {
  flex: 1;
  min-height: 0;
}

.form-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
  position: sticky;
  top: 0;
  background: var(--n-color-card, #1a1d21);
  z-index: 1;
}

.form-title {
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}

.form-actions {
  display: flex;
  gap: 8px;
}

/* ===== 预设卡片 ===== */
.preset-card {
  margin: 16px 20px;
  padding: 14px 16px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(168, 85, 247, 0.04));
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 8px;
}

.preset-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.preset-icon {
  font-size: 16px;
}

.preset-title {
  font-size: 13px;
  font-weight: 600;
}

.preset-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.preset-hint {
  margin: 0;
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
}

/* ===== 表单 ===== */
.config-form {
  padding: 0 20px 24px;
}

.form-section {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--n-border-color, #2a2f3a);
}

.form-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 14px;
  padding-left: 10px;
  border-left: 3px solid var(--n-color-primary, #3b82f6);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--n-text-color-3, #6b7280);
}

.param-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 20px;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.param-slider {
  flex: 1;
}

.field-hint {
  font-size: 11px;
  color: var(--n-text-color-3, #6b7280);
  margin-top: 6px;
  line-height: 1.5;
}

.compat-alert {
  margin-bottom: 14px;
}

/* ===== 测试结果弹窗 ===== */
.test-result {
  padding: 10px 0;
}

.result-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.result-status.ok {
  color: #10b981;
}

.result-status.fail {
  color: #ef4444;
}

.result-icon {
  font-size: 20px;
}

.result-label {
  font-size: 13px;
  color: var(--n-text-color-2, #9ca3af);
  margin-bottom: 8px;
}

.result-content {
  word-break: break-all;
}
</style>
