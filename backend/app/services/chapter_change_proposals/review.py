"""审核提案并在同一事务中更新正式资料和历史快照。"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.business import ChapterChangeProposal, OrganizationRelation
from app.services.organization_history import (
    capture_organization_relation_snapshot,
    capture_organization_snapshot,
    record_organization_history,
)
from app.services.foreshadowing_history import (
    capture_foreshadowing_snapshot,
    record_foreshadowing_history,
)
from .common import _current_field, _get_entity, _json_dump, _json_load, _serialize_proposal
from .constants import ENTITY_MODELS, JSON_FIELDS
from .validation import (
    _find_organization_relation_conflict,
    _validate_foreshadowing_chapter_order,
    _validate_value,
)

def _encode_entity_field(entity_type: str, field_name: str, value: Any) -> Any:
    """将原生对象编码为模型中兼容现有页面的 JSON 文本字段。"""
    if field_name in JSON_FIELDS.get(entity_type, set()):
        return _json_dump(value)
    return value

def _create_entity(
    db: Session,
    project_id: int,
    chapter_id: int,
    proposal: ChapterChangeProposal,
    values: dict[str, Any],
) -> Any:
    """根据已审核提案创建实体，并由服务补齐项目和来源字段。

    步骤 1：处理需要补充来源信息的长期记忆。
    步骤 2：把 JSON 字段编码后构造实体。
    步骤 3：新增并 flush，确保调用方可以记录实体 ID。
    """
    if proposal.entity_type == "organization_relation":
        # 关系端点由项目内 ID 解析，数据库始终按升序保存以避免方向重复。
        source_id = values["source_org_id"]
        target_id = values["target_org_id"]
        first_id, second_id = sorted((source_id, target_id))
        entity = OrganizationRelation(
            project_id=project_id,
            organization_a_id=first_id,
            organization_b_id=second_id,
            relation_type=values["relation_type"],
            description=values.get("description", ""),
            effective_from_chapter=values.get("effective_from_chapter"),
            expires_at_chapter=values.get("expires_at_chapter"),
        )
        db.add(entity)
        db.flush()
        return entity

    if proposal.entity_type == "memory":
        values = {**values, "metadata_json": values.get("metadata_json", {})}
        values["source_type"] = "chapter_analysis"
        values["source_ref"] = f"chapter:{chapter_id}:proposal:{proposal.proposal_id}"
        values["memory_id"] = str(uuid.uuid4())
    model = ENTITY_MODELS[proposal.entity_type]
    encoded = {
        key: _encode_entity_field(proposal.entity_type, key, value)
        for key, value in values.items()
    }
    entity = model(project_id=project_id, **encoded)
    db.add(entity)
    db.flush()
    return entity

def review_proposal(
    db: Session,
    project_id: int,
    chapter_id: int,
    proposal_id: str,
    decision: str,
    proposed_value: dict[str, Any] | None = None,
    review_note: str = "",
) -> dict[str, Any]:
    """审核并可选应用单条提案。

    步骤 1：按项目、章节和提案 ID 定位待审核记录。
    步骤 2：拒绝时只记录决定；确认时重新校验字段和目标归属。
    步骤 3：比对生成提案时的前值，检测并发编辑造成的冲突。
    步骤 4：无冲突时在同一数据库事务中写回设定并标记已应用。
    步骤 5：返回审核结果；由 API 层统一提交事务。
    """
    proposal = db.query(ChapterChangeProposal).filter(
        ChapterChangeProposal.proposal_id == proposal_id,
        ChapterChangeProposal.project_id == project_id,
        ChapterChangeProposal.chapter_id == chapter_id,
    ).first()
    if not proposal:
        raise LookupError("变化提案不存在")
    if proposal.status == "applied" and decision == "approve":
        return {"proposal": _serialize_proposal(proposal), "idempotent": True, "conflict": False}
    if proposal.status != "pending":
        raise ValueError(f"提案当前状态为 {proposal.status}，不能重复审核")

    organization_before_snapshot: dict[str, Any] | None = None
    foreshadowing_before_snapshot: dict[str, Any] = {}
    organization_relation_before_snapshots: dict[int, dict[str, Any]] = {}
    organization_relation_owner_ids: set[int] = set()

    proposal.reviewed_at = datetime.utcnow()
    proposal.review_note = review_note
    if decision == "reject":
        proposal.status = "rejected"
        return {"proposal": _serialize_proposal(proposal), "idempotent": False, "conflict": False}
    if decision != "approve":
        raise ValueError("审核决定仅支持 approve 或 reject")

    values = proposed_value if proposed_value is not None else _json_load(proposal.proposed_value, {})
    _validate_value(proposal.entity_type, proposal.operation, proposal.target_id, values)
    if proposal.entity_type == "relationship":
        # 步骤 2b：审核时允许调整关系描述，不允许把提案悄悄改成另一对人物。
        original_value = _json_load(proposal.proposed_value, {})
        if values.get("target_id") != original_value.get("target_id"):
            raise ValueError("审核修改不能更换关系另一端人物；请重新分析后生成关系提案")
    if proposal.operation == "update" and proposal.entity_type != "relationship":
        # 步骤 2a：人工修改可以改值，但不能偷偷扩大或缩小原提案涉及的字段集合。
        before_value = _json_load(proposal.before_value, {})
        if set(values) != set(before_value):
            raise ValueError("审核修改不能增删提案字段；请退回并重新生成提案")

    if proposal.operation == "create" and proposal.entity_type == "organization_relation":
        # 步骤 3b：审核新增关系时再次验证组织归属和时间区间，挡住待审核期间的冲突。
        source = _get_entity(db, "organization", project_id, values["source_org_id"])
        target = _get_entity(db, "organization", project_id, values["target_org_id"])
        if not source or not target or source.id == target.id:
            proposal.status = "conflict"
            proposal.review_note = review_note or "关系端点组织已删除或无效，请重新分析后确认。"
            return {"proposal": _serialize_proposal(proposal), "idempotent": False, "conflict": True}
        conflict = _find_organization_relation_conflict(
            db,
            project_id,
            source.id,
            target.id,
            values.get("effective_from_chapter"),
            values.get("expires_at_chapter"),
        )
        if conflict:
            proposal.status = "conflict"
            proposal.review_note = review_note or "审核期间这两个组织已建立重叠区间关系，请刷新后重新分析。"
            return {"proposal": _serialize_proposal(proposal), "idempotent": False, "conflict": True}
        organization_relation_owner_ids = {source.id, target.id}
        entity = _create_entity(db, project_id, chapter_id, proposal, values)
    elif proposal.operation == "create" and proposal.entity_type != "relationship":
        # 步骤 3a：提案待审核期间若已有同名正式资料，标记冲突而不是创建重复卡片。
        unique_fields = {
            "character": "name",
            "organization": "name",
            "foreshadowing": "keyword",
            "world_setting": "title",
        }
        unique_field = unique_fields.get(proposal.entity_type)
        unique_value = values.get(unique_field) if unique_field else None
        model = ENTITY_MODELS[proposal.entity_type]
        if unique_value:
            duplicate = next(
                (
                    item
                    for item in db.query(model).filter(model.project_id == project_id).all()
                    if str(getattr(item, unique_field) or "").strip().casefold()
                    == str(unique_value).strip().casefold()
                ),
                None,
            )
            if duplicate:
                proposal.status = "conflict"
                proposal.review_note = review_note or f"审核期间已存在同名资料「{unique_value}」，请检查后重新分析。"
                return {"proposal": _serialize_proposal(proposal), "idempotent": False, "conflict": True}
        if proposal.entity_type == "organization" and values.get("parent_id"):
            parent = _get_entity(db, "organization", project_id, values["parent_id"])
            if not parent:
                proposal.status = "conflict"
                proposal.review_note = review_note or "父组织已删除或不属于当前项目，请重新分析后确认。"
                return {"proposal": _serialize_proposal(proposal), "idempotent": False, "conflict": True}
        entity = _create_entity(db, project_id, chapter_id, proposal, values)
    else:
        entity = _get_entity(db, proposal.entity_type, project_id, proposal.target_id)
        if not entity:
            proposal.status = "conflict"
            proposal.review_note = review_note or "提案目标已删除或不属于当前项目，需重新确认。"
            return {"proposal": _serialize_proposal(proposal), "idempotent": False, "conflict": True}

        if proposal.entity_type == "organization":
            # 在应用审核值之前保留完整档案快照，供历史页还原本次变化。
            organization_before_snapshot = capture_organization_snapshot(entity)
        elif proposal.entity_type == "foreshadowing":
            # 章节分析更新伏笔时，保存审核前快照供来源追踪。
            foreshadowing_before_snapshot = capture_foreshadowing_snapshot(entity)
        elif proposal.entity_type == "organization_relation":
            # 把关系两端的旧视角都保存下来，方便从任一组织档案追溯变化。
            organization_relation_owner_ids = {entity.organization_a_id, entity.organization_b_id}
            organization_relation_before_snapshots = {
                owner_id: capture_organization_relation_snapshot(db, entity, owner_id)
                for owner_id in organization_relation_owner_ids
            }

        before_value = _json_load(proposal.before_value, {})
        if proposal.entity_type == "relationship":
            current_relations = _current_field("relationship", entity, "character_relations") or []
            if current_relations != before_value.get("relationships", []):
                proposal.status = "conflict"
                proposal.review_note = review_note or "人物关系在提案生成后发生变化，请重新确认。"
                return {"proposal": _serialize_proposal(proposal), "idempotent": False, "conflict": True}
            relation_target = _get_entity(db, "character", project_id, values["target_id"])
            if not relation_target or relation_target.id == entity.id:
                proposal.status = "conflict"
                proposal.review_note = review_note or "关系目标已删除或无效，请重新分析后确认。"
                return {"proposal": _serialize_proposal(proposal), "idempotent": False, "conflict": True}
            matching_indexes = [
                index
                for index, relation in enumerate(current_relations)
                if isinstance(relation, dict) and relation.get("target_id") == values.get("target_id")
            ]
            if proposal.operation == "update":
                if len(matching_indexes) != 1:
                    proposal.status = "conflict"
                    proposal.review_note = review_note or "待更新的人物关系不存在或不唯一，请重新分析后确认。"
                    return {"proposal": _serialize_proposal(proposal), "idempotent": False, "conflict": True}
                relation_index = matching_indexes[0]
                current_relations[relation_index] = {**current_relations[relation_index], **values}
            elif not matching_indexes:
                current_relations.append(values)
            entity.character_relations = _json_dump(current_relations)
        else:
            current_values = {
                key: _current_field(proposal.entity_type, entity, key)
                for key in values
            }
            if current_values != before_value:
                proposal.status = "conflict"
                proposal.review_note = review_note or "目标资料在提案生成后发生变化，请重新确认。"
                return {"proposal": _serialize_proposal(proposal), "idempotent": False, "conflict": True}
            if proposal.entity_type == "foreshadowing":
                # 步骤 4a：将局部改动与当前档案合并后校验，防止章节分析制造矛盾范围。
                merged_window = {
                    field_name: getattr(entity, field_name)
                    for field_name in ("planted_chapter", "payoff_chapter", "resolved_chapter", "effective_from", "expires_at")
                }
                merged_window.update(values)
                _validate_foreshadowing_chapter_order(merged_window)
            if proposal.entity_type == "organization_relation":
                # 更新章节范围前排除自身并检查同一组织对的重叠关系。
                new_start = values.get("effective_from_chapter", entity.effective_from_chapter)
                new_end = values.get("expires_at_chapter", entity.expires_at_chapter)
                conflict = _find_organization_relation_conflict(
                    db,
                    project_id,
                    entity.organization_a_id,
                    entity.organization_b_id,
                    new_start,
                    new_end,
                    exclude_id=entity.id,
                )
                if conflict:
                    proposal.status = "conflict"
                    proposal.review_note = review_note or "关系章节范围与另一条关系重叠，请刷新后重新分析。"
                    return {"proposal": _serialize_proposal(proposal), "idempotent": False, "conflict": True}
            if proposal.entity_type == "organization" and values.get("parent_id"):
                parent = _get_entity(db, "organization", project_id, values["parent_id"])
                if not parent or parent.id == entity.id:
                    raise ValueError("父组织不存在或不属于当前项目")
            for field_name, value in values.items():
                setattr(entity, field_name, _encode_entity_field(proposal.entity_type, field_name, value))

    if proposal.entity_type == "foreshadowing":
        # 章节提案审核通过后，将档案变更和审核决定留在同一事务。
        after_snapshot = capture_foreshadowing_snapshot(entity)
        operation = proposal.operation
        if proposal.operation == "update" and foreshadowing_before_snapshot.get("status") != after_snapshot.get("status"):
            operation = "status_transition"
        record_foreshadowing_history(
            db=db,
            item=entity,
            source_type="chapter_analysis",
            operation=operation,
            before_snapshot=foreshadowing_before_snapshot,
            after_snapshot=after_snapshot,
            chapter_id=chapter_id,
            proposal_id=proposal.proposal_id,
            rationale=proposal.rationale or "",
            evidence=proposal.evidence or "",
        )
    elif proposal.entity_type == "organization":
        # 步骤 5：审核通过的组织变化与提案状态在同一事务中写入历史。
        after_snapshot = capture_organization_snapshot(entity)
        record_organization_history(
            db=db,
            organization=entity,
            source_type="chapter_analysis",
            operation=proposal.operation,
            before_snapshot=organization_before_snapshot or {},
            after_snapshot=after_snapshot,
            chapter_id=chapter_id,
            proposal_id=proposal.proposal_id,
            rationale=proposal.rationale or "",
            evidence=proposal.evidence or "",
        )
    elif proposal.entity_type == "organization_relation":
        # 步骤 6：两端组织都保留关系变化，章节审核与关系写入同事务提交。
        if proposal.operation == "create":
            organization_relation_owner_ids = {
                entity.organization_a_id,
                entity.organization_b_id,
            }
        for owner_id in organization_relation_owner_ids:
            owner = _get_entity(db, "organization", project_id, owner_id)
            if not owner:
                continue
            record_organization_history(
                db=db,
                organization=owner,
                source_type="chapter_analysis",
                operation=proposal.operation,
                before_snapshot=organization_relation_before_snapshots.get(owner_id, {}),
                after_snapshot=capture_organization_relation_snapshot(db, entity, owner_id),
                chapter_id=chapter_id,
                proposal_id=proposal.proposal_id,
                rationale=proposal.rationale or "",
                evidence=proposal.evidence or "",
                changed_fields_override=["organization_relation"],
            )

    proposal.status = "applied"
    proposal.applied_at = datetime.utcnow()
    proposal.applied_entity_id = entity.id
    proposal.proposed_value = _json_dump(values)
    return {"proposal": _serialize_proposal(proposal), "idempotent": False, "conflict": False}
