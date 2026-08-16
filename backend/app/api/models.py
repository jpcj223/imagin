"""模型配置 API（核心库）。

model_configs 表已从业务库迁移到核心库，本文件内部使用核心库会话，
对外保持原有接口不变，确保上层调用零改动。
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import inspect

from app.core.llm import LLMError, chat_completion
from app.db.session import get_core_db
from app.models.core.model_config import ModelConfig
from app.schemas.models import ModelConfigCreate


router = APIRouter()


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------
def _config_to_dict(obj: ModelConfig | None) -> dict | None:
    """将 ModelConfig ORM 对象转换为普通 dict，处理 datetime 序列化。"""
    if obj is None:
        return None
    result: dict = {}
    for col in inspect(obj).mapper.column_attrs:
        value = getattr(obj, col.key)
        if isinstance(value, datetime):
            result[col.key] = value.isoformat() if value else None
        else:
            result[col.key] = value
    return result


# ---------------------------------------------------------------------------
# API 路由
# ---------------------------------------------------------------------------
@router.get("")
def list_model_configs() -> list[dict]:
    """列出所有模型配置，按创建时间倒序（最新的在前）。"""
    with get_core_db() as db:
        configs = db.query(ModelConfig).order_by(ModelConfig.id.desc()).all()
    return [_config_to_dict(c) for c in configs]


@router.get("/active")
def get_active_config() -> dict | None:
    """获取当前启用的配置。"""
    with get_core_db() as db:
        config = db.query(ModelConfig).filter(ModelConfig.is_active == 1).first()
    return _config_to_dict(config)


@router.get("/{config_id}")
def get_model_config(config_id: int) -> dict:
    """获取单条配置详情。"""
    with get_core_db() as db:
        config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return _config_to_dict(config)


@router.post("")
def save_model_config(payload: ModelConfigCreate) -> dict:
    """新建配置；is_active 为 True 时会自动取消其他配置的激活状态。"""
    data = payload.model_dump()
    data["is_active"] = 1 if data["is_active"] else 0

    with get_core_db() as db:
        if data["is_active"]:
            db.query(ModelConfig).update({ModelConfig.is_active: 0})
        config = ModelConfig(**data)
        db.add(config)
        db.commit()
        db.refresh(config)
    return _config_to_dict(config)


@router.put("/{config_id}")
def update_model_config(config_id: int, payload: ModelConfigCreate) -> dict:
    """更新配置；如果把 is_active 设为 True，会自动取消其他配置的激活状态。"""
    with get_core_db() as db:
        config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")

        data = payload.model_dump(exclude_unset=True)
        # 如果传了 is_active，转换为 0/1
        if "is_active" in data:
            data["is_active"] = 1 if data["is_active"] else 0
            if data["is_active"]:
                db.query(ModelConfig).update({ModelConfig.is_active: 0})
                db.flush()

        for key, value in data.items():
            setattr(config, key, value)
        db.commit()
        db.refresh(config)
        return _config_to_dict(config)


@router.post("/{config_id}/activate")
def activate_config(config_id: int) -> dict:
    """将指定配置设为当前启用（其他配置自动取消激活）。"""
    with get_core_db() as db:
        config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")
        # 取消所有激活
        db.query(ModelConfig).update({ModelConfig.is_active: 0})
        # 激活指定配置
        config.is_active = 1
        db.commit()
        db.refresh(config)
    return _config_to_dict(config)


@router.delete("/{config_id}")
def delete_model_config(config_id: int) -> dict:
    """删除配置。如果删除的是当前启用的配置，会自动把最新的一条设为启用。"""
    with get_core_db() as db:
        config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")

        was_active = config.is_active == 1
        db.delete(config)
        db.commit()

        # 如果删的是 active 配置，把最新的一条设为 active
        if was_active:
            latest = db.query(ModelConfig).order_by(ModelConfig.id.desc()).first()
            if latest:
                latest.is_active = 1
                db.commit()

    return {"success": True}


@router.post("/test")
def test_model_connection() -> dict:
    """测试当前启用的模型配置是否能完成一次最小聊天请求。"""
    try:
        content = chat_completion(
            [
                {"role": "system", "content": "你是连接测试助手。"},
                {"role": "user", "content": "请只回复：连接成功"},
            ],
            temperature=0,
        )
        return {"ok": True, "message": content}
    except LLMError as exc:
        return {"ok": False, "message": str(exc)}
