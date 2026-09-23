"""内置 Agent 预设。

用 AgentBuilder 预定义常用的 Agent 配置，用户也可以在此基础上自定义。
"""
from __future__ import annotations

from .builder import AgentBuilder
from .registry import AgentRegistry
from .base import BaseAgent, AgentMeta


def create_writer_agent(variant: str = "default", **extra_params) -> BaseAgent:
    """创建 Writer Agent。

    Args:
        variant: 变体名称（default/shuangwen/wenqing/fast）
        **extra_params: 额外参数
    """
    from .variants import VariantManager

    builder = (
        AgentBuilder("writer", name=f"writer_{variant}", label=f"写手·{variant}")
        .with_icon("✍️")
        .with_description("根据大纲和设定生成章节正文")
        .with_category("writing")
        .with_supports_streaming(True)
        .with_system_prompt(
            "你是臆想创作的长篇小说章节生成 Agent。"
            "请严格依据项目资料、世界观、角色、人设、伏笔和章节大纲写作，避免设定漂移。"
        )
        .with_user_prompt_template(
            "请生成第 {chapter_no} 章正文。\n\n"
            "节奏等级：{rhythm_level}\n"
            "用户补充要求：{instruction}\n\n"
            "写作资料包：\n{_writing_context}\n\n"
            "要求：\n"
            "1. 输出中文小说正文。\n"
            "2. 保持连载网文节奏。\n"
            "3. 不要解释你的写作过程。"
        )
    )

    # 应用变体
    VariantManager.apply_to_builder(builder, variant, "writer")

    # 额外参数
    if extra_params:
        builder.with_params(extra_params)

    return builder.build()


def create_analyzer_agent(variant: str = "default", **extra_params) -> BaseAgent:
    """创建 Analyzer Agent。"""
    from .variants import VariantManager

    builder = (
        AgentBuilder("analyzer", name=f"analyzer_{variant}", label=f"分析师·{variant}")
        .with_icon("🔍")
        .with_description("分析章节正文，抽取结构化数据")
        .with_category("analysis")
        .with_system_prompt(
            "你是臆想创作的章节分析 Agent，负责把正文拆成可沉淀的长期记忆。"
        )
        .with_user_prompt_template(
            "请分析下面章节。\n\n章节正文：\n{content}"
        )
    )

    VariantManager.apply_to_builder(builder, variant, "analyzer")

    if extra_params:
        builder.with_params(extra_params)

    return builder.build()


def create_planner_agent(variant: str = "default", **extra_params) -> BaseAgent:
    """创建 Planner Agent。"""
    from .variants import VariantManager

    builder = (
        AgentBuilder("planner", name=f"planner_{variant}", label=f"规划师·{variant}")
        .with_icon("📋")
        .with_description("根据大纲制定详细写作计划")
        .with_category("writing")
        .with_system_prompt(
            "你是臆想创作的剧情规划师 Agent，负责把大纲细化为可执行的写作计划。"
        )
        .with_user_prompt_template(
            "请根据本章大纲，制定详细的写作计划。\n\n"
            "本章大纲：{outline_title}\n"
            "大纲描述：{outline_desc}\n\n"
            "请输出：\n"
            "【出场人物】\n【剧情节拍】\n【场景安排】\n【伏笔安排】\n【注意事项】"
        )
    )

    VariantManager.apply_to_builder(builder, variant, "planner")

    if extra_params:
        builder.with_params(extra_params)

    return builder.build()


def create_polisher_agent(variant: str = "default", **extra_params) -> BaseAgent:
    """创建 Polisher Agent。"""
    from .variants import VariantManager

    builder = (
        AgentBuilder("polisher", name=f"polisher_{variant}", label=f"精修师·{variant}")
        .with_icon("💎")
        .with_description("润色优化章节正文")
        .with_category("writing")
        .with_system_prompt(
            "你是臆想创作的小说精修 Agent，负责保留剧情事实并提升文本质量。"
        )
        .with_user_prompt_template(
            "精修模式：{mode}\n"
            "补充要求：{instruction}\n\n"
            "请重写下面章节，保留事实，不要输出解释：\n{original_content}"
        )
        .with_param("temperature", 0.6)
    )

    # polisher 暂时没有内置变体，用默认参数
    if extra_params:
        builder.with_params(extra_params)

    return builder.build()


# 便捷函数
def get_agent(agent_type: str, variant: str = "default", **params) -> BaseAgent:
    """根据类型和变体获取 Agent 实例。

    这是最常用的入口函数。

    Args:
        agent_type: Agent 类型（writer/analyzer/planner/polisher）
        variant: 变体名称
        **params: 额外参数

    Returns:
        Agent 实例
    """
    creators = {
        "writer": create_writer_agent,
        "analyzer": create_analyzer_agent,
        "planner": create_planner_agent,
        "polisher": create_polisher_agent,
    }

    if agent_type not in creators:
        raise ValueError(
            f"Unknown agent type '{agent_type}'. "
            f"Available: {list(creators.keys())}"
        )

    return creators[agent_type](variant=variant, **params)
