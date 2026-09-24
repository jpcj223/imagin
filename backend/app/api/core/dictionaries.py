from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_core_db_depends
from app.models.core import SysDictItem, SysDictionary
from app.schemas.core import (
    DictItemCreate,
    DictItemReorderRequest,
    DictItemResponse,
    DictItemUpdate,
    DictionaryCreate,
    DictionaryReorderRequest,
    DictionaryResponse,
    DictionaryUpdate,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# 字典管理
# ---------------------------------------------------------------------------
@router.get("", response_model=list[DictionaryResponse])
def list_dictionaries(
    status: str | None = None,
    db: Session = Depends(get_core_db_depends),
) -> list[DictionaryResponse]:
    """获取字典列表。"""
    query = db.query(SysDictionary)
    if status:
        query = query.filter(SysDictionary.status == status)
    dictionaries = query.order_by(SysDictionary.sort_order, SysDictionary.id).all()
    return [DictionaryResponse.model_validate(d) for d in dictionaries]


@router.post("/reorder", response_model=list[DictionaryResponse])
def reorder_dictionaries(
    payload: DictionaryReorderRequest,
    db: Session = Depends(get_core_db_depends),
) -> list[DictionaryResponse]:
    """按前端拖动后的顺序保存全部字典。"""
    # 第一步：检查 ID 唯一，避免重复项导致排序结果不确定。
    if len(payload.ids) != len(set(payload.ids)):
        raise HTTPException(status_code=400, detail="字典排序包含重复项")

    # 第二步：要求请求覆盖当前全部字典，防止局部列表覆盖其他顺序。
    dictionaries = db.query(SysDictionary).all()
    dictionary_by_id = {dictionary.id: dictionary for dictionary in dictionaries}
    if set(payload.ids) != set(dictionary_by_id):
        raise HTTPException(status_code=400, detail="字典排序数据已变化，请刷新后重试")

    # 第三步：按拖动后的顺序写入间隔序号，便于后续插入新字典。
    for index, dictionary_id in enumerate(payload.ids, start=1):
        dictionary_by_id[dictionary_id].sort_order = index * 10

    # 第四步：统一提交并返回最新顺序。
    db.commit()
    ordered = sorted(dictionaries, key=lambda dictionary: (dictionary.sort_order, dictionary.id))
    return [DictionaryResponse.model_validate(dictionary) for dictionary in ordered]


@router.get("/{dict_code}/items", response_model=list[DictItemResponse])
def get_dict_items(
    dict_code: str,
    include_inactive: bool = False,
    db: Session = Depends(get_core_db_depends),
) -> list[DictItemResponse]:
    """获取字典项；管理页可选择同时读取停用项。"""
    dictionary = db.query(SysDictionary).filter(SysDictionary.dict_code == dict_code).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="字典不存在")

    # 普通业务读取只返回启用项；字典管理页需要读取全部状态以便维护。
    query = db.query(SysDictItem).filter(SysDictItem.dict_id == dictionary.id)
    if not include_inactive:
        query = query.filter(SysDictItem.status == "active")
    items = query.order_by(SysDictItem.sort_order, SysDictItem.id).all()
    return [DictItemResponse.model_validate(item) for item in items]


@router.post("/{dict_id}/items/reorder", response_model=list[DictItemResponse])
def reorder_dict_items(
    dict_id: int,
    payload: DictItemReorderRequest,
    db: Session = Depends(get_core_db_depends),
) -> list[DictItemResponse]:
    """在指定字典内按卡片拖动后的顺序保存字典项。"""
    # 第一步：确认目标字典存在，并检查请求中没有重复 ID。
    dictionary = db.query(SysDictionary).filter(SysDictionary.id == dict_id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="字典不存在")
    if len(payload.ids) != len(set(payload.ids)):
        raise HTTPException(status_code=400, detail="字典项排序包含重复项")

    # 第二步：仅允许对当前字典的完整字典项列表排序。
    items = db.query(SysDictItem).filter(SysDictItem.dict_id == dict_id).all()
    item_by_id = {item.id: item for item in items}
    if set(payload.ids) != set(item_by_id):
        raise HTTPException(status_code=400, detail="字典项排序数据已变化，请刷新后重试")

    # 第三步：按目标位置写入间隔序号，并一次性提交。
    for index, item_id in enumerate(payload.ids, start=1):
        item_by_id[item_id].sort_order = index * 10
    db.commit()

    # 第四步：返回保存后的卡片顺序，供前端同步状态。
    ordered = sorted(items, key=lambda item: (item.sort_order, item.id))
    return [DictItemResponse.model_validate(item) for item in ordered]


