"""v034：记录章节版本的生成来源以及恢复来源。"""
from __future__ import annotations

from app.db.migrations.common import ensure_columns


def upgrade(db) -> None:
    """为旧版本增加可空来源字段，不改变现有版本记录。"""
    ensure_columns(db, db.bind.dialect.name, "generation_versions", {
        "source_type": "VARCHAR(32) NULL",
        "source_version_id": "VARCHAR(64) NULL",
    })
