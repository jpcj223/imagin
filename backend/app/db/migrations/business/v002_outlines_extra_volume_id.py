"""v002 — 为 outlines 表补充 extra 和 volume_id 字段。

大纲节点需要支持精细化数据存储（卷/章节的扩展字段用 JSON 格式），
以及章节节点需要关联所属卷。

幂等性：使用 _ensure_columns 模式，字段已存在则跳过。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    dialect = db.bind.dialect.name  # 'sqlite' or 'mysql'

    _ensure_columns(db, dialect, "outlines", {
        "extra": "TEXT DEFAULT ''",
        "volume_id": "INTEGER",
    })


# ---------------------------------------------------------------------------
# 工具函数：幂等补齐字段（复制自 v001，避免循环依赖）
# ---------------------------------------------------------------------------
def _existing_columns(db: Session, dialect: str, table: str) -> set[str]:
    if dialect == "sqlite":
        rows = db.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {row[1] for row in rows}
    else:
        rows = db.execute(text(f"DESCRIBE {table}")).fetchall()
        return {row[0] for row in rows}


def _ensure_columns(db: Session, dialect: str, table: str, columns: dict[str, str]) -> None:
    existing = _existing_columns(db, dialect, table)
    for name, definition in columns.items():
        if name not in existing:
            db.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
