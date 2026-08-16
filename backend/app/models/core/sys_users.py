from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.session import Base


class SysUser(Base):
    """系统用户表。"""

    __tablename__ = "sys_users"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    username = Column(String(64), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    nickname = Column(String(64), default="", comment="昵称")
    email = Column(String(128), default="", comment="邮箱")
    avatar = Column(String(255), default="", comment="头像URL")
    role = Column(String(32), default="user", comment="角色: admin/user")
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
