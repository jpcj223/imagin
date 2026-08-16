from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelConfigBase(BaseModel):
    """模型配置基础字段。"""

    name: str = Field(default="默认模型", max_length=128, description="配置名称")
    base_url: str = Field(..., max_length=255, description="API 地址")
    api_key: str = Field(..., max_length=255, description="API Key")
    model: str = Field(..., max_length=128, description="模型名称")
    is_active: bool = Field(default=False, description="是否启用")
    temperature: Optional[float] = Field(default=None, ge=0, le=2, description="采样温度 0-2")
    max_tokens: Optional[int] = Field(default=None, gt=0, description="最大输出 token 数")
    top_p: Optional[float] = Field(default=None, ge=0, le=1, description="nucleus 采样 0-1")
    frequency_penalty: Optional[float] = Field(default=None, ge=-2, le=2, description="频率惩罚 -2到2")
    presence_penalty: Optional[float] = Field(default=None, ge=-2, le=2, description="存在惩罚 -2到2")
    proxy_url: Optional[str] = Field(default=None, max_length=255, description="HTTP 代理地址")


class ModelConfigCreate(ModelConfigBase):
    """创建模型配置请求。"""
    pass


class ModelConfigUpdate(BaseModel):
    """更新模型配置请求（支持局部更新）。"""

    name: Optional[str] = Field(default=None, max_length=128, description="配置名称")
    base_url: Optional[str] = Field(default=None, max_length=255, description="API 地址")
    api_key: Optional[str] = Field(default=None, max_length=255, description="API Key")
    model: Optional[str] = Field(default=None, max_length=128, description="模型名称")
    is_active: Optional[bool] = Field(default=None, description="是否启用")
    temperature: Optional[float] = Field(default=None, ge=0, le=2, description="采样温度 0-2")
    max_tokens: Optional[int] = Field(default=None, gt=0, description="最大输出 token 数")
    top_p: Optional[float] = Field(default=None, ge=0, le=1, description="nucleus 采样 0-1")
    frequency_penalty: Optional[float] = Field(default=None, ge=-2, le=2, description="频率惩罚 -2到2")
    presence_penalty: Optional[float] = Field(default=None, ge=-2, le=2, description="存在惩罚 -2到2")
    proxy_url: Optional[str] = Field(default=None, max_length=255, description="HTTP 代理地址")


class ModelConfigResponse(ModelConfigBase):
    """模型配置响应。"""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
