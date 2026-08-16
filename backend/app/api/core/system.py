from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_core_db_depends
from app.models.core import SysConfig
from app.schemas.core import SysConfigResponse, SysConfigUpdate

router = APIRouter()


@router.get("", response_model=list[SysConfigResponse])
def list_configs(
    db: Session = Depends(get_core_db_depends),
) -> list[SysConfigResponse]:
    """获取所有系统配置。"""
    configs = db.query(SysConfig).order_by(SysConfig.id).all()
    return [SysConfigResponse.model_validate(c) for c in configs]


@router.get("/{config_key}", response_model=SysConfigResponse)
def get_config(
    config_key: str,
    db: Session = Depends(get_core_db_depends),
) -> SysConfigResponse:
    """获取单个配置。"""
    config = db.query(SysConfig).filter(SysConfig.config_key == config_key).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return SysConfigResponse.model_validate(config)


@router.put("/{config_key}", response_model=SysConfigResponse)
def update_config(
    config_key: str,
    payload: SysConfigUpdate,
    db: Session = Depends(get_core_db_depends),
) -> SysConfigResponse:
    """更新某个配置（不存在则创建）。"""
    config = db.query(SysConfig).filter(SysConfig.config_key == config_key).first()

    update_data = payload.model_dump(exclude_unset=True)

    if config:
        for key, value in update_data.items():
            setattr(config, key, value)
    else:
        # 不存在则创建
        config = SysConfig(config_key=config_key, **update_data)
        db.add(config)

    db.commit()
    db.refresh(config)
    return SysConfigResponse.model_validate(config)
