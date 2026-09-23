"""角色对话 Skill。

增强 Writer Agent 的角色对话生成能力，让对话更符合人物性格。
"""
from __future__ import annotations

from app.skills.base import BaseSkill, SkillMeta
from app.skills.registry import SkillRegistry


@SkillRegistry.register("character_dialogue")
class CharacterDialogueSkill(BaseSkill):
    """角色对话 Skill。

    为写作提供角色对话风格指导，让对话更符合各角色的性格设定。
    """

    meta = SkillMeta(
        name="character_dialogue",
        label="角色对话",
        description="根据人物性格生成更自然、更有辨识度的对话",
        category="writing",
        agent_types=["writer"],
        priority=20,
        is_core=True,
    )

    prompt_fragment = """
【对话要求】
- 每个角色的说话方式要符合其性格和身份
- 对话要自然，避免说教式或旁白式对话
- 适当使用动作和表情辅助对话，不要全是"XX说"
- 对话要有潜台词，不要把什么都说透
""".strip()

    def pre_process(self, context, params):
        """补充各角色的对话风格信息。"""
        characters = context.get("characters", [])
        if not characters:
            return context

        dialogue_styles = []
        for ch in characters[:6]:
            name = ch.get("name", "")
            style = ch.get("dialogue_style", "")
            personality = ch.get("personality", "")
            identity = ch.get("identity", "")
            if style or personality:
                info = f"{name}："
                if personality:
                    info += f"性格{personality[:20]}，"
                if style:
                    info += f"说话风格：{style}"
                elif identity:
                    info += f"身份：{identity}"
                dialogue_styles.append(info)

        if dialogue_styles:
            context["_dialogue_styles"] = "\n".join(dialogue_styles)

        return context
