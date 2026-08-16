from __future__ import annotations

from app.db.database import get_connection
from app.db.repository import rows_to_dicts


def build_chapter_context(project_id: int, chapter_no: int, outline_id: int | None = None) -> dict:
    """组装章节生成上下文。

    第一版先用结构化资料 + 最近摘要；后续可在这里加入向量检索、BM25 和融合排序。
    """
    with get_connection() as conn:
        project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        world = conn.execute(
            "SELECT * FROM world_settings WHERE project_id = ? ORDER BY id DESC LIMIT 1",
            (project_id,),
        ).fetchone()
        if outline_id:
            outline = conn.execute(
                "SELECT * FROM outlines WHERE id = ? AND project_id = ?",
                (outline_id, project_id),
            ).fetchone()
        else:
            outline = conn.execute(
                """
                SELECT * FROM outlines
                WHERE project_id = ? AND (chapter_no = ? OR sort_index = ?)
                ORDER BY chapter_no DESC, id DESC LIMIT 1
                """,
                (project_id, chapter_no, chapter_no),
            ).fetchone()
        characters = conn.execute(
            "SELECT * FROM characters WHERE project_id = ? ORDER BY id DESC LIMIT 12",
            (project_id,),
        ).fetchall()
        organizations = conn.execute(
            "SELECT * FROM organizations WHERE project_id = ? ORDER BY id DESC LIMIT 8",
            (project_id,),
        ).fetchall()
        foreshadowings = conn.execute(
            """
            SELECT * FROM foreshadowings
            WHERE project_id = ? AND status IN ('pending', 'planted', 'developing')
            ORDER BY importance DESC, id DESC LIMIT 12
            """,
            (project_id,),
        ).fetchall()
        summaries = conn.execute(
            """
            SELECT cs.* FROM chapter_summaries cs
            JOIN chapters c ON c.id = cs.chapter_id
            WHERE c.project_id = ? AND c.chapter_no < ?
            ORDER BY c.chapter_no DESC LIMIT 5
            """,
            (project_id, chapter_no),
        ).fetchall()

    return {
        "project": dict(project) if project else {},
        "world": dict(world) if world else {},
        "outline": dict(outline) if outline else {},
        "characters": rows_to_dicts(characters),
        "organizations": rows_to_dicts(organizations),
        "foreshadowings": rows_to_dicts(foreshadowings),
        "recent_summaries": rows_to_dicts(summaries),
    }


def build_context_preview(project_id: int, chapter_no: int, outline_id: int | None = None) -> dict:
    """生成给前端展示的上下文包预览。

    这个接口不改变生成逻辑，只把 Agent 实际会读取的资料压缩成可视摘要，
    方便用户在生成前判断“这次模型到底看到了什么”。
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
