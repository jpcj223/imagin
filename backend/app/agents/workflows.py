from __future__ import annotations

import json
from collections.abc import Iterator

from app.agents.context import build_chapter_context
from app.core.llm import LLMError, chat_completion, chat_completion_stream
from app.db.session import get_business_db
from app.models.business import Chapter, ChapterSummary, GenerationLog, Outline


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
    with get_business_db() as db:
        if chapter_id:
            chapter = (
                db.query(Chapter)
                .filter(Chapter.id == chapter_id, Chapter.project_id == project_id)
                .first()
            )
        else:
            chapter = (
                db.query(Chapter)
                .filter(Chapter.project_id == project_id, Chapter.chapter_no == chapter_no)
                .order_by(Chapter.id.desc())
                .first()
            )

        if chapter:
            chapter.outline_id = outline_id
            chapter.chapter_no = chapter_no
            chapter.title = title
            chapter.content = content
            chapter.status = status
            db.commit()
            db.refresh(chapter)
            chapter_id = chapter.id
        else:
            chapter = Chapter(
                project_id=project_id,
                outline_id=outline_id,
                chapter_no=chapter_no,
                title=title,
                content=content,
                status=status,
            )
            db.add(chapter)
            db.commit()
            db.refresh(chapter)
            chapter_id = chapter.id

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
    with get_business_db() as db:
        log = GenerationLog(
            project_id=project_id,
            task_type="chapter_draft",
            request=instruction,
            response=source,
            status="success",
        )
        db.add(log)
        db.commit()

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

    with get_business_db() as db:
        summary = ChapterSummary(
            chapter_id=chapter_id,
            summary=sections["summary"],
            character_changes=sections["character_changes"],
            world_changes=sections["world_changes"],
            new_foreshadowings=sections["new_foreshadowings"],
            timeline_events=sections["timeline_events"],
        )
        db.add(summary)

        log = GenerationLog(
            project_id=project_id,
            task_type="chapter_analyze",
            request=f"chapter_id={chapter_id}",
            response=analysis,
            status="success",
        )
        db.add(log)
        db.commit()

    return {"chapter_id": chapter_id, "analysis": analysis, **sections}


def check_consistency(project_id: int, chapter_id: int | None, content: str) -> dict:
    """检查章节与资料库的一致性。

    第一版不强依赖模型：先用上下文完整度和正文情况产出结构化建议；配置模型后可替换为
    真正的 LLM 检查，但接口契约保持不变。
    """
    chapter_no = 1
    with get_business_db() as db:
        chapter = None
        if chapter_id:
            chapter = (
                db.query(Chapter)
                .filter(Chapter.id == chapter_id, Chapter.project_id == project_id)
                .first()
            )
            if chapter:
                chapter_no = chapter.chapter_no
                content = content or chapter.content
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

    with get_business_db() as db:
        log = GenerationLog(
            project_id=project_id,
            task_type="consistency_check",
            request=f"chapter_id={chapter_id or ''}",
            response=risk_level,
            status="success",
        )
        db.add(log)
        db.commit()

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
    with get_business_db() as db:
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        return {"chapter_id": chapter_id, "content": "", "error": "章节不存在"}

    original = chapter.content
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

    with get_business_db() as db:
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if chapter:
            chapter.content = content
            db.commit()

        log = GenerationLog(
            project_id=project_id,
            task_type="chapter_polish",
            request=mode,
            response="polished",
            status="success",
        )
        db.add(log)
        db.commit()

    return {"chapter_id": chapter_id, "content": content}


