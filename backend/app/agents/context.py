from __future__ import annotations

from sqlalchemy import desc, or_

from app.db.repository import row_to_dict, rows_to_dicts
from app.db.session import get_business_db
from app.models.business import (
    Chapter,
    ChapterSummary,
    Character,
    Foreshadowing,
    MemoryItem,
    Organization,
    OrganizationRelation,
    Outline,
    Project,
    WorldSetting,
)


def build_chapter_context(project_id: int, chapter_no: int, outline_id: int | None = None) -> dict:
    """组装章节生成上下文。

    第一版先用结构化资料 + 最近摘要；后续可在这里加入向量检索、BM25 和融合排序。
    """
    with get_business_db() as db:
        project = db.query(Project).filter(Project.id == project_id).first()

        world = (
            db.query(WorldSetting)
            .filter(WorldSetting.project_id == project_id)
            .order_by(WorldSetting.id.desc())
            .first()
        )

        if outline_id:
            outline = (
                db.query(Outline)
                .filter(Outline.id == outline_id, Outline.project_id == project_id)
                .first()
            )
        else:
            outline = (
                db.query(Outline)
                .filter(
                    Outline.project_id == project_id,
                    or_(Outline.chapter_no == chapter_no, Outline.sort_index == chapter_no),
                )
                .order_by(desc(Outline.chapter_no), desc(Outline.id))
                .first()
            )

        characters = (
            db.query(Character)
            .filter(Character.project_id == project_id)
            .order_by(Character.id.desc())
            .limit(12)
            .all()
        )

        organizations = (
            db.query(Organization)
            .filter(Organization.project_id == project_id)
            .filter(
                (Organization.active_from_chapter.is_(None))
                | (Organization.active_from_chapter <= chapter_no)
            )
            .filter(
                (Organization.disbanded_chapter.is_(None))
                | (Organization.disbanded_chapter >= chapter_no)
            )
            .order_by(Organization.id.desc())
            .limit(8)
            .all()
        )

        # 步骤 1：只检索本章有效、且至少一端出现在上下文中的组织关系。
        organization_ids = [item.id for item in organizations]
        organization_relations = []
        related_organization_names: dict[int, str] = {}
        if organization_ids:
            active_organization_ids = [
                row.id
                for row in db.query(Organization.id).filter(
                    Organization.project_id == project_id,
                    (Organization.active_from_chapter.is_(None))
                    | (Organization.active_from_chapter <= chapter_no),
                    (Organization.disbanded_chapter.is_(None))
                    | (Organization.disbanded_chapter >= chapter_no),
                ).all()
            ]
            organization_relations = db.query(OrganizationRelation).filter(
                OrganizationRelation.project_id == project_id,
                (
                    OrganizationRelation.organization_a_id.in_(organization_ids)
                    | OrganizationRelation.organization_b_id.in_(organization_ids)
                ),
                (OrganizationRelation.effective_from_chapter.is_(None))
                | (OrganizationRelation.effective_from_chapter <= chapter_no),
                (OrganizationRelation.expires_at_chapter.is_(None))
                | (OrganizationRelation.expires_at_chapter >= chapter_no),
                OrganizationRelation.organization_a_id.in_(active_organization_ids),
                OrganizationRelation.organization_b_id.in_(active_organization_ids),
            ).order_by(OrganizationRelation.id.asc()).all()
            relation_org_ids = {
                org_id
                for relation in organization_relations
                for org_id in (relation.organization_a_id, relation.organization_b_id)
            }
            related_organization_names = {
                row.id: row.name
                for row in db.query(Organization.id, Organization.name).filter(
                    Organization.project_id == project_id,
                    Organization.id.in_(relation_org_ids),
                ).all()
            }

        foreshadowings = (
            db.query(Foreshadowing)
            .filter(
                Foreshadowing.project_id == project_id,
                Foreshadowing.status.in_(["pending", "planted", "developing", "payoff_pending"]),
            )
            .order_by(desc(Foreshadowing.importance), desc(Foreshadowing.id))
            .limit(12)
            .all()
        )

        summaries = (
            db.query(ChapterSummary)
            .join(Chapter, Chapter.id == ChapterSummary.chapter_id)
            .filter(Chapter.project_id == project_id, Chapter.chapter_no < chapter_no)
            .order_by(desc(Chapter.chapter_no))
            .limit(5)
            .all()
        )

        # 步骤 1：只把已经存在于长期记忆库的条目交给旧版章节 Agent；待审核提案不会进入生成上下文。
        long_term_memories = (
            db.query(MemoryItem)
            .filter(MemoryItem.project_id == project_id)
            .order_by(MemoryItem.updated_at.desc(), MemoryItem.importance.desc())
            .limit(8)
            .all()
        )

    organization_items = rows_to_dicts(organizations)
    relation_items_by_organization: dict[int, list[dict]] = {}
    for relation in organization_relations:
        # 步骤 2：把关系以双向视角附在组织资料上，Agent 能读到同盟和敌对信息。
        for current_id, target_id in (
            (relation.organization_a_id, relation.organization_b_id),
            (relation.organization_b_id, relation.organization_a_id),
        ):
            relation_items_by_organization.setdefault(current_id, []).append({
                "target_org_id": target_id,
                "target_org_name": related_organization_names.get(target_id, ""),
                "relation_type": relation.relation_type,
                "description": relation.description or "",
                "effective_from_chapter": relation.effective_from_chapter,
                "expires_at_chapter": relation.expires_at_chapter,
            })
    for item in organization_items:
        item["relations"] = relation_items_by_organization.get(item["id"], [])

    return {
        "project": row_to_dict(project) or {},
        "world": row_to_dict(world) or {},
        "outline": row_to_dict(outline) or {},
        "characters": rows_to_dicts(characters),
        "organizations": organization_items,
        "foreshadowings": rows_to_dicts(foreshadowings),
        "recent_summaries": rows_to_dicts(summaries),
        "long_term_memories": rows_to_dicts(long_term_memories),
    }


