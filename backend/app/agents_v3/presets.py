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

    步骤 1：装配章节正文 Prompt 和核心写作 Skill。
    步骤 2：注入可选的规划结果，让智能模式的 Planner 输出实际指导正文。
    步骤 3：应用写作变体与额外参数并返回 Agent。
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
            "字数目标：{target_word_count} 字；验收范围 {target_word_min}-{target_word_max} 字（正文去除空白后的字符数）。"
            "请按目标范围控制篇幅，到达范围上限附近时自然收束，不得以重复环境、心理或信息来补字，也不要明显超出上限。\n"
            "本次写作重点：\n{writing_skill_guidance}\n\n"
            "用户补充要求：{instruction}\n\n"
            "本章规划：{writing_plan}\n\n"
            "写作资料包：\n{_writing_context}\n\n"
            "要求：\n"
            "1. 输出中文小说正文。\n"
            "2. 规划仅作为执行蓝图；以当前章细纲为事实边界，落实节拍但不要照抄规划条目。\n"
            "3. 保持连载网文节奏，前后段落自然衔接。\n"
            "4. 下一卷/下一章只提供方向，不提前写完其核心事件。\n"
            "5. 正文中不插入规划、分析、设定清单或写作过程说明。"
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
        .with_supports_streaming(True)
        .with_system_prompt(
            "你是臆想创作的章节事实分析 Agent。只依据最终正文提取可沉淀事实，供后续连贯写作和作者审核；"
            "不制定剧情计划、不改写或润色正文、不输出模型内部推理过程。"
        )
        .with_user_prompt_template(
            "请分析第 {chapter_no} 章的最终正文。\n"
            "分析只记录正文明确发生且可能影响后续创作的摘要、人物/关系变化、组织/世界设定变化、伏笔和时间线；"
            "不要重复本章规划或罗列没有发生变化的设定。\n\n章节正文：\n{content}"
        )
        # 分析只沉淀后续创作需要的事实；限制冗长解释，避免分析步骤拖住正文交付。
        .with_param("max_tokens", 1400)
        # 分析步骤最多等待 2 分钟；规划和正文仍使用原模型请求时限，避免压缩高质量生成时间。
        .with_param("_request_timeout_seconds", 120)
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
        .with_supports_streaming(True)
        .with_system_prompt(
            "你是臆想创作的剧情规划师 Agent，负责把大纲细化为可执行的写作计划。"
            "只规划当前章节，不写小说正文、不复述大纲，也不输出模型内部推理过程。"
        )
        .with_user_prompt_template(
            "为第 {chapter_no} 章制定可直接交给写手的情节蓝图。\n"
            "全书及相邻卷章连续性资料（已包含当前卷纲和本章细纲，请勿重复）：\n"
            "{generation_outline_context_text}\n\n"
            "{legacy_volume_outline_prompt}\n\n"
            "与本章直接相关的角色、伏笔及近期剧情：\n{_planning_context}\n\n"
            "请按以下结构精炼输出（4-5 个剧情节拍，避免泛泛口号或复述资料）：\n"
            "【本章目标】一句话说明本章要完成的剧情变化。\n"
            "【出场人物】只列本章实际需要的人物及其行动目的。\n"
            "【剧情节拍】按顺序列 4-5 步；每步简洁写清行动/冲突及其结果或新信息，保证因果递进。\n"
            "【场景与节奏】说明场景转换和节奏变化，避免重复铺垫。\n"
            "【伏笔处理】仅写本章适合埋设、推进或回收的已有伏笔；没有就写无。\n"
            "【章末衔接】给出本章落点，并说明如何自然接向下一章；不得提前完成下一章事件。\n\n"
            "规划必须落实当前章细纲和用户要求。前一卷/章只用于承接，后一卷/章只用于连贯铺垫；"
            "不新增与设定冲突的事实，不把计划写成正文。"
        )
        # 规划需要给写手足够具体的因果节拍，同时限制冗长解释，避免拖慢流水线。
        .with_param("max_tokens", 900)
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
        .with_supports_streaming(True)
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
