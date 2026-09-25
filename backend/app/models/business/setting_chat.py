"""设定共创对话模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.db.session import Base


class SettingChatSession(Base):
    """设定共创会话。"""

    __tablename__ = "setting_chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, unique=True)
    project_id = Column(Integer, nullable=False)
    user_id = Column(Integer, default=1)
    title = Column(String(255), nullable=False, default="新设定对话")
    target_type = Column(String(32), default="character")   # character/world/foreshadowing
    target_id = Column(Integer, nullable=True)
    target_name = Column(String(255), default="")
    status = Column(String(32), default="active")
    completeness = Column(Integer, default=0)
    focus_areas = Column(Text, default="[]")                 # JSON 数组，关注的设定领域
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SettingChatMessage(Base):
    """对话消息。"""

    __tablename__ = "setting_chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False)
    role = Column(String(16), nullable=False)                 # user/assistant
    content = Column(Text, nullable=False, default="")
    thought = Column(Text, default="")                         # Agent 思考过程
    token_usage = Column(Text, default="", nullable=True)       # 模型供应商返回的 Token 用量 JSON
    extracted_fields = Column(Text, default="[]")              # JSON 提取到的设定字段
    memory_written = Column(Integer, default=0)                # 是否已写入记忆
    created_at = Column(DateTime, server_default=func.now())
