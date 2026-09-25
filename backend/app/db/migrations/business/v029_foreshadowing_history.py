"""v029：记录伏笔档案变化与章节来源。"""
from __future__ import annotations

from sqlalchemy import inspect, text


def upgrade(db) -> None:
    """创建伏笔历史表和查询索引。

    步骤 1：为项目内伏笔快照创建独立历史表。
    步骤 2：补建按项目、伏笔、章节和提案查询的索引。
    """
    if db.bind.dialect.name == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS foreshadowing_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                foreshadowing_id INTEGER NOT NULL,
                chapter_id INTEGER,
                proposal_id VARCHAR(64),
                source_type VARCHAR(32) NOT NULL DEFAULT 'manual',
                operation VARCHAR(24) NOT NULL DEFAULT 'update',
                changed_fields TEXT NOT NULL DEFAULT '[]',
                before_snapshot TEXT NOT NULL DEFAULT '{}',
                after_snapshot TEXT NOT NULL DEFAULT '{}',
                rationale TEXT DEFAULT '',
                evidence TEXT DEFAULT '',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS foreshadowing_history (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                project_id INTEGER NOT NULL,
                foreshadowing_id INTEGER NOT NULL,
                chapter_id INTEGER,
                proposal_id VARCHAR(64),
                source_type VARCHAR(32) NOT NULL DEFAULT 'manual',
                operation VARCHAR(24) NOT NULL DEFAULT 'update',
                changed_fields TEXT NOT NULL,
                before_snapshot TEXT NOT NULL,
                after_snapshot TEXT NOT NULL,
                rationale TEXT DEFAULT '',
                evidence TEXT DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    existing_indexes = {item["name"] for item in inspect(db.bind).get_indexes("foreshadowing_history")}
    for index_name, columns in (
        ("idx_foreshadowing_history_project_item", "project_id, foreshadowing_id, created_at"),
        ("idx_foreshadowing_history_chapter", "chapter_id"),
        ("ix_foreshadowing_history_proposal_id", "proposal_id"),
    ):
        if index_name not in existing_indexes:
            db.execute(text(f"CREATE INDEX {index_name} ON foreshadowing_history({columns})"))
