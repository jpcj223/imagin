"""人物变化分析 Skill。

增强 Analyzer Agent 的人物变化分析能力。
"""
from __future__ import annotations

from app.skills.base import BaseSkill, SkillMeta
from app.skills.registry import SkillRegistry


@SkillRegistry.register("character_change")
class CharacterChangeSkill(BaseSkill):
    """人物变化分析 Skill。

    更深入地分析本章中人物的状态、关系、能力变化。
    """

    meta = SkillMeta(
        name="character_change",
        label="人物变化分析",
        description="深入分析人物状态、关系、能力的变化",
        category="analysis",
        agent_types=["analyzer"],
        priority=20,
        is_core=False,
    )

    prompt_fragment = """
【人物分析要求】
- 列出每个出场人物的状态变化
- 注意人物关系的微妙变化
- 关注人物能力/境界的提升或下降
- 记录人物的心理变化和成长
- 如果有新人物出场，做简要介绍
""".strip()

    produced_outputs = ["character_changes_detailed"]
