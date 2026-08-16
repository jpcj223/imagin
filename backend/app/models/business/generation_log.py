"""生成日志表 ORM 模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.db.session import Base


class GenerationLog(Base):
    """Agent 生成日志。"""

    __tablename__ = "generation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    task_type = Column(String(64), nullable=False, default="")
    request = Column(Text, default="")
    response = Column(Text, default="")
    status = Column(String(16), default="success")
    error = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
