"""业务库 ORM 模型。

包含所有创作相关的数据表模型，对应 business_db 数据库。
"""
from __future__ import annotations

from app.models.business.project import Project
from app.models.business.world_setting import WorldSetting
from app.models.business.outline import Outline
from app.models.business.chapter import Chapter
from app.models.business.chapter_summary import ChapterSummary
from app.models.business.character import Character
from app.models.business.organization import Organization
from app.models.business.foreshadowing import Foreshadowing
from app.models.business.generation_log import GenerationLog

__all__ = [
    "Project",
    "WorldSetting",
    "Outline",
    "Chapter",
    "ChapterSummary",
    "Character",
    "Organization",
    "Foreshadowing",
    "GenerationLog",
]
