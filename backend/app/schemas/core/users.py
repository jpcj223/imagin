from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """新增用户请求。"""

    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    password: str = Field(..., min_length=1, max_length=128, description="密码")
    nickname: Optional[str] = Field(default="", max_length=64, description="昵称")
    email: Optional[str] = Field(default="", max_length=128, description="邮箱")
    role: Optional[str] = Field(default="user", description="角色: admin/user")
    status: Optional[str] = Field(default="active", description="状态: active/disabled")


class UserUpdate(BaseModel):
    """更新用户请求。"""

    nickname: Optional[str] = Field(default=None, max_length=64, description="昵称")
    email: Optional[str] = Field(default=None, max_length=128, description="邮箱")
    role: Optional[str] = Field(default=None, description="角色: admin/user")
    status: Optional[str] = Field(default=None, description="状态: active/disabled")
    password: Optional[str] = Field(default=None, min_length=1, max_length=128, description="新密码")
