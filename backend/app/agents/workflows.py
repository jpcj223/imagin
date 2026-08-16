from __future__ import annotations

from collections.abc import Iterator

from app.agents.context import build_chapter_context
from app.core.llm import LLMError, chat_completion, chat_completion_stream
from app.db.database import get_connection


def _format_context(context: dict) -> str:
    """把结构化上下文压缩成模型容易理解的写作资料包。"""
    return f"""
项目：{context.get("project", {})}
世界观：{context.get("world", {})}
本章大纲：{context.get("outline", {})}
角色：{context.get("characters", [])}
组织：{context.get("organizations", [])}
待处理伏笔：{context.get("foreshadowings", [])}
最近章节摘要：{context.get("recent_summaries", [])}
""".strip()


def _build_draft_messages(
    project_id: int,
    chapter_no: int,
    instruction: str,
    rhythm_level: str,
    outline_id: int | None = None,
) -> list[dict[str, str]]:
    """组装章节生成提示词。

    普通生成和流式生成共用这份上下文，避免两个接口生成逻辑漂移。
    """
    context = build_chapter_context(project_id, chapter_no, outline_id)
    context_text = _format_context(context)

    return [
        {
            "role": "system",
            "content": (
                "你是臆想创作的长篇小说章节生成 Agent。"
                "请严格依据项目资料、世界观、角色、人设、伏笔和章节大纲写作，避免设定漂移。"
            ),
        },
        {
            "role": "user",
            "content": f"""
请生成第 {chapter_no} 章正文。

节奏等级：{rhythm_level}
用户补充要求：{instruction or "无"}

写作资料包：
{context_text}

要求：
1. 输出中文小说正文。
2. 保持连载网文节奏。
3. 不要解释你的写作过程。
""".strip(),
        },
    ]


def _fallback_draft_content(chapter_no: int, instruction: str) -> str:
    """开发模式兜底正文，保证模型不可用时前端流程仍可跑通。"""
    return (
        f"第 {chapter_no} 章\n\n"
        "这里是开发模式草稿。配置 API 后，本位置会由真实模型生成章节正文。\n\n"
        f"本章要求：{instruction or '暂无'}\n\n"
        "【场景】主角站在尚未命名的关键地点，旧伏笔开始回响。\n"
        "【冲突】新的阻力出现，迫使主角做出选择。\n"
        "【钩子】章节末尾留下一个会影响后续剧情的问题。"
    )


def _extract_section(text: str, title: str) -> str:
    """从模型分析文本中提取指定小节。

    模型输出格式可能有轻微漂移，因此用章节标题做宽松切分；提取失败时返回空串，
    前端仍可展示完整 summary，不会影响主流程。
    """
    marker = f"【{title}】"
    start = text.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    next_positions = [text.find("【", start), len(text)]
    end = min(position for position in next_positions if position >= 0)
    return text[start:end].strip()


def _chunk_text(text: str, size: int = 18) -> Iterator[str]:
    """把非流式兜底文本切成小块，前端仍能看到流式写入效果。"""
    for start in range(0, len(text), size):
        yield text[start : start + size]


def _upsert_draft_content(
    project_id: int,
    chapter_no: int,
    outline_id: int | None,
    chapter_id: int | None,
    content: str,
    status: str = "generating",
) -> dict:
    """创建或更新章节草稿正文。

    流式生成过程中会多次调用这里，把已经输出的正文及时落库；这样用户关闭标签页、
    切断前端连接或浏览器崩溃时，也能在章节草稿里找回部分内容。
    """
    title = f"第{chapter_no}章"
    with get_connection() as conn:
        if chapter_id:
            row = conn.execute(
                "SELECT id FROM chapters WHERE id = ? AND project_id = ?",
                (chapter_id, project_id),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT id FROM chapters
                WHERE project_id = ? AND chapter_no = ?
                ORDER BY id DESC LIMIT 1
                """,
                (project_id, chapter_no),
            ).fetchone()

        if row:
            chapter_id = row["id"]
            conn.execute(
                """
                UPDATE chapters
                SET outline_id = ?, chapter_no = ?, title = ?, content = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (outline_id, chapter_no, title, content, status, chapter_id),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO chapters (project_id, outline_id, chapter_no, title, content, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, outline_id, chapter_no, title, content, status),
            )
            chapter_id = cursor.lastrowid
        conn.commit()

    return {"chapter_id": chapter_id, "title": title, "content": content}


