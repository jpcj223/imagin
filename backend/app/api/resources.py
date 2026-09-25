from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.repository import delete_row, fetch_all, insert_row, row_to_dict, update_row
from app.db.session import get_business_db
from app.models.business import (
    Chapter,
    Character,
    Foreshadowing,
    Organization,
    OrganizationHistory,
    OrganizationRelation,
    Outline,
    WorldSetting,
)
from app.schemas.models import (
    CharacterSave,
    ChapterSave,
    ForeshadowingSave,
    OrganizationSave,
    OrganizationRelationSave,
    OutlineSave,
    WorldSettingSave,
)
from app.services.organization_history import (
    capture_organization_relation_snapshot,
    capture_organization_snapshot,
    parse_history_json,
    record_organization_history,
)


router = APIRouter()


@router.get("/{project_id}/dashboard")
def dashboard(project_id: int) -> dict:
    """返回项目首页统计数据。

    包含：各资源数量、字数统计、最近章节、组织/世界观数量等，
    供前端创作中心展示项目整体进度和快捷入口。
    """
    with get_business_db() as db:
        # 1. 基础计数
        characters = db.query(func.count(Character.id)).filter(Character.project_id == project_id).scalar() or 0
        outlines = db.query(func.count(Outline.id)).filter(Outline.project_id == project_id).scalar() or 0
        chapters = db.query(func.count(Chapter.id)).filter(Chapter.project_id == project_id).scalar() or 0
        foreshadowings = db.query(func.count(Foreshadowing.id)).filter(Foreshadowing.project_id == project_id).scalar() or 0
        organizations = db.query(func.count(Organization.id)).filter(Organization.project_id == project_id).scalar() or 0
        world_settings = db.query(func.count(WorldSetting.id)).filter(WorldSetting.project_id == project_id).scalar() or 0

        # 2. 总字数（所有章节正文长度之和）
        total_chars_row = db.query(
            func.coalesce(func.sum(func.length(Chapter.content)), 0)
        ).filter(Chapter.project_id == project_id).first()
        total_chars = total_chars_row[0] if total_chars_row else 0

        # 3. 最近章节（按章节号倒序取最近 5 章）
        recent_chapters_rows = db.query(
            Chapter.id,
            Chapter.chapter_no,
            Chapter.title,
            Chapter.status,
            func.length(Chapter.content).label("char_count"),
            Chapter.updated_at,
        ).filter(
            Chapter.project_id == project_id
        ).order_by(
            Chapter.chapter_no.desc()
        ).limit(5).all()

        recent_chapters = [
            {
                "id": row.id,
                "chapter_no": row.chapter_no,
                "title": row.title,
                "status": row.status,
                "char_count": row.char_count,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in recent_chapters_rows
        ]

        # 4. 伏笔状态分布
        foreshadowing_status_rows = db.query(
            Foreshadowing.status,
            func.count(Foreshadowing.id).label("count"),
        ).filter(
            Foreshadowing.project_id == project_id
        ).group_by(Foreshadowing.status).all()
        foreshadowing_by_status = {row.status: row.count for row in foreshadowing_status_rows}

        # 5. 角色类型分布
        character_type_rows = db.query(
            Character.role_type,
            func.count(Character.id).label("count"),
        ).filter(
            Character.project_id == project_id
        ).group_by(Character.role_type).all()
        characters_by_type = {row.role_type: row.count for row in character_type_rows}

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
    """新增组织势力。

    步骤 1：创建组织并取得数据库 ID。
    步骤 2：用创建后的档案生成首条历史快照。
    步骤 3：在同一事务中提交组织和历史记录。
    """
    with get_business_db() as db:
        organization = Organization(**payload.model_dump())
        db.add(organization)
        db.flush()
        record_organization_history(
            db=db,
            organization=organization,
            source_type="manual",
            operation="create",
            before_snapshot={},
            after_snapshot=capture_organization_snapshot(organization),
        )
        db.commit()
        db.refresh(organization)
        result = row_to_dict(organization)
    return result


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


@router.post("/outlines/renumber")
def renumber_outlines(payload: dict) -> dict:
    """重新排列章节号。

    按卷的顺序 + 卷内 sort_index 排序，重新分配连续的 chapter_no。
    body: { project_id, volume_id: 可选，只重排某卷；不传则重排所有 }
    """
    project_id = payload.get("project_id")
    volume_id = payload.get("volume_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="缺少 project_id")

    with get_business_db() as db:
        # 先获取所有卷，按 volume_no 排序
        volumes = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "volume"
        ).order_by(Outline.volume_no).all()

        # 如果指定了 volume_id，只排那卷
        if volume_id:
            volumes = [v for v in volumes if v.id == volume_id]
            if not volumes:
                raise HTTPException(status_code=404, detail="卷不存在")

        # 全局章号计数器
        chapter_no = 0

        # 先计算起始章号（如果只重排某卷，需要知道前面有多少章）
        if volume_id:
            # 找到该卷之前的所有章节数
            target_idx = None
            for i, v in enumerate(volumes):
                if v.id == volume_id:
                    target_idx = i
                    break
            # 计算前面所有卷的章节总数
            all_volumes = db.query(Outline).filter(
                Outline.project_id == project_id,
                Outline.node_type == "volume"
            ).order_by(Outline.volume_no).all()
            before_count = 0
            for v in all_volumes:
                if v.id == volume_id:
                    break
                cnt = db.query(Outline).filter(
                    Outline.project_id == project_id,
                    Outline.node_type == "chapter",
                    Outline.volume_id == v.id
                ).count()
                before_count += cnt
            chapter_no = before_count
            # 只处理目标卷
            volumes_to_process = [v for v in all_volumes if v.id == volume_id]
        else:
            volumes_to_process = volumes

        for vol in volumes_to_process:
            chapters = db.query(Outline).filter(
                Outline.project_id == project_id,
                Outline.node_type == "chapter",
                Outline.volume_id == vol.id
            ).order_by(Outline.sort_index, Outline.chapter_no).all()

            for ch in chapters:
                chapter_no += 1
                ch.chapter_no = chapter_no
                ch.sort_index = chapter_no

        db.commit()

    return {"ok": True, "chapter_no": chapter_no}


@router.post("/outlines/reorder-volume")
def reorder_volume(payload: dict) -> dict:
    """调整卷顺序。

    body: { source_id, target_id, position: 'before'|'after' }
    调整后按新顺序更新 volume_no，然后重新生成章节号。
    """
    source_id = payload.get("source_id")
    target_id = payload.get("target_id")
    position = payload.get("position", "after")
    if not source_id or not target_id or source_id == target_id:
        raise HTTPException(status_code=400, detail="参数错误")

    with get_business_db() as db:
        source = db.query(Outline).filter(Outline.id == source_id, Outline.node_type == "volume").first()
        target = db.query(Outline).filter(Outline.id == target_id, Outline.node_type == "volume").first()
        if not source or not target:
            raise HTTPException(status_code=404, detail="卷不存在")
        if source.project_id != target.project_id:
            raise HTTPException(status_code=400, detail="不能跨项目移动")

        project_id = source.project_id

        # 获取所有卷，按当前 volume_no 排序
        volumes = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "volume"
        ).order_by(Outline.volume_no).all()

        # 把 source 从列表中移除
        volume_list = [v for v in volumes if v.id != source_id]

        # 找到 target 的新位置
        target_idx = next(i for i, v in enumerate(volume_list) if v.id == target_id)
        insert_idx = target_idx if position == "before" else target_idx + 1

        # 插入到新位置
        volume_list.insert(insert_idx, source)

        # 重新分配 volume_no
        for i, v in enumerate(volume_list):
            v.volume_no = i + 1

        # 重新排列章节号
        chapter_no = 0
        for vol in volume_list:
            chapters = db.query(Outline).filter(
                Outline.project_id == project_id,
                Outline.node_type == "chapter",
                Outline.volume_id == vol.id
            ).order_by(Outline.sort_index, Outline.chapter_no).all()
            for ch in chapters:
                chapter_no += 1
                ch.chapter_no = chapter_no
                ch.sort_index = chapter_no

        db.commit()

    return {"ok": True}


