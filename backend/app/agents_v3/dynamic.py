"""动态 Agent 类。

由 Skill 动态组装的 Agent，不需要为每个 Agent 写独立的类。
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.core.llm import LLMError, chat_completion, chat_completion_stream

from .base import BaseAgent, AgentMeta


class _SafeFormatDict(dict):
    """安全格式化字典，缺失 key 时返回空字符串而不是报错。

    用于 prompt template 格式化，避免因为某个上下文字段缺失而整个生成失败。
    """

    def __missing__(self, key):
        return ""


class DynamicAgent(BaseAgent):
    """动态 Agent：由 Skill 组装而成。

    这是 v3.0 微内核架构的核心。大多数 Agent 不需要写独立的类，
    只需要用 AgentBuilder 选择合适的 Skill 和配置，就能组装出一个可用的 Agent。
    """

    def __init__(
        self,
        meta: AgentMeta,
        skills: list | None = None,
        params: dict[str, Any] | None = None,
        system_prompt: str = "",
        user_prompt_template: str = "",
    ):
        """初始化动态 Agent。

        Args:
            meta: Agent 元信息
            skills: Skill 列表
            params: 默认参数
            system_prompt: 系统 Prompt 模板
            user_prompt_template: 用户 Prompt 模板
        """
        super().__init__(params=params, skills=skills)
        self.meta = meta
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template

    def run(self, context: dict[str, Any], params: dict[str, Any] | None = None) -> dict[str, Any]:
        """同步执行。"""
        effective_params = {**self.params, **(params or {})}

        # 1. Skill 前处理
        ctx = self._apply_skills_pre(context, effective_params)

        # 2. 构建消息
        messages = self._build_messages(ctx, effective_params)

        # 3. 调用 LLM（失败时走 fallback）
        try:
            content = chat_completion(messages, **self._extract_llm_params(effective_params))
            source = "llm"
        except LLMError as exc:
            content = self._get_fallback_content(ctx, effective_params)
            source = f"fallback: {exc}"

        result = {"content": content, "analysis_text": content, "source": source}

        # 4. Skill 后处理
        result = self._apply_skills_post(result, ctx, effective_params)

        return result

    def run_stream(
        self,
        context: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """流式执行。"""
        effective_params = {**self.params, **(params or {})}

        # 1. Skill 前处理
        ctx = self._apply_skills_pre(context, effective_params)

        # 2. 构建消息
        messages = self._build_messages(ctx, effective_params)

        # 3. 流式调用 LLM（失败时走 fallback）
        chunks: list[str] = []
        source = "llm"
        try:
            for chunk in chat_completion_stream(messages, **self._extract_llm_params(effective_params)):
                chunks.append(chunk)
                yield {"type": "delta", "content": chunk}
            content = "".join(chunks)
        except LLMError as exc:
            # Fallback：流式输出兜底内容
            source = f"fallback: {exc}"
            content = self._get_fallback_content(ctx, effective_params)
            for chunk in self._chunk_text(content, size=20):
                yield {"type": "delta", "content": chunk}

        result = {"content": content, "analysis_text": content, "source": source}

        # 4. Skill 后处理
        result = self._apply_skills_post(result, ctx, effective_params)

        yield {"type": "done", **result}

    def _build_messages(self, context: dict[str, Any], params: dict[str, Any]) -> list[dict[str, str]]:
        """构建 LLM 消息。"""
        # 合并 context 和 params，params 优先覆盖 context 中的同名字段
        fmt_vars = _SafeFormatDict({**context, **params})

        # 系统消息
        system_msg = self.system_prompt.format_map(fmt_vars) if self.system_prompt else ""

        # 用户消息
        user_msg = self.user_prompt_template.format_map(fmt_vars) if self.user_prompt_template else ""

        # 加入 Skill 的 Prompt 片段
        if user_msg:
            user_msg = self._build_prompt_with_skills(user_msg, context)

        messages = []
        if system_msg:
            messages.append({"role": "system", "content": system_msg})
        if user_msg:
            messages.append({"role": "user", "content": user_msg})

        return messages

    def _extract_llm_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """从参数中提取 LLM 相关参数。"""
        llm_keys = ["temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty"]
        return {k: v for k, v in params.items() if k in llm_keys and v is not None}

    def _get_fallback_content(self, context: dict[str, Any], params: dict[str, Any]) -> str:
        """生成 fallback 兜底内容。

        当 LLM 不可用时，根据 Agent 类型返回合理的兜底内容，
        保证前端流程仍可跑通（开发/测试模式）。
        """
        agent_type = self.meta.agent_type
        chapter_no = context.get("chapter_no", 1)
        instruction = params.get("instruction", "") or context.get("instruction", "")
        outline_title = context.get("outline_title", "") or context.get("outline", {}).get("title", "")

        if agent_type == "writer":
            return self._fallback_writer(chapter_no, instruction, outline_title)
        elif agent_type == "analyzer":
            return self._fallback_analyzer(chapter_no)
        elif agent_type == "planner":
            return self._fallback_planner(chapter_no, instruction, outline_title)
        elif agent_type == "polisher":
            original = context.get("original_content", "") or context.get("content", "")
            return self._fallback_polisher(original)
        else:
            return f"【开发模式兜底】{self.meta.label} 输出占位内容。\n配置模型 API 后，本位置会由真实模型生成结果。"

    def _fallback_writer(self, chapter_no: int, instruction: str, outline_title: str) -> str:
        """写手 Agent 的兜底内容。"""
        title_line = f"第 {chapter_no} 章"
        if outline_title:
            title_line += f" {outline_title}"

        return f"""{title_line}

