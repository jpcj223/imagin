"""核心写作 Skill。

这是 Writer Agent 必须的核心 Skill，负责构建基础写作 Prompt。
"""
from __future__ import annotations

from app.skills.base import BaseSkill, SkillMeta
from app.skills.registry import SkillRegistry


@SkillRegistry.register("core_writing")
class CoreWritingSkill(BaseSkill):
    """核心写作 Skill。

    构建基础的章节写作 Prompt，是 Writer Agent 的必备核心能力。
    """

    meta = SkillMeta(
        name="core_writing",
        label="正文生成",
        description="构建基础章节写作 Prompt，是 Writer Agent 的核心能力",
        category="writing",
        agent_types=["writer"],
        priority=10,
        is_core=True,
    )

    prompt_fragment = """
请严格依据项目资料、世界观、角色、人设、伏笔和章节大纲写作，避免设定漂移。
输出中文小说正文，保持连载网文节奏，不要解释你的写作过程。
""".strip()

    required_context = ["project", "outline", "characters"]

    def pre_process(self, context, params):
        """构建写作上下文文本。"""
        # 把结构化上下文压缩成写作资料包
        project = context.get("project", {})
        world = context.get("world", {})
        outline = context.get("outline", {})
        characters = context.get("characters", [])
        organizations = context.get("organizations", [])
        foreshadowings = context.get("foreshadowings", [])
        recent_summaries = context.get("recent_summaries", [])

        context_text = f"""
项目：{project.get("name", "")}
世界观：{_format_world(world)}
本章大纲：{_format_outline(outline)}
角色：{_format_characters(characters)}
组织：{_format_organizations(organizations)}
待处理伏笔：{_format_foreshadowings(foreshadowings)}
最近章节摘要：{_format_summaries(recent_summaries)}
""".strip()

        context["_writing_context"] = context_text
        return context


def _format_world(world: dict) -> str:
    if not world:
        return "暂无世界观设定"
    parts = []
    if world.get("title") or world.get("era"):
        parts.append(f"时代/背景：{world.get('title') or world.get('era', '')}")
    if world.get("rules"):
        parts.append(f"核心规则：{world['rules']}")
    if world.get("geography"):
        parts.append(f"地理环境：{world['geography']}")
    return "；".join(parts) if parts else "暂无详细设定"


def _format_outline(outline: dict) -> str:
    if not outline:
        return "暂无大纲"
    title = outline.get("title", "")
    desc = outline.get("description", "")
    return f"{title} - {desc}" if desc else title


def _format_characters(characters: list[dict]) -> str:
    if not characters:
        return "暂无角色资料"
    lines = []
    for ch in characters[:8]:  # 最多展示 8 个
        name = ch.get("name", "")
        role = ch.get("role_type", "")
        personality = ch.get("personality", "")
        motivation = ch.get("motivation", "")
        info = f"{name}（{role}）"
        if personality:
            info += f" - 性格：{personality[:30]}"
        if motivation:
            info += f" - 动机：{motivation[:30]}"
        lines.append(info)
    return "\n".join(lines)


def _format_organizations(organizations: list[dict]) -> str:
    if not organizations:
        return "暂无组织资料"
    lines = []
    for org in organizations[:5]:
        name = org.get("name", "")
        org_type = org.get("org_type", "")
        goal = org.get("goal", "")
        info = f"{name}（{org_type}）"
        if goal:
            info += f" - 目标：{goal[:30]}"
        lines.append(info)
    return "\n".join(lines)


def _format_foreshadowings(foreshadowings: list[dict]) -> str:
    if not foreshadowings:
        return "暂无待处理伏笔"
    lines = []
    for f in foreshadowings[:8]:
        keyword = f.get("keyword", "")
        status = f.get("status", "")
        desc = f.get("description", "")
        info = f"{keyword}（{status}）"
        if desc:
            info += f" - {desc[:40]}"
        lines.append(info)
    return "\n".join(lines)


def _format_summaries(summaries: list[dict]) -> str:
    if not summaries:
        return "暂无前情摘要"
    lines = []
    for s in summaries[:3]:
        summary = s.get("summary", "")
        if summary:
            lines.append(summary[:80])
    return "\n".join(lines) if lines else "暂无"
