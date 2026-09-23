"""Skill 能力单元模块。

Skill 是 Agent 微内核架构中的最小功能单元。
每个 Skill 只做一件事，可以被任意 Agent 组合使用。
"""
from .base import BaseSkill
from .registry import SkillRegistry

# 导入所有 Skill 模块，触发装饰器注册
from . import writing
from . import analysis

__all__ = ["BaseSkill", "SkillRegistry"]
