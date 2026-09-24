"""v027：组织档案变更历史和章节来源记录。"""
from __future__ import annotations

from sqlalchemy import inspect, text


def upgrade(db) -> None:
    """创建组织快照历史表和查询索引。

    步骤 1：按数据库类型创建历史表。
    步骤 2：检查并补建组织、章节和提案查询索引。
    """
    if db.bind.dialect.name == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS organization_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                organization_id INTEGER NOT NULL,
                chapter_id INTEGER,
                proposal_id VARCHAR(64),
                source_type VARCHAR(32) NOT NULL DEFAULT 'manual',
                operation VARCHAR(16) NOT NULL DEFAULT 'update',
                changed_fields TEXT NOT NULL DEFAULT '[]',
                before_snapshot TEXT NOT NULL DEFAULT '{}',
                after_snapshot TEXT NOT NULL DEFAULT '{}',
                rationale TEXT DEFAULT '',
                evidence TEXT DEFAULT '',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS organization_history (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                project_id INTEGER NOT NULL,
                organization_id INTEGER NOT NULL,
                chapter_id INTEGER,
                proposal_id VARCHAR(64),
                source_type VARCHAR(32) NOT NULL DEFAULT 'manual',
                operation VARCHAR(16) NOT NULL DEFAULT 'update',
                changed_fields TEXT NOT NULL,
                before_snapshot TEXT NOT NULL,
                after_snapshot TEXT NOT NULL,
                rationale TEXT DEFAULT '',
                evidence TEXT DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    # 数据库迁移器也兼容 MySQL；先检查索引，避免部分 DDL 失败后重复创建。
    existing_indexes = {item["name"] for item in inspect(db.bind).get_indexes("organization_history")}
    for index_name, columns in (
        ("idx_organization_history_project_org", "project_id, organization_id, created_at"),
        ("idx_organization_history_chapter", "chapter_id"),
        ("ix_organization_history_proposal_id", "proposal_id"),
    ):
        if index_name not in existing_indexes:
            db.execute(text(f"CREATE INDEX {index_name} ON organization_history({columns})"))
