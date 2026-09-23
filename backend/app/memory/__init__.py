"""记忆系统模块。

四层记忆体系：
- L1 工作记忆：当前 LLM 调用的上下文
- L2 会话记忆：一次工作流内的共享数据
- L3 项目记忆：项目级知识库（人物/组织/伏笔/世界观/章节）
- L4 长期记忆：跨项目的用户偏好和习惯
"""
from .manager import MemoryManager
from .retriever import MemoryRetriever

__all__ = ["MemoryManager", "MemoryRetriever"]
