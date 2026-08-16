"""大纲表 ORM 模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.session import Base


class Outline(Base):
    """大纲节点，既可以是卷也可以是章。"""

    __tablename__ = "outlines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False, default="")
    node_type = Column(String(16), default="chapter")
    status = Column(String(16), default="draft")
    volume_no = Column(Integer, nullable=True)
    chapter_no = Column(Integer, nullable=True)
    sort_index = Column(Integer, default=0)
    description = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
