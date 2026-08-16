from __future__ import annotations

from sqlalchemy import desc, or_

from app.db.repository import row_to_dict, rows_to_dicts
from app.db.session import get_business_db
from app.models.business import (
    Chapter,
    ChapterSummary,
    Character,
    Foreshadowing,
    Organization,
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
            .order_by(Organization.id.desc())
            .limit(8)
            .all()
        )

        foreshadowings = (
            db.query(Foreshadowing)
            .filter(
                Foreshadowing.project_id == project_id,
                Foreshadowing.status.in_(["pending", "planted", "developing"]),
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

    return {
        "project": row_to_dict(project) or {},
        "world": row_to_dict(world) or {},
        "outline": row_to_dict(outline) or {},
        "characters": rows_to_dicts(characters),
        "organizations": rows_to_dicts(organizations),
        "foreshadowings": rows_to_dicts(foreshadowings),
        "recent_summaries": rows_to_dicts(summaries),
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
    }
