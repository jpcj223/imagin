"""Agent 构建器。

用 Skill 动态组装 Agent，实现微内核架构。
"""
from __future__ import annotations

from typing import Any

from .base import AgentMeta, BaseAgent
from .dynamic import DynamicAgent
from .registry import AgentRegistry
from app.skills.registry import SkillRegistry


class AgentBuilder:
    """Agent 构建器（Builder 模式）。

    用法:
        agent = (
            AgentBuilder("writer")
            .with_skill("core_writing")
            .with_skill("character_dialogue")
            .with_skill("rhythm_control")
            .with_param("temperature", 0.8)
            .with_system_prompt("你是一个小说写作助手...")
            .with_user_prompt_template("请生成第 {chapter_no} 章...")
            .build()
        )
    """

    def __init__(self, agent_type: str, name: str | None = None, label: str | None = None):
        """初始化构建器。

        Args:
            agent_type: Agent 类型（writer/analyzer/planner 等）
            name: Agent 唯一名称（默认自动生成）
            label: 显示名称
        """
        self.agent_type = agent_type
        self._name = name or f"dynamic_{agent_type}"
        self._label = label or f"动态{agent_type} Agent"
        self._skill_names: list[str] = []
        self._params: dict[str, Any] = {}
        self._system_prompt = ""
        self._user_prompt_template = ""
        self._icon = "🤖"
        self._description = ""
        self._category = "general"
        self._supports_streaming = False
        self._include_core_skills = True

    def with_name(self, name: str) -> "AgentBuilder":
        """设置 Agent 名称。"""
        self._name = name
        return self

    def with_label(self, label: str) -> "AgentBuilder":
        """设置显示名称。"""
        self._label = label
        return self

    def with_icon(self, icon: str) -> "AgentBuilder":
        """设置图标。"""
        self._icon = icon
        return self

    def with_description(self, description: str) -> "AgentBuilder":
        """设置描述。"""
        self._description = description
        return self

    def with_category(self, category: str) -> "AgentBuilder":
        """设置分类。"""
        self._category = category
        return self

    def with_supports_streaming(self, supports: bool = True) -> "AgentBuilder":
        """设置是否支持流式输出。"""
        self._supports_streaming = supports
        return self

    def with_skill(self, skill_name: str) -> "AgentBuilder":
        """添加一个 Skill。"""
        if skill_name not in self._skill_names:
            self._skill_names.append(skill_name)
        return self

    def with_skills(self, skill_names: list[str]) -> "AgentBuilder":
        """批量添加 Skill。"""
        for name in skill_names:
            self.with_skill(name)
        return self

    def without_core_skills(self) -> "AgentBuilder":
        """不自动包含核心 Skill（默认会自动加）。"""
        self._include_core_skills = False
        return self

    def with_param(self, key: str, value: Any) -> "AgentBuilder":
        """设置一个参数。"""
        self._params[key] = value
        return self

    def with_params(self, params: dict[str, Any]) -> "AgentBuilder":
        """批量设置参数。"""
        self._params.update(params)
        return self

    def with_system_prompt(self, prompt: str) -> "AgentBuilder":
        """设置系统 Prompt。"""
        self._system_prompt = prompt
        return self

    def with_user_prompt_template(self, template: str) -> "AgentBuilder":
        """设置用户 Prompt 模板。

        支持 {变量名} 占位符，会用 context 和 params 中的值替换。
        """
        self._user_prompt_template = template
        return self

    def build(self) -> BaseAgent:
        """构建 Agent 实例。"""
        # 1. 收集 Skill
        skill_instances = []

        # 核心 Skill（自动添加）
        if self._include_core_skills:
            core_skills = SkillRegistry.get_core_for_agent(self.agent_type)
            skill_instances.extend(core_skills)

        # 用户指定的 Skill
        for name in self._skill_names:
            if SkillRegistry.has(name):
                skill = SkillRegistry.get(name)
                # 避免重复添加
                if not any(s.meta.name == name for s in skill_instances):
                    skill_instances.append(skill)

        # 按优先级排序
        skill_instances.sort(key=lambda s: s.meta.priority)

        # 2. 构建元信息
        meta = AgentMeta(
            name=self._name,
            label=self._label,
            description=self._description,
            agent_type=self.agent_type,
            icon=self._icon,
            category=self._category,
            supports_streaming=self._supports_streaming,
        )

        # 3. 创建动态 Agent
        agent = DynamicAgent(
            meta=meta,
            skills=skill_instances,
            params=self._params,
            system_prompt=self._system_prompt,
            user_prompt_template=self._user_prompt_template,
        )

        return agent

    def build_and_register(self) -> str:
        """构建并注册到 AgentRegistry，返回 Agent 名称。"""
        agent = self.build()

        # 动态注册
        AgentRegistry._agents[self._name] = type(
            f"Dynamic_{self._name}_Agent",
            (BaseAgent,),
            {
                "meta": agent.meta,
                "default_params": self._params,
                "__init__": lambda self, **kw: DynamicAgent.__init__(
                    self,
                    meta=agent.meta,
                    skills=agent.skills,
                    params={**self._params, **kw},
                    system_prompt=self._system_prompt,
                    user_prompt_template=self._user_prompt_template,
                ),
                "run": DynamicAgent.run,
                "run_stream": DynamicAgent.run_stream,
            },
        )

        return self._name
