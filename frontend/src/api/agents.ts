import { apiClient } from './client'
import type { ChapterDraftResult, ChapterSummary, ConsistencyCheckResult, ContextPreview, GenerationLog } from '@/types/domain'

export type ChapterDraftStreamEvent =
  | { type: 'start'; message: string; chapter_id?: number }
  | { type: 'delta'; content: string }
  | { type: 'done'; chapter_id: number; title: string; source: string }
  | { type: 'error'; message: string; trace?: string }

export interface ChapterDraftStreamHandlers {
  onStart?: (message: string, chapterId?: number) => void
  onDelta?: (content: string) => void
  onDone?: (result: Omit<ChapterDraftResult, 'content'>) => void
  onError?: (message: string) => void
}

export async function getAgentLogs(projectId: number, limit = 20) {
  // Agent 日志用于工作台右侧时间线，只读取最近记录，避免前端一次拉取过多历史。
  const { data } = await apiClient.get<GenerationLog[]>(`/agents/${projectId}/logs`, { params: { limit } })
  return data
}

export async function getChapterSummaries(projectId: number, limit = 20) {
  // 长期记忆第一版：先读取结构化章节摘要列表，未来可替换为检索排序结果。
  const { data } = await apiClient.get<ChapterSummary[]>(`/agents/${projectId}/summaries`, { params: { limit } })
  return data
}

export async function getContextPreview(projectId: number, chapterNo: number, outlineId?: number | null) {
  // 上下文包预览只读不写，用于生成前确认 Agent 实际会读取哪些资料。
  const { data } = await apiClient.get<ContextPreview>(`/agents/${projectId}/context-preview`, {
    params: { chapter_no: chapterNo, outline_id: outlineId ?? undefined }
  })
  return data
}

export async function draftChapter(payload: Record<string, unknown>) {
  // 章节生成：后端会读取大纲、世界观、角色、组织、伏笔等上下文。
  const { data } = await apiClient.post<ChapterDraftResult>('/agents/chapter-draft', payload)
  return data
}

export async function draftChapterStream(
  payload: Record<string, unknown>,
  handlers: ChapterDraftStreamHandlers
): Promise<Omit<ChapterDraftResult, 'content'> | null> {
  // 流式章节生成使用 fetch 读取 NDJSON；Axios 在浏览器侧不适合逐块消费响应体。
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), 300000)
  const response = await fetch('/backend-api/agents/chapter-draft/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: controller.signal
  })
  if (!response.ok || !response.body) {
    window.clearTimeout(timeoutId)
    throw new Error(`流式生成请求失败：${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let doneResult: Omit<ChapterDraftResult, 'content'> | null = null

  function consumeLine(line: string) {
    if (!line.trim()) return
    const event = JSON.parse(line) as ChapterDraftStreamEvent
    if (event.type === 'start') handlers.onStart?.(event.message, event.chapter_id)
    if (event.type === 'delta') handlers.onDelta?.(event.content)
    if (event.type === 'error') {
      handlers.onError?.(event.message)
      throw new Error(event.message)
    }
    if (event.type === 'done') {
      doneResult = {
        chapter_id: event.chapter_id,
        title: event.title,
        source: event.source
      }
      handlers.onDone?.(doneResult)
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
      throw new Error('流式生成超时：5 分钟内未完成')
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
    reader.releaseLock()
  }

  return doneResult
}

export async function analyzeChapter(payload: Record<string, unknown>) {
  // 章节分析：把正文拆成摘要、人物变化、世界观变化等长期记忆。
  const { data } = await apiClient.post<{
    chapter_id: number
    analysis: string
    summary: string
    character_changes: string
    world_changes: string
    new_foreshadowings: string
    timeline_events: string
  }>('/agents/chapter-analyze', payload)
  return data
}

export async function polishChapter(payload: Record<string, unknown>) {
  // 章节精修：保留事实基础上按指定模式重写当前章节。
  const { data } = await apiClient.post<{ chapter_id: number; content: string }>('/agents/polish', payload)
  return data
}

export async function checkConsistency(payload: Record<string, unknown>) {
  // 一致性检查：当前支持 fallback 结构化结果，后续可无缝接入真实模型判断。
  const { data } = await apiClient.post<ConsistencyCheckResult>('/agents/consistency-check', payload)
  return data
}

export async function analyzeVolume(payload: Record<string, unknown>) {
  // 卷分析：分析卷设定并自动更新大纲总览，为章节生成 Agent 提供创作方向。
  const { data } = await apiClient.post<{
    volume_id: number
    overview_id: number
    analysis: string
    main_plot: string
    core_conflict: string
    ending: string
    volume_summary: string
    chapter_suggestions: string
    source: string
  }>('/agents/volume-analyze', payload)
  return data
}
