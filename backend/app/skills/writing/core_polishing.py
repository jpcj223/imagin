"""核心精修 Skill。

Polisher Agent 的核心能力，负责构建基础精修 Prompt 并处理不同精修模式。
"""
from __future__ import annotations

from app.skills.base import BaseSkill, SkillMeta
from app.skills.registry import SkillRegistry


@SkillRegistry.register("core_polishing")
class CorePolishingSkill(BaseSkill):
    """核心精修 Skill。

    构建基础的精修 Prompt，处理不同精修模式，是 Polisher Agent 的必备核心能力。
    """

    meta = SkillMeta(
        name="core_polishing",
        label="核心精修",
        description="构建基础精修 Prompt，支持多种精修模式",
        category="writing",
        agent_types=["polisher"],
        priority=10,
        is_core=True,
    )

    prompt_fragment = """
请重写下面章节，保留所有剧情事实和人物设定，只提升文本质量。
不要输出解释，直接输出精修后的正文。
""".strip()

    required_context = []

    # 各精修模式对应的指令
    MODE_INSTRUCTIONS = {
        "flow": {
            "label": "流畅度优化",
            "instruction": "优化语句流畅度，让读起来更顺滑，去除生硬和重复的表达。",
        },
        "detail": {
            "label": "细节增强",
            "instruction": "增强场景描写和人物动作细节，让画面感更强，但不要增加新的剧情。",
        },
        "dialogue": {
            "label": "对话优化",
            "instruction": "优化人物对话，让对话更自然、更符合人物性格，减少说教感。",
        },
        "rhythm": {
            "label": "节奏调整",
            "instruction": "调整叙事节奏，让张弛更有度，关键场景更有张力，过渡更自然。",
        },
        "literary": {
            "label": "文学性提升",
            "instruction": "提升文字的文学性和美感，运用更精妙的修辞和表达，但不要改变剧情。",
        },
        "concise": {
            "label": "精简压缩",
            "instruction": "精简文字，去除冗余和啰嗦的部分，让表达更凝练，但保留所有关键信息。",
        },
    }

    def pre_process(self, context, params):
        """根据精修模式补充指令。"""
        mode = params.get("mode", "flow")
        mode_info = self.MODE_INSTRUCTIONS.get(mode, self.MODE_INSTRUCTIONS["flow"])

        context["_polish_mode"] = mode_info["label"]
        context["_polish_instruction"] = mode_info["instruction"]

        # 用户补充指令
        extra_instruction = params.get("instruction", "")
        if extra_instruction:
            context["_polish_extra"] = f"额外要求：{extra_instruction}"

        return context

    def post_process(self, result, context, params):
        """精修后处理。"""
        content = result.get("content", "")
        original_content = context.get("original_content", "")

        result["polished_content"] = content
        result["mode"] = params.get("mode", "flow")

        # 统计变化
        if original_content and content:
            original_len = len(original_content)
            new_len = len(content)
            result["original_length"] = original_len
            result["polished_length"] = new_len
            result["length_change"] = new_len - original_len
            result["change_percent"] = round((new_len - original_len) / original_len * 100, 1) if original_len > 0 else 0

        return result
