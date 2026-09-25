"""人物资料历史查询路由。"""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func

from app.db.session import get_business_db
from app.models.business import Chapter, ForeshadowingHistory, Organization, OrganizationHistory
from app.services.foreshadowing_history import parse_history_json as parse_foreshadowing_history_json
from app.services.organization_history import parse_history_json

router = APIRouter()

@router.get("/{project_id}/foreshadowings/{foreshadowing_id}/history")
def list_foreshadowing_history(
    project_id: int,
    foreshadowing_id: int,
    limit: int = Query(default=30, ge=1, le=100),
) -> dict:
    """读取伏笔历史，附上章节和提案来源。

    步骤 1：按项目与伏笔 ID 统计并查询历史记录。
    步骤 2：补充章节标题，解析前后快照 JSON。
    步骤 3：返回最近记录，并支持追溯已删除伏笔的删除历史。
    """
    with get_business_db() as db:
        total = db.query(func.count(ForeshadowingHistory.id)).filter(
            ForeshadowingHistory.project_id == project_id,
            ForeshadowingHistory.foreshadowing_id == foreshadowing_id,
        ).scalar() or 0
        rows = db.query(
            ForeshadowingHistory,
            Chapter.chapter_no,
            Chapter.title,
        ).outerjoin(
            Chapter, Chapter.id == ForeshadowingHistory.chapter_id
        ).filter(
            ForeshadowingHistory.project_id == project_id,
            ForeshadowingHistory.foreshadowing_id == foreshadowing_id,
        ).order_by(
            ForeshadowingHistory.created_at.desc(),
            ForeshadowingHistory.id.desc(),
        ).limit(limit).all()

    items = [
        {
            "id": history.id,
            "project_id": history.project_id,
            "foreshadowing_id": history.foreshadowing_id,
            "chapter_id": history.chapter_id,
            "chapter_no": chapter_no,
            "chapter_title": chapter_title or "",
            "proposal_id": history.proposal_id,
            "source_type": history.source_type,
            "operation": history.operation,
            "changed_fields": parse_foreshadowing_history_json(history.changed_fields, []),
            "before_snapshot": parse_foreshadowing_history_json(history.before_snapshot, {}),
            "after_snapshot": parse_foreshadowing_history_json(history.after_snapshot, {}),
            "rationale": history.rationale or "",
            "evidence": history.evidence or "",
            "created_at": history.created_at.isoformat() if history.created_at else None,
        }
        for history, chapter_no, chapter_title in rows
    ]
    return {"items": items, "total": total}


@router.get("/{project_id}/organizations/{organization_id}/history")
def list_organization_history(
    project_id: int,
    organization_id: int,
    limit: int = Query(default=30, ge=1, le=100),
) -> dict:
    """读取组织档案变更历史及章节来源。

    步骤 1：验证组织属于当前项目。
    步骤 2：统计历史总数并读取最近记录。
    步骤 3：补充章节标题并解析前后快照后返回。
    """
    with get_business_db() as db:
        organization = db.query(Organization).filter(
            Organization.id == organization_id,
            Organization.project_id == project_id,
        ).first()
        if not organization:
            raise HTTPException(status_code=404, detail="组织不存在或不属于当前项目")

        total = db.query(func.count(OrganizationHistory.id)).filter(
            OrganizationHistory.project_id == project_id,
            OrganizationHistory.organization_id == organization_id,
        ).scalar() or 0
        rows = db.query(
            OrganizationHistory,
            Chapter.chapter_no,
            Chapter.title,
        ).outerjoin(
            Chapter, Chapter.id == OrganizationHistory.chapter_id
        ).filter(
            OrganizationHistory.project_id == project_id,
            OrganizationHistory.organization_id == organization_id,
        ).order_by(
            OrganizationHistory.created_at.desc(),
            OrganizationHistory.id.desc(),
        ).limit(limit).all()

    items = [
        {
            "id": history.id,
            "project_id": history.project_id,
            "organization_id": history.organization_id,
            "chapter_id": history.chapter_id,
            "chapter_no": chapter_no,
            "chapter_title": chapter_title or "",
            "proposal_id": history.proposal_id,
            "source_type": history.source_type,
            "operation": history.operation,
            "changed_fields": parse_history_json(history.changed_fields, []),
            "before_snapshot": parse_history_json(history.before_snapshot, {}),
            "after_snapshot": parse_history_json(history.after_snapshot, {}),
            "rationale": history.rationale or "",
            "evidence": history.evidence or "",
            "created_at": history.created_at.isoformat() if history.created_at else None,
        }
        for history, chapter_no, chapter_title in rows
    ]
    return {"items": items, "total": total}