@router.post("/outlines/reorder-chapter")
def reorder_chapter(payload: dict) -> dict:
    """调整章节顺序（同卷或跨卷）。

    body: { source_id, target_id, position: 'before'|'after' }
    调整后自动重新编号。
    """
    source_id = payload.get("source_id")
    target_id = payload.get("target_id")
    position = payload.get("position", "after")
    if not source_id or not target_id or source_id == target_id:
        raise HTTPException(status_code=400, detail="参数错误")

    with get_business_db() as db:
        source = db.query(Outline).filter(Outline.id == source_id, Outline.node_type == "chapter").first()
        target = db.query(Outline).filter(Outline.id == target_id, Outline.node_type == "chapter").first()
        if not source or not target:
            raise HTTPException(status_code=404, detail="章节不存在")
        if source.project_id != target.project_id:
            raise HTTPException(status_code=400, detail="不能跨项目移动")

        project_id = source.project_id
        target_volume_id = target.volume_id

        # 获取目标卷的所有章节，按 sort_index 排序
        chapters = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "chapter",
            Outline.volume_id == target_volume_id
        ).order_by(Outline.sort_index).all()

        # 如果源章节也在目标卷，先移除；否则后面统一处理
        chapter_list = [c for c in chapters if c.id != source_id]

        # 找到 target 的位置
        target_idx = next(i for i, c in enumerate(chapter_list) if c.id == target_id)
        insert_idx = target_idx if position == "before" else target_idx + 1

        # 如果源章节不在目标卷，先修改它的 volume_id
        if source.volume_id != target_volume_id:
            source.volume_id = target_volume_id

        # 插入到新位置
        chapter_list.insert(insert_idx, source)

        # 先给目标卷内章节重新排 sort_index
        for i, ch in enumerate(chapter_list):
            ch.sort_index = i + 1

        db.commit()

        # 全局重新编号
        _renumber_all_chapters(db, project_id)
        db.commit()

    return {"ok": True}


