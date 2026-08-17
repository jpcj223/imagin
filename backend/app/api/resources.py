from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.repository import delete_row, fetch_all, insert_row, update_row
from app.db.session import get_business_db
from app.models.business import (
    Chapter,
    Character,
    Foreshadowing,
    Organization,
    Outline,
    WorldSetting,
)
from app.schemas.models import (
    CharacterSave,
    ChapterSave,
    ForeshadowingSave,
    OrganizationSave,
    OutlineSave,
    WorldSettingSave,
)


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


@router.get("/{project_id}/{resource}")
def list_resource(project_id: int, resource: str) -> list[dict]:
    """按项目读取某一类创作资料列表。"""
    table = _resource_table(resource)
    return fetch_all(table, project_id)


@router.post("/world")
def save_world(payload: WorldSettingSave) -> dict:
    """新增世界观设定。"""
    return insert_row("world_settings", payload.model_dump())


@router.post("/outlines")
def save_outline(payload: OutlineSave) -> dict:
    """新增大纲节点。"""
    return insert_row("outlines", payload.model_dump())


@router.post("/chapters")
def save_chapter(payload: ChapterSave) -> dict:
    """新增章节草稿。"""
    return insert_row("chapters", payload.model_dump())


@router.post("/characters")
def save_character(payload: CharacterSave) -> dict:
    """新增角色卡。"""
    return insert_row("characters", payload.model_dump())


@router.post("/organizations")
def save_organization(payload: OrganizationSave) -> dict:
    """新增组织势力。"""
    return insert_row("organizations", payload.model_dump())


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

    return chapter_no


@router.post("/foreshadowings")
def save_foreshadowing(payload: ForeshadowingSave) -> dict:
    """新增伏笔记录。"""
    return insert_row("foreshadowings", payload.model_dump())


@router.put("/{resource}/{item_id}")
def update_resource(resource: str, item_id: int, payload: dict) -> dict:
    """更新某一条创作资料。

    resource 先经过白名单映射，payload 只包含前端提交的业务字段。
    """
    table = _resource_table(resource)
    updated = update_row(table, item_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="资源不存在")
    return updated


@router.delete("/{resource}/{item_id}")
def delete_resource(resource: str, item_id: int) -> dict:
    """删除资源。

    resource 只允许映射表中的业务资源名，避免前端把任意表名传进来。
    删除章节或卷后自动重新编号。
    """
    table = _resource_table(resource)

    # 如果删除的是章节或卷，先获取 project_id 和 node_type 用于后续重编号
    project_id = None
    node_type = None
    if table == "outlines":
        with get_business_db() as db:
            item = db.query(Outline).filter(Outline.id == item_id).first()
            if item:
                project_id = item.project_id
                node_type = item.node_type

    delete_row(table, item_id)

    # 删除章节或卷后自动重新编号
    if project_id and node_type in ("chapter", "volume"):
        with get_business_db() as db:
            if node_type == "volume":
                # 删除卷：先重排卷号，再重排章节号
                _renumber_all_volumes(db, project_id)
            _renumber_all_chapters(db, project_id)
            db.commit()

    return {"ok": True, "id": item_id}


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
