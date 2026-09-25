"""章节变化提案的校验、审核、写回与来源追踪。"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Session

from app.models.business import (
    Chapter,
    ChapterChangeProposal,
    Character,
    Foreshadowing,
    GenerationVersion,
    MemoryItem,
    Organization,
    OrganizationRelation,
    WorldSetting,
    WorkflowRun,
)
from app.models.business.foreshadowing import FORESHADOWING_STATUSES
from app.services.organization_history import (
    capture_organization_relation_snapshot,
    capture_organization_snapshot,
    record_organization_history,
)


# 模型输出只能修改显式列出的业务字段，身份、归属和时间戳由服务管理。
EDITABLE_FIELDS: dict[str, set[str]] = {
    "character": {
        "name", "role_type", "mbti", "mbti_primary", "mbti_secondary", "appearance",
        "personality", "background", "motivation", "arc", "identity", "faction",
        "weakness", "secret", "dialogue_style", "ai_notes", "status",
    },
    "organization": {
        "parent_id", "name", "org_type", "location", "slogan", "description", "level",
        "power_level", "member_count", "status", "hierarchy", "resources", "goal",
        "core_members", "impact", "risk_notes", "hidden_secrets",
        "active_from_chapter", "disbanded_chapter", "hierarchy_system", "hierarchy_levels",
    },
    "organization_relation": {
        "source_org_id", "target_org_id", "relation_type", "description",
        "effective_from_chapter", "expires_at_chapter",
    },
    "foreshadowing": {
        "keyword", "description", "status", "importance", "planted_chapter", "payoff_chapter",
        "effective_from", "expires_at", "notes", "related_character_ids",
        "related_organization_ids", "related_outline_ids", "replaced_by_id",
    },
    "world_setting": {
        "era", "geography", "atmosphere", "rules", "extra", "title", "category", "tags",
        "importance", "related_chapters", "related_characters", "related_organizations",
        "related_foreshadowings", "conflict_notes",
    },
    "memory": {"memory_type", "title", "content", "content_summary", "importance", "metadata_json"},
}

ENTITY_MODELS = {
    "character": Character,
    "organization": Organization,
    "organization_relation": OrganizationRelation,
    "foreshadowing": Foreshadowing,
    "world_setting": WorldSetting,
    "memory": MemoryItem,
}

JSON_FIELDS: dict[str, set[str]] = {
    "character": {"custom_attributes", "org_relations", "character_relations"},
    "relationship": {"character_relations"},
    "organization": {"hierarchy_levels"},
    "memory": {"metadata_json"},
}

RELATION_FIELDS = {"target_id", "relation_type", "depth", "effective_from", "expires_at"}

# 世界观分类与前端分类字典一致，同时保留历史分析结果使用过的值。
WORLD_SETTING_CATEGORIES = {
    "geography", "era", "power_system", "rules", "items", "weapons",
    "medicine", "creatures", "organizations", "other",
    "location", "power", "rule", "taboo", "term",
}


def _json_dump(value: Any) -> str:
    """统一 JSON 序列化，确保中文可读且键顺序稳定。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_load(value: str | None, fallback: Any = None) -> Any:
    """尽量解析数据库中的 JSON 文本，兼容旧数据和空值。"""
    if value in (None, ""):
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def _json_array(value: str | None) -> list[Any]:
    """安全读取列表型 JSON 字段；旧记录损坏时按空列表展示和处理。"""
    parsed = _json_load(value, [])
    return parsed if isinstance(parsed, list) else []


def _current_field(entity_type: str, entity: Any, field_name: str) -> Any:
    """读取当前字段；JSON 文本字段以原生列表/对象参与冲突比较。"""
    raw = getattr(entity, field_name)
    if field_name in JSON_FIELDS.get(entity_type, set()):
        fallback = {} if field_name == "metadata_json" else []
        value = _json_load(raw, fallback)
        return value if isinstance(value, (list, dict)) else fallback
    return raw


