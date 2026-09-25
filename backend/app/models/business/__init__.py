"""业务库 ORM 模型。

包含所有创作相关的数据表模型，对应 business_db 数据库。
"""
from __future__ import annotations

from app.models.business.project import Project
from app.models.business.world_setting import WorldSetting
from app.models.business.outline import Outline
from app.models.business.chapter import Chapter
from app.models.business.chapter_summary import ChapterSummary
from app.models.business.chapter_change_proposal import ChapterChangeProposal
from app.models.business.character import Character
from app.models.business.character_group import CharacterGroup
from app.models.business.organization import Organization
from app.models.business.organization_relation import OrganizationRelation
from app.models.business.organization_history import OrganizationHistory
from app.models.business.foreshadowing import Foreshadowing
from app.models.business.foreshadowing_history import ForeshadowingHistory
from app.models.business.generation_log import GenerationLog
from app.models.business.workflow_memory import (
    WorkflowRun,
    WorkflowStepRecord,
    GenerationVersion,
    UserPreference,
    MemoryItem,
)
from app.models.business.setting_chat import SettingChatSession, SettingChatMessage

__all__ = [
    "Project",
    "WorldSetting",
    "Outline",
    "Chapter",
    "ChapterSummary",
    "ChapterChangeProposal",
    "Character",
    "CharacterGroup",
    "Organization",
    "OrganizationRelation",
    "OrganizationHistory",
    "Foreshadowing",
    "ForeshadowingHistory",
    "GenerationLog",
    "WorkflowRun",
    "WorkflowStepRecord",
    "GenerationVersion",
    "UserPreference",
    "MemoryItem",
    "SettingChatSession",
    "SettingChatMessage",
]
