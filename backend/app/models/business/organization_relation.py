"""组织之间的结构化关系模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func

from app.db.session import Base


class OrganizationRelation(Base):
    """记录组织间带类型、说明和章节有效期的关系。"""

    __tablename__ = "organization_relations"
    __table_args__ = (
        Index("idx_org_relations_project_a", "project_id", "organization_a_id"),
        Index("idx_org_relations_project_b", "project_id", "organization_b_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    # 两端 ID 由服务端按升序保存，确保同一关系不会因录入方向不同而重复。
    organization_a_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    organization_b_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(32), nullable=False, default="alliance")
    description = Column(Text, default="")
    effective_from_chapter = Column(Integer, nullable=True)
    expires_at_chapter = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
