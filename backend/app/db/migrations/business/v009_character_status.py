"""v009 — 为 characters 表增加 status 状态字段。

为角色卡片增加状态管理：
- status：状态（active 启用 / inactive 关闭 / hidden 隐藏）

幂等性：使用 _ensure_columns 模式，字段已存在则跳过。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    dialect = db.bind.dialect.name  # 'sqlite' or 'mysql'

    _ensure_columns(db, dialect, "characters", {
        "status": "VARCHAR(32) DEFAULT 'active'",
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