@router.post("", response_model=DictionaryResponse)
def create_dictionary(
    payload: DictionaryCreate,
    db: Session = Depends(get_core_db_depends),
) -> DictionaryResponse:
    """新增字典。"""
    # 检查编码是否已存在
    existing = db.query(SysDictionary).filter(SysDictionary.dict_code == payload.dict_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="字典编码已存在")

    dictionary = SysDictionary(**payload.model_dump())
    db.add(dictionary)
    db.commit()
    db.refresh(dictionary)
    return DictionaryResponse.model_validate(dictionary)


@router.put("/{dict_id}", response_model=DictionaryResponse)
def update_dictionary(
    dict_id: int,
    payload: DictionaryUpdate,
    db: Session = Depends(get_core_db_depends),
) -> DictionaryResponse:
    """更新字典。"""
    dictionary = db.query(SysDictionary).filter(SysDictionary.id == dict_id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="字典不存在")

    # 如果修改了编码，检查是否冲突
    update_data = payload.model_dump(exclude_unset=True)
    if "dict_code" in update_data and update_data["dict_code"] != dictionary.dict_code:
        existing = db.query(SysDictionary).filter(
            SysDictionary.dict_code == update_data["dict_code"],
            SysDictionary.id != dict_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="字典编码已存在")

    for key, value in update_data.items():
        setattr(dictionary, key, value)

    db.commit()
    db.refresh(dictionary)
    return DictionaryResponse.model_validate(dictionary)


@router.delete("/{dict_id}")
def delete_dictionary(
    dict_id: int,
    db: Session = Depends(get_core_db_depends),
) -> dict:
    """删除字典（级联删除字典项）。"""
    dictionary = db.query(SysDictionary).filter(SysDictionary.id == dict_id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="字典不存在")

    # 先删除字典项
    db.query(SysDictItem).filter(SysDictItem.dict_id == dict_id).delete()
    db.delete(dictionary)
    db.commit()
    return {"success": True}


# ---------------------------------------------------------------------------
# 字典项管理
# ---------------------------------------------------------------------------
@router.post("/{dict_id}/items", response_model=DictItemResponse)
def create_dict_item(
    dict_id: int,
    payload: DictItemCreate,
    db: Session = Depends(get_core_db_depends),
) -> DictItemResponse:
    """新增字典项。"""
    dictionary = db.query(SysDictionary).filter(SysDictionary.id == dict_id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="字典不存在")

    item = SysDictItem(dict_id=dict_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return DictItemResponse.model_validate(item)


@router.put("/dict-items/{item_id}", response_model=DictItemResponse)
def update_dict_item(
    item_id: int,
    payload: DictItemUpdate,
    db: Session = Depends(get_core_db_depends),
) -> DictItemResponse:
    """更新字典项。"""
    item = db.query(SysDictItem).filter(SysDictItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="字典项不存在")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return DictItemResponse.model_validate(item)


@router.delete("/dict-items/{item_id}")
def delete_dict_item(
    item_id: int,
    db: Session = Depends(get_core_db_depends),
) -> dict:
    """删除字典项。"""
    item = db.query(SysDictItem).filter(SysDictItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="字典项不存在")

    db.delete(item)
    db.commit()
    return {"success": True}
