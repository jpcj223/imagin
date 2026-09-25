"""伏笔档案历史快照服务。"""
from __future__ import annotations

import json
from typing import Any

from app.models.business import Foreshadowing, ForeshadowingHistory
from sqlalchemy.orm import Session


SNAPSHOT_FIELDS = (
    "keyword", "description", "status", "importance", "planted_chapter", "payoff_chapter",
    "resolved_chapter", "effective_from", "expires_at", "notes", "related_character_ids",
    "related_organization_ids", "related_outline_ids", "replaced_by_id",
)


def capture_foreshadowing_snapshot(item: Foreshadowing) -> dict[str, Any]:
    """复制伏笔业务字段，排除 ID 和时间戳。

    步骤 1：按稳定字段白名单读取档案内容。
    步骤 2：返回可存入 JSON 快照的普通字典。
    """
    return {field_name: getattr(item, field_name) for field_name in SNAPSHOT_FIELDS}


def record_foreshadowing_history(
    db: Session,
    item: Foreshadowing,
    source_type: str,
    operation: str,
    before_snapshot: dict[str, Any],
    after_snapshot: dict[str, Any],
    chapter_id: int | None = None,
    proposal_id: str | None = None,
    rationale: str = "",
    evidence: str = "",
) -> ForeshadowingHistory | None:
    """把真实变化加入当前事务，由调用方统一提交。

    步骤 1：计算变化字段；创建和删除分别记录实际存在的档案内容。
    步骤 2：没有实际变化时跳过，避免产生空历史。
    步骤 3：保存来源、章节和前后快照。
    """
    if operation == "create":
        changed_fields = [field for field in SNAPSHOT_FIELDS if after_snapshot.get(field) not in (None, "", [], {}, 0)]
    elif operation == "delete":
        changed_fields = [field for field in SNAPSHOT_FIELDS if before_snapshot.get(field) not in (None, "", [], {}, 0)]
    else:
        changed_fields = [
            field for field in SNAPSHOT_FIELDS
            if before_snapshot.get(field) != after_snapshot.get(field)
        ]
    if not changed_fields:
        return None

    history = ForeshadowingHistory(
        project_id=item.project_id,
        foreshadowing_id=item.id,
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
    """安全解析历史 JSON 字段，损坏或空值时返回默认值。"""
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _json_dump(value: Any) -> str:
    """稳定序列化中文 JSON，供快照比较与页面展示。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
