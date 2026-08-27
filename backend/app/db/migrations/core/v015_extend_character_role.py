"""核心库迁移 v015 — 扩展角色类型字典。

添加 NPC、路人（extra）到 character_role 字典。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """添加 NPC、路人等角色类型。"""
    # 获取 character_role 字典ID
    result = db.execute(
        text("SELECT id FROM sys_dictionaries WHERE dict_code = 'character_role'"),
    ).fetchone()
    if not result:
        return

    dict_id = result[0]

    items = [
        ("NPC", "npc", 6, "非玩家角色/工具人"),
        ("路人/群演", "extra", 7, "路人甲、群众演员"),
    ]

    for item_label, item_value, item_sort, remark in items:
        existing = db.execute(
            text("SELECT id FROM sys_dict_items WHERE dict_id = :dict_id AND item_value = :value"),
            {"dict_id": dict_id, "value": item_value},
        ).fetchone()
        if existing:
            db.execute(text("""
                UPDATE sys_dict_items
                SET remark = :remark, sort_order = :sort_order
                WHERE id = :id
            """), {
                "id": existing[0],
                "remark": remark,
                "sort_order": item_sort,
            })
            continue

        db.execute(text("""
            INSERT INTO sys_dict_items (dict_id, item_label, item_value, sort_order, status, remark)
            VALUES (:dict_id, :item_label, :item_value, :sort_order, 'active', :remark)
        """), {
            "dict_id": dict_id,
            "item_label": item_label,
            "item_value": item_value,
            "sort_order": item_sort,
            "remark": remark,
        })


def downgrade(db: Session) -> None:
    """回滚：删除新增的角色类型。"""
    result = db.execute(
        text("SELECT id FROM sys_dictionaries WHERE dict_code = 'character_role'"),
    ).fetchone()
    if not result:
        return

    dict_id = result[0]

    db.execute(text("""
        DELETE FROM sys_dict_items
        WHERE dict_id = :dict_id AND item_value IN ('npc', 'extra')
    """), {"dict_id": dict_id})
