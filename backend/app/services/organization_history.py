"""组织档案历史快照服务。"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.business import Organization, OrganizationHistory


SNAPSHOT_FIELDS = (
    "parent_id", "name", "org_type", "location", "slogan", "description", "level",
    "power_level", "member_count", "status", "hierarchy", "hierarchy_system",
    "hierarchy_levels", "hierarchy_templates", "resources", "goal", "core_members",
    "allies", "enemies", "impact", "risk_notes", "hidden_secrets",
    "active_from_chapter", "disbanded_chapter",
)


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
) -> OrganizationHistory | None:
    """写入组织历史。

    步骤 1：比较变更前后的业务字段。
    步骤 2：无实际变化时跳过，避免产生重复历史。
    步骤 3：将快照与章节提案来源加入当前事务，交由调用方统一提交。
    """
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
