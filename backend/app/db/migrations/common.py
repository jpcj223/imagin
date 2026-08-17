"""迁移脚本公共工具函数。

所有迁移脚本中重复的通用逻辑都提取到这里，避免每份迁移复制粘贴。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def existing_columns(db: Session, dialect: str, table: str) -> set[str]:
    """查询表的现有列名集合。"""
    if dialect == "sqlite":
        rows = db.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {row[1] for row in rows}
    else:
        rows = db.execute(text(f"DESCRIBE {table}")).fetchall()
        return {row[0] for row in rows}


def ensure_columns(db: Session, dialect: str, table: str, columns: dict[str, str]) -> None:
    """幂等补齐字段：不存在则 ALTER TABLE ADD COLUMN。

    columns: {列名: 列定义（含类型和默认值）}
    """
    existing = existing_columns(db, dialect, table)
    for name, definition in columns.items():
        if name not in existing:
            db.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
