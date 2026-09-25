"""伏笔检测分析 Skill。

增强 Analyzer Agent 的伏笔检测能力。
"""
from __future__ import annotations

from app.skills.base import BaseSkill, SkillMeta
from app.skills.registry import SkillRegistry


@SkillRegistry.register("foreshadow_detect")
class ForeshadowDetectSkill(BaseSkill):
    """伏笔检测 Skill。

    自动检测本章中新埋设的伏笔和推进的伏笔。
    """

    meta = SkillMeta(
        name="foreshadow_detect",
        label="伏笔检测",
        description="自动检测本章埋设和推进的伏笔",
        category="analysis",
        agent_types=["analyzer"],
        priority=25,
        is_core=False,
    )

    prompt_fragment = """
【伏笔分析要求】
- 识别本章新埋设的伏笔，给出关键词和描述
- 识别本章推进了哪些已有伏笔，状态如何变化
- 伏笔状态只使用 pending、planted、developing、payoff_pending、resolved、abandoned
- 只有正文明确完成回收时才标记 resolved；尚待揭示或收束的线索标记 payoff_pending
- 判断伏笔的重要程度（高/中/低）
- 推测伏笔可能的回收时机
""".strip()

    produced_outputs = ["foreshadow_analysis"]
