"""章节生成目标解析。

章节大纲可拖动排序，因此新稿目标必须从当前保存的大纲顺序解析，不能依赖
页面残留的章节号或当前正在查看的旧章节。
"""
from __future__ import annotations

from typing import Any, Iterable

from fastapi import HTTPException


def _field(item: Any, name: str, default: Any = None) -> Any:
    """兼容 ORM 对象和普通映射，便于用纯数据覆盖顺序边界。"""
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def resolve_next_chapter_target(
    outlines: Iterable[Any],
    chapters: Iterable[Any],
) -> dict[str, Any]:
    """返回大纲顺序中第一个尚无正文的章节节点。

    已关联 `outline_id` 的章节是权威身份；仅为旧数据保留按章号关联的回退。
    一个大纲节点已有正文时，不因同时存在空白重复草稿而重新生成覆盖。
    """
    chapter_outlines = [
        item for item in outlines
        if _field(item, "node_type", "chapter") == "chapter"
    ]
    chapter_outlines.sort(key=lambda item: (
        _field(item, "chapter_no") is None,
        _field(item, "chapter_no") if _field(item, "chapter_no") is not None else 0,
        _field(item, "sort_index", 0) or 0,
        _field(item, "id", 0) or 0,
    ))
    chapter_rows = list(chapters)
    number_counts: dict[int, int] = {}
    for outline in chapter_outlines:
        number = _field(outline, "chapter_no")
        if number is not None:
            number_counts[int(number)] = number_counts.get(int(number), 0) + 1

    for position, outline in enumerate(chapter_outlines, start=1):
        outline_id = _field(outline, "id")
        chapter_no = _field(outline, "chapter_no")
        linked = [row for row in chapter_rows if _field(row, "outline_id") == outline_id]

        # 老章节可能还没有 outline_id；只有章号唯一时才用章号回填匹配。
        if not linked and chapter_no is not None and number_counts.get(int(chapter_no)) == 1:
            linked = [
                row for row in chapter_rows
                if _field(row, "outline_id") is None
                and _field(row, "chapter_no") == chapter_no
            ]

        if any(str(_field(row, "content", "") or "").strip() for row in linked):
            continue

        blank_rows = sorted(linked, key=lambda row: _field(row, "id", 0) or 0, reverse=True)
        blank_chapter_id = _field(blank_rows[0], "id") if blank_rows else None
        return {
            "available": True,
            "reason": "",
            "outline_id": outline_id,
            "chapter_no": int(chapter_no) if chapter_no is not None else position,
            "outline_title": str(_field(outline, "title", "") or ""),
            "instruction": str(_field(outline, "description", "") or ""),
            "chapter_id": blank_chapter_id,
            "chapter_title": str(_field(blank_rows[0], "title", "") or "") if blank_rows else "",
            "position": position,
            "total_outlines": len(chapter_outlines),
        }

    reason = (
        "当前没有已保存的章节大纲，请先补充章节大纲。"
        if not chapter_outlines
        else "当前大纲中的章节都已有正文，请先补充下一章大纲。"
    )
    return {
        "available": False,
        "reason": reason,
        "outline_id": None,
        "chapter_no": None,
        "outline_title": "",
        "instruction": "",
        "chapter_id": None,
        "chapter_title": "",
        "position": None,
        "total_outlines": len(chapter_outlines),
    }


def get_project_next_chapter_target(project_id: int) -> dict[str, Any]:
    """从数据库读取项目大纲和章节，解析唯一的新稿目标。"""
    from app.db.session import get_business_db
    from app.models.business import Chapter, Outline

    with get_business_db() as db:
        outlines = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "chapter",
        ).all()
        chapters = db.query(Chapter).filter(Chapter.project_id == project_id).all()
        return resolve_next_chapter_target(outlines, chapters)


