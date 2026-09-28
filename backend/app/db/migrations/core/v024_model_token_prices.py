"""核心库迁移 v024：为模型配置增加 Token 单价。"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


PRICE_COLUMNS = {
    "input_price_per_million": "REAL NULL",
    "output_price_per_million": "REAL NULL",
    "cached_input_price_per_million": "REAL NULL",
}


def upgrade(db: Session) -> None:
    """幂等补齐输入、输出及可选缓存输入的人民币单价字段。"""
    dialect = db.bind.dialect.name
    existing = {column["name"] for column in inspect(db.bind).get_columns("model_configs")}
    number_type = "REAL" if dialect == "sqlite" else "DOUBLE"
    for column_name in PRICE_COLUMNS:
        if column_name in existing:
            continue
        db.execute(text(f"ALTER TABLE model_configs ADD COLUMN {column_name} {number_type} NULL"))
