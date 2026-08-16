from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """创建小说项目时提交的基础信息。"""

    name: str = Field(default="新小说项目", description="书名或项目名称")
    theme: str = Field(default="", description="作品主题，例如复仇、成长、群像")
    novel_type: str = Field(default="", description="小说类型，例如玄幻、都市、科幻")
    target_words: int = Field(default=2500, description="单章目标字数")
    synopsis: str = Field(default="", description="项目简介或整体故事概述")


class ProjectUpdate(BaseModel):
    """更新项目配置时允许局部提交的字段。"""

    name: str | None = Field(default=None, description="书名或项目名称")
    theme: str | None = Field(default=None, description="作品主题")
    novel_type: str | None = Field(default=None, description="小说类型")
    target_words: int | None = Field(default=None, description="单章目标字数")
    synopsis: str | None = Field(default=None, description="项目简介")
    pace_level: int | None = Field(default=None, ge=1, le=5, description="整体节奏等级：1-慢热 到 5-高燃")
    view_point: str | None = Field(default=None, description="叙事视角：第一人称/第三人称有限/第三人称全知/第二人称")
    writing_style: str | None = Field(default=None, description="文风基调：严肃/轻松/热血/治愈/暗黑/史诗/其他")


class ModelConfigCreate(BaseModel):
    """OpenAI-compatible 模型连接配置。"""

    name: str = Field(default="默认模型", description="配置名称，便于区分不同模型服务")
    base_url: str = Field(description="OpenAI-compatible API 地址，通常以 /v1 结尾")
    api_key: str = Field(description="模型服务 API Key")
    model: str = Field(description="模型名称，例如 deepseek-v4-pro")
    is_active: bool = Field(default=True, description="是否设置为当前启用模型")
    temperature: float | None = Field(default=None, ge=0, le=2, description="采样温度，0-2")
    max_tokens: int | None = Field(default=None, gt=0, description="最大输出 token 数")
    top_p: float | None = Field(default=None, ge=0, le=1, description="nucleus 采样概率，0-1")
    frequency_penalty: float | None = Field(default=None, ge=-2, le=2, description="频率惩罚，-2到2")
    presence_penalty: float | None = Field(default=None, ge=-2, le=2, description="存在惩罚，-2到2")
    proxy_url: str | None = Field(default=None, description="HTTP 代理地址，如 http://127.0.0.1:7890")


class WorldSettingSave(BaseModel):
    """世界观设定保存请求。"""

    project_id: int = Field(description="所属项目 ID")
    title: str = Field(default="", description="设定标题，便于在设定库中快速识别")
    category: str = Field(default="other", description="设定分类：era/location/power/rule/taboo/term/other")
    era: str = Field(default="", description="时代背景")
    geography: str = Field(default="", description="地点、地理和空间结构设定")
    atmosphere: str = Field(default="", description="整体氛围与叙事基调")
    rules: str = Field(default="", description="世界运行规则、限制和禁忌")
    extra: str = Field(default="", description="补充设定")
    tags: str = Field(default="", description="标签，逗号分隔")
    importance: str = Field(default="medium", description="重要性：low/medium/high")
    related_chapters: str = Field(default="", description="关联章节号或范围，文本形式预留")
    related_characters: str = Field(default="", description="关联角色 ID，逗号分隔")
    related_organizations: str = Field(default="", description="关联组织 ID，逗号分隔")
    related_foreshadowings: str = Field(default="", description="关联伏笔 ID，逗号分隔")
    conflict_notes: str = Field(default="", description="潜在冲突或一致性风险备注")


class OutlineSave(BaseModel):
    """大纲节点保存请求，既可以表示卷，也可以表示章。"""

    project_id: int = Field(description="所属项目 ID")
    title: str = Field(description="大纲标题")
    node_type: str = Field(default="chapter", description="节点类型：chapter 章，volume 卷")
    status: str = Field(default="draft", description="大纲状态：draft 草稿，confirmed 已确认")
    volume_no: int | None = Field(default=None, description="卷号，仅卷级节点需要")
    chapter_no: int | None = Field(default=None, description="章节号，章节生成时用于匹配")
    sort_index: int = Field(default=0, description="排序索引，用于无章节号时的显示顺序")
    description: str = Field(default="", description="剧情目标、冲突、场景、钩子等章节说明")


class ChapterSave(BaseModel):
    """章节草稿保存请求。"""

    project_id: int = Field(description="所属项目 ID")
    outline_id: int | None = Field(default=None, description="关联的大纲节点 ID")
    chapter_no: int = Field(description="章节号")
    title: str = Field(description="章节标题")
    content: str = Field(default="", description="章节正文")
    status: str = Field(default="draft", description="章节状态，第一版默认 draft")


