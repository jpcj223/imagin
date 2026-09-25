"""伏笔档案变更历史模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func

from app.db.session import Base


class ForeshadowingHistory(Base):
    """保存伏笔变化前后快照和章节来源。"""

    __tablename__ = "foreshadowing_history"
    __table_args__ = (
        Index("idx_foreshadowing_history_project_item", "project_id", "foreshadowing_id", "created_at"),
        Index("idx_foreshadowing_history_chapter", "chapter_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    # 不设置 foreshadowing 外键，删除伏笔卡片后仍保留删除记录供追溯。
    foreshadowing_id = Column(Integer, nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    proposal_id = Column(String(64), nullable=True, index=True)
    source_type = Column(String(32), nullable=False, default="manual")
    operation = Column(String(24), nullable=False, default="update")
    changed_fields = Column(Text, nullable=False, default="[]")
    before_snapshot = Column(Text, nullable=False, default="{}")
    after_snapshot = Column(Text, nullable=False, default="{}")
    rationale = Column(Text, default="")
    evidence = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
