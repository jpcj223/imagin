from __future__ import annotations

from fastapi import APIRouter

from app.core.llm import LLMError, chat_completion
from app.db.database import get_connection
from app.db.repository import fetch_all, insert_row
from app.schemas.models import ModelConfigCreate


router = APIRouter()


@router.get("")
def list_model_configs() -> list[dict]:
    return fetch_all("model_configs")


@router.post("")
def save_model_config(payload: ModelConfigCreate) -> dict:
    data = payload.model_dump()
    data["is_active"] = 1 if data["is_active"] else 0
    with get_connection() as conn:
        if data["is_active"]:
            conn.execute("UPDATE model_configs SET is_active = 0")
            conn.commit()
    return insert_row("model_configs", data)


@router.post("/test")
def test_model_connection() -> dict:
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
