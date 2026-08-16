from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_core_db_depends
from app.models.core import SysUser
from app.schemas.core import (
    LoginRequest,
    LoginResponse,
    UserProfileResponse,
    UserProfileUpdate,
)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_core_db_depends),
) -> LoginResponse:
    """用户登录（简化版，验证用户名密码）。"""
    user = db.query(SysUser).filter(SysUser.username == payload.username).first()
    if not user:
        return LoginResponse(success=False, message="用户名或密码错误")

    # 简化版：直接对比明文密码（种子数据用明文存储）
    # 生产环境应使用密码哈希
    if user.password_hash != payload.password:
        return LoginResponse(success=False, message="用户名或密码错误")

    if user.status != "active":
        return LoginResponse(success=False, message="账号已被禁用")

    return LoginResponse(
        success=True,
        message="登录成功",
        user=UserProfileResponse.model_validate(user),
    )


@router.get("/profile", response_model=UserProfileResponse)
def get_profile(
    user_id: int = 1,  # 简化版：默认取第一个用户，后续接入真实认证
    db: Session = Depends(get_core_db_depends),
) -> UserProfileResponse:
    """获取当前用户信息。"""
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserProfileResponse.model_validate(user)


@router.put("/profile", response_model=UserProfileResponse)
def update_profile(
    payload: UserProfileUpdate,
    user_id: int = 1,  # 简化版：默认取第一个用户
    db: Session = Depends(get_core_db_depends),
) -> UserProfileResponse:
    """更新用户信息。"""
    user = db.query(SysUser).filter(SysUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    update_data = payload.model_dump(exclude_unset=True)

    # 如果更新密码，单独处理
    if "password" in update_data:
        new_password = update_data.pop("password")
        user.password_hash = new_password

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return UserProfileResponse.model_validate(user)
