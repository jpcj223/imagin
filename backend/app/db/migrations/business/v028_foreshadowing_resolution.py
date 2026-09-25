"""v028：区分伏笔计划回收章节与实际回收章节。"""
from __future__ import annotations

from app.db.migrations.common import ensure_columns


def upgrade(db) -> None:
    """为伏笔表增加实际回收章节字段。

    步骤 1：按当前数据库方言检查伏笔表列。
    步骤 2：仅在缺少字段时添加 resolved_chapter，保留旧有计划章节数据。
    """
    ensure_columns(db, db.bind.dialect.name, "foreshadowings", {
        "resolved_chapter": "INTEGER NULL",
    })
