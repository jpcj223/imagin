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
  /** 默认节奏等级：1-平淡 / 2-渐入 / 3-适中 / 4-紧凑 / 5-高潮。 */
  pace_level: number
  /** 叙事视角：第一人称/第三人称有限/第三人称全知/第二人称。 */
  view_point: string
  /** 文风基调：严肃/轻松/热血/治愈/暗黑/史诗/其他。 */
  writing_style: string
  /** 创建时间（ISO 字符串）。 */
  created_at: string
  /** 最后更新时间（ISO 字符串）。 */
  updated_at: string
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
  /** 组织数量。 */
  organizations: number
  /** 世界观设定数量。 */
  world_settings: number
}

export interface DashboardRecentChapter {
  id: number
  chapter_no: number
  title: string
  status: string
  char_count: number
  updated_at: string
}

export interface DashboardData {
  counts: DashboardCounts
  /** 全文字符总数。 */
  total_chars: number
  /** 最近章节列表。 */
  recent_chapters: DashboardRecentChapter[]
  /** 伏笔按状态分布。 */
  foreshadowing_by_status: Record<string, number>
  /** 角色按类型分布。 */
  characters_by_type: Record<string, number>
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
  /** 扩展字段，JSON 格式存储卷/章节的精细化数据。 */
  extra: string
  /** 所属卷 ID，仅章节节点需要。 */
  volume_id: number | null
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
  /** MBTI 主性格类型，例如 INTJ。 */
  mbti_primary: string
  /** MBTI 辅助/外在表现类型，可选。 */
  mbti_secondary: string
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
  /** 关系摘要（旧字段，保留兼容）。 */
  relationships: string
  /** 出场章节。 */
  chapters: string
  /** 关联组织 ID，逗号分隔（旧字段，保留兼容）。 */
  organization_ids: string
  /** 关联角色 ID，逗号分隔（旧字段，保留兼容）。 */
  related_character_ids: string
  /** AI 建议或一致性检查备注。 */
  ai_notes: string
  /** 动态属性列表（JSON 数组），用户可自定义添加，适配不同题材。 */
  custom_attributes: CharacterAttribute[]
  /** 组织关系列表（JSON 数组），结构化替代 organization_ids。 */
  org_relations: CharacterOrgRelation[]
  /** 人物关系列表（JSON 数组），结构化替代 related_character_ids。 */
  character_relations: CharacterRelation[]
  /** 旧版 MBTI 字段，保留用于数据迁移兼容。 */
  mbti: string
}

/** 角色动态属性：用户可自定义的扩展属性，解决"人物扩展难"问题。 */
export interface CharacterAttribute {
  /** 属性名称，如"武功"、"宝物"、"职称"。 */
  name: string
  /** 属性值。 */
  value: string
  /** 当前章节号，记录该属性在剧情哪个时间点的状态，可选。 */
  chapter_no?: number | null
  /** 变更原因，可选。 */
  change_reason?: string
}

/** 角色-组织关系：结构化的组织归属数据。 */
export interface CharacterOrgRelation {
  /** 组织 ID。 */
  org_id: number
  /** 在组织中的职位。 */
  position: string
  /** 忠诚值 1-10。 */
  loyalty: number
}

/** 角色-角色关系：结构化的人物关系数据，支持随剧情演变。 */
export interface CharacterRelation {
  /** 目标角色 ID。 */
  target_id: number
  /** 关系类型：师徒/兄弟/恋人/仇敌/其他等。 */
  relation_type: string
  /** 关系深度 1-10。 */
  depth: number
  /** 生效起始章节，可选。 */
  effective_from?: number | null
  /** 失效章节，可选，不填则一直有效。 */
  expires_at?: number | null
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
  /** 核心成员（旧版字符串字段，保留兼容）。 */
  core_members: string
  /** 盟友组织 ID，逗号分隔。 */
  allies: string
  /** 敌对组织 ID，逗号分隔。 */
  enemies: string
  /** 对剧情的影响。 */
  impact: string
  /** 风险提示。 */
  risk_notes: string
  /** 隐藏设定：仅作者可见的秘密/暗线。 */
  hidden_secrets: string
  /** 主效起始章节号。 */
  active_from_chapter: number | null
  /** 覆灭/解散章节号，NULL 表示一直有效。 */
  disbanded_chapter: number | null
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
  /** 被替代伏笔 ID：此伏笔被哪个新伏笔替代，形成替代链。 */
  replaced_by_id: number | null
}