def _serialize_proposal(row: ChapterChangeProposal) -> dict[str, Any]:
    """将 ORM 提案转换为前端可直接使用的 JSON 对象。"""
    return {
        "id": row.id,
        "proposal_id": row.proposal_id,
        "project_id": row.project_id,
        "chapter_id": row.chapter_id,
        "run_id": row.run_id,
        "version_id": row.version_id,
        "entity_type": row.entity_type,
        "operation": row.operation,
        "target_id": row.target_id,
        "target_label": row.target_label or "",
        "before_value": _json_load(row.before_value, {}),
        "proposed_value": _json_load(row.proposed_value, {}),
        "rationale": row.rationale or "",
        "evidence": row.evidence or "",
        "status": row.status,
        "review_note": row.review_note or "",
        "applied_entity_id": row.applied_entity_id,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "applied_at": row.applied_at.isoformat() if row.applied_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _proposal_key(
    project_id: int,
    chapter_id: int,
    run_id: str | None,
    version_id: str | None,
    draft: dict[str, Any],
    before_value: dict[str, Any],
) -> str:
    """生成稳定幂等键，工作流重试时避免重复插入相同候选。"""
    identity = {
        "project_id": project_id,
        "chapter_id": chapter_id,
        "run_id": run_id,
        "version_id": version_id,
        "entity_type": draft["entity_type"],
        "operation": draft["operation"],
        "target_id": draft.get("target_id"),
        "target_label": draft.get("target_label", ""),
        "before_value": before_value,
        "proposed_value": draft["proposed_value"],
    }
    return hashlib.sha256(_json_dump(identity).encode("utf-8")).hexdigest()


def _get_entity(db: Session, entity_type: str, project_id: int, entity_id: int) -> Any | None:
    """按项目边界读取目标资料，防止跨项目引用或改写。"""
    if entity_type == "relationship":
        return db.query(Character).filter(
            Character.id == entity_id,
            Character.project_id == project_id,
        ).first()
    model = ENTITY_MODELS.get(entity_type)
    if model is None:
        return None
    return db.query(model).filter(
        model.id == entity_id,
        model.project_id == project_id,
    ).first()


def load_entity_catalog(db: Session, project_id: int) -> dict[str, list[dict[str, Any]]]:
    """读取分析用实体索引。

    步骤 1：按项目读取人物、组织、伏笔和设定名称。
    步骤 2：附带人物及组织的结构化关系，用于精确定位关系变化。
    步骤 3：只返回匹配和冲突校验所需字段，控制工作流上下文体积。
    """
    characters = db.query(Character.id, Character.name, Character.character_relations).filter(
        Character.project_id == project_id,
    ).all()
    organizations = db.query(Organization.id, Organization.name).filter(
        Organization.project_id == project_id,
    ).all()
    organization_relations = db.query(OrganizationRelation).filter(
        OrganizationRelation.project_id == project_id,
    ).all()
    foreshadowings = db.query(Foreshadowing.id, Foreshadowing.keyword).filter(
        Foreshadowing.project_id == project_id,
    ).all()
    world_settings = db.query(WorldSetting.id, WorldSetting.title).filter(
        WorldSetting.project_id == project_id,
    ).all()
    return {
        "characters": [
            {
                "id": row.id,
                "name": row.name,
                "character_relations": _json_array(row.character_relations),
            }
            for row in characters
        ],
        "organizations": [{"id": row.id, "name": row.name} for row in organizations],
        "organization_relations": [
            {
                "id": row.id,
                "organization_a_id": row.organization_a_id,
                "organization_b_id": row.organization_b_id,
                "relation_type": row.relation_type,
                "description": row.description or "",
                "effective_from_chapter": row.effective_from_chapter,
                "expires_at_chapter": row.expires_at_chapter,
            }
            for row in organization_relations
        ],
        "foreshadowings": [{"id": row.id, "keyword": row.keyword} for row in foreshadowings],
        "world_settings": [{"id": row.id, "title": row.title} for row in world_settings],
    }


def _validate_value(entity_type: str, operation: str, target_id: int | None, value: dict[str, Any]) -> None:
    """校验提案实体、操作方式和字段内容。

    步骤 1：拒绝不支持的操作。
    步骤 2：先校验人物关系和组织关系等专用数据结构。
    步骤 3：对普通实体应用字段白名单和数据库列类型检查。
    """
    if operation not in {"create", "update"}:
        raise ValueError("提案操作仅支持 create 或 update")
    if entity_type == "organization_relation":
        # 步骤 1：新增关系必须给出两个组织 ID；更新只能改关系属性，不能换关系端点。
        if not isinstance(value, dict) or not value:
            raise ValueError("组织关系提案内容不能为空")
        allowed_fields = (
            EDITABLE_FIELDS[entity_type]
            if operation == "create"
            else {"relation_type", "description", "effective_from_chapter", "expires_at_chapter"}
        )
        if set(value) - allowed_fields:
            raise ValueError("组织关系提案包含不允许修改的字段")
        if operation == "create":
            if target_id is not None:
                raise ValueError("新增组织关系不能指定已有关系 ID")
            for field_name in ("source_org_id", "target_org_id"):
                field_value = value.get(field_name)
                if not isinstance(field_value, int) or isinstance(field_value, bool) or field_value <= 0:
                    raise ValueError(f"组织关系字段 {field_name} 必须是有效组织 ID")
        elif not isinstance(target_id, int) or isinstance(target_id, bool) or target_id <= 0:
            raise ValueError("更新组织关系必须指定有效关系 ID")

        relation_type = value.get("relation_type")
        if "relation_type" in value and relation_type not in {"alliance", "hostility"}:
            raise ValueError("组织关系类型仅支持 alliance 或 hostility")
        if operation == "create" and relation_type is None:
            raise ValueError("新增组织关系必须指定关系类型")
        if "description" in value and not isinstance(value["description"], str):
            raise ValueError("组织关系说明必须是文本")
        for field_name in ("effective_from_chapter", "expires_at_chapter"):
            field_value = value.get(field_name)
            if field_value is not None and (
                not isinstance(field_value, int) or isinstance(field_value, bool) or field_value < 1
            ):
                raise ValueError(f"组织关系字段 {field_name} 必须是正整数或空值")
        start = value.get("effective_from_chapter")
        end = value.get("expires_at_chapter")
        if start is not None and end is not None and end < start:
            raise ValueError("关系失效章节不能早于生效章节")
        return

    if entity_type == "relationship":
        if not isinstance(target_id, int) or isinstance(target_id, bool):
            raise ValueError("人物关系提案必须指定源人物")
        if not value or set(value) - RELATION_FIELDS:
            raise ValueError("人物关系字段不符合允许范围")
        if (
            not isinstance(value.get("target_id"), int)
            or isinstance(value.get("target_id"), bool)
            or not value.get("relation_type")
        ):
            raise ValueError("人物关系必须包含有效的 target_id 和 relation_type")
        if not isinstance(value.get("relation_type"), str):
            raise ValueError("人物关系类型必须是文本")
        for field_name in ("depth", "effective_from", "expires_at"):
            field_value = value.get(field_name)
            if field_value is not None and (not isinstance(field_value, int) or isinstance(field_value, bool)):
                raise ValueError(f"人物关系字段 {field_name} 必须是整数或空值")
        return

    if entity_type not in EDITABLE_FIELDS:
        raise ValueError("不支持的提案实体类型")
    if not isinstance(value, dict) or not value:
        raise ValueError("提案内容不能为空")
    if set(value) - EDITABLE_FIELDS[entity_type]:
        unknown = ", ".join(sorted(set(value) - EDITABLE_FIELDS[entity_type]))
        raise ValueError(f"提案包含不允许写入的字段：{unknown}")
    # 步骤 1：根据 ORM 列类型检查值，阻止对象误写入文本列或字符串误写数字列。
    model = ENTITY_MODELS[entity_type]
    for field_name, field_value in value.items():
        if field_name in JSON_FIELDS.get(entity_type, set()):
            if not isinstance(field_value, (list, dict)):
                raise ValueError(f"字段 {field_name} 必须是 JSON 列表或对象")
            continue
        column_type = model.__table__.columns[field_name].type
        if field_value is None:
            continue
        if isinstance(column_type, (String, Text)) and not isinstance(field_value, str):
            raise ValueError(f"字段 {field_name} 必须是文本")
        if isinstance(column_type, Boolean) and not isinstance(field_value, bool):
            raise ValueError(f"字段 {field_name} 必须是布尔值")
        if isinstance(column_type, Integer) and (
            not isinstance(field_value, int) or isinstance(field_value, bool)
        ):
            raise ValueError(f"字段 {field_name} 必须是整数")
        if isinstance(column_type, Float) and not isinstance(field_value, (int, float)):
            raise ValueError(f"字段 {field_name} 必须是数字")
    if operation == "update" and target_id is None:
        raise ValueError("更新提案必须指定目标资料")
    if operation == "create" and target_id is not None:
        raise ValueError("新增提案不能指定已有目标 ID")
    if entity_type == "character" and operation == "create" and not value.get("name"):
        raise ValueError("新增人物必须提供姓名")
    if entity_type == "character" and "name" in value and not value.get("name"):
        raise ValueError("人物姓名不能为空")
    if entity_type == "organization" and operation == "create" and not value.get("name"):
        raise ValueError("新增组织必须提供名称")
    if entity_type == "organization" and "name" in value and not value.get("name"):
        raise ValueError("组织名称不能为空")
    if entity_type == "foreshadowing" and operation == "create":
        if not value.get("keyword") or not value.get("description"):
            raise ValueError("新增伏笔必须提供关键词和描述")
    if entity_type == "foreshadowing" and "keyword" in value and not value.get("keyword"):
        raise ValueError("伏笔关键词不能为空")
    if (
        entity_type == "foreshadowing"
        and value.get("status") is not None
        and value.get("status") not in FORESHADOWING_STATUSES
    ):
        raise ValueError("伏笔状态必须是 pending、planted、developing、payoff_pending、resolved 或 abandoned")
    if entity_type in {"foreshadowing", "world_setting"} and value.get("importance") not in (None, "low", "medium", "high"):
        raise ValueError("重要性必须是 low、medium 或 high")
    if entity_type == "world_setting" and operation == "create":
        if not any(value.get(key) for key in ("title", "era", "geography", "rules")):
            raise ValueError("新增世界观设定至少需要标题、时代、地理或规则之一")
    if entity_type == "world_setting" and value.get("category") not in (
        None, *WORLD_SETTING_CATEGORIES,
    ):
        raise ValueError("世界观分类不在支持范围内")
    if entity_type == "memory" and operation == "create":
        if not value.get("title") or not value.get("content"):
            raise ValueError("新增长期记忆必须提供标题和内容")
    if entity_type == "memory" and operation == "update":
        raise ValueError("长期记忆采用版本化追加，不允许覆盖已有条目")


def _find_organization_relation_conflict(
    db: Session,
    project_id: int,
    organization_a_id: int,
    organization_b_id: int,
    start: int | None,
    end: int | None,
    exclude_id: int | None = None,
    planned_updates: dict[int, dict[str, Any]] | None = None,
) -> OrganizationRelation | None:
    """查找同一组织对中章节区间重叠的关系。

    步骤 1：按项目和规范化后的组织端点筛选既有关系。
    步骤 2：应用本批次已提出的区间调整并跳过指定关系。
    步骤 3：返回首条与候选区间冲突的记录。
    """
    first_id, second_id = sorted((organization_a_id, organization_b_id))
    query = db.query(OrganizationRelation).filter(
        OrganizationRelation.project_id == project_id,
        OrganizationRelation.organization_a_id == first_id,
        OrganizationRelation.organization_b_id == second_id,
    )
    if exclude_id is not None:
        query = query.filter(OrganizationRelation.id != exclude_id)
    for existing in query.all():
        planned = (planned_updates or {}).get(existing.id, {})
        existing_start = planned.get("effective_from_chapter", existing.effective_from_chapter)
        existing_end = planned.get("expires_at_chapter", existing.expires_at_chapter)
        starts_before_existing_ends = (
            existing_end is None
            or start is None
            or start <= existing_end
        )
        existing_starts_before_end = (
            end is None
            or existing_start is None
            or existing_start <= end
        )
        if starts_before_existing_ends and existing_starts_before_end:
            return existing
    return None


def _read_before_value(
    entity_type: str,
    entity: Any,
    operation: str,
    proposed_value: dict[str, Any],
) -> dict[str, Any]:
    """保存拟修改字段的当前快照，供审核时做乐观并发检查。"""
    if operation == "create":
        return {}
    if entity_type == "relationship":
        return {"relationships": _current_field("relationship", entity, "character_relations") or []}
    return {
        key: _current_field(entity_type, entity, key)
        for key in proposed_value
    }


def create_proposals(
    db: Session,
    project_id: int,
    chapter_id: int,
    run_id: str | None,
    version_id: str | None,
    drafts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """校验并保存一批提案。

    步骤 1：确认章节、工作流运行和正文版本都属于指定项目。
    步骤 2：逐项校验实体引用和允许修改的字段。
    步骤 3：快照被修改字段的当前值，并生成稳定幂等键。
    步骤 4：在调用方事务提交前返回已存在或新建的提案。
    """
    chapter = db.query(Chapter).filter(
        Chapter.id == chapter_id,
        Chapter.project_id == project_id,
    ).first()
    if not chapter:
        raise LookupError("章节不存在或不属于当前项目")

    if run_id:
        run = db.query(WorkflowRun).filter(
            WorkflowRun.run_id == run_id,
            WorkflowRun.project_id == project_id,
        ).first()
        if not run or (run.chapter_id is not None and run.chapter_id != chapter_id):
            raise ValueError("工作流运行记录与当前项目或章节不匹配")
    if version_id:
        version = db.query(GenerationVersion).filter(
            GenerationVersion.version_id == version_id,
            GenerationVersion.chapter_id == chapter_id,
        ).first()
        if not version:
            raise ValueError("正文版本与当前章节不匹配")

    results = []
    # 章节可能同时结束旧关系并建立新关系；用本批更新草稿计算其审核后的区间。
    planned_relation_updates = {
        draft.get("target_id"): draft.get("proposed_value", {})
        for draft in drafts
        if draft.get("entity_type") == "organization_relation"
        and draft.get("operation") == "update"
        and isinstance(draft.get("target_id"), int)
    }
    for draft in drafts:
        entity_type = draft["entity_type"]
        operation = draft["operation"]
        target_id = draft.get("target_id")
        proposed_value = draft["proposed_value"]
        _validate_value(entity_type, operation, target_id, proposed_value)

        if entity_type == "organization_relation":
            if operation == "create":
                source = _get_entity(db, "organization", project_id, proposed_value["source_org_id"])
                target = _get_entity(db, "organization", project_id, proposed_value["target_org_id"])
                if not source or not target or source.id == target.id:
                    raise ValueError("组织关系的两端必须是当前项目中的不同组织")
                conflict = _find_organization_relation_conflict(
                    db,
                    project_id,
                    source.id,
                    target.id,
                    proposed_value.get("effective_from_chapter"),
                    proposed_value.get("expires_at_chapter"),
                    planned_updates=planned_relation_updates,
                )
                if conflict:
                    raise ValueError("这两个组织在该章节范围内已有关系记录")
                entity = None
            else:
                entity = _get_entity(db, entity_type, project_id, target_id)
                if not entity:
                    raise ValueError(f"提案目标不存在或不属于当前项目：{entity_type}#{target_id}")
                new_start = proposed_value.get("effective_from_chapter", entity.effective_from_chapter)
                new_end = proposed_value.get("expires_at_chapter", entity.expires_at_chapter)
                conflict = _find_organization_relation_conflict(
                    db,
                    project_id,
                    entity.organization_a_id,
                    entity.organization_b_id,
                    new_start,
                    new_end,
                    exclude_id=entity.id,
                    planned_updates=planned_relation_updates,
                )
                if conflict:
                    raise ValueError("关系更新后的章节范围与同一组织对的其他关系重叠")
        elif entity_type == "relationship":
            source = _get_entity(db, "relationship", project_id, target_id)
            target = _get_entity(db, "character", project_id, proposed_value["target_id"])
            if not source or not target:
                raise ValueError("人物关系的源人物或目标人物不属于当前项目")
            if source.id == target.id:
                raise ValueError("人物不能与自己建立人物关系")
            entity = source
        elif operation == "update":
            entity = _get_entity(db, entity_type, project_id, target_id)
            if not entity:
                raise ValueError(f"提案目标不存在或不属于当前项目：{entity_type}#{target_id}")
        else:
            entity = None

        if entity_type == "organization" and proposed_value.get("parent_id"):
            parent = _get_entity(db, "organization", project_id, proposed_value["parent_id"])
            if not parent:
                raise ValueError("父组织不存在或不属于当前项目")

        before_value = _read_before_value(entity_type, entity, operation, proposed_value)
        key = _proposal_key(project_id, chapter_id, run_id, version_id, draft, before_value)
        row = db.query(ChapterChangeProposal).filter(
            ChapterChangeProposal.proposal_key == key,
        ).first()
        if row:
            results.append(row)
            continue

        # 新增对象没有现成名称时，从候选字段生成可读标签。
        target_label = (
            draft.get("target_label")
            or getattr(entity, "name", "")
            or getattr(entity, "keyword", "")
            or getattr(entity, "title", "")
            or proposed_value.get("name")
            or proposed_value.get("keyword")
            or proposed_value.get("title")
            or ""
        )
        row = ChapterChangeProposal(
            proposal_id=str(uuid.uuid4()),
            proposal_key=key,
            project_id=project_id,
            chapter_id=chapter_id,
            run_id=run_id,
            version_id=version_id,
            entity_type=entity_type,
            operation=operation,
            target_id=target_id,
            target_label=str(target_label),
            before_value=_json_dump(before_value),
            proposed_value=_json_dump(proposed_value),
            rationale=draft.get("rationale", ""),
            evidence=draft.get("evidence", ""),
            status="pending",
        )
        db.add(row)
        db.flush()
        results.append(row)
    return [_serialize_proposal(row) for row in results]


def list_proposals(
    db: Session,
    project_id: int,
    chapter_id: int,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """按章节列出提案，步骤：限定项目与章节、可选筛选状态、按创建顺序返回。"""
    query = db.query(ChapterChangeProposal).filter(
        ChapterChangeProposal.project_id == project_id,
        ChapterChangeProposal.chapter_id == chapter_id,
    )
    if status:
        query = query.filter(ChapterChangeProposal.status == status)
    return [_serialize_proposal(row) for row in query.order_by(ChapterChangeProposal.id.asc()).all()]


def build_proposal_drafts(
    analysis: dict[str, Any],
    entity_catalog: dict[str, list[dict[str, Any]]],
    chapter_no: int,
) -> list[dict[str, Any]]:
    """把结构化分析中的名称引用解析为项目内提案草稿。

    步骤 1：规范实体名称并只接受目录中唯一匹配的既有人物、组织和伏笔。
    步骤 2：把新增/更新意图转换成受字段白名单约束的候选字段。
    步骤 3：无法唯一定位的变化不自动写回，留给后续人工补录流程处理。
    步骤 4：将时间线事件转换为来源明确的长期记忆候选。
    """
    if not isinstance(analysis, dict) or not analysis:
        return []

    def key_name(value: Any) -> str:
        return str(value or "").strip().casefold()

    def unique_match(items: list[dict[str, Any]], field: str, name: Any) -> dict[str, Any] | None:
        target = key_name(name)
        matches = [item for item in items if key_name(item.get(field)) == target and target]
        return matches[0] if len(matches) == 1 else None

    proposals: list[dict[str, Any]] = []

    # 人物变化：模型只给名称，服务端从项目目录解析 ID。
    for item in analysis.get("character_changes", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        operation = item.get("operation", "update")
        changes = item.get("changes") or {}
        if not isinstance(changes, dict):
            continue
        allowed = EDITABLE_FIELDS["character"]
        values = {key: value for key, value in changes.items() if key in allowed}
        match = unique_match(entity_catalog.get("characters", []), "name", name)
        if operation == "create" and not match:
            values["name"] = name
            target_id = None
        elif match and operation == "update":
            target_id = match["id"]
        else:
            continue
        if not values:
            continue
        proposals.append({
            "entity_type": "character",
            "operation": operation,
            "target_id": target_id,
            "target_label": name,
            "proposed_value": values,
            "rationale": item.get("rationale", ""),
            "evidence": item.get("evidence", ""),
        })

    # 人物关系：两端都必须唯一匹配当前项目中的人物卡；变更已有关系必须明确标记 update。
    for item in analysis.get("relationships", []):
        if not isinstance(item, dict):
            continue
        source = unique_match(entity_catalog.get("characters", []), "name", item.get("source_name"))
        target = unique_match(entity_catalog.get("characters", []), "name", item.get("target_name"))
        relation_type = str(item.get("relation_type") or "").strip()
        if not source or not target or source["id"] == target["id"] or not relation_type:
            continue
        operation = item.get("operation", "create")
        if operation not in {"create", "update"}:
            continue
        current_relations = source.get("character_relations") or []
        existing_relations = [
            relation
            for relation in current_relations
            if isinstance(relation, dict) and relation.get("target_id") == target["id"]
        ]
        # 步骤 1：已有相同关系不重复提案；不同关系类型必须由分析器明确提出更新。
        if operation == "create" and existing_relations:
            continue
        if operation == "update" and len(existing_relations) != 1:
            continue
        relation_value = {
            "target_id": target["id"],
            "relation_type": relation_type,
        }
        if operation == "create":
            relation_value.update({
                "depth": item.get("depth", 3),
                "effective_from": item.get("effective_from") or chapter_no,
                "expires_at": item.get("expires_at"),
            })
        else:
            # 更新只写模型明确提出的关系字段，保留未变化的深度和有效期。
            for field_name in ("depth", "effective_from", "expires_at"):
                if field_name in item:
                    relation_value[field_name] = item[field_name]
        proposals.append({
            "entity_type": "relationship",
            "operation": operation,
            "target_id": source["id"],
            "target_label": f'{item.get("source_name")} → {item.get("target_name")}',
            "proposed_value": relation_value,
            "rationale": item.get("rationale", ""),
            "evidence": item.get("evidence", ""),
        })

    # 组织变化：新组织必须由分析器明确标记 create。
    for item in analysis.get("organization_changes", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        operation = item.get("operation", "update")
        changes = item.get("changes") or {}
        if not isinstance(changes, dict):
            continue
        values = {key: value for key, value in changes.items() if key in EDITABLE_FIELDS["organization"]}
        match = unique_match(entity_catalog.get("organizations", []), "name", name)
        if operation == "create" and not match:
            values["name"] = name
            target_id = None
        elif match and operation == "update":
            target_id = match["id"]
        else:
            continue
        if values:
            proposals.append({
                "entity_type": "organization",
                "operation": operation,
                "target_id": target_id,
                "target_label": name,
                "proposed_value": values,
                "rationale": item.get("rationale", ""),
                "evidence": item.get("evidence", ""),
            })

    # 组织间关系：按唯一组织名称定位端点，并把章节区间冲突挡在待审核队列之外。
    organizations = entity_catalog.get("organizations", [])
    existing_org_relations = [dict(relation) for relation in entity_catalog.get("organization_relations", [])]
    relation_changes = [
        item for item in analysis.get("organization_relations", []) if isinstance(item, dict)
    ]
    # 先排关系区间更新，再排新增，支持“结束旧同盟并转为敌对”等同章变化。
    relation_changes.sort(key=lambda item: 0 if item.get("operation") == "update" else 1)
    used_relation_ids: set[int] = set()
    for item in relation_changes:
        source = unique_match(organizations, "name", item.get("source_name"))
        target = unique_match(organizations, "name", item.get("target_name"))
        operation = item.get("operation", "create")
        relation_type = item.get("relation_type")
        if not source or not target or source["id"] == target["id"]:
            continue
        pair_ids = tuple(sorted((source["id"], target["id"])))
        pair_relations = [
            relation
            for relation in existing_org_relations
            if (relation["organization_a_id"], relation["organization_b_id"]) == pair_ids
        ]
        if operation == "create":
            requested_start = item.get("effective_from_chapter")
            start = chapter_no if requested_start is None else requested_start
            end = item.get("expires_at_chapter")
            if relation_type not in {"alliance", "hostility"}:
                continue
            if start < 1 or (end is not None and end < start):
                continue
            if any(_chapter_ranges_overlap(
                start,
                end,
                relation.get("effective_from_chapter"),
                relation.get("expires_at_chapter"),
            ) for relation in pair_relations):
                continue
            relation_values = {
                "source_org_id": source["id"],
                "target_org_id": target["id"],
                "relation_type": relation_type,
                "description": item.get("description") or "",
                "effective_from_chapter": start,
                "expires_at_chapter": end,
            }
            target_id = None
        elif operation == "update":
            target_effective_from = item.get("target_effective_from_chapter")
            matches = pair_relations
            if "target_effective_from_chapter" in item:
                matches = [
                    relation for relation in matches
                    if relation.get("effective_from_chapter") == target_effective_from
                ]
            if len(matches) != 1:
                continue
            existing = matches[0]
            target_id = existing["id"]
            if target_id in used_relation_ids:
                continue
            relation_values = {}
            for field_name in (
                "relation_type", "description", "effective_from_chapter", "expires_at_chapter",
            ):
                if field_name in item and item[field_name] is not None:
                    relation_values[field_name] = item[field_name]
                elif field_name == "description" and field_name in item:
                    relation_values[field_name] = item[field_name] or ""
                elif field_name in item and field_name in {"effective_from_chapter", "expires_at_chapter"}:
                    relation_values[field_name] = None
            if not relation_values or all(
                existing.get(field_name) == value
                for field_name, value in relation_values.items()
            ):
                continue
            start = relation_values.get("effective_from_chapter", existing.get("effective_from_chapter"))
            end = relation_values.get("expires_at_chapter", existing.get("expires_at_chapter"))
            if (start is not None and start < 1) or (end is not None and end < 1):
                continue
            if start is not None and end is not None and end < start:
                continue
            if any(
                relation["id"] != target_id
                and _chapter_ranges_overlap(
                    start,
                    end,
                    relation.get("effective_from_chapter"),
                    relation.get("expires_at_chapter"),
                )
                for relation in pair_relations
            ):
                continue
            for relation in existing_org_relations:
                if relation["id"] == target_id:
                    relation.update(relation_values)
                    break
            used_relation_ids.add(target_id)
        else:
            continue

        if operation == "create":
            existing_org_relations.append({
                "id": -len(existing_org_relations) - 1,
                "organization_a_id": pair_ids[0],
                "organization_b_id": pair_ids[1],
                **relation_values,
            })

        proposals.append({
            "entity_type": "organization_relation",
            "operation": operation,
            "target_id": target_id,
            "target_label": f'{source["name"]} → {target["name"]}',
            "proposed_value": relation_values,
            "rationale": item.get("rationale", ""),
            "evidence": item.get("evidence", ""),
        })

    # 伏笔变化：通过关键词唯一定位旧伏笔，否则只允许明确新增。
    for item in analysis.get("foreshadowing_changes", []):
        if not isinstance(item, dict):
            continue
        keyword = str(item.get("keyword") or "").strip()
        operation = item.get("operation", "create")
        changes = item.get("changes") or {}
        if not isinstance(changes, dict):
            continue
        values = {key: value for key, value in changes.items() if key in EDITABLE_FIELDS["foreshadowing"]}
        if operation == "create":
            # 避免模型将已存在伏笔误判为新伏笔而重复建卡。
            if unique_match(entity_catalog.get("foreshadowings", []), "keyword", keyword):
                continue
            values["keyword"] = keyword
            values.setdefault("planted_chapter", chapter_no)
            if not values.get("description"):
                continue
            target_id = None
        elif operation == "update":
            match = unique_match(
                entity_catalog.get("foreshadowings", []),
                "keyword",
                item.get("target_keyword") or keyword,
            )
            if not match:
                continue
            target_id = match["id"]
        else:
            continue
        if values:
            proposals.append({
                "entity_type": "foreshadowing",
                "operation": operation,
                "target_id": target_id,
                "target_label": keyword,
                "proposed_value": values,
                "rationale": item.get("rationale", ""),
                "evidence": item.get("evidence", ""),
            })

    # 世界观变化：按标题匹配现有设定；未匹配时允许明确创建新设定。
    for item in analysis.get("world_changes", []):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        operation = item.get("operation", "update")
        changes = item.get("changes") or {}
        if not isinstance(changes, dict):
            continue
        values = {key: value for key, value in changes.items() if key in EDITABLE_FIELDS["world_setting"]}
        match = unique_match(entity_catalog.get("world_settings", []), "title", title)
        if operation == "create" and not match:
            values["title"] = title
            target_id = None
        elif match and operation == "update":
            target_id = match["id"]
        else:
            continue
        if values:
            proposals.append({
                "entity_type": "world_setting",
                "operation": operation,
                "target_id": target_id,
                "target_label": title,
                "proposed_value": values,
                "rationale": item.get("rationale", ""),
                "evidence": item.get("evidence", ""),
            })

    # 时间线事件属于章节事实，作为长期记忆候选追加，不覆盖人物或设定卡片。
    for index, item in enumerate(analysis.get("timeline_events", []), start=1):
        if isinstance(item, str):
            title, content, importance = f"第{chapter_no}章事件 {index}", item.strip(), 60
        elif isinstance(item, dict):
            title = str(item.get("title") or f"第{chapter_no}章事件 {index}").strip()
            content = str(item.get("content") or "").strip()
            importance = item.get("importance", 60)
        else:
            continue
        if title and content:
            proposals.append({
                "entity_type": "memory",
                "operation": "create",
                "target_id": None,
                "target_label": title,
                "proposed_value": {
                    "memory_type": "timeline_event",
                    "title": title,
                    "content": content,
                    "content_summary": content[:240],
                    "importance": importance,
                    "metadata_json": {"chapter_no": chapter_no},
                },
                "rationale": "记录本章时间线事件，供后续章节回顾。",
                "evidence": content,
            })
    # 步骤 5：丢弃字段类型错误或缺少必要字段的模型候选，不能让章节生成因分析瑕疵失败。
    validated = []
    for proposal in proposals:
        try:
            _validate_value(
                proposal["entity_type"],
                proposal["operation"],
                proposal["target_id"],
                proposal["proposed_value"],
            )
        except (TypeError, ValueError):
            continue
        validated.append(proposal)
    return validated


def _chapter_ranges_overlap(
    first_start: int | None,
    first_end: int | None,
    second_start: int | None,
    second_end: int | None,
) -> bool:
    """判断两个组织关系章节区间是否重叠。

    步骤 1：把空起止边界视为没有时间限制。
    步骤 2：分别检查两个区间的起点是否落在对方范围内。
    """
    first_starts_before_second_ends = second_end is None or first_start is None or first_start <= second_end
    second_starts_before_first_end = first_end is None or second_start is None or second_start <= first_end
    return first_starts_before_second_ends and second_starts_before_first_end


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

    if proposal.entity_type == "organization":
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
