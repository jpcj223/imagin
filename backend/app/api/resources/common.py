"""资源路由共用的表名白名单与大纲编号工具。"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.business import Chapter, Outline


def _link_legacy_chapters_to_outlines(db: Session, project_id: int) -> None:
    """排序变化前，把章号唯一对应的旧章节绑定到稳定的大纲 ID。"""
    outlines = db.query(Outline).filter(
        Outline.project_id == project_id,
        Outline.node_type == "chapter",
        Outline.chapter_no.isnot(None),
    ).all()
    outlines_by_number: dict[int, list[Outline]] = {}
    for outline in outlines:
        outlines_by_number.setdefault(int(outline.chapter_no), []).append(outline)

    legacy_chapters = db.query(Chapter).filter(
        Chapter.project_id == project_id,
        Chapter.outline_id.is_(None),
    ).all()
    for chapter in legacy_chapters:
        matches = outlines_by_number.get(int(chapter.chapter_no), [])
        if len(matches) == 1:
            chapter.outline_id = matches[0].id


def _sync_linked_chapter_numbers(db: Session, project_id: int) -> None:
    """大纲重排后，同步已绑定章节的展示序号。"""
    outline_numbers = {
        outline.id: outline.chapter_no
        for outline in db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "chapter",
        ).all()
    }
    linked_chapters = db.query(Chapter).filter(
        Chapter.project_id == project_id,
        Chapter.outline_id.isnot(None),
    ).all()
    for chapter in linked_chapters:
        chapter_no = outline_numbers.get(chapter.outline_id)
        if chapter_no is not None:
            chapter.chapter_no = chapter_no

def _renumber_all_volumes(db: Session, project_id: int) -> int:
    """内部工具：全局重新排列卷号。"""
    volumes = db.query(Outline).filter(
        Outline.project_id == project_id,
        Outline.node_type == "volume"
    ).order_by(Outline.volume_no, Outline.id).all()

    for i, vol in enumerate(volumes):
        vol.volume_no = i + 1

    return len(volumes)


def _renumber_all_chapters(db: Session, project_id: int) -> int:
    """内部工具：全局重新排列章节号。"""
    volumes = db.query(Outline).filter(
        Outline.project_id == project_id,
        Outline.node_type == "volume"
    ).order_by(Outline.volume_no).all()

    chapter_no = 0
    for vol in volumes:
        chapters = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "chapter",
            Outline.volume_id == vol.id
        ).order_by(Outline.sort_index).all()
        for ch in chapters:
            chapter_no += 1
            ch.chapter_no = chapter_no
            ch.sort_index = chapter_no

    _sync_linked_chapter_numbers(db, project_id)
    return chapter_no


def _resource_table(resource: str) -> str:
    """把前端资源名映射到数据库表名。

    所有通用 CRUD 都必须通过这里，避免任意表名被拼进 SQL。
    """
    mapping = {
        "world": "world_settings",
        "outlines": "outlines",
        "characters": "characters",
        "organizations": "organizations",
        "foreshadowings": "foreshadowings",
        "chapters": "chapters",
        "character-groups": "character_groups",
    }
    if resource not in mapping:
        raise HTTPException(status_code=404, detail="未知资源")
    return mapping[resource]
