"""组织档案历史快照服务。"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.business import Organization, OrganizationHistory, OrganizationRelation


SNAPSHOT_FIELDS = (
    "parent_id", "name", "org_type", "location", "slogan", "description", "level",
    "power_level", "member_count", "status", "hierarchy", "hierarchy_system",
    "hierarchy_levels", "hierarchy_templates", "resources", "goal", "core_members",
    "allies", "enemies", "impact", "risk_notes", "hidden_secrets",
    "active_from_chapter", "disbanded_chapter",
)


def capture_organization_relation_snapshot(
    db: Session,
    relation: OrganizationRelation,
    organization_id: int,
) -> dict[str, Any]:
    """按当前组织视角读取关系快照。

    步骤 1：从关系两端确定当前组织对应的另一端。
    步骤 2：查询对端名称并返回关系类型、说明和章节区间。
    """
    target_id = (
        relation.organization_b_id
        if relation.organization_a_id == organization_id
        else relation.organization_a_id
    )
    target = db.query(Organization).filter(
        Organization.id == target_id,
        Organization.project_id == relation.project_id,
    ).first()
    return {
        "organization_relation": {
            "target_org_id": target_id,
            "target_org_name": target.name if target else "（组织已删除）",
            "relation_type": relation.relation_type,
            "description": relation.description or "",
            "effective_from_chapter": relation.effective_from_chapter,
            "expires_at_chapter": relation.expires_at_chapter,
        }
    }


def capture_organization_snapshot(organization: Organization) -> dict[str, Any]:
    """复制组织业务字段，排除 ID 和时间戳等系统字段。

    步骤 1：按白名单读取稳定的档案字段。
    步骤 2：返回可直接序列化的字段快照。
    """
    return {field_name: getattr(organization, field_name) for field_name in SNAPSHOT_FIELDS}


def record_organization_history(
    db: Session,
    organization: Organization,
    source_type: str,
    operation: str,
    before_snapshot: dict[str, Any],
    after_snapshot: dict[str, Any],
    chapter_id: int | None = None,
    proposal_id: str | None = None,
    rationale: str = "",
    evidence: str = "",
    changed_fields_override: list[str] | None = None,
) -> OrganizationHistory | None:
    """写入组织历史。

    步骤 1：比较变更前后的档案字段，或使用调用方指定的关系事件字段。
    步骤 2：无实际变化时跳过，避免产生重复历史。
    步骤 3：将快照与章节提案来源加入当前事务，交由调用方统一提交。
    """
    if changed_fields_override is not None:
        changed_fields = [
            field_name
            for field_name in changed_fields_override
            if before_snapshot.get(field_name) != after_snapshot.get(field_name)
        ]
    else:
        changed_fields = [
            field_name
            for field_name in SNAPSHOT_FIELDS
            if before_snapshot.get(field_name) != after_snapshot.get(field_name)
        ]
        if operation == "create":
            changed_fields = [
                field_name
                for field_name in SNAPSHOT_FIELDS
                if after_snapshot.get(field_name) not in (None, "", [], {}, 0)
            ]
    if not changed_fields:
        return None

    history = OrganizationHistory(
        project_id=organization.project_id,
        organization_id=organization.id,
        chapter_id=chapter_id,
        proposal_id=proposal_id,
        source_type=source_type,
        operation=operation,
        changed_fields=_json_dump(changed_fields),
        before_snapshot=_json_dump(before_snapshot),
        after_snapshot=_json_dump(after_snapshot),
        rationale=rationale,
        evidence=evidence,
    )
    db.add(history)
    return history


def parse_history_json(value: str | None, fallback: Any) -> Any:
    """读取历史 JSON 字段，兼容空值和损坏记录。

    步骤 1：空字段直接返回调用方提供的默认值。
    步骤 2：正常解析 JSON；解析失败时安全回退。
    """
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _json_dump(value: Any) -> str:
    """序列化快照，中文可读并保持键顺序稳定。

    步骤 1：保留中文字符，避免历史快照难以排查。
    步骤 2：固定键顺序和分隔符，便于比较记录。
    """
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
