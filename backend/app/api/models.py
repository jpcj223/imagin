from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.llm import LLMError, chat_completion
from app.db.database import get_connection
from app.db.repository import fetch_all, fetch_one, insert_row, update_row, delete_row
from app.schemas.models import ModelConfigCreate


router = APIRouter()


@router.get("")
def list_model_configs() -> list[dict]:
    """列出所有模型配置，按创建时间倒序（最新的在前）。"""
    return fetch_all("model_configs")


@router.get("/active")
def get_active_config() -> dict | None:
    """获取当前启用的配置。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM model_configs WHERE is_active = 1 LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


@router.get("/{config_id}")
def get_model_config(config_id: int) -> dict:
    """获取单条配置详情。"""
    item = fetch_one("model_configs", config_id)
    if not item:
        raise HTTPException(status_code=404, detail="配置不存在")
    return item


@router.post("")
def save_model_config(payload: ModelConfigCreate) -> dict:
    """新建配置；is_active 为 True 时会自动取消其他配置的激活状态。"""
    data = payload.model_dump()
    data["is_active"] = 1 if data["is_active"] else 0
    with get_connection() as conn:
        if data["is_active"]:
            conn.execute("UPDATE model_configs SET is_active = 0")
            conn.commit()
    return insert_row("model_configs", data)


@router.put("/{config_id}")
def update_model_config(config_id: int, payload: ModelConfigCreate) -> dict:
    """更新配置；如果把 is_active 设为 True，会自动取消其他配置的激活状态。"""
    existing = fetch_one("model_configs", config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="配置不存在")

    data = payload.model_dump(exclude_unset=True)
    # 如果传了 is_active，转换为 0/1
    if "is_active" in data:
        data["is_active"] = 1 if data["is_active"] else 0
        if data["is_active"]:
            with get_connection() as conn:
                conn.execute("UPDATE model_configs SET is_active = 0")
                conn.commit()

    result = update_row("model_configs", config_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="配置不存在")
    return result


@router.post("/{config_id}/activate")
def activate_config(config_id: int) -> dict:
    """将指定配置设为当前启用（其他配置自动取消激活）。"""
    existing = fetch_one("model_configs", config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="配置不存在")
    with get_connection() as conn:
        conn.execute("UPDATE model_configs SET is_active = 0")
        conn.execute(
            "UPDATE model_configs SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (config_id,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM model_configs WHERE id = ?", (config_id,)
        ).fetchone()
    return dict(row)


@router.delete("/{config_id}")
def delete_model_config(config_id: int) -> dict:
    """删除配置。如果删除的是当前启用的配置，会自动把最新的一条设为启用。"""
    existing = fetch_one("model_configs", config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="配置不存在")

    was_active = existing["is_active"] == 1
    delete_row("model_configs", config_id)

    # 如果删的是 active 配置，把最新的一条设为 active
    if was_active:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM model_configs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE model_configs SET is_active = 1 WHERE id = ?",
                    (row["id"],),
                )
                conn.commit()

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
