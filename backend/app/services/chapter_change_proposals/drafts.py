"""从章节分析生成提案、记录候选并查询审核列表。"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.business import Chapter, ChapterChangeProposal, GenerationVersion, WorkflowRun
from .common import (
    _get_entity,
    _json_dump,
    _proposal_key,
    _read_before_value,
    _serialize_proposal,
)
from .constants import EDITABLE_FIELDS
from .validation import (
    _chapter_ranges_overlap,
    _find_organization_relation_conflict,
    _validate_value,
)

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
        # 步骤 1：章节分析确认伏笔已回收时，将本章记录为实际回收章节。
        if values.get("status") == "resolved" and not values.get("resolved_chapter"):
            values["resolved_chapter"] = chapter_no
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
