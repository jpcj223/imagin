"""角色表 ORM 模型。"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.session import Base


class Character(Base):
    """角色卡。"""

    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    # 基础字段（第一版）
    name = Column(String(255), nullable=False, default="")
    role_type = Column(String(32), default="supporting")
    mbti = Column(String(16), default="")
    appearance = Column(Text, default="")
    personality = Column(Text, default="")
    background = Column(Text, default="")
    motivation = Column(Text, default="")
    arc = Column(Text, default="")
    # 第二版新增字段
    identity = Column(Text, default="")
    faction = Column(Text, default="")
    weakness = Column(Text, default="")
    secret = Column(Text, default="")
    dialogue_style = Column(Text, default="")
    relationships = Column(Text, default="")
    chapters = Column(Text, default="")
    organization_ids = Column(Text, default="")
    related_character_ids = Column(Text, default="")
    ai_notes = Column(Text, default="")
    # 第三版新增字段
    mbti_primary = Column(String(16), default="")
    mbti_secondary = Column(String(16), default="")
    custom_attributes = Column(Text, default="[]")
    org_relations = Column(Text, default="[]")
    character_relations = Column(Text, default="[]")
    # 第四版：角色状态
    status = Column(String(32), default="active")
    # 第五版：内置角色标记（不可删除）
    is_builtin = Column(Boolean, default=False)
    # 第六版：分组与排序
    group_id = Column(Integer, nullable=True)
    sort_index = Column(Integer, default=0)
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
