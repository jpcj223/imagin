"""组织档案关系路由及其组织视角的关系快照工具。"""

from fastapi import APIRouter, HTTPException

from app.db.session import get_business_db
from app.models.business import Organization, OrganizationRelation
from app.schemas.models import OrganizationRelationSave
from app.services.organization_history import (
    capture_organization_relation_snapshot,
    record_organization_history,
)

router = APIRouter()

@router.get("/{project_id}/organizations/{organization_id}/relations")
def list_organization_relations(project_id: int, organization_id: int) -> dict:
    """读取组织间关系。

    步骤 1：验证当前组织属于项目。
    步骤 2：查找组织作为关系任一端的记录。
    步骤 3：从当前组织视角附上对端名称后返回。
    """
    with get_business_db() as db:
        organization = db.query(Organization).filter(
            Organization.id == organization_id,
            Organization.project_id == project_id,
        ).first()
        if not organization:
            raise HTTPException(status_code=404, detail="组织不存在或不属于当前项目")

        rows = db.query(OrganizationRelation).filter(
            OrganizationRelation.project_id == project_id,
            (OrganizationRelation.organization_a_id == organization_id)
            | (OrganizationRelation.organization_b_id == organization_id),
        ).order_by(OrganizationRelation.effective_from_chapter, OrganizationRelation.id).all()
        items = [_serialize_organization_relation(db, row, organization_id) for row in rows]
    return {"items": items, "total": len(items)}


@router.post("/{project_id}/organizations/{organization_id}/relations")
def create_organization_relation(
    project_id: int,
    organization_id: int,
    payload: OrganizationRelationSave,
) -> dict:
    """新增组织关系。

    步骤 1：验证关系两端都属于当前项目。
    步骤 2：校验自关联与章节范围重叠。
    步骤 3：以固定端点顺序保存，并为两端组织记历史。
    步骤 4：提交关系和历史记录后返回关系视图。
    """
    with get_business_db() as db:
        current = _get_project_organization(db, project_id, organization_id)
        target = _get_project_organization(db, project_id, payload.target_org_id)
        _validate_organization_relation(db, project_id, current, target, payload)

        first_id, second_id = sorted((current.id, target.id))
        relation = OrganizationRelation(
            project_id=project_id,
            organization_a_id=first_id,
            organization_b_id=second_id,
            relation_type=payload.relation_type,
            description=payload.description,
            effective_from_chapter=payload.effective_from_chapter,
            expires_at_chapter=payload.expires_at_chapter,
        )
        db.add(relation)
        db.flush()
        _record_manual_organization_relation_history(
            db,
            project_id,
            relation,
            before_snapshots={},
            after_organization_ids={current.id, target.id},
        )
        db.commit()
        db.refresh(relation)
        result = _serialize_organization_relation(db, relation, current.id)
    return result


@router.put("/{project_id}/organizations/{organization_id}/relations/{relation_id}")
def update_organization_relation(
    project_id: int,
    organization_id: int,
    relation_id: int,
    payload: OrganizationRelationSave,
) -> dict:
    """更新当前组织关联的一条关系记录。

    步骤 1：按项目和关系两端限定目标记录，并保存旧快照。
    步骤 2：重新校验组织归属和时间范围。
    步骤 3：写回关系并记录两端变更历史。
    步骤 4：提交并返回当前组织视角的结果。
    """
    with get_business_db() as db:
        current = _get_project_organization(db, project_id, organization_id)
        relation = db.query(OrganizationRelation).filter(
            OrganizationRelation.id == relation_id,
            OrganizationRelation.project_id == project_id,
            (OrganizationRelation.organization_a_id == organization_id)
            | (OrganizationRelation.organization_b_id == organization_id),
        ).first()
        if not relation:
            raise HTTPException(status_code=404, detail="组织关系不存在")
        old_organization_ids = {relation.organization_a_id, relation.organization_b_id}
        before_snapshots = {
            owner_id: capture_organization_relation_snapshot(db, relation, owner_id)
            for owner_id in old_organization_ids
        }
        target = _get_project_organization(db, project_id, payload.target_org_id)
        _validate_organization_relation(db, project_id, current, target, payload, exclude_id=relation.id)

        first_id, second_id = sorted((current.id, target.id))
        relation.organization_a_id = first_id
        relation.organization_b_id = second_id
        relation.relation_type = payload.relation_type
        relation.description = payload.description
        relation.effective_from_chapter = payload.effective_from_chapter
        relation.expires_at_chapter = payload.expires_at_chapter
        db.flush()
        _record_manual_organization_relation_history(
            db,
            project_id,
            relation,
            before_snapshots=before_snapshots,
            after_organization_ids={relation.organization_a_id, relation.organization_b_id},
        )
        db.commit()
        db.refresh(relation)
        result = _serialize_organization_relation(db, relation, current.id)
    return result


