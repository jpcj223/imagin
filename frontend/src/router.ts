import {createRouter, createWebHistory} from 'vue-router'
import DashboardPage from '@/pages/DashboardPage.vue'
import ApiConfigPage from '@/pages/ApiConfigPage.vue'
import ProjectConfigPage from '@/pages/ProjectConfigPage.vue'
import WorldSettingPage from '@/pages/WorldSettingPage.vue'
import OutlinePage from '@/pages/OutlinePage.vue'
import ChapterGeneratePage from '@/pages/ChapterGeneratePage.vue'
import CharacterPage from '@/pages/CharacterPage.vue'
import OrganizationPage from '@/pages/OrganizationPage.vue'
import ForeshadowingPage from '@/pages/ForeshadowingPage.vue'
import MemoryCenterPage from '@/pages/MemoryCenterPage.vue'
import CharacterRelationsPage from '@/pages/CharacterRelationsPage.vue'
import UserManagePage from '@/pages/system/UserManagePage.vue'
import MenuManagePage from '@/pages/system/MenuManagePage.vue'
import DictManagePage from '@/pages/system/DictManagePage.vue'
import SystemConfigPage from '@/pages/system/SystemConfigPage.vue'


const router = createRouter({
    history: createWebHistory(),
    routes: [
        {path: '/', redirect: '/dashboard'},
        {path: '/dashboard', component: DashboardPage, meta: {title: '创作中心', icon: '🚀'}},
        {path: '/api-config', component: ApiConfigPage, meta: {title: 'API 配置', icon: '🔌'}},
        {path: '/project-config', component: ProjectConfigPage, meta: {title: '项目配置', icon: '⚙️'}},
        {path: '/world', component: WorldSettingPage, meta: {title: '世界观设定', icon: '🌍'}},
        {path: '/outline', component: OutlinePage, meta: {title: '大纲管理', icon: '📋'}},
        {path: '/chapter-generate', component: ChapterGeneratePage, meta: {title: '章节生成', icon: '✨'}},
        {path: '/characters', component: CharacterPage, meta: {title: '人物卡片', icon: '👥'}},
        {path: '/character-relations', component: CharacterRelationsPage, meta: {title: '人物关系', icon: '🕸️'}},
        {path: '/organizations', component: OrganizationPage, meta: {title: '组织势力', icon: '🏛️'}},
        {path: '/foreshadowings', component: ForeshadowingPage, meta: {title: '伏笔看板', icon: '🎭'}},
        {path: '/memory', component: MemoryCenterPage, meta: {title: '长期记忆', icon: '🧠'}},
        // 系统管理
        {path: '/system/users', component: UserManagePage, meta: {title: '用户管理', icon: '👥'}},
        {path: '/system/menus', component: MenuManagePage, meta: {title: '菜单管理', icon: '📋'}},
        {path: '/system/dictionaries', component: DictManagePage, meta: {title: '字典管理', icon: '📚'}},
        {path: '/system/configs', component: SystemConfigPage, meta: {title: '系统配置', icon: '🔧'}},
    ]
})

export default router
