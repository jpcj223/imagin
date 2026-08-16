"""组织表 ORM 模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.session import Base


class Organization(Base):
    """组织势力。"""

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    # 基础字段（第一版）
    name = Column(String(255), nullable=False, default="")
    org_type = Column(String(64), default="")
    location = Column(Text, default="")
    slogan = Column(Text, default="")
    description = Column(Text, default="")
    level = Column(Integer, default=1)
    power_level = Column(Integer, default=5)
    member_count = Column(Integer, default=0)
    status = Column(String(32), default="")
    # 第二版新增字段
    hierarchy = Column(Text, default="")
    resources = Column(Text, default="")
    goal = Column(Text, default="")
    core_members = Column(Text, default="")
    allies = Column(Text, default="")
    enemies = Column(Text, default="")
    impact = Column(Text, default="")
    risk_notes = Column(Text, default="")
    # 第三版新增字段
    hidden_secrets = Column(Text, default="")
    active_from_chapter = Column(Integer, nullable=True)
    disbanded_chapter = Column(Integer, nullable=True)
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
