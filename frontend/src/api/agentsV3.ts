import { apiClient } from './client'

// ============================================================
// 类型定义
// ============================================================

export interface WorkflowTemplate {
  name: string
  label: string
  description: string
  icon: string
  category: string
  step_count: number
}

export interface WorkflowStep {
  step_id: string
  agent_type: string
  variant: string
  label: string
  depends_on: string[]
}

export interface SkillInfo {
  name: string
  label: string
  description: string
  category: string
  agent_types: string[]
  priority: number
  is_core: boolean
}

export interface VariantInfo {
  name: string
  label: string
  icon: string
  description: string
  is_default: boolean
  skill_count?: number
}

export interface WorkflowRunRecord {
  id: number
  run_id: string
  project_id: number
  chapter_id: number | null
  outline_id: number | null
  template_name: string
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'
  current_step: string | null
  progress: number
  word_count: number
  output_preview: string
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface WorkflowStepRecord {
  id: number
  run_id: string
  step_id: string
  step_name: string
  agent_type: string
  variant_name: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  error_message: string | null
}

export interface GenerationVersion {
  id: number
  version_id: string
  chapter_id: number
  run_id: string | null
  version_number: number
  is_current: number
  word_count: number
  summary: string
  rating: number | null
  is_favorite: number
  created_at: string
}

// 工作流流式事件类型
export type WorkflowStreamEvent =
  | { type: 'step_start'; step_id: string; label: string }
  | { type: 'delta'; step_id: string; content: string }
  | { type: 'step_done'; step_id: string; result: Record<string, unknown> }
  | { type: 'workflow_done'; status: string; run_id: string; session_context: Record<string, unknown>; step_statuses: Record<string, string> }
  | { type: 'error'; step_id?: string; message: string; trace?: string }

export interface WorkflowStreamHandlers {
  onStepStart?: (stepId: string, label: string) => void
  onDelta?: (stepId: string, content: string) => void
  onStepDone?: (stepId: string, result: Record<string, unknown>) => void
  onWorkflowDone?: (status: string, runId: string, sessionContext: Record<string, unknown>) => void
  onError?: (message: string, stepId?: string) => void
}

// ============================================================
// 查询接口
// ============================================================

export async function getWorkflowTemplates() {
  const { data } = await apiClient.get<WorkflowTemplate[]>('/agents/v3/templates')
  return data
}

export async function getSkills(category?: string) {
  const { data } = await apiClient.get<SkillInfo[]>('/agents/v3/skills', { params: { category } })
  return data
}

export async function getVariants(agentType?: string) {
  const { data } = await apiClient.get<Record<string, VariantInfo[]>>('/agents/v3/variants', {
    params: { agent_type: agentType },
  })
  return data
}

// ============================================================
// 工作流执行
// ============================================================

export async function workflowGenerate(payload: Record<string, unknown>) {
  const { data } = await apiClient.post<{
    status: string
    run_id: string
    session_context: Record<string, unknown>
    step_statuses: Record<string, string>
  }>('/agents/v3/workflow/generate', payload)
  return data
}

export async function workflowGenerateStream(
  payload: Record<string, unknown>,
  handlers: WorkflowStreamHandlers,
): Promise<{ status: string; run_id: string; session_context: Record<string, unknown> } | null> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), 600000) // 10 分钟超时
  const response = await fetch('/backend-api/agents/v3/workflow/generate/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: controller.signal,
  })

  if (!response.ok || !response.body) {
    window.clearTimeout(timeoutId)
    throw new Error(`工作流请求失败：${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalResult: { status: string; run_id: string; session_context: Record<string, unknown> } | null = null

  function consumeLine(line: string) {
    if (!line.trim()) return
    try {
      const event = JSON.parse(line) as WorkflowStreamEvent
      switch (event.type) {
        case 'step_start':
          handlers.onStepStart?.(event.step_id, event.label)
          break
        case 'delta':
          handlers.onDelta?.(event.step_id, event.content)
          break
        case 'step_done':
          handlers.onStepDone?.(event.step_id, event.result)
          break
        case 'workflow_done':
          finalResult = {
            status: event.status,
            run_id: event.run_id,
            session_context: event.session_context,
          }
          handlers.onWorkflowDone?.(event.status, event.run_id, event.session_context)
          break
        case 'error':
          handlers.onError?.(event.message, event.step_id)
          throw new Error(event.message)
      }
    } catch (e) {
      if (e instanceof SyntaxError) {
        // 非 JSON 行忽略（可能是心跳或其他）
        return
      }
      throw e
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        consumeLine(line)
      }
    }
    buffer += decoder.decode()
    consumeLine(buffer)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('工作流执行超时：10 分钟内未完成')
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
    reader.releaseLock()
  }

  return finalResult
}

// ============================================================
// 断点续传
// ============================================================

export async function workflowResumeStream(
  payload: {
    run_id: string
    chapter_no: number
    outline_id?: number
    instruction?: string
    rhythm_level?: string
    restart_from_step_id?: string
  },
  handlers: WorkflowStreamHandlers,
): Promise<{ status: string; run_id: string; session_context: Record<string, unknown> } | null> {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), 600000)
  const response = await fetch('/backend-api/agents/v3/workflow/resume/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: controller.signal,
  })

  if (!response.ok || !response.body) {
    window.clearTimeout(timeoutId)
    throw new Error(`续传请求失败：${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalResult: { status: string; run_id: string; session_context: Record<string, unknown> } | null = null

  function consumeLine(line: string) {
    if (!line.trim()) return
    try {
      const event = JSON.parse(line) as WorkflowStreamEvent
      switch (event.type) {
        case 'step_start':
          handlers.onStepStart?.(event.step_id, event.label)
          break
        case 'delta':
          handlers.onDelta?.(event.step_id, event.content)
          break
        case 'step_done':
          handlers.onStepDone?.(event.step_id, event.result)
          break
        case 'workflow_done':
          finalResult = {
            status: event.status,
            run_id: event.run_id,
            session_context: event.session_context,
          }
          handlers.onWorkflowDone?.(event.status, event.run_id, event.session_context)
          break
        case 'error':
          handlers.onError?.(event.message, event.step_id)
          throw new Error(event.message)
      }
    } catch (e) {
      if (e instanceof SyntaxError) return
      throw e
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) consumeLine(line)
    }
    buffer += decoder.decode()
    consumeLine(buffer)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('工作流执行超时：10 分钟内未完成')
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
    reader.releaseLock()
  }

  return finalResult
}

// ============================================================
// 历史记录
// ============================================================

export async function getWorkflowRuns(
  projectId: number,
  options: { chapter_id?: number; status?: string; limit?: number; offset?: number } = {},
) {
  const { data } = await apiClient.get<WorkflowRunRecord[]>('/agents/v3/workflow/runs', {
    params: { project_id: projectId, ...options },
  })
  return data
}

export async function getWorkflowRunDetail(runId: string) {
  const { data } = await apiClient.get<{
    run: WorkflowRunRecord
    steps: WorkflowStepRecord[]
  }>(`/agents/v3/workflow/runs/${runId}`)
  return data
}

// ============================================================
// 版本管理
// ============================================================

export async function getGenerationVersions(chapterId: number, limit = 10) {
  const { data } = await apiClient.get<GenerationVersion[]>(`/agents/v3/versions/${chapterId}`, {
    params: { limit },
  })
  return data
}

export async function getVersionContent(chapterId: number, versionId: string) {
  const { data } = await apiClient.get<{ version_id: string; content: string }>(
    `/agents/v3/versions/${chapterId}/${versionId}/content`,
  )
  return data
}

export async function setCurrentVersion(chapterId: number, versionId: string) {
  const { data } = await apiClient.post<{
    success: boolean
    content: string
    version: GenerationVersion | null
  }>(`/agents/v3/versions/${chapterId}/set-current`, { version_id: versionId })
  return data
}

// ============================================================
// 记忆管理
// ============================================================

export async function getUserPreferences(projectId: number, projectLevel = true) {
  const { data } = await apiClient.get<Record<string, unknown>>('/agents/v3/memory/preferences', {
    params: { project_id: projectId, project_level: projectLevel },
  })
  return data
}

export async function updateUserPreferences(projectId: number, preferences: Record<string, unknown>, projectLevel = true) {
  const { data } = await apiClient.post<{ success: boolean }>('/agents/v3/memory/preferences', {
    project_id: projectId,
    preferences,
    project_level: projectLevel,
  })
  return data
}
