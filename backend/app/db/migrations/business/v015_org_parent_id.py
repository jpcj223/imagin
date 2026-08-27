"""业务库迁移 v015 — 组织表新增 parent_id 字段，支持树状层级。"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """为 organizations 表新增 parent_id 字段。"""

    cols = db.execute(text("PRAGMA table_info(organizations)")).fetchall()
    existing = {c[1] for c in cols}
    if 'parent_id' not in existing:
        db.execute(text("ALTER TABLE organizations ADD COLUMN parent_id INTEGER DEFAULT NULL"))
        db.commit()
