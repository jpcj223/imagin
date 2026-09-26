"""大纲卷章排序与编号路由。"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import func

from app.db.session import get_business_db
from app.models.business import Outline
from .common import (
    _link_legacy_chapters_to_outlines,
    _renumber_all_chapters,
    _sync_linked_chapter_numbers,
)

router = APIRouter()

@router.post("/outlines/renumber")
def renumber_outlines(payload: dict) -> dict:
    """重新排列章节号。

    按卷的顺序 + 卷内 sort_index 排序，重新分配连续的 chapter_no。
    body: { project_id, volume_id: 可选，只重排某卷；不传则重排所有 }
    """
    project_id = payload.get("project_id")
    volume_id = payload.get("volume_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="缺少 project_id")

    with get_business_db() as db:
        _link_legacy_chapters_to_outlines(db, project_id)
        # 先获取所有卷，按 volume_no 排序
        volumes = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "volume"
        ).order_by(Outline.volume_no).all()

        # 如果指定了 volume_id，只排那卷
        if volume_id:
            volumes = [v for v in volumes if v.id == volume_id]
            if not volumes:
                raise HTTPException(status_code=404, detail="卷不存在")

        # 全局章号计数器
        chapter_no = 0

        # 先计算起始章号（如果只重排某卷，需要知道前面有多少章）
        if volume_id:
            # 找到该卷之前的所有章节数
            target_idx = None
            for i, v in enumerate(volumes):
                if v.id == volume_id:
                    target_idx = i
                    break
            # 计算前面所有卷的章节总数
            all_volumes = db.query(Outline).filter(
                Outline.project_id == project_id,
                Outline.node_type == "volume"
            ).order_by(Outline.volume_no).all()
            before_count = 0
            for v in all_volumes:
                if v.id == volume_id:
                    break
                cnt = db.query(Outline).filter(
                    Outline.project_id == project_id,
                    Outline.node_type == "chapter",
                    Outline.volume_id == v.id
                ).count()
                before_count += cnt
            chapter_no = before_count
            # 只处理目标卷
            volumes_to_process = [v for v in all_volumes if v.id == volume_id]
        else:
            volumes_to_process = volumes

        for vol in volumes_to_process:
            chapters = db.query(Outline).filter(
                Outline.project_id == project_id,
                Outline.node_type == "chapter",
                Outline.volume_id == vol.id
            ).order_by(Outline.sort_index, Outline.chapter_no).all()

            for ch in chapters:
                chapter_no += 1
                ch.chapter_no = chapter_no
                ch.sort_index = chapter_no

        _sync_linked_chapter_numbers(db, project_id)
        db.commit()

    return {"ok": True, "chapter_no": chapter_no}


@router.post("/outlines/reorder-volume")
def reorder_volume(payload: dict) -> dict:
    """调整卷顺序。

    body: { source_id, target_id, position: 'before'|'after' }
    调整后按新顺序更新 volume_no，然后重新生成章节号。
    """
    source_id = payload.get("source_id")
    target_id = payload.get("target_id")
    position = payload.get("position", "after")
    if not source_id or not target_id or source_id == target_id:
        raise HTTPException(status_code=400, detail="参数错误")

    with get_business_db() as db:
        source = db.query(Outline).filter(Outline.id == source_id, Outline.node_type == "volume").first()
        target = db.query(Outline).filter(Outline.id == target_id, Outline.node_type == "volume").first()
        if not source or not target:
            raise HTTPException(status_code=404, detail="卷不存在")
        if source.project_id != target.project_id:
            raise HTTPException(status_code=400, detail="不能跨项目移动")

        project_id = source.project_id
        _link_legacy_chapters_to_outlines(db, project_id)

        # 获取所有卷，按当前 volume_no 排序
        volumes = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "volume"
        ).order_by(Outline.volume_no).all()

        # 把 source 从列表中移除
        volume_list = [v for v in volumes if v.id != source_id]

        # 找到 target 的新位置
        target_idx = next(i for i, v in enumerate(volume_list) if v.id == target_id)
        insert_idx = target_idx if position == "before" else target_idx + 1

        # 插入到新位置
        volume_list.insert(insert_idx, source)

        # 重新分配 volume_no
        for i, v in enumerate(volume_list):
            v.volume_no = i + 1

        # 重新排列章节号
        chapter_no = 0
        for vol in volume_list:
            chapters = db.query(Outline).filter(
                Outline.project_id == project_id,
                Outline.node_type == "chapter",
                Outline.volume_id == vol.id
            ).order_by(Outline.sort_index, Outline.chapter_no).all()
            for ch in chapters:
                chapter_no += 1
                ch.chapter_no = chapter_no
                ch.sort_index = chapter_no

        _sync_linked_chapter_numbers(db, project_id)
        db.commit()

    return {"ok": True}


@router.post("/outlines/reorder-chapter")
def reorder_chapter(payload: dict) -> dict:
    """调整章节顺序（同卷或跨卷）。

    body: { source_id, target_id, position: 'before'|'after' }
    调整后自动重新编号。
    """
    source_id = payload.get("source_id")
    target_id = payload.get("target_id")
    position = payload.get("position", "after")
    if not source_id or not target_id or source_id == target_id:
        raise HTTPException(status_code=400, detail="参数错误")

    with get_business_db() as db:
        source = db.query(Outline).filter(Outline.id == source_id, Outline.node_type == "chapter").first()
        target = db.query(Outline).filter(Outline.id == target_id, Outline.node_type == "chapter").first()
        if not source or not target:
            raise HTTPException(status_code=404, detail="章节不存在")
        if source.project_id != target.project_id:
            raise HTTPException(status_code=400, detail="不能跨项目移动")

        project_id = source.project_id
        _link_legacy_chapters_to_outlines(db, project_id)
        target_volume_id = target.volume_id

        # 获取目标卷的所有章节，按 sort_index 排序
        chapters = db.query(Outline).filter(
            Outline.project_id == project_id,
            Outline.node_type == "chapter",
            Outline.volume_id == target_volume_id
        ).order_by(Outline.sort_index).all()

        # 如果源章节也在目标卷，先移除；否则后面统一处理
        chapter_list = [c for c in chapters if c.id != source_id]

        # 找到 target 的位置
        target_idx = next(i for i, c in enumerate(chapter_list) if c.id == target_id)
        insert_idx = target_idx if position == "before" else target_idx + 1

        # 如果源章节不在目标卷，先修改它的 volume_id
        if source.volume_id != target_volume_id:
            source.volume_id = target_volume_id

        # 插入到新位置
        chapter_list.insert(insert_idx, source)

        # 先给目标卷内章节重新排 sort_index
        for i, ch in enumerate(chapter_list):
            ch.sort_index = i + 1

        db.commit()

        # 全局重新编号
        _renumber_all_chapters(db, project_id)
        db.commit()

    return {"ok": True}


@router.post("/outlines/move-chapter")
def move_chapter(payload: dict) -> dict:
    """移动章节到指定卷末尾。

    body: { chapter_id, volume_id }
    移动后自动重新编号。
    """
    chapter_id = payload.get("chapter_id")
    volume_id = payload.get("volume_id")
    if not chapter_id or not volume_id:
        raise HTTPException(status_code=400, detail="参数错误")

    with get_business_db() as db:
        chapter = db.query(Outline).filter(Outline.id == chapter_id, Outline.node_type == "chapter").first()
        volume = db.query(Outline).filter(Outline.id == volume_id, Outline.node_type == "volume").first()
        if not chapter or not volume:
            raise HTTPException(status_code=404, detail="章节或卷不存在")
        if chapter.project_id != volume.project_id:
            raise HTTPException(status_code=400, detail="不能跨项目移动")

        project_id = chapter.project_id
        _link_legacy_chapters_to_outlines(db, project_id)

        # 修改所属卷
        chapter.volume_id = volume_id

        # 获取目标卷最大 sort_index
        max_sort = db.query(func.max(Outline.sort_index)).filter(
            Outline.project_id == project_id,
            Outline.node_type == "chapter",
            Outline.volume_id == volume_id
        ).scalar() or 0
        chapter.sort_index = max_sort + 1

        db.commit()

        # 全局重新编号
        _renumber_all_chapters(db, project_id)
        db.commit()

    return {"ok": True}
