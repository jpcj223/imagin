"""章节对话改稿：生成候选文本，不在对话接口中修改正文。"""
from __future__ import annotations

import json
import re
from typing import Any

from app.agents.context import build_chapter_context
from app.core.llm import LLMError, chat_completion_stream_with_usage, chat_completion_with_usage


def _compact_context(context: dict[str, Any]) -> dict[str, Any]:
    """只把本章相关的少量设定放入改稿提示，避免无关资料淹没正文。"""
    outline = context.get("outline") or {}
    world = context.get("world") or {}
    return {
        "本章大纲": {
            "标题": outline.get("title", ""),
            "内容": str(outline.get("description", ""))[:1200],
        },
        "世界规则": str(world.get("rules", ""))[:1000],
        "相关人物": [
            {"姓名": item.get("name", ""), "身份": item.get("identity", ""), "动机": item.get("motivation", "")}
            for item in context.get("characters", [])[:6]
        ],
        "相关组织": [
            {"名称": item.get("name", ""), "目标": item.get("goal", "")}
            for item in context.get("organizations", [])[:5]
        ],
        "相关伏笔": [
            {"线索": item.get("keyword", ""), "状态": item.get("status", "")}
            for item in context.get("foreshadowings", [])[:6]
        ],
        "前情摘要": [
            str(item.get("summary", ""))[:500]
            for item in context.get("recent_summaries", [])[:3]
        ],
    }


def _parse_response(raw: str) -> dict[str, str]:
    """解析模型约定的 JSON；无法解析时只返回讨论答复，不把解释误当正文。"""
    text = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    try:
        result = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {"action": "discussion", "reply": raw.strip(), "candidate_text": ""}

    if not isinstance(result, dict):
        return {"action": "discussion", "reply": raw.strip(), "candidate_text": ""}
    action = "proposal" if result.get("action") == "proposal" else "discussion"
    reply = str(result.get("reply", "")).strip()
    candidate = str(result.get("candidate_text", "")) if action == "proposal" else ""
    if action == "proposal" and not candidate.strip():
        action = "discussion"
        reply = reply or "这次没有生成可预览的改稿，请补充希望调整的方向。"
    return {"action": action, "reply": reply, "candidate_text": candidate}


def _prepare_chapter_edit_messages(
    *,
    project_id: int,
    chapter_no: int,
    chapter_title: str,
    outline_id: int | None,
    content: str,
    scope: str,
    selection_start: int | None,
    selection_end: int | None,
    instruction: str,
    conversation: list[dict[str, str]],
    context_selection: dict[str, list[int]] | None = None,
) -> tuple[list[dict[str, str]], str, int | None, int | None]:
    """构造可供同步或流式接口共用的章节编辑请求。"""
    if not content.strip():
        raise ValueError("章节正文为空，暂时无法对话改稿")
    if not instruction.strip():
        raise ValueError("请先描述想讨论或调整的内容")
    if scope not in {"chapter", "selection"}:
        raise ValueError("改稿范围无效")

    selected_text = ""
    adjacent_context = ""
    if scope == "selection":
        if selection_start is None or selection_end is None:
            raise ValueError("请先在正文中选中要改写的片段")
        if selection_start < 0 or selection_end <= selection_start or selection_end > len(content):
            raise ValueError("所选片段已失效，请重新选择正文")
        selected_text = content[selection_start:selection_end]
        if not selected_text.strip():
            raise ValueError("选中的内容为空，请重新选择正文")
        left = content.rfind("\n", 0, selection_start)
        right = content.find("\n", selection_end)
        adjacent_context = content[max(0, left - 500):selection_start] + content[selection_end:right + 500 if right >= 0 else len(content)]

    # 步骤 1：与章节生成共用项目记忆检索，改稿时也能守住大纲和设定边界。
    try:
        context = build_chapter_context(
            project_id,
            chapter_no,
            outline_id,
            query=instruction,
            selection=context_selection,
        )
        compact_context = _compact_context(context)
    except Exception:  # noqa: BLE001
        compact_context = {"提示": "相关资料暂不可用；请以正文和用户要求为准。"}

    recent_turns = [
        {"role": item.get("role"), "content": str(item.get("content", ""))[:3000]}
        for item in conversation[-8:]
        if item.get("role") in {"user", "assistant"} and item.get("content")
    ]
    target_text = selected_text if scope == "selection" else content
    request_context = {
        "章节": f"第{chapter_no}章《{chapter_title or '未命名'}》",
        "改稿范围": "只替换选中片段" if scope == "selection" else "完整章节",
        "相关设定": compact_context,
        "对话上下文": recent_turns,
        "相邻正文（仅供衔接，不可改写）": adjacent_context if scope == "selection" else "",
        "本轮用户要求": instruction.strip(),
        "待处理正文": target_text,
    }
    messages = [
        {
            "role": "system",
            "content": (
                "你是小说作者的章节编辑搭档。先理解作者意图，保持故事事实、人物设定、世界规则和叙事视角一致。"
                "作者在讨论、提问或要求分析时，只答复讨论，不生成正文；作者明确要求修改、润色、扩写、压缩或调整时，"
                "给出简短修改说明，并生成可直接替换的正文。不得展示隐含思维链。"
                "必须只输出一个 JSON 对象，字段为 action（discussion 或 proposal）、reply（简洁说明）、candidate_text（候选正文）。"
                "讨论时 candidate_text 为空；改稿时 candidate_text 只含正文，不加标题、代码围栏或解释。"
                "完整章节范围必须返回完整章节；选中片段范围只能返回替换片段，不能重复相邻上下文。"
            ),
        },
        {"role": "user", "content": json.dumps(request_context, ensure_ascii=False)},
    ]

    return messages, scope, selection_start, selection_end