def require_next_chapter_target(
    project_id: int,
    outline_id: int | None,
    chapter_no: int,
    chapter_id: int | None = None,
) -> dict[str, Any]:
    """验证生成请求仍指向当前下一章，并返回后端解析出的规范目标。"""
    target = get_project_next_chapter_target(project_id)
    if not target["available"]:
        raise HTTPException(status_code=409, detail=target["reason"])

    same_outline = outline_id == target["outline_id"]
    same_number = chapter_no == target["chapter_no"]
    same_blank_draft = chapter_id is None or chapter_id == target["chapter_id"]
    if not (same_outline and same_number and same_blank_draft):
        raise HTTPException(
            status_code=409,
            detail="大纲顺序或下一章目标已变化，请刷新资料后重新生成。",
        )
    return target


def resolve_chapter_generation_target(
    outlines: Iterable[Any],
    chapters: Iterable[Any],
    outline_id: int | None,
    chapter_no: int,
    chapter_id: int | None = None,
) -> dict[str, Any]:
    """验证作者当前选中的章节生成目标，允许空章初稿和已有章节重生成。"""
    chapter_outlines = [
        item for item in outlines
        if _field(item, "node_type", "chapter") == "chapter"
    ]
    chapter_outlines.sort(key=lambda item: (
        _field(item, "chapter_no") is None,
        _field(item, "chapter_no") if _field(item, "chapter_no") is not None else 0,
        _field(item, "sort_index", 0) or 0,
        _field(item, "id", 0) or 0,
    ))
    if outline_id is None:
        raise HTTPException(status_code=422, detail="请先选择单章细纲再生成正文。")

    outline = next((item for item in chapter_outlines if _field(item, "id") == outline_id), None)
    if outline is None:
        raise HTTPException(status_code=409, detail="当前章节细纲已不存在或已调整，请刷新后重新选择。")

    position = chapter_outlines.index(outline) + 1
    outline_no = _field(outline, "chapter_no")
    canonical_no = int(outline_no) if outline_no is not None else position
    if int(chapter_no) != canonical_no:
        raise HTTPException(status_code=409, detail="章节顺序已调整，请刷新资料后重新生成。")

    chapter_rows = list(chapters)
    same_number_outlines = [
        item for item in chapter_outlines
        if _field(item, "chapter_no") == outline_no
    ]
    linked = [row for row in chapter_rows if _field(row, "outline_id") == outline_id]
    if not linked and len(same_number_outlines) == 1:
        linked = [
            row for row in chapter_rows
            if _field(row, "outline_id") is None
            and _field(row, "chapter_no") == canonical_no
        ]

    selected_chapter = None
    if chapter_id is not None:
        selected_chapter = next(
            (row for row in chapter_rows if _field(row, "id") == chapter_id),
            None,
        )
        if selected_chapter is None:
            raise HTTPException(status_code=404, detail="当前章节不存在或不属于此项目，请刷新后重试。")
        if selected_chapter not in linked:
            raise HTTPException(status_code=409, detail="所选章节与当前细纲不匹配，请刷新后重新选择。")
    else:
        if any(str(_field(row, "content", "") or "").strip() for row in linked):
            raise HTTPException(
                status_code=409,
                detail="本章已有正文，请刷新资料并选择当前章节后再重新生成。",
            )
        blank_rows = sorted(linked, key=lambda row: _field(row, "id", 0) or 0, reverse=True)
        selected_chapter = blank_rows[0] if blank_rows else None

    return {
        "available": True,
        "outline_id": outline_id,
        "chapter_no": canonical_no,
        "outline_title": str(_field(outline, "title", "") or ""),
        "instruction": str(_field(outline, "description", "") or ""),
        "chapter_id": _field(selected_chapter, "id") if selected_chapter else None,
        "chapter_title": str(_field(selected_chapter, "title", "") or "") if selected_chapter else "",
        "position": position,
        "total_outlines": len(chapter_outlines),
    }


def require_chapter_generation_target(
    project_id: int,
    outline_id: int | None,
    chapter_no: int,
    chapter_id: int | None = None,
) -> dict[str, Any]:
    """从项目资料核验当前章节目标；生成初稿与重生成使用同一规则。"""
    from app.db.session import get_business_db
    from app.models.business import Chapter, Outline

    with get_business_db() as db:
        outlines = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "chapter",
        ).all()
        chapters = db.query(Chapter).filter(Chapter.project_id == project_id).all()
        return resolve_chapter_generation_target(
            outlines,
            chapters,
            outline_id,
            chapter_no,
            chapter_id,
        )
