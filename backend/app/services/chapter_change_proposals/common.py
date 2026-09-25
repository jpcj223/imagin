"""提案序列化、实体读取和乐观并发快照工具。"""

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.business import Character, ChapterChangeProposal
from .constants import ENTITY_MODELS, JSON_FIELDS

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
