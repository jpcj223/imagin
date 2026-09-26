"""章节对话改稿会话。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.session import Base


class ChapterEditSession(Base):
    """同一章节可保留多个独立改稿会话及未应用候选稿。"""

    __tablename__ = "chapter_edit_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="新建改稿对话")
    revision = Column(Integer, nullable=False, default=1)
    state_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), index=True)
