from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.db.session import Base


class SysConfig(Base):
    """系统配置表。"""

    __tablename__ = "sys_configs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    config_key = Column(String(128), unique=True, nullable=False, comment="配置键")
    config_value = Column(Text, default="", comment="配置值")
    config_name = Column(String(128), default="", comment="配置名称")
    description = Column(String(255), default="", comment="描述")
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )
