"""v032：持久化章节改稿会话和候选稿。"""
from __future__ import annotations

def upgrade(db) -> None:
    """创建带项目/章节归属和修订号的会话表，支持安全恢复与并发保护。"""
    from app.models.business.chapter_edit_session import ChapterEditSession

    ChapterEditSession.__table__.create(bind=db.bind, checkfirst=True)
