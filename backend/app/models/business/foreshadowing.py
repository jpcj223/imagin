"""伏笔表 ORM 模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.session import Base


class Foreshadowing(Base):
    """伏笔记录。"""

    __tablename__ = "foreshadowings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    keyword = Column(String(255), nullable=False, default="")
    description = Column(Text, nullable=False, default="")
    status = Column(String(16), default="pending")
    importance = Column(String(16), default="medium")
    planted_chapter = Column(Integer, nullable=True)
    payoff_chapter = Column(Integer, nullable=True)
    effective_from = Column(Integer, nullable=True)
    expires_at = Column(Integer, nullable=True)
    notes = Column(Text, default="")
    # 第二版新增字段
    related_character_ids = Column(Text, default="")
    related_organization_ids = Column(Text, default="")
    related_outline_ids = Column(Text, default="")
    # 第三版新增字段
    replaced_by_id = Column(Integer, nullable=True)
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
