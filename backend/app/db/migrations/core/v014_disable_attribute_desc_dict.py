"""v014 — 禁用无用的 attribute_desc 字典。

attribute_desc（属性描述）字典在前端没有实际使用，仅被加载但从未渲染为选项，
属于冗余字典。为保持数据安全，这里不直接删除，而是将其 status 设为 disabled，
前端字典 API 只返回 active 状态的项，因此用户侧将不再可见。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    # 将 attribute_desc 字典及其所有项的 status 设为 disabled
    db.execute(
        text("""
            UPDATE sys_dict_items
            SET status = 'disabled'
            WHERE dict_id IN (
                SELECT id FROM sys_dictionaries WHERE dict_code = 'attribute_desc'
            )
        """)
    )
    db.execute(
        text("""
            UPDATE sys_dictionaries
            SET status = 'disabled'
            WHERE dict_code = 'attribute_desc'
        """)
    )
