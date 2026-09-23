"""Skill 注册表。

所有 Skill 通过注册机制接入，核心代码不需要知道具体有哪些 Skill。
新增 Skill 只需要写一个文件、加一个装饰器，自动出现在列表里。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseSkill


class SkillRegistry:
    """Skill 注册表（单例模式）。"""

    _skills: dict[str, type["BaseSkill"]] = {}
    _categories: dict[str, list[str]] = {}

    @classmethod
    def register(cls, name: str):
        """装饰器：注册一个 Skill。

        用法:
            @SkillRegistry.register("my_skill")
            class MySkill(BaseSkill):
                ...
        """

        def decorator(skill_cls: type["BaseSkill"]) -> type["BaseSkill"]:
            cls._skills[name] = skill_cls
            # 按分类索引
            cat = skill_cls.meta.category
            if cat not in cls._categories:
                cls._categories[cat] = []
            cls._categories[cat].append(name)
            return skill_cls

        return decorator

    @classmethod
    def get(cls, name: str) -> "BaseSkill":
        """根据名字获取 Skill 实例。

        Args:
            name: Skill 名称

        Returns:
            Skill 实例

        Raises:
            ValueError: 如果 Skill 不存在
        """
        if name not in cls._skills:
            raise ValueError(f"Skill '{name}' not found. Available: {list(cls._skills.keys())}")
        return cls._skills[name]()

    @classmethod
    def get_class(cls, name: str) -> type["BaseSkill"]:
        """根据名字获取 Skill 类（不实例化）。"""
        if name not in cls._skills:
            raise ValueError(f"Skill '{name}' not found")
        return cls._skills[name]

    @classmethod
    def list_all(cls) -> list[dict]:
        """列出所有可用 Skill（给前端展示用）。"""
        return [
            {
                "name": name,
                "label": skill_cls.meta.label,
                "description": skill_cls.meta.description,
                "category": skill_cls.meta.category,
                "priority": skill_cls.meta.priority,
                "is_core": skill_cls.meta.is_core,
            }
            for name, skill_cls in cls._skills.items()
        ]

    @classmethod
    def list_by_category(cls, category: str) -> list[dict]:
        """按分类列出 Skill。"""
        names = cls._categories.get(category, [])
        return [
            {
                "name": name,
                "label": cls._skills[name].meta.label,
                "description": cls._skills[name].meta.description,
            }
            for name in names
        ]

    @classmethod
    def get_core_for_agent(cls, agent_type: str) -> list["BaseSkill"]:
        """获取指定 Agent 类型的所有核心 Skill 实例。

        核心 Skill 是 is_core=True 且 agent_types 包含该 Agent 类型的 Skill。
        """
        core_skills = []
        for name, skill_cls in cls._skills.items():
            meta = skill_cls.meta
            if meta.is_core and (not meta.agent_types or agent_type in meta.agent_types):
                core_skills.append(skill_cls())
        # 按优先级排序
        core_skills.sort(key=lambda s: s.meta.priority)
        return core_skills

    @classmethod
    def get_available_for_agent(cls, agent_type: str) -> list["BaseSkill"]:
        """获取指定 Agent 类型可用的所有 Skill 实例（核心+可选）。"""
        available = []
        for name, skill_cls in cls._skills.items():
            meta = skill_cls.meta
            if not meta.agent_types or agent_type in meta.agent_types:
                available.append(skill_cls())
        available.sort(key=lambda s: s.meta.priority)
        return available

    @classmethod
    def has(cls, name: str) -> bool:
        """检查 Skill 是否存在。"""
        return name in cls._skills
