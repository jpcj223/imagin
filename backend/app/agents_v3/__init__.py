"""Agent 模块（v3.0 微内核架构）。

Agent 由 Skill 动态组装而成，不再是写死的类。
"""
from .base import BaseAgent, AgentMeta
from .registry import AgentRegistry
from .builder import AgentBuilder
from .variants import VariantManager
from .dynamic import DynamicAgent

__all__ = [
    "BaseAgent",
    "AgentMeta",
    "AgentRegistry",
    "AgentBuilder",
    "VariantManager",
    "DynamicAgent",
]
