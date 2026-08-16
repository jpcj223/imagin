import {defineStore} from 'pinia'
import {listProjects} from '@/api/projects'
import type {Project} from '@/types/domain'

export const useProjectStore = defineStore('project', {
    state: () => ({
        // 当前选中的小说项目。第一版默认取后端返回的第一个项目。
        currentProject: null as Project | null
    }),
    actions: {
        async loadDefaultProject() {
            // 多项目切换尚未实现前，所有页面都通过这个方法兜底拿到当前项目。
            const projects = await listProjects()
            this.currentProject = projects[0] ?? null
        }
    }
})
