import { defineStore } from 'pinia'
import { listProjects, createProject, deleteProject, getProject } from '@/api/projects'
import type { Project } from '@/types/domain'
import { notify } from '@/utils/notify'

const LAST_PROJECT_KEY = 'yixiang:last-project-id'

export const useProjectStore = defineStore('project', {
  state: () => ({
    /** 项目列表。 */
    projects: [] as Project[],
    /** 当前选中的小说项目。 */
    currentProject: null as Project | null,
    /** 是否正在加载中。 */
    loading: false,
  }),
  actions: {
    /**
     * 加载项目列表并恢复上次选中的项目。
     * - 首次加载：从 localStorage 读取 last-project-id，有则选中那个项目，否则选第一个。
     * - 如果列表为空，返回 null。
     */
    async loadProjects() {
      this.loading = true
      try {
        this.projects = await listProjects()
        // 尝试恢复上次选中的项目
        const lastId = Number(localStorage.getItem(LAST_PROJECT_KEY))
        if (lastId && this.projects.some((p) => p.id === lastId)) {
          this.currentProject = this.projects.find((p) => p.id === lastId)!
        } else if (this.projects.length > 0) {
          this.currentProject = this.projects[0]
        } else {
          this.currentProject = null
        }
      } catch {
        notify.error('加载项目列表失败')
      } finally {
        this.loading = false
      }
    },

    /**
     * 兼容旧调用：兜底加载默认项目。
     * 新代码请用 loadProjects()。
     */
    async loadDefaultProject() {
      if (this.projects.length === 0) {
        await this.loadProjects()
      }
      return this.currentProject
    },

    /** 切换到指定项目，同时写入 localStorage 以便下次恢复。 */
    async switchTo(projectId: number) {
      const target = this.projects.find((p) => p.id === projectId)
      if (!target) {
        notify.error('项目不存在')
        return
      }
      this.currentProject = target
      localStorage.setItem(LAST_PROJECT_KEY, String(projectId))
    },

    /** 刷新当前项目详情（保存后调用，同步最新数据）。 */
    async refreshCurrent() {
      if (!this.currentProject) return
      try {
        const fresh = await getProject(this.currentProject.id)
        this.currentProject = fresh
        // 同步更新列表中的对应项
        const idx = this.projects.findIndex((p) => p.id === fresh.id)
        if (idx >= 0) this.projects[idx] = fresh
      } catch {
        notify.error('刷新项目数据失败')
      }
    },

    /** 新建项目并自动切换过去。 */
    async createNew(name: string) {
      try {
        const newProject = await createProject({ name })
        this.projects.unshift(newProject)
        this.currentProject = newProject
        localStorage.setItem(LAST_PROJECT_KEY, String(newProject.id))
        notify.success(`已创建项目「${name}」`)
        return newProject
      } catch {
        notify.error('创建项目失败')
        return null
      }
    },

    /**
     * 删除项目。
     * - 如果删除的是当前项目，自动切到第一个剩余项目。
     * - 至少保留一个项目（后端也会校验）。
     */
    async remove(projectId: number) {
      try {
        await deleteProject(projectId)
        this.projects = this.projects.filter((p) => p.id !== projectId)
        // 如果删的是当前项目，切到第一个剩余项目
        if (this.currentProject?.id === projectId) {
          if (this.projects.length > 0) {
            this.currentProject = this.projects[0]
            localStorage.setItem(LAST_PROJECT_KEY, String(this.projects[0].id))
          } else {
            this.currentProject = null
            localStorage.removeItem(LAST_PROJECT_KEY)
          }
        }
        notify.success('项目已删除')
        return true
      } catch {
        notify.error('删除失败')
        return false
      }
    },
  },
})
