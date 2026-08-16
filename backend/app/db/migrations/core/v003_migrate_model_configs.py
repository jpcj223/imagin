"""v003: 旧数据迁移 — 将 model_configs 从业务库迁移到核心库。

背景：在双库架构之前，model_configs 存在业务库 (yixiang.db) 中。
拆分后，模型配置属于全局共享数据，应放在核心库。

此迁移幂等：
- 如果核心库已有 model_configs 数据，跳过
- 如果业务库没有 model_configs 表或表为空，跳过
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import _business_engine


def upgrade(db: Session) -> None:
    # 1. 先检查核心库是否已有模型配置数据
    core_count = db.execute(text("SELECT COUNT(*) as cnt FROM model_configs")).fetchone()
    if core_count and core_count[0] > 0:
        print("[core] v003: 核心库已有模型配置，跳过迁移")
        return

    # 2. 检查业务库是否有 model_configs 表
    from sqlalchemy import inspect
    inspector = inspect(_business_engine)
    if "model_configs" not in inspector.get_table_names():
        print("[core] v003: 业务库无 model_configs 表，跳过迁移")
        return

    # 3. 从业务库读取数据
    from sqlalchemy.orm import sessionmaker
    BusinessSession = sessionmaker(bind=_business_engine)
    biz_db = BusinessSession()
    try:
        biz_rows = biz_db.execute(text(
            "SELECT name, base_url, api_key, model, is_active, "
            "temperature, max_tokens, top_p, frequency_penalty, "
            "presence_penalty, proxy_url, created_at, updated_at "
            "FROM model_configs ORDER BY id"
        )).fetchall()

        if not biz_rows:
            print("[core] v003: 业务库无模型配置数据，跳过迁移")
            return

        # 4. 插入到核心库
        dialect = db.bind.dialect.name
        for row in biz_rows:
            if dialect == "sqlite":
                db.execute(text(
                    "INSERT INTO model_configs "
                    "(name, base_url, api_key, model, is_active, "
                    "temperature, max_tokens, top_p, frequency_penalty, "
                    "presence_penalty, proxy_url, created_at, updated_at) "
                    "VALUES (:name, :base_url, :api_key, :model, :is_active, "
                    ":temperature, :max_tokens, :top_p, :frequency_penalty, "
                    ":presence_penalty, :proxy_url, :created_at, :updated_at)"
                ), {
                    "name": row[0], "base_url": row[1], "api_key": row[2],
                    "model": row[3], "is_active": row[4], "temperature": row[5],
                    "max_tokens": row[6], "top_p": row[7], "frequency_penalty": row[8],
                    "presence_penalty": row[9], "proxy_url": row[10],
                    "created_at": row[11], "updated_at": row[12],
                })
            else:
                db.execute(text(
                    "INSERT INTO model_configs "
                    "(name, base_url, api_key, model, is_active, "
                    "temperature, max_tokens, top_p, frequency_penalty, "
                    "presence_penalty, proxy_url, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                ), (
                    row[0], row[1], row[2], row[3], row[4], row[5],
                    row[6], row[7], row[8], row[9], row[10], row[11], row[12],
                ))

        print(f"[core] v003: 已从业务库迁移 {len(biz_rows)} 条模型配置")
        db.commit()
    finally:
        biz_db.close()
