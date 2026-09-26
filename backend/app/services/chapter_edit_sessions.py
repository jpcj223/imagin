"""章节改稿会话的持久化服务。"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import update

from app.db.session import get_business_db
from app.models.business import Chapter, ChapterEditSession


def _session_to_dict(row: ChapterEditSession, include_state: bool = False) -> dict[str, Any]:
    result = {
        "session_id": row.session_id,
        "project_id": row.project_id,
        "chapter_id": row.chapter_id,
        "title": row.title,
        "revision": row.revision,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    if include_state:
        try:
            result["state"] = json.loads(row.state_json or "{}")
        except (TypeError, json.JSONDecodeError):
            result["state"] = {}
    return result


def _require_chapter(db, project_id: int, chapter_id: int) -> None:
    if not db.query(Chapter.id).filter(
        Chapter.id == chapter_id, Chapter.project_id == project_id
    ).first():
        raise ValueError("章节不存在或不属于当前项目")


def list_chapter_edit_sessions(project_id: int, chapter_id: int) -> list[dict[str, Any]]:
    with get_business_db() as db:
        _require_chapter(db, project_id, chapter_id)
        rows = (
            db.query(ChapterEditSession)
            .filter(
                ChapterEditSession.project_id == project_id,
                ChapterEditSession.chapter_id == chapter_id,
            )
            .order_by(ChapterEditSession.updated_at.desc(), ChapterEditSession.id.desc())
            .limit(100)
            .all()
        )
        return [_session_to_dict(row) for row in rows]


def create_chapter_edit_session(project_id: int, chapter_id: int) -> dict[str, Any]:
    with get_business_db() as db:
        _require_chapter(db, project_id, chapter_id)
        row = ChapterEditSession(
            session_id=str(uuid.uuid4()),
            project_id=project_id,
            chapter_id=chapter_id,
            title="新建改稿对话",
            state_json=json.dumps({"scope": "chapter", "messages": [], "candidate": None}, ensure_ascii=False),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _session_to_dict(row, include_state=True)


def get_chapter_edit_session(project_id: int, chapter_id: int, session_id: str) -> dict[str, Any] | None:
    with get_business_db() as db:
        row = (
            db.query(ChapterEditSession)
            .filter(
                ChapterEditSession.session_id == session_id,
                ChapterEditSession.project_id == project_id,
                ChapterEditSession.chapter_id == chapter_id,
            )
            .first()
        )
        return _session_to_dict(row, include_state=True) if row else None


def save_chapter_edit_session(
    project_id: int,
    chapter_id: int,
    session_id: str,
    expected_revision: int,
    title: str,
    state: dict[str, Any],
) -> dict[str, Any] | None:
    """只接受基于当前修订号的写入，防止旧标签页覆盖较新的对话。"""
    with get_business_db() as db:
        filters = (
            ChapterEditSession.session_id == session_id,
            ChapterEditSession.project_id == project_id,
            ChapterEditSession.chapter_id == chapter_id,
        )
        row = db.query(ChapterEditSession).filter(*filters).first()
        if not row:
            return None
        if row.revision != expected_revision:
            return {"conflict": True, **_session_to_dict(row, include_state=True)}

        # Revision 条件放进 UPDATE 本身，SQLite 下也能防止两个页面同时读改造成覆盖。
        result = db.execute(
            update(ChapterEditSession)
            .where(*filters, ChapterEditSession.revision == expected_revision)
            .values(
                title=title[:255] or "新建改稿对话",
                state_json=json.dumps(state, ensure_ascii=False),
                revision=expected_revision + 1,
                updated_at=datetime.utcnow(),
            )
        )
        if result.rowcount != 1:
            db.rollback()
            latest = db.query(ChapterEditSession).filter(*filters).first()
            return {"conflict": True, **_session_to_dict(latest, include_state=True)} if latest else None
        db.commit()
        saved = db.query(ChapterEditSession).filter(*filters).first()
        return _session_to_dict(saved, include_state=True) if saved else None
