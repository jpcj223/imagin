"""设定共创 API。

提供对话式设定完善的接口：
- 会话列表 / 创建会话
- 发送消息 / 获取回复
- 获取设定详情（右侧卡片）
"""
from __future__ import annotations

import json
import uuid
import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.session import get_business_db
from app.models.business import (
    SettingChatSession,
    SettingChatMessage,
    Character,
)
from app.db.repository import row_to_dict, rows_to_dicts
from app.agents_v3.setting_co_agent import SettingCoAgent, SETTING_FIELD_TEMPLATES


router = APIRouter()


# ============================================================
# 请求模型
# ============================================================

class CreateSessionRequest(BaseModel):
    project_id: int
    target_type: str = "character"   # character/world/foreshadowing
    target_id: int | None = None
    target_name: str = ""


class SendMessageRequest(BaseModel):
    session_id: str
    message: str


# ============================================================
# 会话管理
# ============================================================

@router.get("/sessions")
def list_sessions(project_id: int, target_type: str | None = None):
    """获取会话列表。"""
    with get_business_db() as db:
        query = db.query(SettingChatSession).filter(
            SettingChatSession.project_id == project_id
        )
        if target_type:
            query = query.filter(SettingChatSession.target_type == target_type)

        sessions = (
            query.order_by(SettingChatSession.updated_at.desc())
            .limit(50)
            .all()
        )
        return {"sessions": rows_to_dicts(sessions)}


