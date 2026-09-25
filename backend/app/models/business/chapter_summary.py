"""章节摘要表 ORM 模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.session import Base


class ChapterSummary(Base):
    """章节分析后的长期记忆摘要。"""

    __tablename__ = "chapter_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    # 保存分析对应的生成来源，避免章节正文重写后旧摘要看起来仍属于最新版本。
    source_run_id = Column(String(64), nullable=True)
    source_version_id = Column(String(64), nullable=True)
    summary = Column(Text, default="")
    character_changes = Column(Text, default="")
    world_changes = Column(Text, default="")
    new_foreshadowings = Column(Text, default="")
    timeline_events = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
