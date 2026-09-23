"""环境描写 Skill。

增强 Writer Agent 的环境描写能力。
"""
from __future__ import annotations

from app.skills.base import BaseSkill, SkillMeta
from app.skills.registry import SkillRegistry


@SkillRegistry.register("environment_desc")
class EnvironmentDescSkill(BaseSkill):
    """环境描写 Skill。

    增强场景环境描写能力，让场景更有画面感。
    """

    meta = SkillMeta(
        name="environment_desc",
        label="环境描写",
        description="增强场景环境描写，让故事更有画面感和氛围感",
        category="writing",
        agent_types=["writer"],
        priority=35,
        is_core=False,
    )

    prompt_fragment = """
【环境描写要求】
- 场景开场时用 1-2 句环境描写奠定氛围
- 环境描写要服务于情节和人物心情，不要为了写景而写景
- 调动多种感官：视觉、听觉、嗅觉、触觉
- 用环境烘托情绪，用天气暗示剧情走向
""".strip()
