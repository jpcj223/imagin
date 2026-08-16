"""章节摘要表 ORM 模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, func

from app.db.session import Base


class ChapterSummary(Base):
    """章节分析后的长期记忆摘要。"""

    __tablename__ = "chapter_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    summary = Column(Text, default="")
    character_changes = Column(Text, default="")
    world_changes = Column(Text, default="")
    new_foreshadowings = Column(Text, default="")
    timeline_events = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
