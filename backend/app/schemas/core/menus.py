from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MenuBase(BaseModel):
    """菜单基础字段。"""

    parent_id: int = Field(default=0, description="父菜单ID，0表示顶级")
    name: str = Field(..., min_length=1, max_length=64, description="菜单名称")
    path: str = Field(default="", max_length=255, description="前端路由路径")
    icon: str = Field(default="", max_length=64, description="图标")
    component: str = Field(default="", max_length=255, description="前端组件路径")
    sort_order: int = Field(default=0, description="排序")
    menu_type: str = Field(default="menu", max_length=16, description="类型: menu/dir/button")
    permission: str = Field(default="", max_length=128, description="权限标识")
    is_visible: int = Field(default=1, description="是否显示: 1显示 0隐藏")


class MenuCreate(MenuBase):
    """创建菜单请求。"""
    pass


class MenuUpdate(BaseModel):
    """更新菜单请求（支持局部更新）。"""

    parent_id: Optional[int] = Field(default=None, description="父菜单ID")
    name: Optional[str] = Field(default=None, max_length=64, description="菜单名称")
    path: Optional[str] = Field(default=None, max_length=255, description="前端路由路径")
    icon: Optional[str] = Field(default=None, max_length=64, description="图标")
    component: Optional[str] = Field(default=None, max_length=255, description="前端组件路径")
    sort_order: Optional[int] = Field(default=None, description="排序")
    menu_type: Optional[str] = Field(default=None, max_length=16, description="类型")
    permission: Optional[str] = Field(default=None, max_length=128, description="权限标识")
    is_visible: Optional[int] = Field(default=None, description="是否显示")


class MenuResponse(MenuBase):
    """菜单响应。"""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MenuTreeNode(MenuResponse):
    """菜单树节点（带子菜单）。"""

    children: list["MenuTreeNode"] = Field(default_factory=list, description="子菜单列表")


MenuTreeNode.model_rebuild()
