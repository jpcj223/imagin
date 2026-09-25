"""v030：保存设定共创回复的模型 Token 用量。"""
from __future__ import annotations

from sqlalchemy import inspect, text


def upgrade(db) -> None:
    """为历史与新消息添加供应商用量字段。

    步骤 1：确认设定共创消息表存在且尚无用量列；步骤 2：按数据库类型安全添加列。
    """
    inspector = inspect(db.bind)
    if "setting_chat_messages" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("setting_chat_messages")}
    if "token_usage" in columns:
        return

    if db.bind.dialect.name == "sqlite":
        db.execute(text(
            "ALTER TABLE setting_chat_messages "
            "ADD COLUMN token_usage TEXT DEFAULT ''"
        ))
    else:
        db.execute(text(
            "ALTER TABLE setting_chat_messages "
            "ADD COLUMN token_usage TEXT NULL"
        ))
