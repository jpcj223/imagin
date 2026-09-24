"""核心库迁移 v022 — 显示系统管理菜单并补齐设定共创入口。"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """修复旧库中隐藏或挂错父级的系统菜单，并补充设定共创菜单。"""
    system_root = db.execute(
        text(
            "SELECT id FROM sys_menus "
            "WHERE parent_id = 0 AND name = '系统管理' "
            "ORDER BY id LIMIT 1"
        )
    ).fetchone()

    if system_root:
        system_root_id = system_root[0]
        db.execute(
            text("UPDATE sys_menus SET is_visible = 1 WHERE id = :id"),
            {"id": system_root_id},
        )
        for path in (
            "/system/users",
            "/system/menus",
            "/system/dictionaries",
            "/system/configs",
        ):
            db.execute(
                text(
                    "UPDATE sys_menus "
                    "SET parent_id = :parent_id, is_visible = 1 "
                    "WHERE path = :path"
                ),
                {"parent_id": system_root_id, "path": path},
            )

    project_group = db.execute(
        text(
            "SELECT id FROM sys_menus "
            "WHERE parent_id = 0 AND name = '项目数据' "
            "ORDER BY id LIMIT 1"
        )
    ).fetchone()
    project_group_id = project_group[0] if project_group else 0

    setting_menu = db.execute(
        text("SELECT id FROM sys_menus WHERE path = '/setting-co' ORDER BY id LIMIT 1")
    ).fetchone()
    if setting_menu:
        db.execute(
            text(
                "UPDATE sys_menus SET parent_id = :parent_id, name = :name, "
                "icon = :icon, component = :component, sort_order = :sort_order, "
                "is_visible = 1 WHERE id = :id"
            ),
            {
                "parent_id": project_group_id,
                "name": "设定共创",
                "icon": "💬",
                "component": "SettingCo",
                "sort_order": 7,
                "id": setting_menu[0],
            },
        )
    else:
        db.execute(
            text(
                "INSERT INTO sys_menus "
                "(parent_id, name, path, icon, component, sort_order, menu_type, permission, is_visible) "
                "VALUES (:parent_id, :name, :path, :icon, :component, :sort_order, :menu_type, :permission, :is_visible)"
            ),
            {
                "parent_id": project_group_id,
                "name": "设定共创",
                "path": "/setting-co",
                "icon": "💬",
                "component": "SettingCo",
                "sort_order": 7,
                "menu_type": "menu",
                "permission": "",
                "is_visible": 1,
            },
        )
