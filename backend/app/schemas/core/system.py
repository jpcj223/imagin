from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SysConfigResponse(BaseModel):
    """系统配置响应。"""

    id: int
    config_key: str
    config_value: str
    config_name: str
    description: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class SysConfigUpdate(BaseModel):
    """更新系统配置请求。"""

    config_value: str = Field(default="", description="配置值")
    config_name: Optional[str] = Field(default=None, max_length=128, description="配置名称")
    description: Optional[str] = Field(default=None, max_length=255, description="描述")
