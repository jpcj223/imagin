"""伏笔埋设 Skill。

增强 Writer Agent 的伏笔埋设能力，让伏笔安排更自然。
"""
from __future__ import annotations

from app.skills.base import BaseSkill, SkillMeta
from app.skills.registry import SkillRegistry


@SkillRegistry.register("foreshadow_plant")
class ForeshadowPlantSkill(BaseSkill):
    """伏笔埋设 Skill。

    在写作中合理安排伏笔的埋设和推进，让伏笔融入剧情不生硬。
    """

    meta = SkillMeta(
        name="foreshadow_plant",
        label="伏笔埋设",
        description="在写作中自然地安排伏笔，推动伏笔状态进展",
        category="writing",
        agent_types=["writer", "planner"],
        priority=30,
        is_core=False,
    )

    prompt_fragment = """
【伏笔要求】
- 本章涉及的伏笔要自然融入剧情，不要生硬地提及
- 待埋伏笔可以适当埋设，已埋设的伏笔可以推进发展
- 待回收伏笔应优先承接已有铺垫；若本章没有回收计划，不要强行揭晓
- 伏笔的揭示要有节奏，不要一口气全说出来
- 注意伏笔的前后呼应，不要前后矛盾
""".strip()

    required_context = ["foreshadowings"]

    def pre_process(self, context, params):
        """整理本章应关注的伏笔。"""
        foreshadowings = context.get("foreshadowings", [])
        if not foreshadowings:
            return context

        # 按状态分类整理
        pending = [f for f in foreshadowings if f.get("status") == "pending"]
        planted = [f for f in foreshadowings if f.get("status") == "planted"]
        developing = [f for f in foreshadowings if f.get("status") == "developing"]
        payoff_pending = [f for f in foreshadowings if f.get("status") == "payoff_pending"]

        foreshadow_context = []
        if pending:
            items = "、".join(f.get("keyword", "") for f in pending[:3])
            foreshadow_context.append(f"待埋伏笔：{items}")
        if planted:
            items = "、".join(f.get("keyword", "") for f in planted[:3])
            foreshadow_context.append(f"已埋伏笔：{items}（可推进发展）")
        if developing:
            items = "、".join(f.get("keyword", "") for f in developing[:3])
            foreshadow_context.append(f"发展中伏笔：{items}（继续推进）")
        if payoff_pending:
            items = "、".join(f.get("keyword", "") for f in payoff_pending[:3])
            foreshadow_context.append(f"待回收伏笔：{items}（优先承接，不要无故搁置）")

        if foreshadow_context:
            context["_foreshadow_notes"] = "\n".join(foreshadow_context)

        return context
