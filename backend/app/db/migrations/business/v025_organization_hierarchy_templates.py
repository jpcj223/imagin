"""v025：为组织保存各层级体系的独立副本。"""
from __future__ import annotations

from sqlalchemy import text


def upgrade(db) -> None:
    """添加体系模板副本字段，并为已有组织初始化空映射。"""
    # 第一步：读取当前数据库方言下的组织表字段。
    dialect = db.bind.dialect.name
    if dialect == "sqlite":
        columns = {row[1] for row in db.execute(text("PRAGMA table_info(organizations)")).fetchall()}
    else:
        columns = {row[0] for row in db.execute(text("DESCRIBE organizations")).fetchall()}

    # 第二步：兼容已有数据库，仅在字段缺失时添加。
    if "hierarchy_templates" not in columns:
        db.execute(text("ALTER TABLE organizations ADD COLUMN hierarchy_templates TEXT"))

    # 第三步：旧数据没有体系副本，统一初始化为空 JSON 对象。
    db.execute(text("UPDATE organizations SET hierarchy_templates = '{}' WHERE hierarchy_templates IS NULL"))

