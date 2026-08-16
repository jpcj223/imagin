from __future__ import annotations

from typing import Any

from app.db.database import get_connection


def rows_to_dicts(rows: list[Any]) -> list[dict[str, Any]]:
    """把 sqlite3.Row 结果转换为普通 dict，便于 FastAPI JSON 序列化。"""
    return [dict(row) for row in rows]


def fetch_all(table: str, project_id: int | None = None) -> list[dict[str, Any]]:
    """读取列表数据。

    table 来自上层白名单映射；project_id 为空时用于读取不绑定项目的配置表。
    """
    with get_connection() as conn:
        if project_id is None:
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY id DESC").fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE project_id = ? ORDER BY id DESC",
                (project_id,),
            ).fetchall()
    return rows_to_dicts(rows)


def fetch_one(table: str, item_id: int) -> dict[str, Any] | None:
    """按 ID 读取单条记录。"""
    with get_connection() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def insert_row(table: str, payload: dict[str, Any]) -> dict[str, Any]:
    """插入记录并返回数据库生成的完整行。"""
    columns = list(payload.keys())
    values = [payload[column] for column in columns]
    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(columns)

    with get_connection() as conn:
        cursor = conn.execute(
            f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def update_row(table: str, item_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    """更新记录并返回更新后的完整行。"""
    if not payload:
        return fetch_one(table, item_id)

    assignments = ", ".join(f"{column} = ?" for column in payload)
    values = list(payload.values()) + [item_id]

    with get_connection() as conn:
        conn.execute(
            f"UPDATE {table} SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values,
        )
        conn.commit()
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def delete_row(table: str, item_id: int) -> None:
    """按 ID 删除记录。外键级联行为由数据库 schema 控制。"""
    with get_connection() as conn:
        conn.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
        conn.commit()
