from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db.database import get_connection
from app.db.repository import delete_row, fetch_all, insert_row, update_row
from app.schemas.models import (
    CharacterSave,
    ChapterSave,
    ForeshadowingSave,
    OrganizationSave,
    OutlineSave,
    WorldSettingSave,
)


router = APIRouter()


@router.get("/{project_id}/dashboard")
def dashboard(project_id: int) -> dict:
    """返回项目首页统计数据。

    包含：各资源数量、字数统计、最近章节、组织/世界观数量等，
    供前端创作中心展示项目整体进度和快捷入口。
    """
    with get_connection() as conn:
        # 1. 基础计数
        characters = conn.execute(
            "SELECT COUNT(*) AS total FROM characters WHERE project_id = ?", (project_id,)
        ).fetchone()["total"]
        outlines = conn.execute(
            "SELECT COUNT(*) AS total FROM outlines WHERE project_id = ?", (project_id,)
        ).fetchone()["total"]
        chapters = conn.execute(
            "SELECT COUNT(*) AS total FROM chapters WHERE project_id = ?", (project_id,)
        ).fetchone()["total"]
        foreshadowings = conn.execute(
            "SELECT COUNT(*) AS total FROM foreshadowings WHERE project_id = ?", (project_id,)
        ).fetchone()["total"]
        organizations = conn.execute(
            "SELECT COUNT(*) AS total FROM organizations WHERE project_id = ?", (project_id,)
        ).fetchone()["total"]
        world_settings = conn.execute(
            "SELECT COUNT(*) AS total FROM world_settings WHERE project_id = ?", (project_id,)
        ).fetchone()["total"]

        # 2. 总字数（所有章节正文长度之和）
        total_words_row = conn.execute(
            "SELECT COALESCE(SUM(LENGTH(content)), 0) AS total FROM chapters WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        total_chars = total_words_row["total"] if total_words_row else 0

        # 3. 最近章节（按章节号倒序取最近 5 章）
        recent_chapters_rows = conn.execute(
            """
            SELECT id, chapter_no, title, status, LENGTH(content) as char_count, updated_at
            FROM chapters
            WHERE project_id = ?
            ORDER BY chapter_no DESC
            LIMIT 5
            """,
            (project_id,),
        ).fetchall()
        recent_chapters = [dict(row) for row in recent_chapters_rows]

        # 4. 伏笔状态分布
        foreshadowing_status_rows = conn.execute(
            """
            SELECT status, COUNT(*) as count
            FROM foreshadowings
            WHERE project_id = ?
            GROUP BY status
            """,
            (project_id,),
        ).fetchall()
        foreshadowing_by_status = {row["status"]: row["count"] for row in foreshadowing_status_rows}

        # 5. 角色类型分布
        character_type_rows = conn.execute(
            """
            SELECT role_type, COUNT(*) as count
            FROM characters
            WHERE project_id = ?
            GROUP BY role_type
            """,
            (project_id,),
        ).fetchall()
        characters_by_type = {row["role_type"]: row["count"] for row in character_type_rows}

    return {
        "counts": {
            "characters": characters,
            "outlines": outlines,
            "chapters": chapters,
            "foreshadowings": foreshadowings,
            "organizations": organizations,
            "world_settings": world_settings,
        },
        "total_chars": total_chars,
        "recent_chapters": recent_chapters,
        "foreshadowing_by_status": foreshadowing_by_status,
        "characters_by_type": characters_by_type,
    }


@router.get("/{project_id}/{resource}")
def list_resource(project_id: int, resource: str) -> list[dict]:
    """按项目读取某一类创作资料列表。"""
    table = _resource_table(resource)
    return fetch_all(table, project_id)


@router.post("/world")
def save_world(payload: WorldSettingSave) -> dict:
    """新增世界观设定。"""
    return insert_row("world_settings", payload.model_dump())


@router.post("/outlines")
def save_outline(payload: OutlineSave) -> dict:
    """新增大纲节点。"""
    return insert_row("outlines", payload.model_dump())


@router.post("/chapters")
def save_chapter(payload: ChapterSave) -> dict:
    """新增章节草稿。"""
    return insert_row("chapters", payload.model_dump())


@router.post("/characters")
def save_character(payload: CharacterSave) -> dict:
    """新增角色卡。"""
    return insert_row("characters", payload.model_dump())


@router.post("/organizations")
def save_organization(payload: OrganizationSave) -> dict:
    """新增组织势力。"""
    return insert_row("organizations", payload.model_dump())


@router.post("/foreshadowings")
def save_foreshadowing(payload: ForeshadowingSave) -> dict:
    """新增伏笔记录。"""
    return insert_row("foreshadowings", payload.model_dump())


@router.put("/{resource}/{item_id}")
def update_resource(resource: str, item_id: int, payload: dict) -> dict:
    """更新某一条创作资料。

    resource 先经过白名单映射，payload 只包含前端提交的业务字段。
    """
    table = _resource_table(resource)
    updated = update_row(table, item_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="资源不存在")
    return updated


@router.delete("/{resource}/{item_id}")
def delete_resource(resource: str, item_id: int) -> dict:
    """删除资源。

    resource 只允许映射表中的业务资源名，避免前端把任意表名传进来。
    """
    table = _resource_table(resource)
    delete_row(table, item_id)
    return {"ok": True, "id": item_id}


def _resource_table(resource: str) -> str:
    """把前端资源名映射到数据库表名。

    所有通用 CRUD 都必须通过这里，避免任意表名被拼进 SQL。
    """
    mapping = {
        "world": "world_settings",
        "outlines": "outlines",
        "characters": "characters",
        "organizations": "organizations",
        "foreshadowings": "foreshadowings",
        "chapters": "chapters",
    }
    if resource not in mapping:
        raise HTTPException(status_code=404, detail="未知资源")
    return mapping[resource]