def propose_chapter_edit(
    *,
    project_id: int,
    chapter_no: int,
    chapter_title: str,
    outline_id: int | None,
    content: str,
    scope: str,
    selection_start: int | None,
    selection_end: int | None,
    instruction: str,
    conversation: list[dict[str, str]],
    context_selection: dict[str, list[int]] | None = None,
) -> dict[str, Any]:
    """围绕当前正文进行对话；编辑意图只返回候选，不落库。"""
    messages, scope, selection_start, selection_end = _prepare_chapter_edit_messages(
        project_id=project_id,
        chapter_no=chapter_no,
        chapter_title=chapter_title,
        outline_id=outline_id,
        content=content,
        scope=scope,
        selection_start=selection_start,
        selection_end=selection_end,
        instruction=instruction,
        conversation=conversation,
        context_selection=context_selection,
    )
    # 返回供应商用量；本接口只提出候选，不写正文或版本。
    raw, usage = chat_completion_with_usage(messages, temperature=0.65, max_tokens=12000)
    parsed = _parse_response(raw)
    return {
        **parsed,
        "usage": usage,
        "scope": scope,
        "selection_start": selection_start if scope == "selection" else None,
        "selection_end": selection_end if scope == "selection" else None,
    }


def propose_chapter_edit_stream(**kwargs: Any):
    """流式对话改稿；只发送处理状态和最终候选，客户端断开会关闭模型流。"""
    messages, scope, selection_start, selection_end = _prepare_chapter_edit_messages(**kwargs)
    fragments: list[str] = []
    usage = None
    yield {"type": "stage", "stage": "正在分析正文与选中的相关设定"}
    model_stream = iter(chat_completion_stream_with_usage(messages, temperature=0.65, max_tokens=12000))
    try:
        for event in model_stream:
            if event.get("type") == "delta":
                fragments.append(event.get("content", ""))
                if len(fragments) == 1 or len(fragments) % 32 == 0:
                    yield {"type": "progress", "received_characters": sum(map(len, fragments))}
            elif event.get("type") == "usage":
                usage = event.get("usage")

        parsed = _parse_response("".join(fragments))
        yield {
            "type": "done",
            **parsed,
            "usage": usage,
            "scope": scope,
            "selection_start": selection_start if scope == "selection" else None,
            "selection_end": selection_end if scope == "selection" else None,
        }
    except GeneratorExit:
        # 响应流关闭时，Python 会关闭底层模型流，不保存不完整候选。
        raise
    finally:
        close_stream = getattr(model_stream, "close", None)
        if close_stream:
            close_stream()


__all__ = ["LLMError", "propose_chapter_edit", "propose_chapter_edit_stream"]
