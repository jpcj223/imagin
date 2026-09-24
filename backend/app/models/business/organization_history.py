"""组织资料变更历史模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func

from app.db.session import Base


class OrganizationHistory(Base):
    """保存组织档案变更前后快照和章节分析来源。"""

    __tablename__ = "organization_history"
    __table_args__ = (
        Index("idx_organization_history_project_org", "project_id", "organization_id", "created_at"),
        Index("idx_organization_history_chapter", "chapter_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    proposal_id = Column(String(64), nullable=True, index=True)
    source_type = Column(String(32), nullable=False, default="manual")
    operation = Column(String(16), nullable=False, default="update")
    changed_fields = Column(Text, nullable=False, default="[]")
    before_snapshot = Column(Text, nullable=False, default="{}")
    after_snapshot = Column(Text, nullable=False, default="{}")
    rationale = Column(Text, default="")
    evidence = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
