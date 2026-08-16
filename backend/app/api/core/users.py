from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_core_db_depends
from app.models.core import SysUser
from app.schemas.core import UserProfileResponse
from app.schemas.core.users import UserCreate, UserUpdate

router = APIRouter()


@router.get("", response_model=list[UserProfileResponse])
def list_users(
    status: str | None = None,
    db: Session = Depends(get_core_db_depends),
) -> list[UserProfileResponse]:
    """获取用户列表。"""
    query = db.query(SysUser)
    if status:
        query = query.filter(SysUser.status == status)
    users = query.order_by(SysUser.id.desc()).all()
    return [UserProfileResponse.model_validate(u) for u in users]


@router.post("", response_model=UserProfileResponse)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_core_db_depends),
) -> UserProfileResponse:
    """新增用户。"""
    existing = db.query(SysUser).filter(SysUser.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    data = payload.model_dump()
    password = data.pop("password")
    data["password_hash"] = password

    user = SysUser(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserProfileResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserProfileResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_core_db_depends),
) -> UserProfileResponse:
    """更新用户。"""
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    update_data = payload.model_dump(exclude_unset=True)

    if "password" in update_data:
        password = update_data.pop("password")
        user.password_hash = password

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return UserProfileResponse.model_validate(user)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_core_db_depends),
) -> dict:
    """删除用户。"""
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    db.delete(user)
    db.commit()
    return {"success": True}
