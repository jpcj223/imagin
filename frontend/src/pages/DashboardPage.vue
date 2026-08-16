<template>
  <div class="page">
    <div class="page-title">
      <h1>🚀 创作中心</h1>
      <n-button @click="load">刷新</n-button>
    </div>

    <div class="grid-2">
      <n-card v-for="item in stats" :key="item.label" :bordered="false" class="stat-card">
        <div class="stat-value">{{ item.value }}</div>
        <div class="muted">{{ item.label }}</div>
      </n-card>
    </div>

    <div class="section">
      <h2 class="section-title">第一版创作闭环</h2>
      <n-steps :current="2" status="process">
        <n-step title="配置项目" description="填写题材、主题、目标字数" />
        <n-step title="管理资料" description="维护世界观、角色、组织、伏笔" />
        <n-step title="生成章节" description="读取资料包并生成正文" />
        <n-step title="分析沉淀" description="生成摘要，沉淀长期记忆" />
      </n-steps>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getDashboard } from '@/api/resources'
import { useProjectStore } from '@/stores/project'
import type { DashboardCounts } from '@/types/domain'

const projectStore = useProjectStore()
const counts = ref<DashboardCounts>({ characters: 0, outlines: 0, chapters: 0, foreshadowings: 0 })

const stats = computed(() => [
  { label: '人物卡', value: counts.value.characters },
  { label: '大纲节点', value: counts.value.outlines },
  { label: '章节草稿', value: counts.value.chapters },
  { label: '伏笔', value: counts.value.foreshadowings }
])

async function load() {
  // 首页加载默认项目后，只读取各模块数量，用于快速判断项目资料完整度。
  if (!projectStore.currentProject) {
    await projectStore.loadDefaultProject()
  }
  if (projectStore.currentProject) {
    counts.value = await getDashboard(projectStore.currentProject.id)
  }
}

onMounted(load)
</script>

<style scoped>
.stat-card {
  background: #202327;
}

.stat-value {
  margin-bottom: 8px;
  font-size: 34px;
  font-weight: 800;
}
</style>
