"""v024: 章节变化提案与审核记录。

提案将章节分析结果与当前设定写回分离，只有审核通过后才修改正式资料。
"""
from __future__ import annotations

from sqlalchemy import text


def upgrade(db) -> None:
    """创建提案表和查询索引；IF NOT EXISTS 保证迁移脚本可安全重入。"""
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS chapter_change_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT NOT NULL UNIQUE,
            proposal_key TEXT NOT NULL UNIQUE,
            project_id INTEGER NOT NULL,
            chapter_id INTEGER NOT NULL,
            run_id TEXT,
            version_id TEXT,
            entity_type TEXT NOT NULL,
            operation TEXT NOT NULL DEFAULT 'update',
            target_id INTEGER,
            target_label TEXT DEFAULT '',
            before_value TEXT DEFAULT '{}',
            proposed_value TEXT NOT NULL DEFAULT '{}',
            rationale TEXT DEFAULT '',
            evidence TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            review_note TEXT DEFAULT '',
            applied_entity_id INTEGER,
            reviewed_at TIMESTAMP,
            applied_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
        )
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_change_proposals_project_chapter_status
        ON chapter_change_proposals(project_id, chapter_id, status)
    """))
    db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_change_proposals_run_id
        ON chapter_change_proposals(run_id)
    """))


def downgrade(db) -> None:
    """移除本迁移创建的表。"""
    db.execute(text("DROP TABLE IF EXISTS chapter_change_proposals"))
