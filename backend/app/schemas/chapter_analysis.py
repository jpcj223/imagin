"""章节分析 Agent 的结构化输出契约。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CharacterChange(BaseModel):
    name: str
    operation: Literal["create", "update"] = "update"
    changes: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    evidence: str = ""


class RelationshipChange(BaseModel):
    source_name: str
    target_name: str
    relation_type: str
    operation: Literal["create", "update"] = "create"
    depth: int = 3
    effective_from: int | None = None
    expires_at: int | None = None
    rationale: str = ""
    evidence: str = ""


class OrganizationChange(BaseModel):
    name: str
    operation: Literal["create", "update"] = "update"
    changes: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    evidence: str = ""


class OrganizationRelationChange(BaseModel):
    """章节中明确出现的组织关系变化。"""

    source_name: str
    target_name: str
    operation: Literal["create", "update"] = "create"
    relation_type: Literal["alliance", "hostility"] | None = None
    description: str | None = None
    effective_from_chapter: int | None = Field(default=None, ge=1)
    expires_at_chapter: int | None = Field(default=None, ge=1)
    target_effective_from_chapter: int | None = Field(default=None, ge=1)
    rationale: str = ""
    evidence: str = ""


class ForeshadowingChange(BaseModel):
    keyword: str
    operation: Literal["create", "update"] = "create"
    target_keyword: str | None = None
    changes: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    evidence: str = ""


class WorldSettingChange(BaseModel):
    title: str
    operation: Literal["create", "update"] = "update"
    changes: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    evidence: str = ""


class TimelineEvent(BaseModel):
    title: str
    content: str
    importance: int = Field(default=60, ge=0, le=100)


class ChapterAnalysis(BaseModel):
    """每章分析的稳定外部结构；正文资料的实际写回应经过审核服务。"""

    summary: str = ""
    character_changes: list[CharacterChange] = Field(default_factory=list)
    relationships: list[RelationshipChange] = Field(default_factory=list)
    organization_changes: list[OrganizationChange] = Field(default_factory=list)
    organization_relations: list[OrganizationRelationChange] = Field(default_factory=list)
    foreshadowing_changes: list[ForeshadowingChange] = Field(default_factory=list)
    world_changes: list[WorldSettingChange] = Field(default_factory=list)
    timeline_events: list[TimelineEvent] = Field(default_factory=list)
