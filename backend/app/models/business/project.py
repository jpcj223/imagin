"""项目表 ORM 模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.db.session import Base


class Project(Base):
    """小说项目。"""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, default="")
    theme = Column(String(255), default="")
    novel_type = Column(String(64), default="")
    target_words = Column(Integer, default=2500)
    synopsis = Column(Text, default="")
    pace_level = Column(Integer, default=3, comment="整体节奏等级：1-慢热 到 5-高燃")
    view_point = Column(String(64), default="", comment="叙事视角")
    writing_style = Column(String(64), default="", comment="文风基调")
    user_id = Column(Integer, default=1, comment="所属用户 ID，为多用户铺垫")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
