from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    password: str = Field(..., min_length=1, max_length=128, description="密码")


class LoginResponse(BaseModel):
    """登录响应。"""

    success: bool = Field(description="是否成功")
    message: str = Field(default="", description="提示信息")
    user: Optional["UserProfileResponse"] = Field(default=None, description="用户信息")


class UserProfileResponse(BaseModel):
    """用户信息响应。"""

    id: int
    username: str
    nickname: str
    email: str
    avatar: str
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """更新用户信息请求。"""

    nickname: Optional[str] = Field(default=None, max_length=64, description="昵称")
    email: Optional[str] = Field(default=None, max_length=128, description="邮箱")
    avatar: Optional[str] = Field(default=None, max_length=255, description="头像URL")
    password: Optional[str] = Field(default=None, min_length=1, max_length=128, description="新密码")


LoginResponse.model_rebuild()
