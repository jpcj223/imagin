"""核心分析 Skill。

Analyzer Agent 的核心能力，抽取章节摘要等基础信息。
"""
from __future__ import annotations

import re

from app.skills.base import BaseSkill, SkillMeta
from app.skills.registry import SkillRegistry


@SkillRegistry.register("core_analysis")
class CoreAnalysisSkill(BaseSkill):
    """核心分析 Skill。

    抽取章节摘要、世界观变化、时间线事件等基础信息。
    """

    meta = SkillMeta(
        name="core_analysis",
        label="核心分析",
        description="抽取章节摘要、世界观变化、时间线等基础信息",
        category="analysis",
        agent_types=["analyzer"],
        priority=10,
        is_core=True,
    )

    prompt_fragment = """
请分析下面章节，输出以下内容，用【】标记各段：

【章节摘要】
用 200 字以内概括本章主要内容。

【人物变化】
本章中人物的状态、关系、能力等有哪些变化。

【世界观变化】
本章中有没有揭示新的世界观设定或规则。

【新增伏笔】
本章埋设或推进了哪些伏笔。

【时间线事件】
本章发生了哪些重要事件，按时间顺序列出。
""".strip()

    produced_outputs = ["summary", "character_changes", "world_changes", "new_foreshadowings", "timeline_events"]

    def post_process(self, result, context, params):
        """解析分析结果，提取各字段。"""
        analysis_text = result.get("analysis_text", "")
        if not analysis_text:
            return result

        result["summary"] = _extract_section(analysis_text, "章节摘要") or analysis_text
        result["character_changes"] = _extract_section(analysis_text, "人物变化")
        result["world_changes"] = _extract_section(analysis_text, "世界观变化")
        result["new_foreshadowings"] = _extract_section(analysis_text, "新增伏笔")
        result["timeline_events"] = _extract_section(analysis_text, "时间线事件")

        return result


def _extract_section(text: str, title: str) -> str:
    """从分析文本中提取指定小节。"""
    marker = f"【{title}】"
    start = text.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    # 找下一个【】标记
    next_marker = re.search(r"【[^】]+】", text[start:])
    end = start + next_marker.start() if next_marker else len(text)
    return text[start:end].strip()
