"""核心规划 Skill。

Planner Agent 的核心能力，负责构建基础规划 Prompt 并解析结果。
"""
from __future__ import annotations

from app.skills.base import BaseSkill, SkillMeta
from app.skills.registry import SkillRegistry


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
请根据本章大纲，制定详细的写作计划。要求结构清晰、可执行性强，
包含出场人物、剧情节拍、场景安排、伏笔安排和注意事项。
""".strip()

    required_context = ["outline"]

    def pre_process(self, context, params):
        """构建规划上下文文本。"""
        outline = context.get("outline", {})
        characters = context.get("characters", [])
        foreshadowings = context.get("foreshadowings", [])
        recent_summaries = context.get("recent_summaries", [])

        # 构建补充信息
        extra_info = []

        if characters:
            char_names = [c.get("name", "") for c in characters[:5] if c.get("name")]
            if char_names:
                extra_info.append(f"可能出场的人物：{', '.join(char_names)}")

        if foreshadowings:
            pending = [f.get("keyword", "") for f in foreshadowings[:5]
                       if f.get("status") in ("pending", "planted") and f.get("keyword")]
            if pending:
                extra_info.append(f"待处理伏笔：{', '.join(pending)}")

        if recent_summaries:
            extra_info.append("前情提要：已准备好，写作时请注意承接上一章剧情")

        if extra_info:
            context["_planning_extra"] = "\n".join(extra_info)

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
