from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR.parent / "data"
DB_PATH = DATA_DIR / "yixiang.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """读取表的现有字段，用于幂等迁移判断。"""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    """为旧库补齐新增字段。

    SQLite 的轻量迁移以 ADD COLUMN 为主；每次启动都检查字段是否存在，
    因此重复启动不会破坏旧数据，也不会重复添加字段。
    """
    existing = _existing_columns(conn, table)
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db() -> None:
    """初始化 SQLite 表结构。

    第一版先使用轻量 schema，让核心创作闭环尽快可运行；复杂向量记忆后续再扩展。
    """
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                theme TEXT DEFAULT '',
                novel_type TEXT DEFAULT '',
                target_words INTEGER DEFAULT 2500,
                synopsis TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS model_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                base_url TEXT NOT NULL,
                api_key TEXT NOT NULL,
                model TEXT NOT NULL,
                is_active INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS world_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                era TEXT DEFAULT '',
                geography TEXT DEFAULT '',
                atmosphere TEXT DEFAULT '',
                rules TEXT DEFAULT '',
                extra TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS outlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                node_type TEXT DEFAULT 'chapter',
                status TEXT DEFAULT 'draft',
                volume_no INTEGER,
                chapter_no INTEGER,
                sort_index INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                outline_id INTEGER,
                chapter_no INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(outline_id) REFERENCES outlines(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS chapter_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id INTEGER NOT NULL,
                summary TEXT DEFAULT '',
                character_changes TEXT DEFAULT '',
                world_changes TEXT DEFAULT '',
                new_foreshadowings TEXT DEFAULT '',
                timeline_events TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                role_type TEXT DEFAULT 'supporting',
                mbti TEXT DEFAULT '',
                appearance TEXT DEFAULT '',
                personality TEXT DEFAULT '',
                background TEXT DEFAULT '',
                motivation TEXT DEFAULT '',
                arc TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                org_type TEXT DEFAULT '',
                location TEXT DEFAULT '',
                slogan TEXT DEFAULT '',
                description TEXT DEFAULT '',
                level INTEGER DEFAULT 1,
                power_level INTEGER DEFAULT 5,
                member_count INTEGER DEFAULT 0,
                status TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS foreshadowings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                importance TEXT DEFAULT 'medium',
                planted_chapter INTEGER,
                payoff_chapter INTEGER,
                effective_from INTEGER,
                expires_at INTEGER,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS generation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                task_type TEXT NOT NULL,
                request TEXT DEFAULT '',
                response TEXT DEFAULT '',
                status TEXT DEFAULT 'success',
                error TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """
        )

        # 资料工作台第二版新增的结构化字段。它们都给默认值，保证旧库可直接升级。
        _ensure_columns(
            conn,
            "world_settings",
            {
                "title": "TEXT DEFAULT ''",
                "category": "TEXT DEFAULT 'other'",
                "tags": "TEXT DEFAULT ''",
                "importance": "TEXT DEFAULT 'medium'",
                "related_chapters": "TEXT DEFAULT ''",
                "related_characters": "TEXT DEFAULT ''",
                "related_organizations": "TEXT DEFAULT ''",
                "related_foreshadowings": "TEXT DEFAULT ''",
                "conflict_notes": "TEXT DEFAULT ''",
            },
        )
        _ensure_columns(
            conn,
            "characters",
            {
                "identity": "TEXT DEFAULT ''",
                "faction": "TEXT DEFAULT ''",
                "weakness": "TEXT DEFAULT ''",
                "secret": "TEXT DEFAULT ''",
                "dialogue_style": "TEXT DEFAULT ''",
                "relationships": "TEXT DEFAULT ''",
                "chapters": "TEXT DEFAULT ''",
                "organization_ids": "TEXT DEFAULT ''",
                "related_character_ids": "TEXT DEFAULT ''",
                "ai_notes": "TEXT DEFAULT ''",
            },
        )
        _ensure_columns(
            conn,
            "organizations",
            {
                "hierarchy": "TEXT DEFAULT ''",
                "resources": "TEXT DEFAULT ''",
                "goal": "TEXT DEFAULT ''",
                "core_members": "TEXT DEFAULT ''",
                "allies": "TEXT DEFAULT ''",
                "enemies": "TEXT DEFAULT ''",
                "impact": "TEXT DEFAULT ''",
                "risk_notes": "TEXT DEFAULT ''",
            },
        )
        _ensure_columns(
            conn,
            "foreshadowings",
            {
                "related_character_ids": "TEXT DEFAULT ''",
                "related_organization_ids": "TEXT DEFAULT ''",
                "related_outline_ids": "TEXT DEFAULT ''",
            },
        )

        row = conn.execute("SELECT id FROM projects LIMIT 1").fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO projects (name, theme, novel_type, synopsis)
                VALUES (?, ?, ?, ?)
                """,
                ("臆想创作示例项目", "未设置", "长篇网文", "从这里开始搭建你的第一本小说。"),
            )