def analyze_volume(project_id: int, volume_id: int, instruction: str = "") -> dict:
    """分析卷设定并自动更新大纲总览。

    读取卷的描述、核心事件、出场人物等信息，通过 LLM 分析后
    补充完善大纲总览（主线、核心冲突、结局走向等）。
    """
    with get_business_db() as db:
        volume = db.query(Outline).filter(
            Outline.id == volume_id,
            Outline.project_id == project_id,
            Outline.node_type == "volume"
        ).first()
        if not volume:
            return {"error": "卷不存在"}

        # 获取当前总览
        overview = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "overview"
        ).first()

        # 获取所有卷的信息用于整体分析
        all_volumes = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "volume"
        ).order_by(Outline.volume_no).all()

        # 获取本卷章节
        chapters = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "chapter",
            Outline.volume_id == volume_id
        ).order_by(Outline.chapter_no).all()

    # 组装上下文
    volume_info = {
        "卷名": volume.title,
        "卷号": volume.volume_no,
        "卷简介": volume.description,
    }
    try:
        extra = volume.extra and json.loads(volume.extra) or {}
        volume_info["核心事件"] = extra.get("core_events", "")
        volume_info["主要场景"] = extra.get("locations", "")
        volume_info["卷末高潮"] = extra.get("climax", "")
    except Exception:
        pass

    chapters_info = [{"章号": c.chapter_no, "标题": c.title, "简介": c.description} for c in chapters]

    overview_info = {}
    if overview:
        overview_info["当前主线"] = overview.description
        try:
            extra = overview.extra and json.loads(overview.extra) or {}
            overview_info["核心冲突"] = extra.get("core_conflict", "")
            overview_info["结局走向"] = extra.get("ending", "")
        except Exception:
            pass

    all_volumes_info = [{"卷号": v.volume_no, "卷名": v.title, "简介": v.description} for v in all_volumes]

    messages = [
        {
            "role": "system",
            "content": "你是臆想创作的大纲分析 Agent，负责分析卷设定并完善大纲总览，为后续章节生成 Agent 提供更清晰的创作方向。",
        },
        {
            "role": "user",
            "content": f"""
请分析当前卷的设定，并基于全卷规划补充完善大纲总览。

【当前卷信息】
{json.dumps(volume_info, ensure_ascii=False, indent=2)}

【本卷章节】
{json.dumps(chapters_info, ensure_ascii=False, indent=2)}

【所有卷概览】
{json.dumps(all_volumes_info, ensure_ascii=False, indent=2)}

【当前总览】
{json.dumps(overview_info, ensure_ascii=False, indent=2)}

【用户补充要求】
{instruction or "无"}

请输出以下内容，用【】标记各段：
【故事主线】
基于全卷规划，提炼更清晰的故事主线（一句话概括）。

【核心冲突】
分析本卷和整体故事的核心矛盾、冲突点。

【结局走向】
基于当前卷的走向，推断或完善故事的结局方向。

【卷分析摘要】
本卷在整体故事中的定位、作用和叙事价值。

【章节生成建议】
针对本卷章节生成的建议，包括节奏、重点场景、需要注意的伏笔和人物弧光。
""".strip(),
        },
    ]

    try:
        analysis = chat_completion(messages, temperature=0.3)
        source = "llm"
    except LLMError:
        analysis = (
            "【故事主线】开发模式：配置模型后将生成完整的故事主线分析。\n"
            "【核心冲突】开发模式：配置模型后将分析核心冲突。\n"
            "【结局走向】开发模式：配置模型后将推断结局走向。\n"
            "【卷分析摘要】开发模式：本卷是故事发展的重要阶段，配置模型后将获得详细分析。\n"
            "【章节生成建议】开发模式：配置模型后将生成针对性的章节生成建议。"
        )
        source = "fallback"

    # 提取各段
    def _extract(text: str, title: str) -> str:
        marker = f"【{title}】"
        start = text.find(marker)
        if start < 0:
            return ""
        start += len(marker)
        next_positions = [text.find("【", start), len(text)]
        end = min(p for p in next_positions if p >= 0)
        return text[start:end].strip()

    main_plot = _extract(analysis, "故事主线")
    core_conflict = _extract(analysis, "核心冲突")
    ending = _extract(analysis, "结局走向")
    volume_summary = _extract(analysis, "卷分析摘要")
    chapter_suggestions = _extract(analysis, "章节生成建议")

    # 更新总览
    with get_business_db() as db:
        if overview:
            # 合并更新：用新分析补充，不覆盖已有内容
            try:
                extra = overview.extra and json.loads(overview.extra) or {}
            except Exception:
                extra = {}
            if main_plot and not overview.description:
                overview.description = main_plot
            elif main_plot:
                # 追加到现有描述后
                overview.description = overview.description + "\n\n" + main_plot
            if core_conflict:
                extra["core_conflict"] = extra.get("core_conflict", "") + ("\n\n" if extra.get("core_conflict") else "") + core_conflict
            if ending:
                extra["ending"] = extra.get("ending", "") + ("\n\n" if extra.get("ending") else "") + ending
            extra["ai_analysis"] = extra.get("ai_analysis", "") + ("\n\n---\n\n" if extra.get("ai_analysis") else "") + f"第{volume.volume_no}卷分析：{volume_summary}"
            overview.extra = json.dumps(extra, ensure_ascii=False)
            overview_id = overview.id
        else:
            # 创建新总览
            extra = {
                "core_conflict": core_conflict,
                "ending": ending,
                "ai_analysis": f"第{volume.volume_no}卷分析：{volume_summary}",
                "target_words": 1000000,
                "target_volumes": len(all_volumes),
                "target_chapters": len(chapters) * len(all_volumes),
                "pace": "3",
            }
            new_overview = Outline(
                project_id=project_id,
                title="大纲总览",
                node_type="overview",
                status="confirmed",
                description=main_plot or "",
                extra=json.dumps(extra, ensure_ascii=False),
                sort_index=0,
            )
            db.add(new_overview)
            db.flush()
            overview_id = new_overview.id

        # 更新卷的extra，加入分析结果
        try:
            vol_extra = volume.extra and json.loads(volume.extra) or {}
        except Exception:
            vol_extra = {}
        vol_extra["ai_summary"] = volume_summary
        vol_extra["chapter_suggestions"] = chapter_suggestions
        volume.extra = json.dumps(vol_extra, ensure_ascii=False)

        # 记录日志
        log = GenerationLog(
            project_id=project_id,
            task_type="volume_analyze",
            request=f"volume_id={volume_id}, instruction={instruction}",
            response=analysis,
            status="success",
        )
        db.add(log)
        db.commit()

    return {
        "volume_id": volume_id,
        "overview_id": overview_id,
        "analysis": analysis,
        "main_plot": main_plot,
        "core_conflict": core_conflict,
        "ending": ending,
        "volume_summary": volume_summary,
        "chapter_suggestions": chapter_suggestions,
        "source": source,
    }
