"""创作资料的通用查询、新增、更新和删除路由。"""

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.repository import delete_row, fetch_all, insert_row, row_to_dict, update_row
from app.db.session import get_business_db
from app.models.business import Foreshadowing, Organization, Outline
from app.schemas.models import (
    CharacterSave, ChapterSave, ForeshadowingSave, OrganizationSave, OutlineSave, WorldSettingSave,
)
from app.services.foreshadowing_history import (
    capture_foreshadowing_snapshot,
    record_foreshadowing_history,
)
from app.services.organization_history import capture_organization_snapshot, record_organization_history
from .common import _renumber_all_chapters, _renumber_all_volumes, _resource_table

router = APIRouter()

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


@router.post("/foreshadowings")
def save_foreshadowing(payload: ForeshadowingSave) -> dict:
    """新增伏笔并将首条档案快照写入历史。"""
    with get_business_db() as db:
        # 步骤 1：检查替代线索确实属于当前项目。
        _validate_foreshadowing_replacement(db, payload.project_id, payload.replaced_by_id)
        # 步骤 2：创建档案并取得 ID，再将首条快照加入同一事务。
        item = Foreshadowing(**payload.model_dump())
        db.add(item)
        db.flush()
        record_foreshadowing_history(
            db=db,
            item=item,
            source_type="manual",
            operation="create",
            before_snapshot={},
            after_snapshot=capture_foreshadowing_snapshot(item),
        )
        db.commit()
        db.refresh(item)
        return row_to_dict(item)


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

        # 步骤 1：保留修改前快照，并按完整字段校验局部更新。
        before_snapshot = capture_foreshadowing_snapshot(item)
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

        # 步骤 3：只记录实际变化，并把状态变更标成状态迁移。
        after_snapshot = capture_foreshadowing_snapshot(item)
        operation = "status_transition" if before_snapshot.get("status") != after_snapshot.get("status") else "update"
        record_foreshadowing_history(
            db=db,
            item=item,
            source_type="manual",
            operation=operation,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )

        # 步骤 4：档案和历史一起提交，返回刷新后的记录。
        db.commit()
        db.refresh(item)
        return row_to_dict(item)


def _delete_foreshadowing_with_history(item_id: int) -> dict:
    """先记下删除前快照，再删除伏笔卡片并保留历史记录。"""
    with get_business_db() as db:
        item = db.query(Foreshadowing).filter(Foreshadowing.id == item_id).first()
        if not item:
            return {"ok": True, "id": item_id}

        # 步骤 1：历史表不依赖伏笔外键，因此删除后仍可追溯该档案。
        record_foreshadowing_history(
            db=db,
            item=item,
            source_type="manual",
            operation="delete",
            before_snapshot=capture_foreshadowing_snapshot(item),
            after_snapshot={},
        )
        # 步骤 2：与历史记录在同一个事务内提交。
        db.delete(item)
        db.commit()
    return {"ok": True, "id": item_id}


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
    if table == "foreshadowings":
        return _delete_foreshadowing_with_history(item_id)

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
