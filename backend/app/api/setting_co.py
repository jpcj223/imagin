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
    Foreshadowing,
    WorldSetting,
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
    """创建新的设定共创会话。

    步骤 1：限制会话目标类型并验证目标属于当前项目。
    步骤 2：世界观总览在不存在时创建，其余目标必须选择现有档案。
    步骤 3：保存会话及开场消息，并返回目标当前缺失字段。
    """
    if req.target_type not in {"character", "world", "foreshadowing"}:
        raise HTTPException(status_code=422, detail="不支持的设定类型")

    session_id = f"sc_{uuid.uuid4().hex[:16]}"
    target_id = req.target_id
    target_name = req.target_name

    with get_business_db() as db:
        # 步骤 1：世界观共创始终绑定总览记录；不存在时在本项目内创建空记录。
        if req.target_type == "world":
            world_query = db.query(WorldSetting).filter(
                WorldSetting.project_id == req.project_id
            )
            world = (
                world_query.filter(WorldSetting.id == target_id).first()
                if target_id
                else world_query.filter(
                    (WorldSetting.category == "overview")
                    | (WorldSetting.title == "世界观总览")
                ).order_by(WorldSetting.id.asc()).first()
            )
            if target_id and not world:
                raise HTTPException(status_code=404, detail="世界观总览不存在")
            if not world:
                world = WorldSetting(
                    project_id=req.project_id,
                    title=target_name or "世界观总览",
                    category="overview",
                    importance="high",
                )
                db.add(world)
                db.flush()
            target_id = world.id
            target_name = world.title or target_name or "世界观总览"
        elif req.target_type == "character":
            if not target_id:
                raise HTTPException(status_code=422, detail="请先选择一个角色档案")
            char = (
                db.query(Character)
                .filter(Character.id == target_id, Character.project_id == req.project_id)
                .first()
            )
            if not char:
                raise HTTPException(status_code=404, detail="角色不存在或不属于当前项目")
            target_name = char.name
        elif req.target_type == "foreshadowing":
            if not target_id:
                raise HTTPException(status_code=422, detail="请先选择一条伏笔线索")
            item = db.query(Foreshadowing).filter(
                Foreshadowing.id == target_id,
                Foreshadowing.project_id == req.project_id,
            ).first()
            if not item:
                raise HTTPException(status_code=404, detail="伏笔不存在或不属于当前项目")
            target_name = item.keyword

        # 步骤 2：创建会话并保留目标记录 ID，后续回答才能准确写回。
        session = SettingChatSession(
            session_id=session_id,
            project_id=req.project_id,
            title=f"{target_name or '新设定'}的对话",
            target_type=req.target_type,
            target_id=target_id,
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
        if req.target_type == "character" and target_id:
            char = db.query(Character).filter(Character.id == target_id).first()
            if char:
                existing_data = row_to_dict(char)
        elif req.target_type == "world" and target_id:
            existing_data = agent.get_setting_detail("world", target_id)
        elif req.target_type == "foreshadowing" and target_id:
            existing_data = agent.get_setting_detail("foreshadowing", target_id)

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
        # 步骤 1：先提交用户消息，释放 SQLite 写锁，供 Agent 独立事务更新设定和记忆。
        db.commit()

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
            # 步骤 1：内部保留错误日志；步骤 2：界面只收到可恢复提示，不暴露服务细节。
            result = {
                "reply": "抱歉，本轮设定整理暂时失败。刚才的消息已保留，你可以稍后重试。",
                "thought": "本轮设定整理失败，未确认任何字段写回。",
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

        # 步骤 1：根据已写回的目标资料刷新会话完整度。
        if session.target_type in {"character", "world", "foreshadowing"} and session.target_id:
            detail = agent.get_setting_detail(session.target_type, session.target_id)
            session.completeness = detail.get("completeness", session.completeness)

        session.title = f"{session.target_name}的对话"  # 更新标题
        db.commit()
        db.refresh(session)

        # 返回最新的设定数据（供右侧卡片更新）
        setting_detail = {}
        if session.target_type in {"character", "world", "foreshadowing"} and session.target_id:
            setting_detail = agent.get_setting_detail(
                session.target_type, session.target_id
            )

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

    # 步骤 1：读取本项目的世界观总览，左侧状态与实际资料同步。
    with get_business_db() as db:
        world = (
            db.query(WorldSetting)
            .filter(
                WorldSetting.project_id == project_id,
                (WorldSetting.category == "overview")
                | (WorldSetting.title == "世界观总览"),
            )
            .order_by(WorldSetting.id.asc())
            .first()
        )
        world_detail = (
            agent._world_data_from_row(world)
            if world
            else {field["key"]: "" for field in SETTING_FIELD_TEMPLATES["world"]}
        )
        world_completeness = agent.calculate_completeness("world", world_detail)
        result["world"] = {
            "target_id": world.id if world else None,
            "name": world.title if world and world.title else "世界观总览",
            "completeness": world_completeness,
            "items": [
                {
                    "key": field["key"],
                    "label": field["label"],
                    "status": "complete" if world_detail.get(field["key"]) else "empty",
                }
                for field in SETTING_FIELD_TEMPLATES["world"]
            ],
        }

    # 步骤 1：把实际伏笔档案作为共创目标，而不是展示不可点击的静态字段。
    with get_business_db() as db:
        foreshadowings = (
            db.query(Foreshadowing)
            .filter(Foreshadowing.project_id == project_id)
            .order_by(Foreshadowing.updated_at.desc(), Foreshadowing.id.desc())
            .limit(100)
            .all()
        )
        foreshadowing_items = []
        for item in foreshadowings:
            detail = row_to_dict(item)
            completeness = agent.calculate_completeness("foreshadowing", detail)
            status = "complete" if completeness >= 80 else "partial" if completeness >= 30 else "empty"
            foreshadowing_items.append({
                "id": item.id,
                "name": item.keyword,
                "completeness": completeness,
                "status": status,
                "lifecycle_status": item.status,
            })

    result["foreshadowing"] = {
        "completeness": (
            int(sum(item["completeness"] for item in foreshadowing_items) / len(foreshadowing_items))
            if foreshadowing_items else 0
        ),
        "items": foreshadowing_items,
    }

    return result
