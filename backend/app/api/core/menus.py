from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_core_db_depends
from app.models.core import SysMenu
from app.schemas.core import MenuCreate, MenuResponse, MenuTreeNode, MenuUpdate

router = APIRouter()


# ---------------------------------------------------------------------------
# 工具函数：构建菜单树
# ---------------------------------------------------------------------------
def _build_menu_tree(menus: list[SysMenu], parent_id: int = 0) -> list[MenuTreeNode]:
    """递归构建菜单树。"""
    tree = []
    for menu in menus:
        if menu.parent_id == parent_id:
            node = MenuTreeNode.model_validate(menu)
            node.children = _build_menu_tree(menus, menu.id)
            tree.append(node)
    # 按 sort_order 排序
    tree.sort(key=lambda x: x.sort_order)
    return tree


# ---------------------------------------------------------------------------
# API 接口
# ---------------------------------------------------------------------------
@router.get("", response_model=list[MenuTreeNode])
def get_menu_tree(db: Session = Depends(get_core_db_depends)) -> list[MenuTreeNode]:
    """获取菜单树（返回嵌套树形结构）。"""
    menus = db.query(SysMenu).order_by(SysMenu.sort_order, SysMenu.id).all()
    return _build_menu_tree(menus, 0)


@router.post("", response_model=MenuResponse)
def create_menu(
    payload: MenuCreate,
    db: Session = Depends(get_core_db_depends),
) -> MenuResponse:
    """新增菜单。"""
    menu = SysMenu(**payload.model_dump())
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return MenuResponse.model_validate(menu)


@router.put("/{menu_id}", response_model=MenuResponse)
def update_menu(
    menu_id: int,
    payload: MenuUpdate,
    db: Session = Depends(get_core_db_depends),
) -> MenuResponse:
    """更新菜单。"""
    menu = db.query(SysMenu).filter(SysMenu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(menu, key, value)

    db.commit()
    db.refresh(menu)
    return MenuResponse.model_validate(menu)


@router.delete("/{menu_id}")
def delete_menu(
    menu_id: int,
    db: Session = Depends(get_core_db_depends),
) -> dict:
    """删除菜单（同时删除子菜单）。"""
    menu = db.query(SysMenu).filter(SysMenu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="菜单不存在")

    # 递归删除所有子菜单
    def _delete_children(parent_id: int) -> None:
        children = db.query(SysMenu).filter(SysMenu.parent_id == parent_id).all()
        for child in children:
            _delete_children(child.id)
            db.delete(child)

    _delete_children(menu_id)
    db.delete(menu)
    db.commit()
    return {"success": True}