【开发模式草稿】

配置模型 API 后，本位置会由真实模型生成章节正文。

本章要求：{instruction or "暂无特殊要求"}

【场景一】
主角站在尚未命名的关键地点，周围的环境透着一丝不寻常。旧伏笔开始在脑海中回响，似乎预示着什么即将发生。

"该来的总会来的。"主角低声自语，目光投向远方。

【冲突】
新的阻力悄然出现，迫使主角做出选择。一边是稳妥但平庸的道路，一边是充满未知但可能带来突破的冒险。

主角握紧了拳头，做出了决定。

【钩子】
就在这时，一个意想不到的人物出现了，带来了一个会彻底改变后续剧情的消息。

"你可能不相信，"来人喘着气说，"但事情比我们想象的要复杂得多。"

——本章完——

【开发模式提示】以上为开发模式兜底文本。配置有效的模型 API 后，将生成真实的小说正文。"""

    def _fallback_analyzer(self, chapter_no: int) -> str:
        """分析师 Agent 的兜底内容。"""
        return f"""【章节摘要】
开发模式摘要：本章内容已保存，等待配置模型后重新分析。第 {chapter_no} 章主要描述了主角在关键节点的抉择和新冲突的出现。

【人物变化】
主角：在本章中做出了重要决定，心态有所转变。
配角：出现了新的人物，带来了关键信息。

【世界观变化】
暂无新的世界观设定揭示。

【新增伏笔】
1. 神秘来人的身份和目的尚不明确
2. 提到的"复杂事情"预示着更大的阴谋

【时间线事件】
1. 主角到达关键地点
2. 新的阻力出现
3. 主角做出决定
4. 神秘人物出现并带来消息"""

    def _fallback_planner(self, chapter_no: int, instruction: str, outline_title: str) -> str:
        """规划师 Agent 的兜底内容。"""
        return f"""【出场人物】
- 主角：本章核心人物，面临关键抉择
- 神秘来客：带来重要信息的新角色
- （可根据实际大纲调整）

【剧情节拍】
1. 开场：场景铺垫，主角到达目标地点
2. 发展：旧伏笔回响，铺垫紧张氛围
3. 冲突：新阻力出现，迫使主角选择
4. 转折：主角做出决定，行动开始
5. 高潮：神秘人物登场，抛出惊人消息
6. 结尾：留下悬念，钩子收束

【场景安排】
场景一：关键地点（日/外景）
- 描写环境，烘托气氛
- 主角内心活动，旧伏笔浮现

场景二：冲突现场（日/内景或外景）
- 阻力出现，对峙或交涉
- 主角的心理挣扎和抉择

场景三：相遇地点（黄昏/外景）
- 神秘人物登场
- 揭示关键信息
- 章节结束钩子

【伏笔安排】
- 回收：本章回应当前待处理的伏笔（根据实际伏笔列表）
- 新埋：神秘人物的身份、更大的阴谋

【注意事项】
1. 保持节奏：开场铺垫→冲突升级→转折高潮→悬念收尾
2. 人物对话要符合性格
3. 结尾钩子要有足够吸引力
4. 本章要求：{instruction or "按大纲正常推进"}"""

    def _fallback_polisher(self, original_content: str) -> str:
        """精修师 Agent 的兜底内容。"""
        if not original_content:
            return "【开发模式提示】暂无原文可精修。"
        return original_content + "\n\n【开发模式提示】配置模型 API 后可获得真实精修结果。当前为原文兜底输出。"

    def _chunk_text(self, text: str, size: int = 20) -> Iterator[str]:
        """把文本切成小块，模拟流式输出效果。"""
        for start in range(0, len(text), size):
            yield text[start : start + size]
