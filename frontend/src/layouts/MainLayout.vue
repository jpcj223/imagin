<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <strong>臆想创作</strong>
        <span>AI 小说创作工作台</span>
      </div>

      <div class="nav-scroll">
        <div v-for="group in groups" :key="group.title" class="nav-group">
          <div class="group-title">{{ group.title }}</div>
          <button
              v-for="item in group.items"
              :key="item.path"
              class="nav-item"
              :class="{ active: route.path === item.path && tabsStore.isRouteOpen(item.path) }"
              @click="go(item)"
          >
            <span>{{ item.icon }}</span>
            <span>{{ item.title }}</span>
          </button>
        </div>
      </div>
    </aside>

    <main class="workspace">
      <div class="tabs">
        <button
            v-for="tab in tabsStore.tabs"
            :key="tab.path"
            class="tab"
            :class="{ active: route.path === tab.path }"
            @click="router.push(tab.path)"
        >
          <span>{{ tab.icon }}</span>
          <span>{{ tab.title }}</span>
          <span class="close" @click.stop="closeTab(tab.path)">×</span>
        </button>
      </div>

      <!-- 只有当前路由存在对应标签时才显示页面，标签清空后内容区保持真正空白。 -->
      <div class="content">
        <router-view v-if="tabsStore.isRouteOpen(route.path)" v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" :key="route.path"/>
          </keep-alive>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import {onMounted, watch} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {useProjectStore} from '@/stores/project'
import {useWorkspaceTabsStore, type WorkspaceTab} from '@/stores/workspaceTabs'

const router = useRouter()
const route = useRoute()
const projectStore = useProjectStore()
const tabsStore = useWorkspaceTabsStore()

const groups = [
  {
    title: '导航控制台',
    items: [
      {title: '创作中心', path: '/dashboard', icon: '🚀'},
      {title: '章节生成', path: '/chapter-generate', icon: '✨'}
    ]
  },
  {
    title: '核心管理',
    items: [
      {title: '世界观设定', path: '/world', icon: '🌍'},
      {title: '大纲管理', path: '/outline', icon: '📋'}
    ]
  },
  {
    title: '项目数据',
    items: [
      {title: '人物卡片', path: '/characters', icon: '👥'},
      {title: '人物关系', path: '/character-relations', icon: '🕸️'},
      {title: '组织势力', path: '/organizations', icon: '🏛️'},
      {title: '伏笔看板', path: '/foreshadowings', icon: '🎭'},
      {title: '长期记忆', path: '/memory', icon: '🧠'},
      {title: '项目配置', path: '/project-config', icon: '⚙️'}
    ]
  },
  {
    title: '配置',
    items: [{title: 'API 配置', path: '/api-config', icon: '🔌'}]
  }
]

const navTabs = groups.flatMap((group) => group.items)
tabsStore.sanitize()

function go(item: WorkspaceTab) {
  tabsStore.open(item)
  router.push(item.path)
}

function closeTab(path: string) {
  const closingActiveTab = route.path === path
  tabsStore.close(path)
  if (closingActiveTab && tabsStore.tabs.length > 0) {
    // 关闭当前标签后切到最后访问的标签；如果已经没有标签，就只清空标签栏，不做无效跳转。
    router.push(tabsStore.tabs[tabsStore.tabs.length - 1].path)
  }
}

watch(
    () => route.path,
    () => {
      const tab = navTabs.find((item) => item.path === route.path)
      // 标签只允许来自导航白名单；没有标题的临时路由不生成标签。
      // 注意：即使标签列表为空，只要当前路由是合法页面，也应该自动打开它，
      // 避免刷新后因缓存清空导致内容区空白。
      if (!tab) return
      tabsStore.open(tab)
    },
    {immediate: true}
)

onMounted(() => {
  projectStore.loadDefaultProject()
})
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 260px 1fr;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  border-right: 1px solid #2c3035;
  background: #171a1d;
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 18px 18px 14px;
  border-bottom: 1px solid #2c3035;
}

.brand strong {
  font-size: 17px;
}

.brand span {
  color: #9ca3af;
  font-size: 12px;
}

.nav-scroll {
  height: calc(100vh - 72px);
  overflow: auto;
}

.nav-group {
  padding: 12px 14px;
  border-bottom: 1px solid #24282d;
}

.group-title {
  margin: 0 0 6px;
  color: #c8d1df;
  font-size: 13px;
  font-weight: 700;
  text-align: left;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  height: 34px;
  padding: 0 12px;
  border: 0;
  border-left: 3px solid transparent;
  border-radius: 4px;
  color: #d1d5db;
  background: transparent;
  text-align: left;
  cursor: pointer;
  justify-content: flex-start;
}

.nav-item:hover,
.nav-item.active {
  border-left-color: #3b82f6;
  background: #22262b;
  color: #ffffff;
}

.workspace {
  min-width: 0;
  background: #151719;
}

.tabs {
  display: flex;
  height: 40px;
  overflow: hidden;
  border-bottom: 1px solid #30343a;
  background: #171a1d;
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 132px;
  max-width: 220px;
  padding: 0 10px;
  border: 0;
  border-right: 1px solid #30343a;
  color: #cbd5e1;
  background: #171a1d;
  cursor: pointer;
}

.tab.active {
  color: #ffffff;
  background: #202327;
}

.close {
  margin-left: auto;
  color: #9ca3af;
}

.content {
  height: calc(100vh - 40px);
  overflow: auto;
}
</style>
