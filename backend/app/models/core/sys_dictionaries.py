from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.session import Base


class SysDictionary(Base):
    """字典表（字典分类）。"""

    __tablename__ = "sys_dictionaries"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    dict_code = Column(String(64), unique=True, nullable=False, comment="字典编码")
    dict_name = Column(String(128), nullable=False, comment="字典名称")
    description = Column(String(255), default="", comment="描述")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(String(16), default="active", comment="状态: active/disabled")
    created_at = Column(
        DateTime,
        server_default=func.now(),
        default=datetime.utcnow,
        comment="创建时间",
    )
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )
