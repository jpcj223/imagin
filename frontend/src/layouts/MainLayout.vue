<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <strong>臆想</strong>
        <span>AI 小说创作工作台</span>
      </div>

      <div class="nav-scroll">
        <n-spin v-if="menuStore.loading" size="small" class="nav-loading">
          <span>加载菜单中...</span>
        </n-spin>

        <template v-else>
          <!-- 平铺菜单项 + 可展开分组 -->
          <div class="nav-list">
            <template v-for="item in menuStore.visibleTree" :key="item.id">
              <!-- 目录型菜单（有子项） -->
              <div v-if="item.menu_type === 'dir' && item.children?.length" class="nav-group">
                <div class="group-title">{{ item.name }}</div>
                <button
                  v-for="child in item.children"
                  :key="child.path"
                  class="nav-item"
                  :class="{ active: route.path === child.path && tabsStore.isRouteOpen(child.path) }"
                  @click="go(child)"
                >
                  <span class="nav-icon">{{ child.icon }}</span>
                  <span class="nav-text">{{ child.name }}</span>
                </button>
              </div>

              <!-- 普通菜单（无子项） -->
              <button
                v-else-if="item.menu_type === 'menu'"
                class="nav-item single"
                :class="{ active: route.path === item.path && tabsStore.isRouteOpen(item.path) }"
                @click="go(item)"
              >
                <span class="nav-icon">{{ item.icon }}</span>
                <span class="nav-text">{{ item.name }}</span>
              </button>
            </template>
          </div>
        </template>
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
import {useMenuStore, type MenuItem} from '@/stores/menu'
import { useDictStore } from '@/stores/dict'

const router = useRouter()
const route = useRoute()
const projectStore = useProjectStore()
const tabsStore = useWorkspaceTabsStore()
const menuStore = useMenuStore()
const dictStore = useDictStore()

tabsStore.sanitize()

/** 将菜单项转为标签页格式 */
function toTab(item: MenuItem): WorkspaceTab {
  return {
    title: item.name,
    path: item.path,
    icon: item.icon,
  }
}

function go(item: MenuItem) {
  tabsStore.open(toTab(item))
  router.push(item.path)
}

function closeTab(path: string) {
  const closingActiveTab = route.path === path
  tabsStore.close(path)
  if (closingActiveTab && tabsStore.tabs.length > 0) {
    router.push(tabsStore.tabs[tabsStore.tabs.length - 1].path)
  }
}

/**
 * 根据路由路径匹配对应的菜单项（支持多层级查找）
 */
function findMenuByPath(path: string): MenuItem | undefined {
  return menuStore.findByPath(path)
}

watch(
    () => route.path,
    () => {
      const menuItem = findMenuByPath(route.path)
      // 只有找到对应菜单项的路由才自动打开标签
      if (!menuItem) return
      tabsStore.open(toTab(menuItem))
    },
    {immediate: true}
)

onMounted(async () => {
  // 先加载菜单
  await menuStore.load()
  // 菜单加载完成后，确保当前路由对应的标签已打开
  const currentMenu = menuStore.findByPath(route.path)
  if (currentMenu) {
    // 当前路由有对应菜单项，打开它
    if (!tabsStore.isRouteOpen(route.path)) {
      tabsStore.open(toTab(currentMenu))
    }
  } else {
    // 当前路由没有对应菜单项，跳转到第一个可用菜单
    const firstPath = menuStore.firstMenuPath
    const firstMenu = menuStore.findByPath(firstPath)
    if (firstMenu) {
      tabsStore.open(toTab(firstMenu))
      router.replace(firstPath)
    }
  }
  // 加载常用字典（预加载，提升后续页面体验）
  dictStore.loadBatch(['novel_type', 'importance', 'character_role', 'foreshadowing_status', 'writing_style', 'view_point'])
  // 加载默认项目
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

.nav-loading {
  display: flex;
  justify-content: center;
  padding: 40px 0;
  color: #9ca3af;
  font-size: 13px;
}

.nav-list {
  padding: 8px 0;
}

.nav-group {
  padding: 8px 14px 12px;
  border-bottom: 1px solid #24282d;
}

.group-title {
  margin: 4px 0 8px;
  padding: 0 12px;
  color: #c8d1df;
  font-size: 12px;
  font-weight: 600;
  text-align: left;
  letter-spacing: 0.5px;
  opacity: 0.85;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  height: 36px;
  padding: 0 12px;
  border: 0;
  border-left: 3px solid transparent;
  border-radius: 4px;
  color: #d1d5db;
  background: transparent;
  text-align: left;
  cursor: pointer;
  justify-content: flex-start;
  transition: all 0.15s ease;
}

.nav-icon {
  font-size: 15px;
  width: 18px;
  text-align: center;
  flex-shrink: 0;
}

.nav-text {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-item:hover,
.nav-item.active {
  border-left-color: #3b82f6;
  background: #22262b;
  color: #ffffff;
}

.nav-item.single {
  margin: 2px 0;
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
