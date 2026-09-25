"""v031：为章节摘要记录分析来源的工作流和正文版本。"""
from __future__ import annotations

from sqlalchemy import inspect, text

from app.db.migrations.common import ensure_columns


def upgrade(db) -> None:
    """补齐来源字段和索引，兼容已存在的章节摘要。"""
    # 步骤 1：数据库可能没有章节摘要表（旧安装或部分迁移环境），此时安全跳过。
    inspector = inspect(db.bind)
    if "chapter_summaries" not in inspector.get_table_names():
        return

    # 步骤 2：添加可空来源字段，不影响现有摘要记录和旧版人工分析。
    ensure_columns(
        db,
        db.bind.dialect.name,
        "chapter_summaries",
        {
            "source_run_id": "VARCHAR(64) NULL",
            "source_version_id": "VARCHAR(64) NULL",
        },
    )

    # 步骤 3：为按工作流或正文版本追溯摘要提供索引。
    existing_indexes = {item["name"] for item in inspect(db.bind).get_indexes("chapter_summaries")}
    for name, column in (
        ("idx_chapter_summaries_source_run", "source_run_id"),
        ("idx_chapter_summaries_source_version", "source_version_id"),
    ):
        if name not in existing_indexes:
            db.execute(text(f"CREATE INDEX {name} ON chapter_summaries({column})"))
