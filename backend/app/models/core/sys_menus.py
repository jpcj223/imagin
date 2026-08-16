from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.session import Base


class SysMenu(Base):
    """系统菜单表。"""

    __tablename__ = "sys_menus"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    parent_id = Column(Integer, default=0, comment="父菜单ID，0表示顶级")
    name = Column(String(64), nullable=False, comment="菜单名称")
    path = Column(String(255), default="", comment="前端路由路径")
    icon = Column(String(64), default="", comment="图标（emoji或图标名）")
    component = Column(String(255), default="", comment="前端组件路径")
    sort_order = Column(Integer, default=0, comment="排序")
    menu_type = Column(String(16), default="menu", comment="类型: menu/dir/button")
    permission = Column(String(128), default="", comment="权限标识")
    is_visible = Column(Integer, default=1, comment="是否显示: 1显示 0隐藏")
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
