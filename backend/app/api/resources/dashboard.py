"""项目仪表盘统计路由。"""

from fastapi import APIRouter
from sqlalchemy import func

from app.db.session import get_business_db
from app.models.business import Chapter, Character, Foreshadowing, Organization, Outline, WorldSetting

router = APIRouter()

@router.get("/{project_id}/dashboard")
def dashboard(project_id: int) -> dict:
    """返回项目首页统计数据。

    包含：各资源数量、字数统计、最近章节、组织/世界观数量等，
    供前端创作中心展示项目整体进度和快捷入口。
    """
    with get_business_db() as db:
        # 1. 基础计数
        characters = db.query(func.count(Character.id)).filter(Character.project_id == project_id).scalar() or 0
        outlines = db.query(func.count(Outline.id)).filter(Outline.project_id == project_id).scalar() or 0
        chapters = db.query(func.count(Chapter.id)).filter(Chapter.project_id == project_id).scalar() or 0
        foreshadowings = db.query(func.count(Foreshadowing.id)).filter(Foreshadowing.project_id == project_id).scalar() or 0
        organizations = db.query(func.count(Organization.id)).filter(Organization.project_id == project_id).scalar() or 0
        world_settings = db.query(func.count(WorldSetting.id)).filter(WorldSetting.project_id == project_id).scalar() or 0

        # 2. 总字数（所有章节正文长度之和）
        total_chars_row = db.query(
            func.coalesce(func.sum(func.length(Chapter.content)), 0)
        ).filter(Chapter.project_id == project_id).first()
        total_chars = total_chars_row[0] if total_chars_row else 0

        # 3. 最近章节（按章节号倒序取最近 5 章）
        recent_chapters_rows = db.query(
            Chapter.id,
            Chapter.chapter_no,
            Chapter.title,
            Chapter.status,
            func.length(Chapter.content).label("char_count"),
            Chapter.updated_at,
        ).filter(
            Chapter.project_id == project_id
        ).order_by(
            Chapter.chapter_no.desc()
        ).limit(5).all()

        recent_chapters = [
            {
                "id": row.id,
                "chapter_no": row.chapter_no,
                "title": row.title,
                "status": row.status,
                "char_count": row.char_count,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in recent_chapters_rows
        ]

        # 4. 伏笔状态分布
        foreshadowing_status_rows = db.query(
            Foreshadowing.status,
            func.count(Foreshadowing.id).label("count"),
        ).filter(
            Foreshadowing.project_id == project_id
        ).group_by(Foreshadowing.status).all()
        foreshadowing_by_status = {row.status: row.count for row in foreshadowing_status_rows}

        # 5. 角色类型分布
        character_type_rows = db.query(
            Character.role_type,
            func.count(Character.id).label("count"),
        ).filter(
            Character.project_id == project_id
        ).group_by(Character.role_type).all()
        characters_by_type = {row.role_type: row.count for row in character_type_rows}

    return {
        "counts": {
            "characters": characters,
            "outlines": outlines,
            "chapters": chapters,
            "foreshadowings": foreshadowings,
            "organizations": organizations,
            "world_settings": world_settings,
        },
        "total_chars": total_chars,
        "recent_chapters": recent_chapters,
        "foreshadowing_by_status": foreshadowing_by_status,
        "characters_by_type": characters_by_type,
    }
