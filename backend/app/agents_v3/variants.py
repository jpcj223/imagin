"""变体系统。

同一个 Agent 可以有多种变体（Variant），一键切换风格/模式。
变体 = 预设的 Skill 组合 + 参数配置。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VariantConfig:
    """变体配置。"""

    name: str                                # 变体唯一标识
    label: str                               # 显示名称
    icon: str = "🎨"                         # 图标
    description: str = ""                    # 描述
    skill_names: list[str] = field(default_factory=list)   # 使用的 Skill 列表（在核心 Skill 之外追加）
    params: dict[str, Any] = field(default_factory=dict)   # 参数覆盖
    system_prompt_override: str = ""         # 系统 Prompt 覆盖（可选）
    user_prompt_override: str = ""           # 用户 Prompt 覆盖（可选）
    is_default: bool = False                 # 是否是默认变体


class VariantManager:
    """变体管理器。

    管理所有 Agent 的变体定义，提供查询和应用功能。
    """

    _variants: dict[str, dict[str, VariantConfig]] = {}
    # key: agent_type, value: {variant_name: VariantConfig}

    @classmethod
    def register(cls, agent_type: str, variant: VariantConfig) -> None:
        """注册一个变体。"""
        if agent_type not in cls._variants:
            cls._variants[agent_type] = {}
        cls._variants[agent_type][variant.name] = variant

    @classmethod
    def register_many(cls, agent_type: str, variants: list[VariantConfig]) -> None:
        """批量注册变体。"""
        for v in variants:
            cls.register(agent_type, v)

    @classmethod
    def get(cls, agent_type: str, variant_name: str) -> VariantConfig:
        """获取指定变体。"""
        variants = cls._variants.get(agent_type, {})
        if variant_name not in variants:
            raise ValueError(
                f"Variant '{variant_name}' not found for agent type '{agent_type}'. "
                f"Available: {list(variants.keys())}"
            )
        return variants[variant_name]

    @classmethod
    def list_for_agent(cls, agent_type: str) -> list[dict]:
        """列出某 Agent 类型的所有变体（给前端展示用）。"""
        variants = cls._variants.get(agent_type, {})
        return [
            {
                "name": v.name,
                "label": v.label,
                "icon": v.icon,
                "description": v.description,
                "is_default": v.is_default,
                "skill_count": len(v.skill_names),
            }
            for v in variants.values()
        ]

    @classmethod
    def get_default(cls, agent_type: str) -> VariantConfig | None:
        """获取某 Agent 类型的默认变体。"""
        variants = cls._variants.get(agent_type, {})
        for v in variants.values():
            if v.is_default:
                return v
        # 如果没有标记默认的，返回第一个
        return next(iter(variants.values()), None)

    @classmethod
    def apply_to_builder(cls, builder, variant_name: str, agent_type: str) -> None:
        """将变体应用到 AgentBuilder。

        Args:
            builder: AgentBuilder 实例
            variant_name: 变体名称
            agent_type: Agent 类型
        """
        variant = cls.get(agent_type, variant_name)

        # 应用 Skill
        for skill_name in variant.skill_names:
            builder.with_skill(skill_name)

        # 应用参数
        builder.with_params(variant.params)

        # 应用 Prompt 覆盖
        if variant.system_prompt_override:
            builder.with_system_prompt(variant.system_prompt_override)
        if variant.user_prompt_override:
            builder.with_user_prompt_template(variant.user_prompt_override)

    @classmethod
    def all_variants(cls) -> dict[str, list[dict]]:
        """获取所有变体（按 Agent 类型分组）。"""
        result = {}
        for agent_type, variants in cls._variants.items():
            result[agent_type] = [
                {
                    "name": v.name,
                    "label": v.label,
                    "icon": v.icon,
                    "description": v.description,
                    "is_default": v.is_default,
                }
                for v in variants.values()
            ]
        return result


# ============================================================
# 内置变体定义
# ============================================================

def _register_builtin_variants():
    """注册内置变体。"""

    # ---- Writer 变体 ----
    VariantManager.register_many("writer", [
        VariantConfig(
            name="default",
            label="默认",
            icon="✍️",
            description="平衡质量和速度的标准写作模式",
            skill_names=["rhythm_control"],
            params={"temperature": 0.8},
            is_default=True,
        ),
        VariantConfig(
            name="shuangwen",
            label="爽文",
            icon="🔥",
            description="节奏快、冲突强、打脸爽，适合网文连载",
            skill_names=["rhythm_control", "foreshadow_plant"],
            params={
                "temperature": 0.9,
                "rhythm_level": "fast",
            },
        ),
        VariantConfig(
            name="wenqing",
            label="文青",
            icon="🌸",
            description="文字优美、意境深远，适合文学性较强的作品",
            skill_names=["environment_desc", "rhythm_control"],
            params={
                "temperature": 0.85,
                "rhythm_level": "slow",
            },
        ),
        VariantConfig(
            name="fast",
            label="极速",
            icon="⚡",
            description="快速出稿，减少描写，直奔情节",
            skill_names=[],
            params={
                "temperature": 0.7,
                "rhythm_level": "very_fast",
            },
        ),
    ])

    # ---- Analyzer 变体 ----
    VariantManager.register_many("analyzer", [
        VariantConfig(
            name="default",
            label="标准",
            icon="🔍",
            description="标准分析，抽取摘要和关键变化",
            skill_names=[],
            params={"temperature": 0.2},
            is_default=True,
        ),
        VariantConfig(
            name="deep",
            label="深度",
            icon="🧐",
            description="深入分析，包含人物变化和伏笔检测",
            skill_names=["character_change", "foreshadow_detect"],
            params={"temperature": 0.3},
        ),
        VariantConfig(
            name="quick",
            label="快速",
            icon="⚡",
            description="只生成章节摘要，速度最快",
            skill_names=[],
            params={"temperature": 0.1},
        ),
    ])

    # ---- Planner 变体 ----
    VariantManager.register_many("planner", [
        VariantConfig(
            name="default",
            label="标准",
            icon="📋",
            description="标准规划，平衡详细程度",
            skill_names=["foreshadow_plant"],
            params={"temperature": 0.5},
            is_default=True,
        ),
        VariantConfig(
            name="detailed",
            label="详细",
            icon="📝",
            description="更详细的写作计划，分场景规划",
            skill_names=["foreshadow_plant"],
            params={"temperature": 0.6},
        ),
    ])


# 导入时自动注册内置变体
_register_builtin_variants()
