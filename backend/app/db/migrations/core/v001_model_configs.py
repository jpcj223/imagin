"""v001 — 核心库初始 schema：模型配置表。

model_configs 存放 OpenAI-compatible 模型连接配置，属于全局共享数据，
因此放在核心库中。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    dialect = db.bind.dialect.name  # 'sqlite' or 'mysql'

    if dialect == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS model_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT '',
                base_url TEXT NOT NULL DEFAULT '',
                api_key TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                is_active INTEGER DEFAULT 0,
                temperature REAL DEFAULT 0.7,
                max_tokens INTEGER,
                top_p REAL DEFAULT 0.9,
                frequency_penalty REAL DEFAULT 0,
                presence_penalty REAL DEFAULT 0,
                proxy_url TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS model_configs (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(255) NOT NULL DEFAULT '',
                base_url VARCHAR(512) NOT NULL DEFAULT '',
                api_key VARCHAR(512) NOT NULL DEFAULT '',
                model VARCHAR(255) NOT NULL DEFAULT '',
                is_active INTEGER DEFAULT 0,
                temperature FLOAT DEFAULT 0.7,
                max_tokens INTEGER,
                top_p FLOAT DEFAULT 0.9,
                frequency_penalty FLOAT DEFAULT 0,
                presence_penalty FLOAT DEFAULT 0,
                proxy_url VARCHAR(512) DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    # 补齐旧库可能缺失的字段（幂等）
    _ensure_columns(db, dialect, "model_configs", {
        "temperature": "REAL DEFAULT 0.7" if dialect == "sqlite" else "FLOAT DEFAULT 0.7",
        "max_tokens": "INTEGER",
        "top_p": "REAL DEFAULT 0.9" if dialect == "sqlite" else "FLOAT DEFAULT 0.9",
        "frequency_penalty": "REAL DEFAULT 0" if dialect == "sqlite" else "FLOAT DEFAULT 0",
        "presence_penalty": "REAL DEFAULT 0" if dialect == "sqlite" else "FLOAT DEFAULT 0",
        "proxy_url": "TEXT DEFAULT ''",
    })


def _existing_columns(db: Session, dialect: str, table: str) -> set[str]:
    """读取表的现有字段名集合。"""
    if dialect == "sqlite":
        rows = db.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {row[1] for row in rows}
    else:
        rows = db.execute(text(f"DESCRIBE {table}")).fetchall()
        return {row[0] for row in rows}


def _ensure_columns(db: Session, dialect: str, table: str, columns: dict[str, str]) -> None:
    """为旧库补齐新增字段（幂等）。"""
    existing = _existing_columns(db, dialect, table)
    for name, definition in columns.items():
        if name not in existing:
            db.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