@router.post("/sessions")
def create_session(req: CreateSessionRequest):
    """创建新的设定共创会话。"""
    session_id = f"sc_{uuid.uuid4().hex[:16]}"

    # 根据 target 类型获取名称
    target_name = req.target_name
    if req.target_type == "character" and req.target_id and not target_name:
        with get_business_db() as db:
            char = db.query(Character).filter(Character.id == req.target_id).first()
            if char:
                target_name = char.name

    with get_business_db() as db:
        session = SettingChatSession(
            session_id=session_id,
            project_id=req.project_id,
            title=f"{target_name or '新设定'}的对话",
            target_type=req.target_type,
            target_id=req.target_id,
            target_name=target_name,
            status="active",
            completeness=0,
            focus_areas="[]",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # 生成开场白
        agent = SettingCoAgent(req.project_id)
        existing_data = {}
        if req.target_type == "character" and req.target_id:
            char = db.query(Character).filter(Character.id == req.target_id).first()
            if char:
                existing_data = row_to_dict(char)

        opening = agent.generate_opening(
            target_type=req.target_type,
            target_name=target_name,
            existing_data=existing_data,
        )

        # 保存开场白消息
        msg = SettingChatMessage(
            session_id=session_id,
            role="assistant",
            content=opening["message"],
            thought=opening["thought"],
            extracted_fields=json.dumps([], ensure_ascii=False),
            memory_written=0,
        )
        db.add(msg)

        # 更新完整度
        session.completeness = opening["completeness"]
        db.commit()

        return {
            "session": row_to_dict(session),
            "opening": {
                "message": opening["message"],
                "quick_replies": opening["quick_replies"],
            },
        }


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    """获取会话详情。"""
    with get_business_db() as db:
        session = (
            db.query(SettingChatSession)
            .filter(SettingChatSession.session_id == session_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        messages = (
            db.query(SettingChatMessage)
            .filter(SettingChatMessage.session_id == session_id)
            .order_by(SettingChatMessage.id.asc())
            .all()
        )

        return {
            "session": row_to_dict(session),
            "messages": rows_to_dicts(messages),
        }


# ============================================================
# 消息对话
# ============================================================

@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: str):
    """获取会话消息列表。"""
    with get_business_db() as db:
        messages = (
            db.query(SettingChatMessage)
            .filter(SettingChatMessage.session_id == session_id)
            .order_by(SettingChatMessage.id.asc())
            .all()
        )
        return {"messages": rows_to_dicts(messages)}


@router.post("/sessions/{session_id}/messages")
def send_message(session_id: str, req: SendMessageRequest):
    """发送消息并获取回复。"""
    with get_business_db() as db:
        session = (
            db.query(SettingChatSession)
            .filter(SettingChatSession.session_id == session_id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        # 保存用户消息
        user_msg = SettingChatMessage(
            session_id=session_id,
            role="user",
            content=req.message,
            extracted_fields="[]",
            memory_written=0,
        )
        db.add(user_msg)
        db.flush()

        # 调用 Agent 处理
        agent = SettingCoAgent(session.project_id)

        try:
            result = agent.process_user_message(
                session_id=session_id,
                user_message=req.message,
                target_type=session.target_type,
                target_id=session.target_id,
                target_name=session.target_name,
            )
        except Exception as e:
            traceback.print_exc()
            # 出错时返回友好提示
            result = {
                "reply": f"抱歉，处理时出了点问题：{str(e)}\n\n你可以重新描述一下，或者换个话题继续聊～",
                "thought": f"Error: {str(e)}",
                "extracted_fields": [],
                "memory_written": False,
                "quick_replies": ["重新描述一下", "换个话题"],
            }

        # 保存 Agent 回复
        assistant_msg = SettingChatMessage(
            session_id=session_id,
            role="assistant",
            content=result["reply"],
            thought=result["thought"],
            extracted_fields=json.dumps(
                result["extracted_fields"], ensure_ascii=False
            ),
            memory_written=1 if result["memory_written"] else 0,
        )
        db.add(assistant_msg)

        # 更新完整度
        if session.target_type == "character" and session.target_id:
            char = db.query(Character).filter(Character.id == session.target_id).first()
            if char:
                char_data = row_to_dict(char)
                completeness = agent.calculate_completeness(
                    session.target_type, char_data
                )
                session.completeness = completeness

        session.title = f"{session.target_name}的对话"  # 更新标题
        db.commit()
        db.refresh(session)

        # 返回最新的设定数据（供右侧卡片更新）
        setting_detail = {}
        if session.target_type == "character" and session.target_id:
            char = db.query(Character).filter(Character.id == session.target_id).first()
            if char:
                setting_detail = agent.get_setting_detail("character", session.target_id)

        return {
            "reply": {
                "role": "assistant",
                "content": result["reply"],
                "thought": result["thought"],
                "extracted_fields": result["extracted_fields"],
                "memory_written": result["memory_written"],
                "created_at": assistant_msg.created_at.isoformat() if assistant_msg.created_at else None,
            },
            "quick_replies": result["quick_replies"],
            "session": row_to_dict(session),
            "setting_detail": setting_detail,
        }


# ============================================================
# 设定详情
# ============================================================

@router.get("/setting-detail")
def get_setting_detail(target_type: str, target_id: int, project_id: int):
    """获取设定详情（供右侧卡片展示）。"""
    agent = SettingCoAgent(project_id)
    detail = agent.get_setting_detail(target_type, target_id)
    return {"detail": detail}


@router.get("/field-templates")
def get_field_templates(target_type: str):
    """获取设定字段模板。"""
    templates = SETTING_FIELD_TEMPLATES.get(target_type, [])
    return {"templates": templates}


# ============================================================
# 设定目录（带完整度）
# ============================================================

@router.get("/setting-index")
def get_setting_index(project_id: int):
    """获取设定目录（按类型分组，带完整度）。"""
    agent = SettingCoAgent(project_id)
    result = {}

    # 角色
    with get_business_db() as db:
        characters = (
            db.query(Character)
            .filter(Character.project_id == project_id)
            .order_by(Character.sort_index.asc(), Character.id.asc())
            .limit(50)
            .all()
        )

        char_list = []
        for c in characters:
            data = row_to_dict(c)
            completeness = agent.calculate_completeness("character", data)
            # 状态：complete/partial/empty
            if completeness >= 80:
                status = "complete"
            elif completeness >= 30:
                status = "partial"
            else:
                status = "empty"
            char_list.append({
                "id": c.id,
                "name": c.name,
                "role_type": c.role_type,
                "completeness": completeness,
                "status": status,
            })

        result["characters"] = char_list
        result["character_count"] = len(char_list)
        result["character_completeness"] = (
            int(sum(c["completeness"] for c in char_list) / len(char_list))
            if char_list else 0
        )

    # 世界观（简化）
    result["world"] = {
        "completeness": 40,
        "items": [
            {"key": "power_system", "label": "修炼体系", "status": "partial"},
            {"key": "factions", "label": "势力分布", "status": "partial"},
            {"key": "geography", "label": "地理环境", "status": "empty"},
        ],
    }

    # 伏笔
    result["foreshadowing"] = {
        "completeness": 20,
        "items": [
            {"key": "main_plot", "label": "主线伏笔", "status": "empty"},
            {"key": "character_secrets", "label": "人物秘密", "status": "empty"},
        ],
    }

    return result
