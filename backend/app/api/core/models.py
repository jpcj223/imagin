from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.llm import LLMError, chat_completion
from app.db.session import get_core_db_depends
from app.models.core import ModelConfig
from app.schemas.core import ModelConfigCreate, ModelConfigResponse, ModelConfigUpdate

router = APIRouter()


@router.get("", response_model=list[ModelConfigResponse])
def list_model_configs(
    db: Session = Depends(get_core_db_depends),
) -> list[ModelConfigResponse]:
    """获取所有模型配置，按创建时间倒序。"""
    configs = db.query(ModelConfig).order_by(ModelConfig.id.desc()).all()
    return [ModelConfigResponse.model_validate(c) for c in configs]


@router.get("/active", response_model=ModelConfigResponse | None)
def get_active_config(
    db: Session = Depends(get_core_db_depends),
) -> ModelConfigResponse | None:
    """获取当前启用的配置。"""
    config = db.query(ModelConfig).filter(ModelConfig.is_active == 1).first()
    return ModelConfigResponse.model_validate(config) if config else None


@router.get("/{config_id}", response_model=ModelConfigResponse)
def get_model_config(
    config_id: int,
    db: Session = Depends(get_core_db_depends),
) -> ModelConfigResponse:
    """获取单条配置详情。"""
    config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return ModelConfigResponse.model_validate(config)


@router.post("", response_model=ModelConfigResponse)
def create_model_config(
    payload: ModelConfigCreate,
    db: Session = Depends(get_core_db_depends),
) -> ModelConfigResponse:
    """新增模型配置。"""
    data = payload.model_dump()
    is_active = data.pop("is_active", False)
    data["is_active"] = 1 if is_active else 0

    # 如果设为启用，先取消其他配置的激活状态
    if data["is_active"]:
        db.query(ModelConfig).update({ModelConfig.is_active: 0})

    config = ModelConfig(**data)
    db.add(config)
    db.commit()
    db.refresh(config)
    return ModelConfigResponse.model_validate(config)


@router.put("/{config_id}", response_model=ModelConfigResponse)
def update_model_config(
    config_id: int,
    payload: ModelConfigUpdate,
    db: Session = Depends(get_core_db_depends),
) -> ModelConfigResponse:
    """更新模型配置。"""
    config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    update_data = payload.model_dump(exclude_unset=True)

    # 处理 is_active 转换
    if "is_active" in update_data:
        is_active = update_data.pop("is_active")
        update_data["is_active"] = 1 if is_active else 0
        if update_data["is_active"]:
            db.query(ModelConfig).update({ModelConfig.is_active: 0})

    for key, value in update_data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return ModelConfigResponse.model_validate(config)


@router.delete("/{config_id}")
def delete_model_config(
    config_id: int,
    db: Session = Depends(get_core_db_depends),
) -> dict:
    """删除模型配置。"""
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


@router.post("/{config_id}/activate", response_model=ModelConfigResponse)
def activate_config(
    config_id: int,
    db: Session = Depends(get_core_db_depends),
) -> ModelConfigResponse:
    """设为启用。"""
    config = db.query(ModelConfig).filter(ModelConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 取消其他配置的激活状态
    db.query(ModelConfig).update({ModelConfig.is_active: 0})
    config.is_active = 1
    db.commit()
    db.refresh(config)
    return ModelConfigResponse.model_validate(config)


@router.post("/test")
def test_model_connection() -> dict:
    """测试当前启用的模型配置连接。"""
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
