"""核心规划 Skill。

Planner Agent 的核心能力，负责构建基础规划 Prompt 并解析结果。
"""
from __future__ import annotations

from app.skills.base import BaseSkill, SkillMeta
from app.skills.registry import SkillRegistry
from app.memory.retriever import format_volume_outline


@SkillRegistry.register("core_planning")
class CorePlanningSkill(BaseSkill):
    """核心规划 Skill。

    构建基础的剧情规划 Prompt，是 Planner Agent 的必备核心能力。
    """

    meta = SkillMeta(
        name="core_planning",
        label="核心规划",
        description="构建基础剧情规划 Prompt，是 Planner Agent 的核心能力",
        category="writing",
        agent_types=["planner"],
        priority=10,
        is_core=True,
    )

    prompt_fragment = """
规划只需给出当前章节可执行的因果安排；具体章节目标、人物行动、冲突结果、场景节奏和伏笔处理由 Agent 主提示规定。
不要重述输入资料、输出小说正文或生成泛化的写作建议。
""".strip()

    required_context = ["outline"]

    def pre_process(self, context, params):
        """构建规划上下文文本。"""
        has_combined_outline_context = bool(context.get("generation_outline_context_text"))
        context["generation_outline_context_text"] = context.get("generation_outline_context_text") or "暂无全书及相邻卷章细纲"
        # 保留旧版单步骤生成依赖的独立卷纲字段；当前 V3 规划 Prompt 不引用它，避免重复装入。
        context["volume_outline_text"] = format_volume_outline(context.get("volume_outline"))
        context["legacy_volume_outline_prompt"] = (
            f"当前卷纲（必读）：{context['volume_outline_text']}"
            if not has_combined_outline_context and context.get("volume_outline")
            else ""
        )
        characters = context.get("characters", [])
        foreshadowings = context.get("foreshadowings", [])
        recent_summaries = context.get("recent_summaries", [])

        # 只把对情节决策有用的字段压缩给规划师；完整设定仍会进入正文写作上下文。
        references = ["【相关人物】"]
        for character in characters:
            if not isinstance(character, dict) or not character.get("name"):
                continue
            details = [
                character.get("role_type"),
                str(character.get("personality") or "")[:80],
                str(character.get("motivation") or "")[:80],
            ]
            references.append(f"- {character['name']}：" + "；".join(str(item) for item in details if item))
        if len(references) == 1:
            references.append("- 暂无明确角色资料")

        references.append("【相关伏笔】")
        found_foreshadowing = False
        for item in foreshadowings:
            if not isinstance(item, dict) or not item.get("keyword"):
                continue
            if item.get("status") not in ("pending", "planted", "developing", "payoff_pending"):
                continue
            found_foreshadowing = True
            description = str(item.get("description") or "")[:100]
            references.append(f"- {item['keyword']}（{item.get('status', '未标记')}）：{description}".rstrip("："))
        if not found_foreshadowing:
            references.append("- 暂无待处理伏笔")

        if recent_summaries:
            references.append("【近期剧情摘要】")
            for item in recent_summaries[:3]:
                summary = str(item.get("summary") or "").strip()
                if summary:
                    references.append(f"- 第{item.get('chapter_no', '?')}章：{summary[:140]}")

        context["_planning_context"] = "\n".join(references)

        return context

    def post_process(self, result, context, params):
        """解析规划结果，提取结构化字段。"""
        content = result.get("content", "")
        if not content:
            return result

        # 提取各部分
        result["writing_plan"] = content
        result["characters_appear"] = _extract_section(content, "出场人物")
        result["plot_beats"] = _extract_section(content, "剧情节拍")
        result["scenes"] = _extract_section(content, "场景安排")
        result["foreshadowing_arrangement"] = _extract_section(content, "伏笔安排")
        result["notes"] = _extract_section(content, "注意事项")

        return result


def _extract_section(text: str, title: str) -> str:
    """从规划文本中提取指定小节。"""
    import re
    # 尝试多种标记格式
    markers = [f"【{title}】", f"[{title}]", f"## {title}", f"### {title}", f"{title}："]
    for marker in markers:
        start = text.find(marker)
        if start >= 0:
            start += len(marker)
            # 找下一个类似标记
            next_match = re.search(r"[【\[]\s*[^】\]]+\s*[】\]]|^##+\s", text[start:], re.MULTILINE)
            end = start + next_match.start() if next_match else len(text)
            return text[start:end].strip()
    return ""
