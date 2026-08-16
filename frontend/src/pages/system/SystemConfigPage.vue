<template>
  <div class="page page-wide system-config-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">🔧</span>
          系统配置
        </h1>
        <p class="page-subtitle">管理系统全局参数和运行配置</p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ configs.length }}</span>
            <span class="stat-label">配置项</span>
          </div>
        </div>
        <n-button type="primary" @click="openCreate">
          <template #icon>＋</template>
          新增配置
        </n-button>
      </div>
    </div>

    <!-- 配置列表 -->
    <div class="config-grid">
      <div v-for="cfg in configs" :key="cfg.id" class="config-card">
        <div class="card-head">
          <div class="card-title">
            <span class="card-icon">⚙️</span>
            <span>{{ cfg.config_name }}</span>
          </div>
          <div class="card-actions">
            <n-button size="small" text @click="openEdit(cfg)">编辑</n-button>
          </div>
        </div>
        <div class="card-key">{{ cfg.config_key }}</div>
        <div class="card-value">{{ cfg.config_value }}</div>
        <div class="card-desc" v-if="cfg.description">{{ cfg.description }}</div>
        <div class="card-meta">更新于 {{ formatTime(cfg.updated_at) }}</div>
      </div>
      <div v-if="configs.length === 0 && !loading" class="empty-card">
        <div class="empty-icon">🔧</div>
        <p>暂无配置项</p>
        <p class="empty-sub">点击右上角「新增配置」添加</p>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <n-modal v-model:show="showModal" preset="card" :title="isEdit ? '编辑配置' : '新增配置'" style="width: 480px">
      <n-form :model="form" label-placement="left" label-width="90px">
        <n-form-item label="配置键名">
          <n-input v-model:value="form.config_key" placeholder="如: site_name" :disabled="isEdit" />
        </n-form-item>
        <n-form-item label="配置名称">
          <n-input v-model:value="form.config_name" placeholder="如: 站点名称" />
        </n-form-item>
        <n-form-item label="配置值">
          <n-input v-model:value="form.config_value" type="textarea" :rows="3" placeholder="配置内容" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="form.description" type="textarea" :rows="2" placeholder="配置说明" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="text-align: right">
          <n-button style="margin-right: 8px" @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSave">确定</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import {
  fetchConfigs,
  updateConfig,
  type SysConfig,
} from '@/api/core'

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const configs = ref<SysConfig[]>([])

const showModal = ref(false)
const isEdit = ref(false)
const editKey = ref('')
const form = reactive({
  config_key: '',
  config_value: '',
  config_name: '',
  description: '',
})

async function load() {
  loading.value = true
  try {
    configs.value = await fetchConfigs()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editKey.value = ''
  Object.assign(form, {
    config_key: '',
    config_value: '',
    config_name: '',
    description: '',
  })
  showModal.value = true
}

function openEdit(cfg: SysConfig) {
  isEdit.value = true
  editKey.value = cfg.config_key
  Object.assign(form, {
    config_key: cfg.config_key,
    config_value: cfg.config_value,
    config_name: cfg.config_name,
    description: cfg.description,
  })
  showModal.value = true
}

async function handleSave() {
  if (!form.config_key.trim()) {
    message.warning('请输入配置键名')
    return
  }
  saving.value = true
  try {
    const key = isEdit.value ? editKey.value : form.config_key
    await updateConfig(key, {
      config_value: form.config_value,
      config_name: form.config_name,
      description: form.description,
    })
    message.success('保存成功')
    showModal.value = false
    load()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function formatTime(t: string): string {
  if (!t) return ''
  return t.replace('T', ' ').substring(0, 16)
}

onMounted(load)
</script>

<style scoped>
.system-config-page {
  padding: 28px 32px;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.config-card {
  background: #1c1f23;
  border: 1px solid #2c3035;
  border-radius: 10px;
  padding: 18px;
  transition: border-color 0.2s;
}
.config-card:hover {
  border-color: #3b82f6;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #f3f4f6;
}

.card-icon {
  font-size: 18px;
}

.card-key {
  font-size: 12px;
  color: #6b7280;
  font-family: monospace;
  margin-bottom: 10px;
}

.card-value {
  font-size: 14px;
  color: #d1d5db;
  padding: 10px 12px;
  background: #151719;
  border-radius: 6px;
  word-break: break-all;
  margin-bottom: 10px;
  min-height: 40px;
}

.card-desc {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 10px;
}

.card-meta {
  font-size: 11px;
  color: #6b7280;
}

.empty-card {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #6b7280;
  background: #1c1f23;
  border: 1px dashed #2c3035;
  border-radius: 10px;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.empty-sub {
  font-size: 12px;
  margin-top: 4px;
  color: #4b5563;
}
</style>