@router.post("/outlines/move-chapter")
def move_chapter(payload: dict) -> dict:
    """移动章节到指定卷末尾。

    body: { chapter_id, volume_id }
    移动后自动重新编号。
    """
    chapter_id = payload.get("chapter_id")
    volume_id = payload.get("volume_id")
    if not chapter_id or not volume_id:
        raise HTTPException(status_code=400, detail="参数错误")

    with get_business_db() as db:
        chapter = db.query(Outline).filter(Outline.id == chapter_id, Outline.node_type == "chapter").first()
        volume = db.query(Outline).filter(Outline.id == volume_id, Outline.node_type == "volume").first()
        if not chapter or not volume:
            raise HTTPException(status_code=404, detail="章节或卷不存在")
        if chapter.project_id != volume.project_id:
            raise HTTPException(status_code=400, detail="不能跨项目移动")

        project_id = chapter.project_id

        # 修改所属卷
        chapter.volume_id = volume_id

        # 获取目标卷最大 sort_index
        max_sort = db.query(func.max(Outline.sort_index)).filter(
            Outline.project_id == project_id,
            Outline.node_type == "chapter",
            Outline.volume_id == volume_id
        ).scalar() or 0
        chapter.sort_index = max_sort + 1

        db.commit()

        # 全局重新编号
        _renumber_all_chapters(db, project_id)
        db.commit()

    return {"ok": True}


def _renumber_all_volumes(db: Session, project_id: int) -> int:
    """内部工具：全局重新排列卷号。"""
    volumes = db.query(Outline).filter(
        Outline.project_id == project_id,
        Outline.node_type == "volume"
    ).order_by(Outline.volume_no, Outline.id).all()

    for i, vol in enumerate(volumes):
        vol.volume_no = i + 1

    return len(volumes)


def _renumber_all_chapters(db: Session, project_id: int) -> int:
    """内部工具：全局重新排列章节号。"""
    volumes = db.query(Outline).filter(
        Outline.project_id == project_id,
        Outline.node_type == "volume"
    ).order_by(Outline.volume_no).all()

    chapter_no = 0
    for vol in volumes:
        chapters = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "chapter",
            Outline.volume_id == vol.id
        ).order_by(Outline.sort_index).all()
        for ch in chapters:
            chapter_no += 1
            ch.chapter_no = chapter_no
            ch.sort_index = chapter_no

    return chapter_no


@router.post("/foreshadowings")
def save_foreshadowing(payload: ForeshadowingSave) -> dict:
    """新增伏笔记录并校验替代线索的项目归属。"""
    # 步骤 1：检查替代线索确实属于当前项目；步骤 2：校验通过后写入完整数据。
    with get_business_db() as db:
        _validate_foreshadowing_replacement(db, payload.project_id, payload.replaced_by_id)
    return insert_row("foreshadowings", payload.model_dump())


@router.put("/{resource}/{item_id}")
def update_resource(resource: str, item_id: int, payload: dict) -> dict:
    """更新某一条创作资料。

    resource 先经过白名单映射，payload 只包含前端提交的业务字段。
    """
    table = _resource_table(resource)
    if table == "organizations":
        # 组织卡片更新和历史快照共用一个事务，防止只保存一半。
        return _update_organization_with_history(item_id, payload)
    if table == "foreshadowings":
        return _update_foreshadowing_with_validation(item_id, payload)
    updated = update_row(table, item_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="资源不存在")
    return updated