def build_context_preview(project_id: int, chapter_no: int, outline_id: int | None = None) -> dict:
    """生成给前端展示的上下文包预览。

    这个接口不改变生成逻辑，只把 Agent 实际会读取的资料压缩成可视摘要，
    方便用户在生成前判断"这次模型到底看到了什么"。
    """
    context = build_chapter_context(project_id, chapter_no, outline_id)
    world = context["world"]
    outline = context["outline"]

    return {
        "chapter_no": chapter_no,
        "outline": {
            "title": outline.get("title", ""),
            "description": outline.get("description", ""),
        },
        "world": {
            "title": world.get("title") or world.get("era", ""),
            "category": world.get("category", ""),
            "rules": world.get("rules", ""),
        },
        "characters": [
            {
                "id": item.get("id"),
                "name": item.get("name", ""),
                "role_type": item.get("role_type", ""),
                "motivation": item.get("motivation", ""),
            }
            for item in context["characters"]
        ],
        "organizations": [
            {
                "id": item.get("id"),
                "name": item.get("name", ""),
                "goal": item.get("goal", ""),
                "power_level": item.get("power_level", 0),
                "relations": item.get("relations", []),
            }
            for item in context["organizations"]
        ],
        "foreshadowings": [
            {
                "id": item.get("id"),
                "keyword": item.get("keyword", ""),
                "status": item.get("status", ""),
                "payoff_chapter": item.get("payoff_chapter"),
            }
            for item in context["foreshadowings"]
        ],
        "recent_summaries": [
            {
                "id": item.get("id"),
                "summary": item.get("summary", ""),
                "timeline_events": item.get("timeline_events", ""),
            }
            for item in context["recent_summaries"]
        ],
        "long_term_memories": [
            {
                "memory_id": item.get("memory_id", ""),
                "title": item.get("title") or "",
                "content_summary": (item.get("content_summary") or item.get("content") or "")[:120],
                "importance": item.get("importance") or 0,
                "source_type": item.get("source_type") or "",
            }
            for item in context["long_term_memories"]
        ],
    }
