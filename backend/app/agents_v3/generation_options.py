"""章节生成参数的默认值、校验和 Prompt 描述。"""
from __future__ import annotations

import math
from typing import Any


DEFAULT_GENERATION_OPTIONS: dict[str, Any] = {
    "writer_variant": "default",
    "temperature": 0.8,
    "target_word_count": 3000,
    "active_skills": ["outline", "character", "world", "rhythm"],
}

SUPPORTED_WRITER_VARIANTS = {"default", "shuangwen", "wenqing", "fast"}
SKILL_GUIDANCE: dict[str, str] = {
    "outline": "按本章大纲推进，不擅自改变核心事件与目标。",
    "character": "让人物言行符合已知性格、动机、关系與成长阶段。",
    "world": "遵守项目世界观、组织规则与已确认设定。",
    "foreshadow": "结合相关伏笔，适度埋设或回收线索，避免生硬点题。",
    "rhythm": "控制场景节奏与信息密度，避免重复和拖沓。",
    "emotion": "加强人物情绪变化及其与行动、对话的联系。",
}


def normalize_generation_options(options: dict[str, Any] | None) -> dict[str, Any]:
    """合并并规整生成参数，兼容旧工作流记录。"""
    values = {**DEFAULT_GENERATION_OPTIONS, **(options or {})}
    variant = values.get("writer_variant")
    if variant not in SUPPORTED_WRITER_VARIANTS:
        values["writer_variant"] = "default"

    try:
        temperature = float(values.get("temperature", 0.8))
    except (TypeError, ValueError):
        temperature = 0.8
    values["temperature"] = min(2.0, max(0.0, temperature))

    try:
        target = int(values.get("target_word_count", 3000))
    except (TypeError, ValueError):
        target = 3000
    values["target_word_count"] = min(10000, max(500, target))

    selected = values.get("active_skills")
    if not isinstance(selected, list):
        selected = DEFAULT_GENERATION_OPTIONS["active_skills"]
    active_skills: list[str] = []
    for name in selected:
        if isinstance(name, str) and name in SKILL_GUIDANCE and name not in active_skills:
            active_skills.append(name)
    values["active_skills"] = active_skills
    return values


def build_skill_guidance(active_skills: list[str]) -> str:
    """把界面选择转换成明确、可审计的写作要求。"""
    lines = [SKILL_GUIDANCE[key] for key in active_skills if key in SKILL_GUIDANCE]
    return "\n".join(f"- {line}" for line in lines) or "按项目资料和本章目标完成连贯正文。"


def target_word_range(target_word_count: int, tolerance: float = 0.1) -> tuple[int, int]:
    """按正文区实际口径（忽略空白字符）计算字数验收范围。"""
    target = max(1, int(target_word_count))
    lower = math.ceil(target * (1 - tolerance))
    upper = math.floor(target * (1 + tolerance))
    return lower, max(lower, upper)
