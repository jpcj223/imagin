"""Agent 注册表。

所有 Agent 通过注册机制接入，核心代码不需要知道具体有哪些 Agent。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseAgent


class AgentRegistry:
    """Agent 注册表（单例模式）。"""

    _agents: dict[str, type["BaseAgent"]] = {}
    _by_type: dict[str, list[str]] = {}

    @classmethod
    def register(cls, name: str):
        """装饰器：注册一个 Agent。

        用法:
            @AgentRegistry.register("my_agent")
            class MyAgent(BaseAgent):
                ...
        """

        def decorator(agent_cls: type["BaseAgent"]) -> type["BaseAgent"]:
            cls._agents[name] = agent_cls
            # 按类型索引
            atype = agent_cls.meta.agent_type
            if atype not in cls._by_type:
                cls._by_type[atype] = []
            cls._by_type[atype].append(name)
            return agent_cls

        return decorator

    @classmethod
    def get(cls, name: str, **kwargs) -> "BaseAgent":
        """根据名字获取 Agent 实例。

        Args:
            name: Agent 名称
            **kwargs: 传递给 Agent 构造函数的参数

        Returns:
            Agent 实例

        Raises:
            ValueError: 如果 Agent 不存在
        """
        if name not in cls._agents:
            raise ValueError(f"Agent '{name}' not found. Available: {list(cls._agents.keys())}")
        return cls._agents[name](**kwargs)

    @classmethod
    def get_class(cls, name: str) -> type["BaseAgent"]:
        """获取 Agent 类（不实例化）。"""
        if name not in cls._agents:
            raise ValueError(f"Agent '{name}' not found")
        return cls._agents[name]

    @classmethod
    def list_all(cls) -> list[dict]:
        """列出所有可用 Agent（给前端展示用）。"""
        return [
            {
                "name": name,
                "label": agent_cls.meta.label,
                "description": agent_cls.meta.description,
                "agent_type": agent_cls.meta.agent_type,
                "icon": agent_cls.meta.icon,
                "category": agent_cls.meta.category,
                "supports_streaming": agent_cls.meta.supports_streaming,
            }
            for name, agent_cls in cls._agents.items()
        ]

    @classmethod
    def list_by_type(cls, agent_type: str) -> list[dict]:
        """按类型列出 Agent。"""
        names = cls._by_type.get(agent_type, [])
        return [
            {
                "name": name,
                "label": cls._agents[name].meta.label,
                "description": cls._agents[name].meta.description,
                "icon": cls._agents[name].meta.icon,
            }
            for name in names
        ]

    @classmethod
    def has(cls, name: str) -> bool:
        """检查 Agent 是否存在。"""
        return name in cls._agents
