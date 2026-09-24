"""章节变化提案 ORM 模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.session import Base


class ChapterChangeProposal(Base):
    """由章节分析产生、等待作者审核后再写回设定的变化提案。"""

    __tablename__ = "chapter_change_proposals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proposal_id = Column(String(64), nullable=False, unique=True, index=True)
    proposal_key = Column(String(64), nullable=False, unique=True)

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String(64), nullable=True, index=True)
    version_id = Column(String(64), nullable=True)

    entity_type = Column(String(32), nullable=False)
    operation = Column(String(16), nullable=False, default="update")
    target_id = Column(Integer, nullable=True)
    target_label = Column(String(255), default="")

    # JSON 文本让提案能够保存单字段、多字段和创建实体的快照。
    before_value = Column(Text, default="{}")
    proposed_value = Column(Text, nullable=False, default="{}")
    rationale = Column(Text, default="")
    evidence = Column(Text, default="")

    status = Column(String(16), nullable=False, default="pending", index=True)
    review_note = Column(Text, default="")
    applied_entity_id = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