def _save_draft_chapter(
    project_id: int,
    chapter_no: int,
    outline_id: int | None,
    chapter_id: int | None,
    instruction: str,
    content: str,
    source: str,
) -> dict:
    """保存生成结果。

    完整生成结束后使用 draft 状态保存，并写入一条 Agent 日志。
    """
    chapter = _upsert_draft_content(project_id, chapter_no, outline_id, chapter_id, content, "draft")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO generation_logs (project_id, task_type, request, response, status)
            VALUES (?, 'chapter_draft', ?, ?, 'success')
            """,
            (project_id, instruction, source),
        )
        conn.commit()

    return {**chapter, "source": source}


def draft_chapter(
    project_id: int,
    chapter_no: int,
    instruction: str,
    rhythm_level: str,
    outline_id: int | None = None,
    chapter_id: int | None = None,
) -> dict:
    """生成章节正文并保存为草稿。

    如果传入 chapter_id，则覆盖已有章节；否则按 project_id + chapter_no 查找并更新，
    找不到时创建新章节。未配置模型时走 fallback，保证前端流程可测试。
    """
    messages = _build_draft_messages(project_id, chapter_no, instruction, rhythm_level, outline_id)
    try:
        content = chat_completion(messages)
        source = "llm"
    except LLMError as exc:
        content = _fallback_draft_content(chapter_no, instruction)
        source = f"fallback: {exc}"

    return _save_draft_chapter(project_id, chapter_no, outline_id, chapter_id, instruction, content, source)


def draft_chapter_stream(
    project_id: int,
    chapter_no: int,
    instruction: str,
    rhythm_level: str,
    outline_id: int | None = None,
    chapter_id: int | None = None,
) -> Iterator[dict]:
    """流式生成章节正文。

    事件约定：
    - start：进入生成流程
    - delta：正文增量
    - done：生成完成并已保存
    """
    chapter = _upsert_draft_content(project_id, chapter_no, outline_id, chapter_id, "", "generating")
    chapter_id = chapter["chapter_id"]
    yield {"type": "start", "message": f"第 {chapter_no} 章开始生成", "chapter_id": chapter_id}
    messages = _build_draft_messages(project_id, chapter_no, instruction, rhythm_level, outline_id)
    chunks: list[str] = []
    saved_length = 0

    try:
        for chunk in chat_completion_stream(messages):
            chunks.append(chunk)
            content = "".join(chunks)
            if len(content) - saved_length >= 80:
                _upsert_draft_content(project_id, chapter_no, outline_id, chapter_id, content, "generating")
                saved_length = len(content)
            yield {"type": "delta", "content": chunk}
        content = "".join(chunks)
        if not content.strip():
            raise LLMError("模型未返回正文内容")
        source = "llm"
    except LLMError as exc:
        content = _fallback_draft_content(chapter_no, instruction)
        source = f"fallback: {exc}"
        chunks = []
        for chunk in _chunk_text(content):
            chunks.append(chunk)
            current = "".join(chunks)
            _upsert_draft_content(project_id, chapter_no, outline_id, chapter_id, current, "generating")
            yield {"type": "delta", "content": chunk}

    result = _save_draft_chapter(project_id, chapter_no, outline_id, chapter_id, instruction, content, source)
    yield {
        "type": "done",
        "chapter_id": result["chapter_id"],
        "title": result["title"],
        "source": result["source"],
    }


def analyze_chapter(project_id: int, chapter_id: int, content: str) -> dict:
    """分析章节正文并写入章节摘要表。

    第一版先把模型输出整体保存到 summary；后续可以继续拆分到人物变化、伏笔、时间线字段。
    """
    messages = [
        {
            "role": "system",
            "content": "你是臆想创作的章节分析 Agent，负责把正文拆成可沉淀的长期记忆。",
        },
        {
            "role": "user",
            "content": f"""
请分析下面章节，输出四段：
【章节摘要】
【人物变化】
【世界观变化】
【新增伏笔】
【时间线事件】

