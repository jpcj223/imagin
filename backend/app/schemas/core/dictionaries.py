from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 字典（分类）
# ---------------------------------------------------------------------------
class DictionaryBase(BaseModel):
    """字典基础字段。"""

    dict_code: str = Field(..., min_length=1, max_length=64, description="字典编码")
    dict_name: str = Field(..., min_length=1, max_length=128, description="字典名称")
    description: str = Field(default="", max_length=255, description="描述")
    sort_order: int = Field(default=0, description="排序")
    status: str = Field(default="active", max_length=16, description="状态: active/disabled")


class DictionaryCreate(DictionaryBase):
    """创建字典请求。"""
    pass


class DictionaryUpdate(BaseModel):
    """更新字典请求（支持局部更新）。"""

    dict_code: Optional[str] = Field(default=None, max_length=64, description="字典编码")
    dict_name: Optional[str] = Field(default=None, max_length=128, description="字典名称")
    description: Optional[str] = Field(default=None, max_length=255, description="描述")
    sort_order: Optional[int] = Field(default=None, description="排序")
    status: Optional[str] = Field(default=None, max_length=16, description="状态")


class DictionaryResponse(DictionaryBase):
    """字典响应。"""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# 字典项
# ---------------------------------------------------------------------------
class DictItemBase(BaseModel):
    """字典项基础字段。"""

    item_label: str = Field(..., min_length=1, max_length=128, description="显示标签")
    item_value: str = Field(..., min_length=1, max_length=128, description="存储值")
    sort_order: int = Field(default=0, description="排序")
    status: str = Field(default="active", max_length=16, description="状态: active/disabled")
    remark: str = Field(default="", max_length=255, description="备注")


class DictItemCreate(DictItemBase):
    """创建字典项请求。"""
    pass


class DictItemUpdate(BaseModel):
    """更新字典项请求（支持局部更新）。"""

    item_label: Optional[str] = Field(default=None, max_length=128, description="显示标签")
    item_value: Optional[str] = Field(default=None, max_length=128, description="存储值")
    sort_order: Optional[int] = Field(default=None, description="排序")
    status: Optional[str] = Field(default=None, max_length=16, description="状态")
    remark: Optional[str] = Field(default=None, max_length=255, description="备注")


class DictItemResponse(DictItemBase):
    """字典项响应。"""

    id: int
    dict_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
