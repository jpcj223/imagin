"""v008 — 为 organizations 表增加层级体系字段。

为组织增加结构化的内部层级体系：
- hierarchy_system：层级体系类型（门派/公司/军队/家族/黑帮/学院/自定义）
- hierarchy_levels：层级列表 JSON 数组，每项 { name, level } 按从高到低排序

幂等性：使用 _ensure_columns 模式，字段已存在则跳过。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    dialect = db.bind.dialect.name  # 'sqlite' or 'mysql'

    _ensure_columns(db, dialect, "organizations", {
        "hierarchy_system": "VARCHAR(64) DEFAULT ''",
        "hierarchy_levels": "TEXT DEFAULT '[]'",
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
