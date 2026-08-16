from __future__ import annotations

import json
import traceback
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import desc

from app.agents.context import build_context_preview
from app.agents.workflows import analyze_chapter, check_consistency, draft_chapter, draft_chapter_stream, polish_chapter
from app.db.repository import rows_to_dicts
from app.db.session import get_business_db
from app.models.business import Chapter, ChapterSummary, GenerationLog
from app.schemas.models import ChapterAnalyzeRequest, ChapterDraftRequest, ConsistencyCheckRequest, PolishRequest


router = APIRouter()


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
                ChapterSummary.created_at,
            )
            .join(Chapter, Chapter.id == ChapterSummary.chapter_id)
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
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/{project_id}/context-preview")
def context_preview(project_id: int, chapter_no: int = 1, outline_id: int | None = None) -> dict:
    """预览章节生成会读取的上下文包。"""
    return build_context_preview(project_id, chapter_no, outline_id)


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


@router.post("/chapter-analyze")
def chapter_analyze(payload: ChapterAnalyzeRequest) -> dict:
    """分析章节正文并沉淀摘要。"""
    return analyze_chapter(payload.project_id, payload.chapter_id, payload.content)


@router.post("/polish")
def polish(payload: PolishRequest) -> dict:
    """按指定模式精修章节正文。"""
    return polish_chapter(payload.project_id, payload.chapter_id, payload.mode, payload.instruction)


@router.post("/consistency-check")
def consistency_check(payload: ConsistencyCheckRequest) -> dict:
    """检查章节与资料库是否存在明显缺口或冲突。"""
    return check_consistency(payload.project_id, payload.chapter_id, payload.content)
