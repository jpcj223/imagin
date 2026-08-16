<template>
  <div class="page">
    <div class="page-title">
      <h1>🔌 API 配置</h1>
      <n-button @click="testConnection">测试连接</n-button>
    </div>

    <n-form class="section" label-placement="top">
      <n-alert class="compat-alert" type="info" :bordered="false">
        当前 Agent 使用 OpenAI-compatible 通道。Claude Code 的 Anthropic 地址可留给外部工具使用，
        应用内请填写以 /v1 结尾的兼容地址。
      </n-alert>

      <div class="preset-row">
        <n-button size="small" secondary @click="applySiliconFlowPreset">应用硅基流动 DeepSeek 预设</n-button>
        <n-text depth="3">预设只填地址和模型，API Key 仍从本地配置读取或手动粘贴。</n-text>
      </div>

      <n-form-item label="配置名称">
        <n-input v-model:value="form.name" placeholder="例如：硅基流动 DeepSeek V4 Pro" />
      </n-form-item>
      <n-form-item label="API 地址">
        <n-input v-model:value="form.base_url" placeholder="https://api.siliconflow.cn/v1" />
      </n-form-item>
      <n-alert v-if="isAnthropicUrl" class="compat-alert" type="warning" :bordered="false">
        检测到 Anthropic 地址。当前后端会调用 /chat/completions，请改用 OpenAI-compatible 地址。
      </n-alert>
      <n-form-item label="API Key">
        <n-input v-model:value="form.api_key" type="password" show-password-on="click" placeholder="sk-..." />
      </n-form-item>
      <n-form-item label="模型名称">
        <n-input v-model:value="form.model" placeholder="例如：deepseek-ai/DeepSeek-V4-Pro" />
      </n-form-item>
      <div class="actions">
        <n-button type="primary" @click="save">💾 保存配置</n-button>
      </div>
    </n-form>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { useMessage } from 'naive-ui'
import { listModelConfigs, saveModelConfig, testModelConnection } from '@/api/models'

const message = useMessage()
const form = reactive({
  name: '硅基流动 DeepSeek V4 Pro',
  base_url: 'https://api.siliconflow.cn/v1',
  api_key: '',
  model: 'deepseek-ai/DeepSeek-V4-Pro',
  is_active: true
})

const isAnthropicUrl = computed(() => form.base_url.toLowerCase().includes('/anthropic'))

function applySiliconFlowPreset() {
  // 预设只负责填协议匹配的服务地址和模型名，不覆盖用户已经粘贴的密钥。
  form.name = '硅基流动 DeepSeek V4 Pro'
  form.base_url = 'https://api.siliconflow.cn/v1'
  form.model = 'deepseek-ai/DeepSeek-V4-Pro'
}

function normalizeForm() {
  // 有些工具配置会写成 openai:model-name，后端直连 OpenAI-compatible 时只需要真实模型名。
  form.base_url = form.base_url.trim().replace(/\/+$/, '')
  form.model = form.model.trim().replace(/^openai:/, '')
  form.api_key = form.api_key.trim()
}

async function loadActiveConfig() {
  // 进入页面先回填当前启用配置，保证测试按钮测的是用户看得到的这份配置。
  const configs = await listModelConfigs()
  const active = configs.find((item) => item.is_active === 1) ?? configs[configs.length - 1]
  if (active) {
    form.name = active.name
    form.base_url = active.base_url
    form.api_key = active.api_key
    form.model = active.model
    form.is_active = true
  }
}

async function save() {
  normalizeForm()
  if (isAnthropicUrl.value) {
    message.error('当前应用内模型配置请使用 OpenAI-compatible /v1 地址')
    return false
  }
  // 保存后端模型配置；真正调用模型时由后端读取 active 配置。
  await saveModelConfig({ ...form })
  message.success('API 配置已保存')
  return true
}

async function testConnection() {
  const saved = await save()
  if (!saved) return
  // 测试当前 active 模型配置是否能完成一次最小聊天请求。
  const result = await testModelConnection()
  result.ok ? message.success(result.message) : message.error(result.message)
}

onMounted(loadActiveConfig)
</script>

<style scoped>
.compat-alert {
  margin-bottom: 14px;
}

.preset-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
</style>
