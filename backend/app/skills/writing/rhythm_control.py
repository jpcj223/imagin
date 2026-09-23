"""节奏控制 Skill。

控制章节的叙事节奏，可快可慢。
"""
from __future__ import annotations

from app.skills.base import BaseSkill, SkillMeta
from app.skills.registry import SkillRegistry


@SkillRegistry.register("rhythm_control")
class RhythmControlSkill(BaseSkill):
    """节奏控制 Skill。

    根据节奏等级调整写作的紧凑程度和场景切换速度。
    """

    meta = SkillMeta(
        name="rhythm_control",
        label="节奏控制",
        description="控制章节叙事节奏，可快可慢",
        category="writing",
        agent_types=["writer"],
        priority=25,
        is_core=False,
    )

    def pre_process(self, context, params):
        """根据节奏等级注入节奏控制指令。"""
        rhythm_level = params.get("rhythm_level", "medium")

        rhythm_prompts = {
            "very_slow": """
【节奏要求：舒缓】
- 多用环境描写和心理描写
- 场景切换慢，一个场景写透再切
- 对话可以长一些，充分展现人物互动
- 节奏舒缓，像涓涓细流
""".strip(),
            "slow": """
【节奏要求：偏慢】
- 适当加入环境和心理描写
- 场景切换不要太频繁
- 对话可以有来有回
- 节奏从容，不急躁
""".strip(),
            "medium": """
【节奏要求：适中】
- 叙事节奏适中，张弛有度
- 有场景描写也有情节推进
- 对话和叙述比例均衡
""".strip(),
            "fast": """
【节奏要求：偏快】
- 情节推进要快，少废话
- 场景切换干脆利落
- 对话简洁有力
- 多动作少描写
""".strip(),
            "very_fast": """
【节奏要求：紧凑】
- 节奏极快，直奔主题
- 几乎不用环境描写，全是情节和对话
- 对话简短有力，一句顶十句
- 高密度的冲突和转折
""".strip(),
        }

        prompt = rhythm_prompts.get(rhythm_level, rhythm_prompts["medium"])
        context["_rhythm_instruction"] = prompt
        return context