class CharacterSave(BaseModel):
    """角色卡保存请求。"""

    project_id: int = Field(description="所属项目 ID")
    name: str = Field(description="角色名称")
    role_type: str = Field(default="supporting", description="角色类型：protagonist/supporting/antagonist")
    identity: str = Field(default="", description="身份、职业或表层定位")
    faction: str = Field(default="", description="阵营或所属势力")
    mbti: str = Field(default="", description="MBTI 或其他性格类型标签")
    appearance: str = Field(default="", description="外貌特征")
    personality: str = Field(default="", description="性格特征和行为倾向")
    background: str = Field(default="", description="背景故事")
    motivation: str = Field(default="", description="核心动机")
    weakness: str = Field(default="", description="弱点、缺陷或容易被利用的点")
    secret: str = Field(default="", description="角色秘密或隐藏信息")
    dialogue_style: str = Field(default="", description="对白风格和常用表达")
    arc: str = Field(default="", description="人物成长线或变化方向")
    relationships: str = Field(default="", description="关系摘要，文本形式预留")
    chapters: str = Field(default="", description="出场章节，文本形式预留")
    organization_ids: str = Field(default="", description="关联组织 ID，逗号分隔")
    related_character_ids: str = Field(default="", description="关联角色 ID，逗号分隔")
    ai_notes: str = Field(default="", description="AI 建议或一致性检查备注")


class OrganizationSave(BaseModel):
    """组织势力保存请求。"""

    project_id: int = Field(description="所属项目 ID")
    name: str = Field(description="组织名称")
    org_type: str = Field(default="", description="组织类型，例如宗门、公司、帮派、官方机构")
    location: str = Field(default="", description="组织所在地或势力范围")
    slogan: str = Field(default="", description="宗旨、口号或核心信条")
    description: str = Field(default="", description="组织背景、目标、资源和叙事用途")
    hierarchy: str = Field(default="", description="组织层级、职级或内部结构")
    resources: str = Field(default="", description="核心资源、人脉、资产或能力")
    goal: str = Field(default="", description="组织目标或当前战略")
    level: int = Field(default=1, description="组织层级，1-10")
    power_level: int = Field(default=5, description="组织实力等级，1-10")
    member_count: int = Field(default=0, description="成员总数")
    status: str = Field(default="", description="组织当前状态，例如隐世、扩张、衰落")
    core_members: str = Field(default="", description="核心成员，文本形式预留")
    allies: str = Field(default="", description="盟友组织")
    enemies: str = Field(default="", description="敌对组织")
    impact: str = Field(default="", description="对剧情推进的影响")
    risk_notes: str = Field(default="", description="组织设定风险或冲突提示")


class ForeshadowingSave(BaseModel):
    """伏笔保存请求。"""

    project_id: int = Field(description="所属项目 ID")
    keyword: str = Field(description="伏笔关键词，用于快速识别")
    description: str = Field(description="伏笔内容、出现方式和意义")
    status: str = Field(default="pending", description="状态：pending/planted/developing/resolved/abandoned")
    importance: str = Field(default="medium", description="重要性：low/medium/high")
    planted_chapter: int | None = Field(default=None, description="首次埋下伏笔的章节号")
    payoff_chapter: int | None = Field(default=None, description="计划或实际回收伏笔的章节号")
    effective_from: int | None = Field(default=None, description="伏笔开始生效的章节号")
    expires_at: int | None = Field(default=None, description="伏笔过期或失效章节号")
    notes: str = Field(default="", description="备注信息")
    related_character_ids: str = Field(default="", description="关联角色 ID，逗号分隔")
    related_organization_ids: str = Field(default="", description="关联组织 ID，逗号分隔")
    related_outline_ids: str = Field(default="", description="关联大纲 ID，逗号分隔")


class ChapterDraftRequest(BaseModel):
    """章节生成 Agent 请求。"""

    project_id: int = Field(description="所属项目 ID")
    chapter_no: int = Field(description="要生成或覆盖的章节号")
    outline_id: int | None = Field(default=None, description="指定使用的大纲 ID")
    chapter_id: int | None = Field(default=None, description="指定覆盖的已有章节 ID")
    instruction: str = Field(default="", description="用户对本章的补充目标或限制")
    rhythm_level: str = Field(default="3 - 适中", description="章节节奏等级")


class ChapterAnalyzeRequest(BaseModel):
    """章节分析 Agent 请求。"""

    project_id: int = Field(description="所属项目 ID")
    chapter_id: int = Field(description="要分析的章节 ID")
    content: str = Field(description="章节正文")


class PolishRequest(BaseModel):
    """章节精修 Agent 请求。"""

    project_id: int = Field(description="所属项目 ID")
    chapter_id: int = Field(description="要精修的章节 ID")
    mode: str = Field(default="增强冲突", description="精修模式，例如增强冲突、增强对白、去 AI 味")
    instruction: str = Field(default="", description="用户补充精修要求")


class ConsistencyCheckRequest(BaseModel):
    """一致性检查 Agent 请求。

    当前先支持 fallback 结构化检查，后续接入真实模型时仍复用同一个入口。
    """

    project_id: int = Field(description="所属项目 ID")
    chapter_id: int | None = Field(default=None, description="可选章节 ID")
    content: str = Field(default="", description="待检查正文或片段")