def _validate_foreshadowing_replacement(db: Session, project_id: int, replaced_by_id: int | None, item_id: int | None = None) -> None:
    """确保替代链只指向同项目中的另一条伏笔。"""
    if replaced_by_id is None:
        return
    # 步骤 1：拒绝自我替代；步骤 2：确认目标存在且项目归属一致。
    if item_id is not None and replaced_by_id == item_id:
        raise HTTPException(status_code=422, detail="伏笔不能替代自身")
    target = db.query(Foreshadowing.id).filter(
        Foreshadowing.id == replaced_by_id,
        Foreshadowing.project_id == project_id,
    ).first()
    if not target:
        raise HTTPException(status_code=422, detail="被替代线索必须属于当前项目")


def _update_foreshadowing_with_validation(item_id: int, payload: dict) -> dict:
    """合并现有伏笔后校验字段与章节顺序，再保存允许更新的字段。"""
    with get_business_db() as db:
        item = db.query(Foreshadowing).filter(Foreshadowing.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="资源不存在")

        # 步骤 1：从模型字段构造完整候选，局部更新也按完整生命周期规则校验。
        editable_fields = set(ForeshadowingSave.model_fields) - {"project_id"}
        candidate = {
            field_name: getattr(item, field_name)
            for field_name in ForeshadowingSave.model_fields
            if hasattr(item, field_name)
        }
        candidate.update({key: value for key, value in payload.items() if key in editable_fields})
        candidate["project_id"] = item.project_id
        try:
            validated = ForeshadowingSave.model_validate(candidate)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        # 步骤 2：限制为显式业务字段，阻止跨项目迁移和任意属性写入。
        _validate_foreshadowing_replacement(
            db,
            item.project_id,
            validated.replaced_by_id,
            item_id=item.id,
        )
        for field_name in editable_fields.intersection(payload):
            setattr(item, field_name, getattr(validated, field_name))

        # 步骤 3：提交并返回数据库刷新后的记录。
        db.commit()
        db.refresh(item)
        return row_to_dict(item)


def _update_organization_with_history(item_id: int, payload: dict) -> dict:
    """保存组织字段，并在同一个数据库事务中记录变化前后快照。"""
    with get_business_db() as db:
        organization = db.query(Organization).filter(Organization.id == item_id).first()
        if not organization:
            raise HTTPException(status_code=404, detail="资源不存在")

        # 步骤 1：只接纳 ORM 实际映射的业务字段，忽略主键和时间戳。
        before_snapshot = capture_organization_snapshot(organization)
        allowed_fields = {column.key for column in Organization.__mapper__.column_attrs}
        protected_fields = {"id", "project_id", "created_at", "updated_at"}
        for field_name, value in payload.items():
            if field_name in allowed_fields and field_name not in protected_fields:
                setattr(organization, field_name, value)

        # 步骤 2：字段有实际变化时写入历史；步骤 3：与资料修改一起提交。
        after_snapshot = capture_organization_snapshot(organization)
        record_organization_history(
            db=db,
            organization=organization,
            source_type="manual",
            operation="update",
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
        db.commit()
        db.refresh(organization)
        return row_to_dict(organization)


@router.delete("/{resource}/{item_id}")
def delete_resource(resource: str, item_id: int) -> dict:
    """删除资源。

    resource 只允许映射表中的业务资源名，避免前端把任意表名传进来。
    删除章节或卷后自动重新编号。
    """
    table = _resource_table(resource)

    # 如果删除的是章节或卷，先获取 project_id 和 node_type 用于后续重编号
    project_id = None
    node_type = None
    if table == "outlines":
        with get_business_db() as db:
            item = db.query(Outline).filter(Outline.id == item_id).first()
            if item:
                project_id = item.project_id
                node_type = item.node_type

    delete_row(table, item_id)

    # 删除章节或卷后自动重新编号
    if project_id and node_type in ("chapter", "volume"):
        with get_business_db() as db:
            if node_type == "volume":
                # 删除卷：先重排卷号，再重排章节号
                _renumber_all_volumes(db, project_id)
            _renumber_all_chapters(db, project_id)
            db.commit()

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
        "character-groups": "character_groups",
    }
    if resource not in mapping:
        raise HTTPException(status_code=404, detail="未知资源")
    return mapping[resource]
