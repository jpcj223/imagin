"""世界观设定表 ORM 模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.session import Base


class WorldSetting(Base):
    """世界观设定条目。"""

    __tablename__ = "world_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    # 基础字段（第一版）
    era = Column(Text, default="")
    geography = Column(Text, default="")
    atmosphere = Column(Text, default="")
    rules = Column(Text, default="")
    extra = Column(Text, default="")
    # 第二版新增结构化字段
    title = Column(String(255), default="")
    category = Column(String(32), default="other")
    tags = Column(Text, default="")
    importance = Column(String(16), default="medium")
    related_chapters = Column(Text, default="")
    related_characters = Column(Text, default="")
    related_organizations = Column(Text, default="")
    related_foreshadowings = Column(Text, default="")
    conflict_notes = Column(Text, default="")
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
