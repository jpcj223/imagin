"""Agent 基类。

v3.0 微内核架构中，Agent 由 Skill 动态组装。
BaseAgent 定义了所有 Agent 的公共接口。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentMeta:
    """Agent 元信息。"""

    name: str                               # 唯一标识
    label: str                              # 显示名称
    description: str = ""                   # 描述
    agent_type: str = "general"             # Agent 类型：writer/analyzer/planner/sync/consistency/polisher
    icon: str = "🤖"                        # 图标 emoji
    category: str = "writing"               # 分类
    inputs: list[str] = field(default_factory=list)   # 需要的输入字段
    outputs: list[str] = field(default_factory=list)  # 产出的输出字段
    supports_streaming: bool = False        # 是否支持流式输出


class BaseAgent(ABC):
    """Agent 基类。

    所有 Agent 都必须实现 run 方法。流式输出可选择性实现 run_stream。
    """

    # Agent 元信息
    meta: AgentMeta

    # 默认参数配置
    default_params: dict[str, Any] = {}

    def __init__(self, params: dict[str, Any] | None = None, skills: list | None = None):
        """初始化 Agent。

        Args:
            params: 参数配置，会覆盖 default_params
            skills: 附加的 Skill 列表
        """
        self.params = {**self.default_params, **(params or {})}
        self.skills = skills or []

    @abstractmethod
    def run(self, context: dict[str, Any], params: dict[str, Any] | None = None) -> dict[str, Any]:
        """同步执行 Agent。

        Args:
            context: 上下文字典（包含项目数据、人物、伏笔等）
            params: 本次调用的参数，会覆盖初始化参数

        Returns:
            执行结果字典
        """
        ...

    def run_stream(
        self,
        context: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """流式执行 Agent（可选实现）。

        yield 输出片段，最后一个 yield 是完整结果。

        Args:
            context: 上下文字典
            params: 本次调用的参数

        Yields:
            事件字典，格式: {"type": "delta"/"done", ...}
        """
        # 默认实现：调用同步方法，一次性返回
        result = self.run(context, params)
        yield {"type": "done", **result}

    def validate_input(self, context: dict[str, Any]) -> list[str] | None:
        """校验输入是否完整。

        Returns:
            有错误返回错误列表，没有错误返回 None。
        """
        # 检查所有 Skill 的校验
        all_errors = []
        for skill in self.skills:
            errors = skill.validate(context)
            if errors:
                all_errors.extend(errors)
        return all_errors if all_errors else None

    def _apply_skills_pre(self, context: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """依次执行所有 Skill 的 pre_process 钩子。"""
        ctx = context
        for skill in self.skills:
            ctx = skill.pre_process(ctx, params) or ctx
        return ctx

    def _apply_skills_post(
        self,
        result: dict[str, Any],
        context: dict[str, Any],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """依次执行所有 Skill 的 post_process 钩子。"""
        res = result
        for skill in self.skills:
            res = skill.post_process(res, context, params) or res
        return res

    def _build_prompt_with_skills(self, base_prompt: str, context: dict[str, Any]) -> str:
        """把所有 Skill 的 Prompt 片段拼接到基础 Prompt 中。"""
        fragments = []
        for skill in self.skills:
            if skill.prompt_fragment:
                fragments.append(skill.prompt_fragment)

        # 同时把上下文里的 Skill 生成的补充信息也加进去
        for key in context:
            if key.startswith("_") and key.endswith(("_instruction", "_notes", "_styles", "_context")):
                val = context[key]
                if val:
                    fragments.append(str(val))

        if not fragments:
            return base_prompt

        # 把片段插入到 user message 末尾
        combined = "\n\n".join(fragments)
        return base_prompt + "\n\n" + combined
