"""章节变化提案 API 契约。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ChangeEntityType = Literal[
    "character",
    "relationship",
    "organization",
    "organization_relation",
    "foreshadowing",
    "world_setting",
    "memory",
]


class ChapterChangeProposalDraft(BaseModel):
    """一条由分析器或人工提交的变化候选。"""

    entity_type: ChangeEntityType
    operation: Literal["create", "update"] = "update"
    target_id: int | None = None
    target_label: str = Field(default="", max_length=255)
    proposed_value: dict[str, Any]
    rationale: str = ""
    evidence: str = ""


class ChapterChangeProposalBatchCreate(BaseModel):
    """同一章节的一批分析候选；run/version 用于回溯正文来源。"""

    run_id: str | None = None
    version_id: str | None = None
    proposals: list[ChapterChangeProposalDraft] = Field(default_factory=list, max_length=100)


class ChapterChangeProposalReview(BaseModel):
    """审核一条提案；修改 proposed_value 后确认可在同一事务中应用。"""

    decision: Literal["approve", "reject"]
    proposed_value: dict[str, Any] | None = None
    review_note: str = ""