@router.delete("/{project_id}/organizations/{organization_id}/relations/{relation_id}")
def delete_organization_relation(project_id: int, organization_id: int, relation_id: int) -> dict:
    """删除当前组织关联的一条关系记录并保存两端历史。

    步骤 1：限定项目、当前组织和关系 ID。
    步骤 2：在删除前保存两端的关系快照。
    步骤 3：删除关系并把变化记录到两端组织历史。
    """
    with get_business_db() as db:
        _get_project_organization(db, project_id, organization_id)
        relation = db.query(OrganizationRelation).filter(
            OrganizationRelation.id == relation_id,
            OrganizationRelation.project_id == project_id,
            (OrganizationRelation.organization_a_id == organization_id)
            | (OrganizationRelation.organization_b_id == organization_id),
        ).first()
        if not relation:
            raise HTTPException(status_code=404, detail="组织关系不存在")
        old_organization_ids = {relation.organization_a_id, relation.organization_b_id}
        before_snapshots = {
            owner_id: capture_organization_relation_snapshot(db, relation, owner_id)
            for owner_id in old_organization_ids
        }
        db.delete(relation)
        _record_manual_organization_relation_history(
            db,
            project_id,
            relation,
            before_snapshots=before_snapshots,
            after_organization_ids=set(),
        )
        db.commit()
    return {"ok": True, "id": relation_id}


def _record_manual_organization_relation_history(
    db,
    project_id: int,
    relation: OrganizationRelation,
    before_snapshots: dict[int, dict],
    after_organization_ids: set[int],
) -> None:
    """为组织关系两端写入手动变更历史。

    步骤 1：合并关系变更前后的组织端点。
    步骤 2：按组织视角整理前后快照和新增、更新、移除动作。
    步骤 3：把历史行加入当前事务，随关系写入一并提交。
    """
    before_organization_ids = set(before_snapshots)
    for owner_id in before_organization_ids | after_organization_ids:
        owner = db.query(Organization).filter(
            Organization.id == owner_id,
            Organization.project_id == project_id,
        ).first()
        if not owner:
            continue
        before_snapshot = before_snapshots.get(owner_id, {})
        after_snapshot = (
            capture_organization_relation_snapshot(db, relation, owner_id)
            if owner_id in after_organization_ids
            else {}
        )
        operation = (
            "create" if owner_id not in before_organization_ids
            else "delete" if owner_id not in after_organization_ids
            else "update"
        )
        record_organization_history(
            db=db,
            organization=owner,
            source_type="manual",
            operation=operation,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            changed_fields_override=["organization_relation"],
        )


def _get_project_organization(db, project_id: int, organization_id: int) -> Organization:
    """限定组织必须属于当前项目，避免跨项目建立关联。"""
    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.project_id == project_id,
    ).first()
    if not organization:
        raise HTTPException(status_code=404, detail="组织不存在或不属于当前项目")
    return organization


def _validate_organization_relation(
    db,
    project_id: int,
    current: Organization,
    target: Organization,
    payload: OrganizationRelationSave,
    exclude_id: int | None = None,
) -> None:
    """校验自关联、章节区间和同一组织对的区间重叠。"""
    if current.id == target.id:
        raise HTTPException(status_code=422, detail="组织不能与自身建立关系")
    start = payload.effective_from_chapter
    end = payload.expires_at_chapter
    if start is not None and end is not None and end < start:
        raise HTTPException(status_code=422, detail="关系失效章节不能早于生效章节")

    first_id, second_id = sorted((current.id, target.id))
    query = db.query(OrganizationRelation).filter(
        OrganizationRelation.project_id == project_id,
        OrganizationRelation.organization_a_id == first_id,
        OrganizationRelation.organization_b_id == second_id,
    )
    if exclude_id is not None:
        query = query.filter(OrganizationRelation.id != exclude_id)
    for existing in query.all():
        old_start = existing.effective_from_chapter
        old_end = existing.expires_at_chapter
        starts_before_old_end = old_end is None or start is None or start <= old_end
        old_starts_before_end = end is None or old_start is None or old_start <= end
        if starts_before_old_end and old_starts_before_end:
            raise HTTPException(status_code=409, detail="这两个组织在该章节范围内已有关系记录")


def _serialize_organization_relation(db, relation: OrganizationRelation, current_org_id: int) -> dict:
    """按请求组织方向序列化另一端名称和章节范围。"""
    target_id = (
        relation.organization_b_id
        if relation.organization_a_id == current_org_id
        else relation.organization_a_id
    )
    target = db.query(Organization).filter(Organization.id == target_id).first()
    return {
        "id": relation.id,
        "project_id": relation.project_id,
        "organization_id": current_org_id,
        "target_org_id": target_id,
        "target_org_name": target.name if target else "（组织已删除）",
        "relation_type": relation.relation_type,
        "description": relation.description or "",
        "effective_from_chapter": relation.effective_from_chapter,
        "expires_at_chapter": relation.expires_at_chapter,
        "created_at": relation.created_at.isoformat() if relation.created_at else None,
        "updated_at": relation.updated_at.isoformat() if relation.updated_at else None,
    }