章节正文：
{content}
""".strip(),
        },
    ]

    try:
        analysis = chat_completion(messages, temperature=0.2)
    except LLMError:
        analysis = (
            "【章节摘要】开发模式摘要：本章内容已保存，等待配置模型后重新分析。\n"
            "【人物变化】暂无。\n"
            "【世界观变化】暂无。\n"
            "【新增伏笔】暂无。\n"
            "【时间线事件】暂无。"
        )

    # 分析结果同时保存完整文本和拆分字段；右侧工作台可直接读取结构化长期记忆。
    sections = {
        "summary": _extract_section(analysis, "章节摘要") or analysis,
        "character_changes": _extract_section(analysis, "人物变化"),
        "world_changes": _extract_section(analysis, "世界观变化"),
        "new_foreshadowings": _extract_section(analysis, "新增伏笔"),
        "timeline_events": _extract_section(analysis, "时间线事件"),
    }

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chapter_summaries
            (chapter_id, summary, character_changes, world_changes, new_foreshadowings, timeline_events)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                chapter_id,
                sections["summary"],
                sections["character_changes"],
                sections["world_changes"],
                sections["new_foreshadowings"],
                sections["timeline_events"],
            ),
        )
        conn.execute(
            """
            INSERT INTO generation_logs (project_id, task_type, request, response, status)
            VALUES (?, 'chapter_analyze', ?, ?, 'success')
            """,
            (project_id, f"chapter_id={chapter_id}", analysis),
        )
        conn.commit()

    return {"chapter_id": chapter_id, "analysis": analysis, **sections}


def check_consistency(project_id: int, chapter_id: int | None, content: str) -> dict:
    """检查章节与资料库的一致性。

    第一版不强依赖模型：先用上下文完整度和正文情况产出结构化建议；配置模型后可替换为
    真正的 LLM 检查，但接口契约保持不变。
    """
    chapter_no = 1
    with get_connection() as conn:
        chapter = None
        if chapter_id:
            chapter = conn.execute(
                "SELECT * FROM chapters WHERE id = ? AND project_id = ?",
                (chapter_id, project_id),
            ).fetchone()
            if chapter:
                chapter_no = chapter["chapter_no"]
                content = content or chapter["content"]
    context = build_chapter_context(project_id, chapter_no)

    missing: list[str] = []
    if not context.get("outline"):
        missing.append("缺少本章大纲")
    if not context.get("world"):
        missing.append("缺少世界观设定")
    if not context.get("characters"):
        missing.append("缺少角色资料")
    if not content.strip():
        missing.append("缺少待检查正文")

    risk_level = "low" if not missing else ("medium" if len(missing) <= 2 else "high")
    suggestions = [
        "生成前建议先确认本章目标、核心角色与伏笔状态。",
        "若章节涉及新设定，请在分析后沉淀到世界观或伏笔看板。",
    ]
    if missing:
        suggestions.insert(0, "请补齐：" + "、".join(missing))

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO generation_logs (project_id, task_type, request, response, status)
            VALUES (?, 'consistency_check', ?, ?, 'success')
            """,
            (project_id, f"chapter_id={chapter_id or ''}", risk_level),
        )
        conn.commit()

    return {
        "risk_level": risk_level,
        "missing": missing,
        "suggestions": suggestions,
        "context_stats": {
            "world": 1 if context.get("world") else 0,
            "characters": len(context.get("characters", [])),
            "organizations": len(context.get("organizations", [])),
            "foreshadowings": len(context.get("foreshadowings", [])),
            "recent_summaries": len(context.get("recent_summaries", [])),
        },
    }


def polish_chapter(project_id: int, chapter_id: int, mode: str, instruction: str) -> dict:
    """精修已有章节并覆盖原正文。"""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
    if not row:
        return {"chapter_id": chapter_id, "content": "", "error": "章节不存在"}

    original = row["content"]
    messages = [
        {"role": "system", "content": "你是臆想创作的小说精修 Agent，负责保留剧情事实并提升文本质量。"},
        {
            "role": "user",
            "content": f"""
精修模式：{mode}
补充要求：{instruction or "无"}

请重写下面章节，保留事实，不要输出解释：
{original}
""".strip(),
        },
    ]

    try:
        content = chat_completion(messages, temperature=0.6)
    except LLMError:
        content = original + "\n\n【开发模式提示】配置模型后可在这里获得真实精修结果。"

    with get_connection() as conn:
        conn.execute(
            "UPDATE chapters SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (content, chapter_id),
        )
        conn.execute(
            """
            INSERT INTO generation_logs (project_id, task_type, request, response, status)
            VALUES (?, 'chapter_polish', ?, ?, 'success')
            """,
            (project_id, mode, "polished"),
        )
        conn.commit()

    return {"chapter_id": chapter_id, "content": content}
