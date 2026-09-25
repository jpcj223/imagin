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
        """构建写作上下文文本。

        步骤 1：整理世界观、大纲、人物和记忆资料。
        步骤 2：把规划结果加入正文提示；快速写作模板使用明确的无规划说明。
        步骤 3：压缩结构化设定，供 Writer Prompt 统一引用。
        """
        # 步骤 1：把结构化上下文压缩成写作资料包。
        project = context.get("project", {})
        world = context.get("world", {})
        outline = context.get("outline", {})
        characters = context.get("characters", [])
        world_settings = context.get("world_settings", [])
        organizations = context.get("organizations", [])
        foreshadowings = context.get("foreshadowings", [])
        recent_summaries = context.get("recent_summaries", [])
        long_term_memories = context.get("long_term_memories", [])

        # 步骤 2：规划结果为空时说明当前模板直接写作，不展示空白的计划区。
        writing_plan = context.get("writing_plan") or "快速写作模式：没有独立规划步骤，请直接依据本章大纲安排剧情。"

        # 步骤 3：生成统一资料包，Writer Prompt 会同时单独引用 writing_plan。
        context_text = f"""
项目：{project.get("name", "")}
世界观：{_format_world(world, world_settings)}
本章大纲：{_format_outline(outline)}
角色：{_format_characters(characters)}
组织：{_format_organizations(organizations)}
待处理伏笔：{_format_foreshadowings(foreshadowings)}
最近章节摘要：{_format_summaries(recent_summaries)}
已确认长期记忆：{_format_long_term_memories(long_term_memories)}
""".strip()

        context["writing_plan"] = writing_plan
        context["_writing_context"] = context_text
        return context


def _format_world(world: dict, world_settings: list[dict] | None = None) -> str:
    """格式化世界观总览和作者在上下文选择器中勾选的设定条目。

    步骤 1：输出兼容旧资料包的世界观总览。
    步骤 2：补充本章明确选中的世界规则、地理或时代条目。
    """
    if not world:
        parts = []
    else:
        parts = []
        if world.get("title") or world.get("era"):
            parts.append(f"时代/背景：{world.get('title') or world.get('era', '')}")
        if world.get("rules"):
            parts.append(f"核心规则：{world['rules']}")
        if world.get("geography"):
            parts.append(f"地理环境：{world['geography']}")

    # 步骤 2：列出上下文中的所有世界观条目，包含首条设定未出现在总览中的补充信息。
    seen_ids: set[int] = set()
    for setting in world_settings or []:
        if setting.get("id") in seen_ids:
            continue
        seen_ids.add(setting.get("id"))
        title = setting.get("title") or setting.get("era") or "未命名设定"
        is_overview = world and setting.get("id") == world.get("id")
        # 总览已输出首条设定的规则与地理，只补充其余字段，避免重复塞入 Prompt。
        details = [setting.get("atmosphere"), setting.get("extra"), setting.get("conflict_notes")]
        if not is_overview:
            details = [
                setting.get("rules"),
                setting.get("geography"),
                *details,
            ]
        detail_text = "；".join(str(item) for item in details if item)
        label = "总览补充" if is_overview else f"设定条目《{title}》"
        parts.append(f"{label}：{detail_text}" if detail_text else label)

    return "\n".join(parts) if parts else "暂无世界观设定"


def _format_outline(outline: dict) -> str:
    if not outline:
        return "暂无大纲"
    title = outline.get("title", "")
    desc = outline.get("description", "")
    return f"{title} - {desc}" if desc else title


def _format_characters(characters: list[dict]) -> str:
    """格式化本章相关人物；检索器已限制自动推荐数量，手选人物全部保留。

    步骤 1：建立角色 ID 到名称的索引。
    步骤 2：输出所有已检索人物及其核心性格、动机和关系。
    """
    if not characters:
        return "暂无角色资料"
    # 步骤 1：构建当前上下文中的人物名称索引，用于把关系卡里的 target_id 转成人名。
    names_by_id = {
        item.get("id"): item.get("name", "")
        for item in characters
        if item.get("id") is not None and item.get("name")
    }
    lines = []
    # 步骤 2：不再二次截断，避免作者明确勾选超过默认数量时资料被静默丢弃。
    for ch in characters:
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
    """格式化本章势力资料和有效关系。

    步骤 1：逐一输出检索器返回的组织，保留作者手选项。
    步骤 2：附上本章有效的同盟和敌对关系。
    """
    if not organizations:
        return "暂无组织资料"
    lines = []
    # 步骤 1：自动推荐上限由检索器控制；本层不再截断手动选择项。
    for org in organizations:
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
    """格式化本章有效伏笔，保留手动项和自动推荐项。

    步骤 1：按检索排序输出伏笔状态和内容，供写作时遵守。
    """
    if not foreshadowings:
        return "暂无待处理伏笔"
    lines = []
    # 步骤 1：自动推荐上限由检索器控制；避免在写作 Prompt 再次截掉作者手选项。
    for f in foreshadowings:
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
