"""章节变化提案 API。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.db.session import get_business_db
from app.models.business import Chapter
from app.schemas.chapter_change_proposals import (
    ChapterChangeProposalBatchCreate,
    ChapterChangeProposalReview,
)
from app.services.chapter_change_proposals import (
    create_proposals,
    list_proposals,
    review_proposal,
)


router = APIRouter()


@router.get("/{project_id}/chapters/{chapter_id}/change-proposals")
def get_chapter_change_proposals(
    project_id: int,
    chapter_id: int,
    status: str | None = Query(default=None),
) -> dict:
    """查询章节提案。

    步骤 1：验证章节属于项目。
    步骤 2：按可选状态读取提案。
    步骤 3：返回统一 JSON 契约给章节工作台。
    """
    if status and status not in {"pending", "applied", "rejected", "conflict"}:
        raise HTTPException(status_code=422, detail="不支持的提案状态")
    with get_business_db() as db:
        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.project_id == project_id,
        ).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在或不属于当前项目")
        items = list_proposals(db, project_id, chapter_id, status)
    return {"items": items, "total": len(items)}


@router.post("/{project_id}/chapters/{chapter_id}/change-proposals")
def create_chapter_change_proposals(
    project_id: int,
    chapter_id: int,
    payload: ChapterChangeProposalBatchCreate,
) -> dict:
    """保存分析器提出的一批变化候选，不直接改写正式设定。

    步骤 1：将 Pydantic 输入转换为纯数据对象。
    步骤 2：由应用服务校验项目、章节、来源版本和实体字段。
    步骤 3：在单个业务库事务中保存所有提案。
    步骤 4：返回已保存记录；相同输入通过幂等键复用已有提案。
    """
    with get_business_db() as db:
        try:
            items = create_proposals(
                db=db,
                project_id=project_id,
                chapter_id=chapter_id,
                run_id=payload.run_id,
                version_id=payload.version_id,
                drafts=[item.model_dump() for item in payload.proposals],
            )
            db.commit()
        except LookupError as exc:
            db.rollback()
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception:
            db.rollback()
            raise
    return {"items": items, "total": len(items)}


@router.post("/{project_id}/chapters/{chapter_id}/change-proposals/{proposal_id}/review")
def review_chapter_change_proposal(
    project_id: int,
    chapter_id: int,
    proposal_id: str,
    payload: ChapterChangeProposalReview,
) -> dict:
    """审核提案；批准时应用服务在同一事务内检查冲突并写回。

    步骤 1：限定项目、章节和提案 ID，避免跨项目审核。
    步骤 2：调用应用服务记录拒绝，或校验并应用批准的变化。
    步骤 3：提交审核状态与实体变更；若发现冲突，只提交冲突标记。
    步骤 4：冲突以 409 返回，提示前端刷新当前资料后重新确认。
    """
    conflict = False
    with get_business_db() as db:
        try:
            result = review_proposal(
                db=db,
                project_id=project_id,
                chapter_id=chapter_id,
                proposal_id=proposal_id,
                decision=payload.decision,
                proposed_value=payload.proposed_value,
                review_note=payload.review_note,
            )
            conflict = result["conflict"]
            db.commit()
        except LookupError as exc:
            db.rollback()
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception:
            db.rollback()
            raise

    if conflict:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "目标资料在提案生成后发生变化，提案已标记为冲突，请刷新后重新分析。",
                "proposal": result["proposal"],
            },
        )
    return result
