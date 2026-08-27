"""业务库迁移 v014 — 角色表增加图谱坐标字段。

添加 graph_x、graph_y 字段，用于保存角色在关系图谱中的自定义位置。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """为 characters 表添加图谱坐标字段。"""
    cols = db.execute(text("PRAGMA table_info(characters)")).fetchall()
    existing = {c[1] for c in cols}

    if 'graph_x' not in existing:
        db.execute(text("""
            ALTER TABLE characters ADD COLUMN graph_x REAL DEFAULT NULL
        """))
    if 'graph_y' not in existing:
        db.execute(text("""
            ALTER TABLE characters ADD COLUMN graph_y REAL DEFAULT NULL
        """))


def downgrade(db: Session) -> None:
    """回滚：移除图谱坐标字段。"""
    db.execute(text("ALTER TABLE characters DROP COLUMN IF EXISTS graph_x"))
    db.execute(text("ALTER TABLE characters DROP COLUMN IF EXISTS graph_y"))
