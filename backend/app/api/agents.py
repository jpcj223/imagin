from __future__ import annotations

import json
import traceback
from collections.abc import Iterator
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, func

from app.agents.chapter_edit import LLMError, propose_chapter_edit
from app.agents.context import build_context_preview
from app.agents.workflows import analyze_chapter, check_consistency, draft_chapter, draft_chapter_stream, polish_chapter, analyze_volume
from app.agents_v3.persistence import WorkflowPersistence
from app.db.repository import rows_to_dicts
from app.db.session import get_business_db
from app.models.business import Chapter, ChapterSummary, GenerationLog, GenerationVersion
from app.schemas.models import ChapterAnalyzeRequest, ChapterDraftRequest, ConsistencyCheckRequest, PolishRequest, VolumeAnalyzeRequest


router = APIRouter()


class ChapterEditChatRequest(BaseModel):
    """章节对话改稿请求；正文由前端传入的编辑快照决定。"""

    project_id: int
    chapter_id: int
    chapter_no: int = 1
    chapter_title: str = ""
    outline_id: int | None = None
    content: str = Field(max_length=500_000)
    scope: Literal["chapter", "selection"] = "chapter"
    selection_start: int | None = None
    selection_end: int | None = None
    instruction: str = Field(min_length=1, max_length=5_000)
    conversation: list[dict[str, str]] = Field(default_factory=list)
    context_selection: dict[str, list[int]] | None = None


class ChapterEditApplyRequest(BaseModel):
    """确认候选改稿请求，带原稿快照用于并发冲突保护。"""

    project_id: int
    chapter_id: int
    expected_content: str = Field(max_length=500_000)
    revised_content: str = Field(min_length=1, max_length=500_000)
    summary: str = Field(default="", max_length=500)


@router.get("/{project_id}/logs")
def generation_logs(project_id: int, limit: int = 20) -> list[dict]:
    """读取 Agent 运行日志。

    前端工作台用它展示最近一次生成、分析、精修的轨迹；limit 做上限保护，
    避免日志很多时一次性传输过多内容。
    """
    safe_limit = max(1, min(limit, 100))
    with get_business_db() as db:
        logs = (
            db.query(GenerationLog)
            .filter(GenerationLog.project_id == project_id)
            .order_by(GenerationLog.id.desc())
            .limit(safe_limit)
            .all()
        )
    return rows_to_dicts(logs)


