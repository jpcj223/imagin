export interface Project {
  /** 项目 ID，后端自增主键。 */
  id: number
  /** 书名或项目名。 */
  name: string
  /** 作品主题，例如成长、复仇、群像。 */
  theme: string
  /** 小说类型，例如玄幻、都市、科幻。 */
  novel_type: string
  /** 单章目标字数。 */
  target_words: number
  /** 项目简介或故事概述。 */
  synopsis: string
}

export interface DashboardCounts {
  /** 角色卡数量。 */
  characters: number
  /** 大纲节点数量。 */
  outlines: number
  /** 章节草稿数量。 */
  chapters: number
  /** 伏笔数量。 */
  foreshadowings: number
}

export interface ChapterDraftResult {
  /** 生成或覆盖后的章节 ID。 */
  chapter_id: number
  /** 章节标题。 */
  title: string
  /** 章节正文。 */
  content: string
  /** 结果来源：llm 表示真实模型，fallback 表示开发模式草稿。 */
  source: string
}

export interface GenerationLog {
  /** 日志 ID，按生成顺序递增。 */
  id: number
  /** 所属项目 ID。 */
  project_id: number
  /** 任务类型：chapter_draft / chapter_analyze / chapter_polish。 */
  task_type: string
  /** 本次任务的简要请求信息。 */
  request: string
  /** 本次任务的简要响应或来源说明。 */
  response: string
  /** 任务状态，第一版主要为 success。 */
  status: string
  /** 失败时的错误信息。 */
  error: string
  /** 日志创建时间。 */
  created_at: string
}

export interface ChapterSummary {
  /** 摘要记录 ID。 */
  id: number
  /** 对应章节 ID。 */
  chapter_id: number
  /** 章节号。 */
  chapter_no: number
  /** 章节标题。 */
  title: string
  /** 章节摘要。 */
  summary: string
  /** 人物变化摘要。 */
  character_changes: string
  /** 世界观变化摘要。 */
  world_changes: string
  /** 新增伏笔摘要。 */
  new_foreshadowings: string
  /** 时间线事件。 */
  timeline_events: string
  /** 摘要创建时间。 */
  created_at: string
}

export interface ConsistencyCheckResult {
  /** 风险等级：low / medium / high。 */
  risk_level: string
  /** 缺失资料项。 */
  missing: string[]
  /** AI 或 fallback 给出的处理建议。 */
  suggestions: string[]
  /** 本次检查读取到的上下文数量统计。 */
  context_stats: Record<string, number>
}

export interface ContextPreview {
  /** 本次预览的章节号。 */
  chapter_no: number
  /** 实际选中的大纲摘要。 */
  outline: { title: string; description: string }
  /** 实际选中的世界观摘要。 */
  world: { title: string; category: string; rules: string }
  /** 会进入上下文的角色摘录。 */
  characters: Array<{ id: number; name: string; role_type: string; motivation: string }>
  /** 会进入上下文的组织摘录。 */
  organizations: Array<{ id: number; name: string; goal: string; power_level: number }>
  /** 会进入上下文的伏笔摘录。 */
  foreshadowings: Array<{ id: number; keyword: string; status: string; payoff_chapter: number | null }>
  /** 最近章节摘要摘录。 */
  recent_summaries: Array<{ id: number; summary: string; timeline_events: string }>
}

export interface WorldSetting {
  /** 世界观 ID。 */
  id: number
  /** 所属项目 ID。 */
  project_id: number
  /** 设定标题。 */
  title: string
  /** 设定分类：era/location/power/rule/taboo/term/other。 */
  category: string
  /** 时代背景。 */
  era: string
  /** 地理、地点和空间结构设定。 */
  geography: string
  /** 叙事氛围和整体基调。 */
  atmosphere: string
  /** 世界规则、限制和禁忌。 */
  rules: string
  /** 补充设定。 */
  extra: string
  /** 标签，逗号分隔。 */
  tags: string
  /** 重要性：low/medium/high。 */
  importance: string
  /** 关联章节号或范围。 */
  related_chapters: string
  /** 关联角色 ID，逗号分隔。 */
  related_characters: string
  /** 关联组织 ID，逗号分隔。 */
  related_organizations: string
  /** 关联伏笔 ID，逗号分隔。 */
  related_foreshadowings: string
  /** 潜在冲突备注。 */
  conflict_notes: string
}

