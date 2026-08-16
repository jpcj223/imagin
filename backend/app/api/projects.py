from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db.repository import fetch_all, fetch_one, insert_row, update_row, delete_row
from app.schemas.models import ProjectCreate, ProjectUpdate


router = APIRouter()


@router.get("")
def list_projects() -> list[dict]:
    return fetch_all("projects")


@router.get("/{project_id}")
def get_project(project_id: int) -> dict:
    project = fetch_one("projects", project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.post("")
def create_project(payload: ProjectCreate) -> dict:
    return insert_row("projects", payload.model_dump())


@router.put("/{project_id}")
def update_project(project_id: int, payload: ProjectUpdate) -> dict:
    data = payload.model_dump(exclude_none=True)
    project = update_row("projects", project_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.delete("/{project_id}")
def delete_project(project_id: int) -> dict:
    """删除项目及其所有关联数据（人物/组织/伏笔/大纲/章节等级联删除）。
    为防止误操作，至少保留一个项目；如果是最后一个，拒绝删除。
    """
    all_projects = fetch_all("projects")
    if len(all_projects) <= 1:
        raise HTTPException(status_code=400, detail="至少需要保留一个项目，无法删除")
    project = fetch_one("projects", project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    delete_row("projects", project_id)
    return {"id": project_id, "deleted": True}
