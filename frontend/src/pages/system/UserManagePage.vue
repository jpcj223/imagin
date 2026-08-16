<template>
  <div class="page page-wide user-manage-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <span class="title-icon">👥</span>
          用户管理
        </h1>
        <p class="page-subtitle">管理系统用户账号、角色和状态</p>
      </div>
      <div class="header-right">
        <div class="header-stats">
          <div class="stat">
            <span class="stat-num">{{ users.length }}</span>
            <span class="stat-label">用户总数</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num success">{{ activeCount }}</span>
            <span class="stat-label">活跃用户</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num warning">{{ adminCount }}</span>
            <span class="stat-label">管理员</span>
          </div>
        </div>
        <n-button type="primary" @click="openCreate">
          <template #icon>＋</template>
          新增用户
        </n-button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="content-card">
      <n-data-table
        :columns="columns"
        :data="users"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        striped
      />
    </div>

    <!-- 编辑弹窗 -->
    <n-modal v-model:show="showModal" preset="card" :title="isEdit ? '编辑用户' : '新增用户'" style="width: 480px">
      <n-form :model="form" label-placement="left" label-width="80px">
        <n-form-item label="用户名">
          <n-input v-model:value="form.username" placeholder="请输入用户名" :disabled="isEdit" />
        </n-form-item>
        <n-form-item :label="isEdit ? '新密码' : '密码'">
          <n-input v-model:value="form.password" type="password" show-password-on="click" :placeholder="isEdit ? '留空则不修改' : '请输入密码'" />
        </n-form-item>
        <n-form-item label="昵称">
          <n-input v-model:value="form.nickname" placeholder="请输入昵称" />
        </n-form-item>
        <n-form-item label="邮箱">
          <n-input v-model:value="form.email" placeholder="请输入邮箱" />
        </n-form-item>
        <n-form-item label="角色">
          <n-select v-model:value="form.role" :options="roleOptions" />
        </n-form-item>
        <n-form-item label="状态">
          <n-select v-model:value="form.status" :options="statusOptions" />
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
import { computed, h, onMounted, reactive, ref } from 'vue'
import { NButton, NPopconfirm, NSpace, useMessage } from 'naive-ui'
import {
  createUser,
  deleteUser,
  fetchUsers,
  updateUser,
  type SysUser,
} from '@/api/core'

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const users = ref<SysUser[]>([])

const showModal = ref(false)
const isEdit = ref(false)
const editId = ref(0)
const form = reactive({
  username: '',
  password: '',
  nickname: '',
  email: '',
  role: 'user',
  status: 'active',
})

const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '普通用户', value: 'user' },
]

const statusOptions = [
  { label: '正常', value: 'active' },
  { label: '禁用', value: 'disabled' },
]

const activeCount = computed(() => users.value.filter((u) => u.status === 'active').length)
const adminCount = computed(() => users.value.filter((u) => u.role === 'admin').length)

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '用户名', key: 'username', width: 140 },
  { title: '昵称', key: 'nickname', width: 140 },
  { title: '邮箱', key: 'email', width: 200 },
  {
    title: '角色',
    key: 'role',
    width: 100,
    render: (row: SysUser) =>
      h(
        'span',
        { class: row.role === 'admin' ? 'role-tag admin' : 'role-tag user' },
        row.role === 'admin' ? '管理员' : '普通用户'
      ),
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: SysUser) =>
      h(
        'span',
        { class: row.status === 'active' ? 'status-tag active' : 'status-tag disabled' },
        row.status === 'active' ? '正常' : '禁用'
      ),
  },
  { title: '创建时间', key: 'created_at', width: 180 },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render: (row: SysUser) =>
      h(NSpace, { size: 'small' }, () => [
        h(NButton, { size: 'small', text: true, onClick: () => openEdit(row) }, () => '编辑'),
        h(
          NPopconfirm,
          { onPositiveClick: () => handleDelete(row.id) },
          { default: () => '确认删除？', trigger: () => h(NButton, { size: 'small', text: true, type: 'error' }, () => '删除') }
        ),
      ]),
  },
]

async function load() {
  loading.value = true
  try {
    users.value = await fetchUsers()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editId.value = 0
  Object.assign(form, {
    username: '',
    password: '',
    nickname: '',
    email: '',
    role: 'user',
    status: 'active',
  })
  showModal.value = true
}

function openEdit(row: SysUser) {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    username: row.username,
    password: '',
    nickname: row.nickname,
    email: row.email,
    role: row.role,
    status: row.status,
  })
  showModal.value = true
}

async function handleSave() {
  if (!form.username.trim()) {
    message.warning('请输入用户名')
    return
  }
  if (!isEdit.value && !form.password.trim()) {
    message.warning('请输入密码')
    return
  }

  saving.value = true
  try {
    if (isEdit.value) {
      const payload: Record<string, string> = {
        nickname: form.nickname,
        email: form.email,
        role: form.role,
        status: form.status,
      }
      if (form.password.trim()) {
        payload.password = form.password
      }
      await updateUser(editId.value, payload)
      message.success('更新成功')
    } else {
      await createUser({
        username: form.username,
        password: form.password,
        nickname: form.nickname,
        email: form.email,
        role: form.role,
        status: form.status,
      })
      message.success('创建成功')
    }
    showModal.value = false
    load()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await deleteUser(id)
    message.success('删除成功')
    load()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.user-manage-page {
  padding: 28px 32px;
}

.role-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
}
.role-tag.admin {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}
.role-tag.user {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}

.status-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
}
.status-tag.active {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}
.status-tag.disabled {
  background: rgba(156, 163, 175, 0.15);
  color: #9ca3af;
}
</style>