export interface OutlineItem {
  /** 大纲节点 ID。 */
  id: number
  /** 所属项目 ID。 */
  project_id: number
  /** 大纲标题。 */
  title: string
  /** 节点类型：chapter 章，volume 卷。 */
  node_type: string
  /** 大纲状态：draft 草稿，confirmed 已确认。 */
  status: string
  /** 卷号，仅卷级节点需要。 */
  volume_no: number | null
  /** 章节号，章节生成时用于匹配。 */
  chapter_no: number | null
  /** 排序索引，用于无章节号时兜底排序。 */
  sort_index: number
  /** 本节点的剧情目标、冲突和场景说明。 */
  description: string
}

export interface ChapterItem {
  /** 章节 ID。 */
  id: number
  /** 所属项目 ID。 */
  project_id: number
  /** 关联的大纲节点 ID。 */
  outline_id: number | null
  /** 章节号。 */
  chapter_no: number
  /** 章节标题。 */
  title: string
  /** 章节正文。 */
  content: string
  /** 章节状态，第一版默认 draft。 */
  status: string
}

export interface CharacterItem {
  /** 角色 ID。 */
  id: number
  /** 所属项目 ID。 */
  project_id: number
  /** 角色名称。 */
  name: string
  /** 角色类型：protagonist/supporting/antagonist。 */
  role_type: string
  /** 身份、职业或表层定位。 */
  identity: string
  /** 阵营或所属势力。 */
  faction: string
  /** MBTI 或其他性格标签。 */
  mbti: string
  /** 外貌特征。 */
  appearance: string
  /** 性格特征和行为倾向。 */
  personality: string
  /** 背景故事。 */
  background: string
  /** 核心动机。 */
  motivation: string
  /** 弱点或缺陷。 */
  weakness: string
  /** 角色秘密。 */
  secret: string
  /** 对白风格。 */
  dialogue_style: string
  /** 人物成长线或变化方向。 */
  arc: string
  /** 关系摘要。 */
  relationships: string
  /** 出场章节。 */
  chapters: string
  /** 关联组织 ID，逗号分隔。 */
  organization_ids: string
  /** 关联角色 ID，逗号分隔。 */
  related_character_ids: string
  /** AI 建议或一致性检查备注。 */
  ai_notes: string
}

export interface OrganizationItem {
  /** 组织 ID。 */
  id: number
  /** 所属项目 ID。 */
  project_id: number
  /** 组织名称。 */
  name: string
  /** 组织类型，例如宗门、公司、帮派。 */
  org_type: string
  /** 组织所在地或势力范围。 */
  location: string
  /** 宗旨、口号或核心信条。 */
  slogan: string
  /** 组织背景、目标、资源和叙事用途。 */
  description: string
  /** 组织层级和内部结构说明。 */
  hierarchy: string
  /** 核心资源。 */
  resources: string
  /** 组织目标。 */
  goal: string
  /** 组织层级，1-10。 */
  level: number
  /** 组织实力等级，1-10。 */
  power_level: number
  /** 成员总数。 */
  member_count: number
  /** 组织当前状态，例如隐世、扩张、衰落。 */
  status: string
  /** 核心成员。 */
  core_members: string
  /** 盟友组织。 */
  allies: string
  /** 敌对组织。 */
  enemies: string
  /** 对剧情的影响。 */
  impact: string
  /** 风险提示。 */
  risk_notes: string
}

export interface ForeshadowingItem {
  /** 伏笔 ID。 */
  id: number
  /** 所属项目 ID。 */
  project_id: number
  /** 伏笔关键词。 */
  keyword: string
  /** 伏笔内容、出现方式和意义。 */
  description: string
  /** 状态：pending/planted/developing/resolved/abandoned。 */
  status: string
  /** 重要性：low/medium/high。 */
  importance: string
  /** 首次埋下伏笔的章节号。 */
  planted_chapter: number | null
  /** 计划或实际回收伏笔的章节号。 */
  payoff_chapter: number | null
  /** 伏笔开始生效的章节号。 */
  effective_from: number | null
  /** 伏笔失效或过期章节号。 */
  expires_at: number | null
  /** 备注信息。 */
  notes: string
  /** 关联角色 ID，逗号分隔。 */
  related_character_ids: string
  /** 关联组织 ID，逗号分隔。 */
  related_organization_ids: string
  /** 关联大纲 ID，逗号分隔。 */
  related_outline_ids: string
}
