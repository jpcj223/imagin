"""v023: 设定共创对话表

新增：
- setting_chat_sessions: 设定共创会话
- setting_chat_messages: 对话消息记录
"""
from __future__ import annotations

from sqlalchemy import text


def upgrade(db) -> None:
    """执行迁移。"""

    # 设定共创会话表
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS setting_chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL UNIQUE,
            project_id INTEGER NOT NULL,
            user_id INTEGER DEFAULT 1,
            title TEXT NOT NULL DEFAULT '新设定对话',
            target_type TEXT NOT NULL DEFAULT 'character',
            target_id INTEGER,
            target_name TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            completeness INTEGER DEFAULT 0,
            focus_areas TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    # 对话消息表
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS setting_chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            thought TEXT DEFAULT '',
            extracted_fields TEXT DEFAULT '[]',
            memory_written INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    # 索引
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_setting_chat_sessions_project
        ON setting_chat_sessions(project_id)
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_setting_chat_messages_session
        ON setting_chat_messages(session_id)
    """))


def downgrade(db) -> None:
    """回滚迁移。"""
    db.execute(text("DROP TABLE IF EXISTS setting_chat_messages"))
    db.execute(text("DROP TABLE IF EXISTS setting_chat_sessions"))
