"""Skill 基类。

Skill 是 Agent 微内核架构中的最小能力单元。
每个 Skill 只做一件事，通过 pre_process 和 post_process 介入 Agent 的执行流程。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillMeta:
    """Skill 元信息。"""

    name: str                          # 唯一标识
    label: str                         # 显示名称
    description: str = ""              # 描述
    category: str = "general"          # 分类：writing/analysis/sync/consistency/utility
    agent_types: list[str] = field(default_factory=list)  # 适用的 Agent 类型，空表示所有
    priority: int = 100                # 优先级，数字越小越先执行（pre_process）
    is_core: bool = False              # 是否是核心 Skill（对应 Agent 必须有）


class BaseSkill:
    """Skill 基类：最小能力单元。

    子类可以选择性地重写 pre_process 和 post_process。
    """

    # Skill 元信息，子类必须定义
    meta: SkillMeta

    # 这个 Skill 需要注入的 Prompt 片段（可选）
    prompt_fragment: str = ""

    # 这个 Skill 需要的上下文字段名列表（可选）
    required_context: list[str] = []

    # 这个 Skill 新增的输出字段名列表（可选）
    produced_outputs: list[str] = []

    def pre_process(self, context: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """执行前处理钩子。

        在 Agent 调用 LLM 之前执行，可以修改上下文、补充数据、注入 Prompt 片段等。

        Args:
            context: 当前上下文字典（包含项目、人物、伏笔等数据）
            params: 当前 Agent 的参数配置

        Returns:
            修改后的上下文字典（也可以原地修改后返回）
        """
        return context

    def post_process(
        self,
        result: dict[str, Any],
        context: dict[str, Any],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """执行后处理钩子。

        在 Agent 得到 LLM 结果之后执行，可以解析结果、提取数据、做额外处理等。

        Args:
            result: Agent 的执行结果字典
            context: 当前上下文字典
            params: 当前 Agent 的参数配置

        Returns:
            修改后的结果字典（也可以原地修改后返回）
        """
        return result

    def validate(self, context: dict[str, Any]) -> list[str] | None:
        """校验当前上下文是否满足此 Skill 的启用条件。

        Returns:
            如果有错误返回错误列表，没有错误返回 None。
        """
        missing = [f for f in self.required_context if f not in context]
        if missing:
            return [f"Skill '{self.meta.name}' 缺少必要上下文: {', '.join(missing)}"]
        return None

    def on_error(
        self,
        error: Exception,
        context: dict[str, Any],
        params: dict[str, Any],
    ) -> dict[str, Any] | None:
        """错误处理钩子。

        当 Agent 执行出错时调用，可以做一些容错处理。

        Returns:
            如果能恢复，返回补救后的结果；如果不能恢复，返回 None 让错误继续传播。
        """
        return None
