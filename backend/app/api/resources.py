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

    前端创作中心只需要数量概览，因此这里直接按表聚合，避免额外传输完整列表。
    """
    with get_connection() as conn:
        counts = {
            "characters": conn.execute(
                "SELECT COUNT(*) AS total FROM characters WHERE project_id = ?", (project_id,)
            ).fetchone()["total"],
            "outlines": conn.execute(
                "SELECT COUNT(*) AS total FROM outlines WHERE project_id = ?", (project_id,)
            ).fetchone()["total"],
            "chapters": conn.execute(
                "SELECT COUNT(*) AS total FROM chapters WHERE project_id = ?", (project_id,)
            ).fetchone()["total"],
            "foreshadowings": conn.execute(
                "SELECT COUNT(*) AS total FROM foreshadowings WHERE project_id = ?", (project_id,)
            ).fetchone()["total"],
        }
    return counts


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
