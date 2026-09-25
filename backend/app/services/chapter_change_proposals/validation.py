"""变化提案的字段、类型、章节区间和组织关系校验。"""

from typing import Any

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Session

from app.models.business import OrganizationRelation
from app.models.business.foreshadowing import FORESHADOWING_STATUSES
from .constants import (
    EDITABLE_FIELDS,
    ENTITY_MODELS,
    JSON_FIELDS,
    RELATION_FIELDS,
    WORLD_SETTING_CATEGORIES,
)

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
    if entity_type == "foreshadowing":
        # 步骤 2：章节编号必须为正数，并校验提案自身包含的生命周期顺序。
        _validate_foreshadowing_chapter_order(value)
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

def _validate_foreshadowing_chapter_order(values: dict[str, Any]) -> None:
    """校验伏笔提案包含的章节编号与局部顺序。"""
    chapter_fields = ("planted_chapter", "payoff_chapter", "resolved_chapter", "effective_from", "expires_at")
    for field_name in chapter_fields:
        chapter_no = values.get(field_name)
        if chapter_no is not None and (not isinstance(chapter_no, int) or isinstance(chapter_no, bool) or chapter_no < 1):
            raise ValueError(f"伏笔章节字段 {field_name} 必须是正整数或空值")

    planted = values.get("planted_chapter")
    payoff = values.get("payoff_chapter")
    resolved = values.get("resolved_chapter")
    effective_from = values.get("effective_from")
    expires_at = values.get("expires_at")
    if planted and payoff and payoff < planted:
        raise ValueError("计划回收章节不能早于埋下章节")
    if planted and resolved and resolved < planted:
        raise ValueError("实际回收章节不能早于埋下章节")
    if effective_from and expires_at and expires_at < effective_from:
        raise ValueError("失效章节不能早于生效章节")

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
