"""v033：将章节分析与变化提案绑定到分析时的正文指纹。"""
from __future__ import annotations

from app.db.migrations.common import ensure_columns


def upgrade(db) -> None:
    """添加可空指纹字段，兼容无法追溯正文的旧分析记录。"""
    ensure_columns(db, db.bind.dialect.name, "chapter_summaries", {
        "source_content_hash": "VARCHAR(64) NULL",
    })
    ensure_columns(db, db.bind.dialect.name, "chapter_change_proposals", {
        "source_content_hash": "VARCHAR(64) NULL",
    })