@router.get("/{project_id}/summaries")
def chapter_summaries(project_id: int, limit: int = 20) -> list[dict]:
    """读取章节长期记忆摘要。

    工作台右侧只需要最近摘要；后续若接入向量检索，可继续保持这个轻量列表入口。
    """
    safe_limit = max(1, min(limit, 100))
    with get_business_db() as db:
        rows = (
            db.query(
                ChapterSummary.id,
                ChapterSummary.chapter_id,
                Chapter.chapter_no,
                Chapter.title,
                ChapterSummary.summary,
                ChapterSummary.character_changes,
                ChapterSummary.world_changes,
                ChapterSummary.new_foreshadowings,
                ChapterSummary.timeline_events,
                ChapterSummary.source_run_id,
                ChapterSummary.source_version_id,
                GenerationVersion.version_number.label("source_version_number"),
                ChapterSummary.created_at,
            )
            .join(Chapter, Chapter.id == ChapterSummary.chapter_id)
            .outerjoin(GenerationVersion, GenerationVersion.version_id == ChapterSummary.source_version_id)
            .filter(Chapter.project_id == project_id)
            .order_by(desc(Chapter.chapter_no), desc(ChapterSummary.id))
            .limit(safe_limit)
            .all()
        )

    return [
        {
            "id": row.id,
            "chapter_id": row.chapter_id,
            "chapter_no": row.chapter_no,
            "title": row.title,
            "summary": row.summary,
            "character_changes": row.character_changes,
            "world_changes": row.world_changes,
            "new_foreshadowings": row.new_foreshadowings,
            "timeline_events": row.timeline_events,
            "source_run_id": row.source_run_id,
            "source_version_id": row.source_version_id,
            "source_version_number": row.source_version_number,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/{project_id}/analysis-status")
def chapter_analysis_status(project_id: int) -> list[dict]:
    """读取章节记忆补充状态，供批量回填和进度统计使用。

    步骤 1：按项目读取章节基本信息和正文长度，不传输整章正文。
    步骤 2：关联摘要记录，标记章节是否已经完成过分析。
    步骤 3：按章节号排序，返回前端可直接用于续跑的状态清单。
    """
    with get_business_db() as db:
        summary_query = (
            db.query(ChapterSummary.chapter_id.label("chapter_id"))
            .filter(
                ChapterSummary.summary.isnot(None),
                ChapterSummary.summary != "",
                ~ChapterSummary.summary.like("开发模式摘要%"),
            )
            .distinct()
            .subquery()
        )
        rows = (
            db.query(
                Chapter.id,
                Chapter.chapter_no,
                Chapter.title,
                Chapter.status,
                func.coalesce(func.length(Chapter.content), 0).label("content_length"),
                summary_query.c.chapter_id.label("analyzed_chapter_id"),
            )
            .outerjoin(summary_query, summary_query.c.chapter_id == Chapter.id)
            .filter(Chapter.project_id == project_id)
            .order_by(Chapter.chapter_no.asc(), Chapter.id.asc())
            .all()
        )

    return [
        {
            "chapter_id": row.id,
            "chapter_no": row.chapter_no,
            "title": row.title,
            "status": row.status,
            "content_length": row.content_length or 0,
            "has_content": (row.content_length or 0) > 0,
            "has_summary": row.analyzed_chapter_id is not None,
        }
        for row in rows
    ]


@router.get("/{project_id}/context-preview")
def context_preview(
    project_id: int,
    chapter_no: int = 1,
    outline_id: int | None = None,
    query: str = "",
    selection: str = "",
) -> dict:
    """预览章节生成会读取的上下文包。

    步骤 1：解析前端提交的上下文选择。
    步骤 2：将补充要求和选择项交给正式上下文检索器。
    """
    # 步骤 1：验证选择参数为 JSON 对象，避免预览请求静默退回自动推荐。
    try:
        context_selection = json.loads(selection) if selection else None
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="上下文选择格式无效") from exc
    if context_selection is not None and not isinstance(context_selection, dict):
        raise HTTPException(status_code=422, detail="上下文选择必须是对象")

    # 步骤 2：把用户要求和手动选择一并交给实际生成使用的检索器。
    return build_context_preview(project_id, chapter_no, outline_id, query, context_selection)


@router.post("/chapter-draft")
def chapter_draft(payload: ChapterDraftRequest) -> dict:
    """生成章节正文。

    支持指定大纲，也支持覆盖已有章节草稿。
    """
    return draft_chapter(
        payload.project_id,
        payload.chapter_no,
        payload.instruction,
        payload.rhythm_level,
        payload.outline_id,
        payload.chapter_id,
        payload.context_selection,
    )


@router.post("/chapter-draft/stream")
def chapter_draft_stream(payload: ChapterDraftRequest) -> StreamingResponse:
    """流式生成章节正文。

    使用 NDJSON：每行一个事件对象，前端可以边读边追加到正文编辑区。
    """

    def event_lines() -> Iterator[str]:
        try:
            for event in draft_chapter_stream(
                payload.project_id,
                payload.chapter_no,
                payload.instruction,
                payload.rhythm_level,
                payload.outline_id,
                payload.chapter_id,
                payload.context_selection,
            ):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except Exception as exc:  # noqa: BLE001
            # 流式响应头一旦发出，后续异常不能再变成标准 500；用 error 事件交给前端做可恢复提示。
            yield json.dumps(
                {
                    "type": "error",
                    "message": f"流式生成中断：{exc}",
                    "trace": traceback.format_exc(limit=2),
                },
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(event_lines(), media_type="application/x-ndjson")


@router.post("/chapter-edit/chat")
def chapter_edit_chat(payload: ChapterEditChatRequest) -> dict:
    """讨论或提出章节改稿候选，绝不在此接口直接覆盖正文。"""
    with get_business_db() as db:
        chapter = db.query(Chapter.id).filter(
            Chapter.id == payload.chapter_id,
            Chapter.project_id == payload.project_id,
        ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在或不属于当前项目")
    try:
        return propose_chapter_edit(
            project_id=payload.project_id,
            chapter_no=payload.chapter_no,
            chapter_title=payload.chapter_title,
            outline_id=payload.outline_id,
            content=payload.content,
            scope=payload.scope,
            selection_start=payload.selection_start,
            selection_end=payload.selection_end,
            instruction=payload.instruction,
            conversation=payload.conversation,
            context_selection=payload.context_selection,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/chapter-edit/apply")
def chapter_edit_apply(payload: ChapterEditApplyRequest) -> dict:
    """校验原稿仍未变化后，保存候选正文并创建新的当前版本。"""
    result = WorkflowPersistence.apply_chapter_edit(
        project_id=payload.project_id,
        chapter_id=payload.chapter_id,
        expected_content=payload.expected_content,
        revised_content=payload.revised_content,
        summary=payload.summary,
    )
    if result is None:
        raise HTTPException(
            status_code=409,
            detail="章节正文已发生变化。请刷新当前内容后重新生成改稿候选，避免覆盖新修改。",
        )
    return {"success": True, **result}


@router.post("/chapter-analyze")
def chapter_analyze(payload: ChapterAnalyzeRequest) -> dict:
    """分析章节正文并沉淀摘要。"""
    try:
        return analyze_chapter(payload.project_id, payload.chapter_id, payload.content)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/polish")
def polish(payload: PolishRequest) -> dict:
    """按指定模式精修章节正文。"""
    return polish_chapter(payload.project_id, payload.chapter_id, payload.mode, payload.instruction)


@router.post("/consistency-check")
def consistency_check(payload: ConsistencyCheckRequest) -> dict:
    """检查章节与资料库是否存在明显缺口或冲突。"""
    return check_consistency(payload.project_id, payload.chapter_id, payload.content)


@router.post("/volume-analyze")
def volume_analyze(payload: VolumeAnalyzeRequest) -> dict:
    """分析卷设定并自动更新大纲总览。

    读取卷的描述、核心事件、章节规划等信息，通过 LLM 分析后
    补充完善大纲总览（主线、核心冲突、结局走向等），
    为后续章节生成 Agent 提供更清晰的创作方向。
    """
    return analyze_volume(payload.project_id, payload.volume_id, payload.instruction)
