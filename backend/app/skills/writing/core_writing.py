"""核心写作 Skill。

这是 Writer Agent 必须的核心 Skill，负责构建基础写作 Prompt。
"""
from __future__ import annotations

import json

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
        long_term_memories = context.get("long_term_memories", [])

        context_text = f"""
项目：{project.get("name", "")}
世界观：{_format_world(world)}
本章大纲：{_format_outline(outline)}
角色：{_format_characters(characters)}
组织：{_format_organizations(organizations)}
待处理伏笔：{_format_foreshadowings(foreshadowings)}
最近章节摘要：{_format_summaries(recent_summaries)}
已确认长期记忆：{_format_long_term_memories(long_term_memories)}
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
    # 步骤 1：构建当前上下文中的人物名称索引，用于把关系卡里的 target_id 转成人名。
    names_by_id = {
        item.get("id"): item.get("name", "")
        for item in characters
        if item.get("id") is not None and item.get("name")
    }
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
        # 步骤 2：兼容 JSON 文本和已解析列表，附上审核确认后生效的人物关系。
        relations = ch.get("character_relations", [])
        if isinstance(relations, str):
            try:
                relations = json.loads(relations) if relations else []
            except json.JSONDecodeError:
                relations = []
        if isinstance(relations, list):
            relation_labels = []
            for relation in relations[:4]:
                if not isinstance(relation, dict):
                    continue
                target_name = relation.get("target_name") or names_by_id.get(relation.get("target_id"))
                if not target_name and relation.get("target_id") is not None:
                    target_name = f"角色#{relation['target_id']}"
                relation_type = relation.get("relation_type", "关系未注明")
                if target_name:
                    relation_labels.append(f"{target_name}（{relation_type}）")
            if relation_labels:
                info += " - 关系：" + "、".join(relation_labels)
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
        relations = org.get("relations", [])
        if relations:
            relation_labels = []
            for relation in relations[:8]:
                relation_type = "盟友" if relation.get("relation_type") == "alliance" else "敌对"
                target_name = relation.get("target_org_name", "")
                if target_name:
                    label = f"{relation_type}：{target_name}"
                    if relation.get("description"):
                        label += f"（{relation['description'][:36]}）"
                    relation_labels.append(label)
            if relation_labels:
                info += " - 势力关系：" + "；".join(relation_labels)
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


def _format_long_term_memories(memories: list[dict]) -> str:
    """把审核通过并已持久化的记忆摘要注入后续章节写作上下文。"""
    if not memories:
        return "暂无已确认的长期记忆"
    lines = []
    for memory in memories[:8]:
        title = memory.get("title", "")
        content = memory.get("content_summary") or memory.get("content", "")
        if title or content:
            lines.append(f"- {title}：{content[:120]}")
    return "\n".join(lines) if lines else "暂无已确认的长期记忆"
