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
          <div class="stat-divider"></div>
          <div class="stat">
            <span class="stat-num">{{ disabledCount }}</span>
            <span class="stat-label">已禁用</span>
          </div>
        </div>
        <n-button @click="load" :loading="loading">刷新</n-button>
        <n-button type="primary" @click="openCreate">
          <template #icon>＋</template>
          新增用户
        </n-button>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="user-toolbar">
      <n-input
        v-model:value="searchText"
        clearable
        placeholder="搜索用户名、昵称或邮箱"
        class="user-search"
      >
        <template #prefix>🔎</template>
      </n-input>
      <n-select v-model:value="roleFilter" :options="roleFilterOptions" clearable placeholder="全部角色" class="user-filter" />
      <n-select v-model:value="statusFilter" :options="statusFilterOptions" clearable placeholder="全部状态" class="user-filter" />
      <span class="result-count">显示 {{ filteredUsers.length }} / {{ users.length }} 位用户</span>
    </div>

    <!-- 用户列表 -->
    <div class="content-card user-table-card">
      <n-data-table
        :columns="columns"
        :data="filteredUsers"
        :loading="loading"
        :bordered="false"
        :single-line="true"
        :pagination="pagination"
        @update:page="pagination.page = $event"
        @update:page-size="pagination.pageSize = $event"
        :row-key="(row: SysUser) => row.id"
        :scroll-x="980"
      />
      <div v-if="!loading && users.length === 0" class="user-empty-state">
        <div class="empty-icon">👥</div>
        <strong>还没有用户</strong>
        <span>添加系统用户后，可以在这里维护角色与账号状态。</span>
        <n-button type="primary" @click="openCreate">新增第一个用户</n-button>
      </div>
      <div v-else-if="!loading && filteredUsers.length === 0" class="user-empty-state compact">
        <strong>没有匹配的用户</strong>
        <span>调整搜索内容或筛选条件后再试。</span>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <n-modal v-model:show="showModal" preset="card" :title="isEdit ? '编辑用户' : '新增用户'" style="width: min(520px, 92vw)">
      <p class="modal-caption">{{ isEdit ? '更新账号资料；密码留空表示保持不变。' : '创建可登录系统的账号，并分配管理角色。' }}</p>
      <n-form :model="form" label-placement="top">
        <n-form-item label="用户名">
          <n-input v-model:value="form.username" placeholder="请输入用户名" :disabled="isEdit" maxlength="64" />
        </n-form-item>
        <n-form-item :label="isEdit ? '新密码' : '密码'">
          <n-input v-model:value="form.password" type="password" show-password-on="click" :placeholder="isEdit ? '留空则不修改' : '至少 8 位'" maxlength="128" />
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
          <n-button type="primary" :loading="saving" @click="handleSave">{{ isEdit ? '保存修改' : '创建用户' }}</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch } from 'vue'
import { NButton, NPopconfirm, NSpace, NTag, useMessage } from 'naive-ui'
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
const searchText = ref('')
const roleFilter = ref<string | null>(null)
const statusFilter = ref<string | null>(null)
const pagination = reactive({
  page: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 20, 50],
})

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

const roleFilterOptions = [
  { label: '管理员', value: 'admin' },
  { label: '普通用户', value: 'user' },
]

const statusFilterOptions = [
  { label: '正常', value: 'active' },
  { label: '禁用', value: 'disabled' },
]

const activeCount = computed(() => users.value.filter((u) => u.status === 'active').length)
const adminCount = computed(() => users.value.filter((u) => u.role === 'admin').length)
const disabledCount = computed(() => users.value.filter((u) => u.status !== 'active').length)
const filteredUsers = computed(() => {
  const keyword = searchText.value.trim().toLocaleLowerCase('zh-CN')
  return users.value.filter((user) => {
    const matchesKeyword = !keyword || [user.username, user.nickname, user.email]
      .some((value) => String(value || '').toLocaleLowerCase('zh-CN').includes(keyword))
    const matchesRole = !roleFilter.value || user.role === roleFilter.value
    const matchesStatus = !statusFilter.value || user.status === statusFilter.value
    return matchesKeyword && matchesRole && matchesStatus
  })
})

watch([searchText, roleFilter, statusFilter], () => {
  // 步骤 1：筛选条件改变后回到第一页，避免页码超出筛选结果。
  pagination.page = 1
})

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
      h(NTag, { size: 'small', bordered: false, type: row.role === 'admin' ? 'error' : 'info' }, {
        default: () => row.role === 'admin' ? '管理员' : '普通用户',
      }),
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: SysUser) =>
      h(NTag, { size: 'small', bordered: false, type: row.status === 'active' ? 'success' : 'default' }, {
        default: () => row.status === 'active' ? '正常' : '禁用',
      }),
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 170,
    render: (row: SysUser) => formatDate(row.created_at),
  },
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
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '用户列表加载失败')
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
  if (form.password.trim() && form.password.trim().length < 8) {
    message.warning('密码至少需要 8 位')
    return
  }
  if (form.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
    message.warning('请填写有效的邮箱地址')
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
    await load()
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
    await load()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '删除失败')
  }
}

function formatDate(value: string) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { dateStyle: 'medium', timeStyle: 'short' })
}

onMounted(load)
</script>

<style scoped>
.user-manage-page {
  padding: 24px 28px 40px;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
}

.header-left {
  min-width: 0;
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

.title-icon {
  font-size: 20px;
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
  min-width: 70px;
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

.stat-num.warning {
  color: #fbbf24;
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

.user-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding: 12px;
  background: var(--n-color-card, #1a1d21);
  border: 1px solid var(--n-border-color, #2a2f3a);
  border-radius: 10px;
}

.user-search {
  width: min(360px, 42vw);
}

.user-filter {
  width: 150px;
}

.result-count {
  margin-left: auto;
  color: var(--n-text-color-3, #8490a3);
  font-size: 12px;
  white-space: nowrap;
}

.user-table-card {
  min-height: 320px;
  padding: 6px 14px 12px;
  overflow: hidden;
}

.user-empty-state {
  display: flex;
  min-height: 280px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  color: var(--n-text-color-3, #8490a3);
  text-align: center;
}

.user-empty-state strong {
  color: var(--n-text-color-1, #e5e7eb);
  font-size: 15px;
}

.user-empty-state span {
  margin-bottom: 5px;
  font-size: 12px;
}

.empty-icon {
  font-size: 38px;
  opacity: 0.8;
}

.user-empty-state.compact {
  min-height: 220px;
}

.modal-caption {
  margin: 0 0 16px;
  color: var(--n-text-color-3, #8490a3);
  font-size: 12px;
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

  .user-toolbar {
    flex-wrap: wrap;
  }

  .user-search {
    width: 100%;
  }

  .result-count {
    width: 100%;
    margin: 2px 0 0;
  }
}

@media (max-width: 600px) {
  .user-manage-page {
    padding: 18px 14px 28px;
  }

  .header-right {
    align-items: stretch;
  }

  .header-stats {
    width: 100%;
    justify-content: space-around;
  }

  .user-filter {
    flex: 1;
    min-width: 120px;
  }
}
</style>
