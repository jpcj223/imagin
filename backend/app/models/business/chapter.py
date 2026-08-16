"""章节表 ORM 模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.session import Base


class Chapter(Base):
    """章节草稿/正文。"""

    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    outline_id = Column(Integer, ForeignKey("outlines.id", ondelete="SET NULL"), nullable=True)
    chapter_no = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False, default="")
    content = Column(Text, default="")
    status = Column(String(16), default="draft")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
