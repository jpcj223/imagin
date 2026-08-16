<template>
  <div class="page">
    <div class="page-title">
      <h1>⚙️ 项目配置</h1>
      <n-button type="primary" @click="save">保存</n-button>
    </div>

    <n-form class="section" label-placement="top">
      <n-form-item label="书名">
        <n-input v-model:value="form.name" />
      </n-form-item>
      <div class="grid-2">
        <n-form-item label="主题">
          <n-input v-model:value="form.theme" />
        </n-form-item>
        <n-form-item label="小说类型">
          <n-input v-model:value="form.novel_type" />
        </n-form-item>
      </div>
      <n-form-item label="目标字数">
        <n-input-number v-model:value="form.target_words" :min="500" :step="500" />
      </n-form-item>
      <n-form-item label="项目简介">
        <n-input v-model:value="form.synopsis" type="textarea" :autosize="{ minRows: 5 }" />
      </n-form-item>
    </n-form>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useMessage } from 'naive-ui'
import { updateProject } from '@/api/projects'
import { useProjectStore } from '@/stores/project'

const message = useMessage()
const projectStore = useProjectStore()
const form = reactive({
  id: 0,
  name: '',
  theme: '',
  novel_type: '',
  target_words: 2500,
  synopsis: ''
})

onMounted(async () => {
  if (!projectStore.currentProject) await projectStore.loadDefaultProject()
  Object.assign(form, projectStore.currentProject)
})

async function save() {
  // 项目配置是后续大纲、角色、章节生成的默认上下文。
  const updated = await updateProject(form.id, form)
  projectStore.currentProject = updated
  message.success('项目配置已保存')
}
</script>
