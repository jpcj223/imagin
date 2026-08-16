"""基于 SQLAlchemy ORM 的通用数据访问层。

提供与旧版 sqlite3 实现完全兼容的函数签名，上层 API 无需改动即可切换到 ORM。

使用方式：
    from app.db.repository import fetch_all, fetch_one, insert_row, update_row, delete_row

    projects = fetch_all("projects")
    project = fetch_one("projects", 1)
    new_project = insert_row("projects", {"name": "新书"})
    updated = update_row("projects", 1, {"name": "新书名"})
    delete_row("projects", 1)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import inspect

from app.db.session import get_business_db
from app.models.business import (
    Chapter,
    ChapterSummary,
    Character,
    Foreshadowing,
    GenerationLog,
    Organization,
    Outline,
    Project,
    WorldSetting,
)


# ---------------------------------------------------------------------------
# 表名 -> ORM 模型类 映射
# 所有通过 repository 操作的业务表都必须在此注册，防止任意表名注入。
# ---------------------------------------------------------------------------
TABLE_MAP: dict[str, type] = {
    "projects": Project,
    "world_settings": WorldSetting,
    "outlines": Outline,
    "chapters": Chapter,
    "chapter_summaries": ChapterSummary,
    "characters": Character,
    "organizations": Organization,
    "foreshadowings": Foreshadowing,
    "generation_logs": GenerationLog,
}


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------
def _get_model(table: str) -> type:
    """根据表名获取 ORM 模型类，表名非法时抛出 ValueError。"""
    if table not in TABLE_MAP:
        raise ValueError(f"未知表名: {table}")
    return TABLE_MAP[table]


def _orm_to_dict(obj: Any) -> dict[str, Any]:
    """将单个 SQLAlchemy ORM 对象转换为普通 dict。

    - 自动转换 datetime 为 ISO 格式字符串，保证 JSON 可序列化
    - 只包含映射到列的属性，排除 SQLAlchemy 内部状态
    """
    if obj is None:
        return None
    result: dict[str, Any] = {}
    for col in inspect(obj).mapper.column_attrs:
        value = getattr(obj, col.key)
        if isinstance(value, datetime):
            result[col.key] = value.isoformat() if value else None
        else:
            result[col.key] = value
    return result


# ---------------------------------------------------------------------------
# 公共 API（与旧版签名完全一致）
# ---------------------------------------------------------------------------
def row_to_dict(obj: Any) -> dict[str, Any] | None:
    """把单个 ORM 对象转换为普通 dict，便于 JSON 序列化。"""
    return _orm_to_dict(obj)


def rows_to_dicts(rows: list[Any]) -> list[dict[str, Any]]:
    """把 ORM 对象列表转换为普通 dict 列表，便于 FastAPI JSON 序列化。"""
    return [_orm_to_dict(row) for row in rows]


def fetch_all(table: str, project_id: int | None = None) -> list[dict[str, Any]]:
    """读取列表数据。

    table 来自上层白名单映射（TABLE_MAP）；project_id 为空时读取全表，
    用于 projects 等不绑定项目的配置表。
    """
    model = _get_model(table)
    with get_business_db() as db:
        query = db.query(model)
        if project_id is not None and hasattr(model, "project_id"):
            query = query.filter(model.project_id == project_id)
        query = query.order_by(model.id.desc())
        return rows_to_dicts(query.all())


def fetch_one(table: str, item_id: int) -> dict[str, Any] | None:
    """按 ID 读取单条记录。"""
    model = _get_model(table)
    with get_business_db() as db:
        obj = db.query(model).filter(model.id == item_id).first()
    return _orm_to_dict(obj)


def insert_row(table: str, payload: dict[str, Any]) -> dict[str, Any]:
    """插入记录并返回数据库生成的完整行。"""
    model = _get_model(table)
    with get_business_db() as db:
        obj = model(**payload)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _orm_to_dict(obj)


def update_row(table: str, item_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    """更新记录并返回更新后的完整行。

    注意：updated_at 由 ORM 模型的 onupdate=func.now() 自动维护，
    无需手动设置。
    """
    if not payload:
        return fetch_one(table, item_id)

    model = _get_model(table)
    with get_business_db() as db:
        obj = db.query(model).filter(model.id == item_id).first()
        if not obj:
            return None
        for key, value in payload.items():
            setattr(obj, key, value)
        db.commit()
        db.refresh(obj)
        return _orm_to_dict(obj)


def delete_row(table: str, item_id: int) -> None:
    """按 ID 删除记录。外键级联行为由数据库 schema 控制。"""
    model = _get_model(table)
    with get_business_db() as db:
        obj = db.query(model).filter(model.id == item_id).first()
        if obj:
            db.delete(obj)
            db.commit()
