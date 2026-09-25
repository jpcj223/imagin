"""v3.0 Agent API。

提供基于微内核架构的新 API：
- 工作流模板列表
- Agent 列表 / Skill 列表 / 变体列表
- 工作流执行（同步 + 流式）
- 工作流历史记录
- 断点续传
- 生成版本管理
- 记忆管理
"""
from __future__ import annotations

import json
import traceback
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, or_

from app.agents_v3.persistence import WorkflowPersistence
from app.agents_v3.presets import get_agent
from app.agents_v3.variants import VariantManager
from app.agents_v3.workflow_engine import WorkflowEngine, list_templates
from app.memory.manager import MemoryManager
from app.skills.registry import SkillRegistry


router = APIRouter()


# ============================================================
# 请求模型
# ============================================================

class WorkflowGenerateRequest(BaseModel):
    """工作流生成请求。"""
    project_id: int
    chapter_no: int
    outline_id: int | None = None
    template_name: str = "smart_mode"
    instruction: str = ""
    rhythm_level: str = "medium"
    chapter_id: int | None = None
    context_selection: dict[str, list[int]] | None = None


class WorkflowResumeRequest(BaseModel):
    """断点续传请求。"""
    run_id: str
    chapter_no: int
    outline_id: int | None = None
    instruction: str = ""
    rhythm_level: str = "medium"
    restart_from_step_id: str | None = None  # 从指定步骤开始重跑（可选）
    context_selection: dict[str, list[int]] | None = None


class AgentGenerateRequest(BaseModel):
    """单个 Agent 调用请求。"""
    project_id: int
    chapter_no: int
    outline_id: int | None = None
    agent_type: str = "writer"
    variant: str = "default"
    instruction: str = ""
    rhythm_level: str = "medium"
    context_selection: dict[str, list[int]] | None = None


class MemoryStoreRequest(BaseModel):
    """存储记忆请求。"""
    project_id: int
    memory_type: str
    title: str
    content: str
    importance: int = 50
    source_type: str = "manual"
    source_ref: str | None = None
    metadata: dict | None = None


class PreferenceUpdateRequest(BaseModel):
    """更新用户偏好请求。"""
    project_id: int
    preferences: dict
    project_level: bool = True


# ============================================================
# 查询接口：模板 / Skill / 变体 / Agent
# ============================================================

@router.get("/templates")
def get_workflow_templates() -> list[dict]:
    """获取工作流模板列表。"""
    return list_templates()


@router.get("/workflow/templates")
def get_workflow_templates_v2() -> list[dict]:
    """获取工作流模板列表（兼容路径）。"""
    return list_templates()


@router.get("/skills")
def get_skills(category: str | None = None) -> list[dict]:
    """获取 Skill 列表。"""
    if category:
        return SkillRegistry.list_by_category(category)
    return SkillRegistry.list_all()


@router.get("/variants")
def get_variants(agent_type: str | None = None) -> dict:
    """获取变体列表。

    Args:
        agent_type: Agent 类型，不传则返回所有类型的变体
    """
    if agent_type:
        return {agent_type: VariantManager.list_for_agent(agent_type)}
    return VariantManager.all_variants()


@router.get("/agents")
def get_agents_info() -> list[dict]:
    """获取可用 Agent 类型信息。"""
    return [
        {
            "type": "writer",
            "label": "写手",
            "icon": "✍️",
            "description": "生成章节正文",
            "supports_streaming": True,
        },
        {
            "type": "analyzer",
            "label": "分析师",
            "icon": "🔍",
            "description": "分析章节，抽取结构化数据",
            "supports_streaming": False,
        },
        {
            "type": "planner",
            "label": "规划师",
            "icon": "📋",
            "description": "制定写作计划",
            "supports_streaming": False,
        },
        {
            "type": "polisher",
            "label": "精修师",
            "icon": "💎",
            "description": "润色优化正文",
            "supports_streaming": False,
        },
    ]


# ============================================================
# 工作流执行
# ============================================================

@router.post("/workflow/generate")
def workflow_generate(payload: WorkflowGenerateRequest) -> dict:
    """同步执行工作流生成章节。"""
    engine = WorkflowEngine(
        project_id=payload.project_id,
        template_name=payload.template_name,
        chapter_id=payload.chapter_id,
        outline_id=payload.outline_id,
    )
    result = engine.run(
        chapter_no=payload.chapter_no,
        outline_id=payload.outline_id,
        instruction=payload.instruction,
        rhythm_level=payload.rhythm_level,
        context_selection=payload.context_selection,
    )

    # 步骤 1：同步和流式生成共用持久化逻辑，避免无 chapter_id 时丢失整章结果。
    if result.get("status") == "completed":
        _persist_completed_workflow_output(
            project_id=payload.project_id,
            chapter_no=payload.chapter_no,
            outline_id=payload.outline_id,
            chapter_id=payload.chapter_id,
            result=result,
        )

    return result


@router.post("/workflow/generate/stream")
def workflow_generate_stream(payload: WorkflowGenerateRequest) -> StreamingResponse:
    """流式执行工作流生成章节。

    使用 NDJSON：每行一个事件对象。
    """

    def event_lines() -> Iterator[str]:
        try:
            engine = WorkflowEngine(
                project_id=payload.project_id,
                template_name=payload.template_name,
                chapter_id=payload.chapter_id,
                outline_id=payload.outline_id,
            )
            content_buffer: list[str] = []
            final_result: dict | None = None

            for event in engine.run_stream(
                chapter_no=payload.chapter_no,
                outline_id=payload.outline_id,
                instruction=payload.instruction,
                rhythm_level=payload.rhythm_level,
                context_selection=payload.context_selection,
            ):
                # 收集正文内容用于保存
                if event.get("type") == "delta" and event.get("step_id") == "writer":
                    content_buffer.append(event.get("content", ""))

                # 记录最终结果
                if event.get("type") == "workflow_done":
                    final_result = event
                    # 步骤 1：暂存最终事件，确保正文、版本和分析先持久化再通知界面成功。
                    continue

                yield json.dumps(event, ensure_ascii=False) + "\n"

            # 步骤 1：工作流完成后，保存最终稿、生成版本和分析提案。
            if final_result and final_result.get("status") == "completed":
                session_context = final_result.get("session_context", {})
                # 旧模板没有 final_content 时，以流式写作正文作为兼容回退。
                session_context.setdefault("draft_content", "".join(content_buffer))
                persisted = _persist_completed_workflow_output(
                    project_id=payload.project_id,
                    chapter_no=payload.chapter_no,
                    outline_id=payload.outline_id,
                    chapter_id=payload.chapter_id,
                    result=final_result,
                )
                # 步骤 2：把保存结果带入完成事件，前端可立即锁定本章与正文版本。
                final_result["chapter_id"] = persisted["chapter_id"]
                final_result["version_id"] = persisted["version_id"]
                yield json.dumps(final_result, ensure_ascii=False) + "\n"
                # 步骤 3：让前端获得最终章节 ID，再加载待审核提案列表。
                if persisted["chapter_id"]:
                    yield json.dumps(
                        {
                            "type": "change_proposals_ready",
                            "chapter_id": persisted["chapter_id"],
                            "pending_count": persisted["pending_count"],
                        },
                        ensure_ascii=False,
                    ) + "\n"
            elif final_result:
                # 步骤 4：失败或暂停事件无需持久化成功结果，仍要明确通知前端。
                yield json.dumps(final_result, ensure_ascii=False) + "\n"

        except Exception as exc:  # noqa: BLE001
            yield json.dumps(
                {
                    "type": "error",
                    "message": f"生成失败：{exc}",
                    "trace": traceback.format_exc(limit=2),
                },
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(event_lines(), media_type="application/x-ndjson")


# ============================================================
# 断点续传
# ============================================================

@router.post("/workflow/resume")
def workflow_resume(payload: WorkflowResumeRequest) -> dict:
    """断点续传：从 run_id 恢复工作流执行（同步）。"""
    # 先获取运行信息以确定模板名称
    run_info = WorkflowPersistence.get_run(payload.run_id)
    if not run_info:
        return {"error": "Run not found", "run_id": payload.run_id}

    # 步骤 1：已完成且已有版本的运行不可直接续跑，避免重复创建相同版本和提案。
    if (
        run_info.get("status") == "completed"
        and not payload.restart_from_step_id
        and _has_persisted_generation_version(payload.run_id)
    ):
        raise HTTPException(status_code=409, detail="该工作流已完成；如需修改，请从指定步骤重跑。")

    template_name = run_info.get("template_name", "smart_mode")
    project_id = run_info.get("project_id")

    engine = WorkflowEngine(
        project_id=project_id,
        template_name=template_name,
        run_id=payload.run_id,
    )

    # 如果指定了重跑起点，重置该步骤及其下游步骤
    if payload.restart_from_step_id:
        engine.restart_from_step(payload.restart_from_step_id)

    result = engine.run(
        chapter_no=payload.chapter_no,
        outline_id=payload.outline_id,
        instruction=payload.instruction,
        rhythm_level=payload.rhythm_level,
        context_selection=payload.context_selection,
    )
    if result.get("status") == "completed":
        # 步骤 1：续跑成功也必须保存正文版本、章节摘要和待审核变化。
        _persist_completed_workflow_output(
            project_id=project_id,
            chapter_no=payload.chapter_no,
            outline_id=payload.outline_id,
            chapter_id=run_info.get("chapter_id"),
            result=result,
        )
    return result


@router.post("/workflow/resume/stream")
def workflow_resume_stream(payload: WorkflowResumeRequest) -> StreamingResponse:
    """断点续传：流式恢复工作流执行。"""

    def event_lines() -> Iterator[str]:
        try:
            run_info = WorkflowPersistence.get_run(payload.run_id)
            if not run_info:
                yield json.dumps(
                    {"type": "error", "message": "Run not found"},
                    ensure_ascii=False,
                ) + "\n"
                return

            # 步骤 1：已持久化的完成运行不能再次续跑，以免重复写入版本和提案。
            if (
                run_info.get("status") == "completed"
                and not payload.restart_from_step_id
                and _has_persisted_generation_version(payload.run_id)
            ):
                yield json.dumps(
                    {"type": "error", "message": "该工作流已完成；如需修改，请从指定步骤重跑。"},
                    ensure_ascii=False,
                ) + "\n"
                return

            template_name = run_info.get("template_name", "smart_mode")
            project_id = run_info.get("project_id")

            engine = WorkflowEngine(
                project_id=project_id,
                template_name=template_name,
                run_id=payload.run_id,
            )

            # 如果指定了重跑起点，重置该步骤及其下游步骤
            if payload.restart_from_step_id:
                engine.restart_from_step(payload.restart_from_step_id)

            content_buffer: list[str] = []
            final_result: dict | None = None
            for event in engine.run_stream(
                chapter_no=payload.chapter_no,
                outline_id=payload.outline_id,
                instruction=payload.instruction,
                rhythm_level=payload.rhythm_level,
                context_selection=payload.context_selection,
            ):
                if event.get("type") == "delta" and event.get("step_id") == "writer":
                    content_buffer.append(event.get("content", ""))
                if event.get("type") == "workflow_done":
                    final_result = event
                    # 步骤 2：暂存完成事件，待正文和分析全部保存后再反馈成功状态。
                    continue
                yield json.dumps(event, ensure_ascii=False) + "\n"

            if final_result and final_result.get("status") == "completed":
                # 步骤 1：恢复完成后使用共享持久化步骤，不留下未入库的正文或分析。
                session_context = final_result.get("session_context", {})
                session_context.setdefault("draft_content", "".join(content_buffer))
                persisted = _persist_completed_workflow_output(
                    project_id=project_id,
                    chapter_no=payload.chapter_no,
                    outline_id=payload.outline_id,
                    chapter_id=run_info.get("chapter_id"),
                    result=final_result,
                )
                # 步骤 3：完成事件返回本次保存的章节与正文版本。
                final_result["chapter_id"] = persisted["chapter_id"]
                final_result["version_id"] = persisted["version_id"]
                yield json.dumps(final_result, ensure_ascii=False) + "\n"
                # 步骤 4：通知前端章节已保存，可加载本章的提案列表。
                if persisted["chapter_id"]:
                    yield json.dumps(
                        {
                            "type": "change_proposals_ready",
                            "chapter_id": persisted["chapter_id"],
                            "pending_count": persisted["pending_count"],
                        },
                        ensure_ascii=False,
                    ) + "\n"
            elif final_result:
                # 步骤 5：未完成运行直接反馈暂停或失败状态。
                yield json.dumps(final_result, ensure_ascii=False) + "\n"

        except Exception as exc:
            yield json.dumps(
                {"type": "error", "message": f"恢复失败：{exc}"},
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(event_lines(), media_type="application/x-ndjson")


# ============================================================
# 工作流历史记录
# ============================================================

@router.get("/workflow/runs")
def get_workflow_runs(
    project_id: int,
    chapter_id: int | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """获取工作流运行历史记录。"""
    return WorkflowPersistence.list_runs(
        project_id=project_id,
        chapter_id=chapter_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/workflow/runs/{run_id}")
def get_workflow_run_detail(run_id: str) -> dict | None:
    """获取工作流运行详情（含步骤记录）。"""
    run_info = WorkflowPersistence.get_run(run_id)
    if not run_info:
        return None

    step_records = WorkflowPersistence.get_step_records(run_id)
    return {
        "run": run_info,
        "steps": step_records,
    }


# ============================================================
# 生成版本管理
# ============================================================

@router.get("/versions/{chapter_id}")
def get_generation_versions(chapter_id: int, limit: int = 10) -> list[dict]:
    """获取章节的生成版本列表。"""
    return WorkflowPersistence.get_versions(chapter_id, limit=limit)


@router.get("/versions/{chapter_id}/{version_id}/content")
def get_version_content(chapter_id: int, version_id: str) -> dict:
    """获取指定版本的完整内容。"""
    content = WorkflowPersistence.get_version_content(version_id)
    return {"version_id": version_id, "content": content}


@router.post("/versions/{chapter_id}/set-current")
def set_current_version(chapter_id: int, version_id: str) -> dict:
    """设置当前版本，并回滚章节内容到该版本。"""
    result = WorkflowPersistence.set_current_version(chapter_id, version_id)
    return result


# ============================================================
# 记忆管理
# ============================================================

@router.get("/memory/preferences")
def get_preferences(project_id: int, project_level: bool = True) -> dict:
    """获取用户偏好（L4 长期记忆）。"""
    mm = MemoryManager(project_id)
    return mm.get_preferences(project_level=project_level)


@router.post("/memory/preferences")
def update_preferences(payload: PreferenceUpdateRequest) -> dict:
    """更新用户偏好。"""
    mm = MemoryManager(payload.project_id)
    mm.set_preferences(payload.preferences, project_level=payload.project_level)
    return {"success": True}


@router.post("/memory/store")
def store_memory(payload: MemoryStoreRequest) -> dict:
    """存储一条通用记忆。"""
    mm = MemoryManager(payload.project_id)
    memory_id = mm.store_memory(
        memory_type=payload.memory_type,
        title=payload.title,
        content=payload.content,
        importance=payload.importance,
        source_type=payload.source_type,
        source_ref=payload.source_ref,
        metadata=payload.metadata,
    )
    return {"memory_id": memory_id, "success": True}


@router.get("/memory/items")
def list_memory_items(
    project_id: int,
    limit: int = 100,
    offset: int = 0,
    keyword: str | None = None,
    memory_type: str | None = None,
) -> dict:
    """按项目读取已沉淀的长期记忆条目。

    步骤 1：把单页大小和偏移限制在合理范围，并限定当前项目。
    步骤 2：在数据库侧按关键词和记忆类型筛选，统计筛选数与项目总数。
    步骤 3：按近期更新和重要性排序并只返回当前页。
    步骤 4：序列化为稳定响应，供长期记忆中心展示和分页。
    """
    from app.db.repository import rows_to_dicts
    from app.db.session import get_business_db
    from app.models.business import MemoryItem

    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    with get_business_db() as db:
        base_query = db.query(MemoryItem).filter(MemoryItem.project_id == project_id)
        all_total = base_query.with_entities(func.count(MemoryItem.id)).scalar() or 0
        filtered_query = base_query
        if memory_type:
            if memory_type == "general":
                filtered_query = filtered_query.filter(or_(
                    MemoryItem.memory_type == "general",
                    MemoryItem.memory_type.is_(None),
                    MemoryItem.memory_type == "",
                ))
            else:
                filtered_query = filtered_query.filter(MemoryItem.memory_type == memory_type)
        search_term = (keyword or "").strip()
        if search_term:
            search_pattern = f"%{search_term}%"
            filtered_query = filtered_query.filter(or_(
                MemoryItem.title.ilike(search_pattern),
                MemoryItem.content.ilike(search_pattern),
                MemoryItem.content_summary.ilike(search_pattern),
                MemoryItem.source_ref.ilike(search_pattern),
            ))
        total = filtered_query.with_entities(func.count(MemoryItem.id)).scalar() or 0
        rows = (
            filtered_query
            .order_by(MemoryItem.updated_at.desc(), MemoryItem.importance.desc(), MemoryItem.id.desc())
            .limit(safe_limit)
            .offset(safe_offset)
            .all()
        )
        items = rows_to_dicts(rows)
    return {"items": items, "total": total, "all_total": all_total}


@router.get("/memory/{memory_id}")
def get_memory(memory_id: str) -> dict | None:
    """获取一条记忆详情。"""
    # memory_id 是全局唯一的，project_id 可以从 memory 本身获取
    # 这里简化处理，用默认 project_id=1
    mm = MemoryManager(project_id=0)  # project_id 不影响 get_memory 查询
    return mm.get_memory(memory_id)


# ============================================================
# 单 Agent 调用（兼容 + 测试用）
# ============================================================

@router.post("/agent/generate")
def agent_generate(payload: AgentGenerateRequest) -> dict:
    """调用单个 Agent（同步）。

    步骤 1：按章节要求和作者选项检索正式上下文。
    步骤 2：补充 Agent 参数并执行对应能力。
    """
    from app.memory.retriever import MemoryRetriever

    # 步骤 1：测试和兼容入口也复用工作流上下文筛选结果。
    retriever = MemoryRetriever(payload.project_id)
    context = retriever.retrieve_for_chapter(
        chapter_no=payload.chapter_no,
        outline_id=payload.outline_id,
        query=payload.instruction,
        selection=payload.context_selection,
    )
    context["chapter_no"] = payload.chapter_no
    context["instruction"] = payload.instruction
    context["rhythm_level"] = payload.rhythm_level

    # 步骤 2：让独立 Agent 与工作流入口使用相同的章节参数。
    agent = get_agent(payload.agent_type, payload.variant)
    result = agent.run(context, {
        "instruction": payload.instruction,
        "rhythm_level": payload.rhythm_level,
    })

    return result


# ============================================================
# 辅助函数
# ============================================================

def _save_chapter_content(
    project_id: int,
    chapter_no: int,
    outline_id: int | None,
    chapter_id: int | None,
    content: str,
    status: str = "draft",
) -> dict:
    """保存最终正文并保留章节已有标题和大纲关联。

    步骤 1：优先按明确章节 ID 定位，其次只复用同号草稿或生成中的章节。
    步骤 2：已有章节只更新本次正文及明确传入的大纲，不覆盖作者维护的标题。
    步骤 3：没有可复用章节时创建默认标题的新章节并返回数据库 ID。
    """
    from app.db.session import get_business_db
    from app.models.business import Chapter

    title = f"第{chapter_no}章"
    with get_business_db() as db:
        if chapter_id:
            chapter = (
                db.query(Chapter)
                .filter(Chapter.id == chapter_id, Chapter.project_id == project_id)
                .first()
            )
        else:
            chapter = (
                db.query(Chapter)
                .filter(
                    Chapter.project_id == project_id,
                    Chapter.chapter_no == chapter_no,
                    Chapter.status.in_(["draft", "generating"]),
                )
                .order_by(Chapter.id.desc())
                .first()
            )

        if chapter:
            if outline_id is not None:
                chapter.outline_id = outline_id
            chapter.chapter_no = chapter_no
            chapter.content = content
            chapter.status = status
            db.commit()
            db.refresh(chapter)
            chapter_id = chapter.id
        else:
            chapter = Chapter(
                project_id=project_id,
                outline_id=outline_id,
                chapter_no=chapter_no,
                title=title,
                content=content,
                status=status,
            )
            db.add(chapter)
            db.commit()
            db.refresh(chapter)
            chapter_id = chapter.id

    return {"chapter_id": chapter_id, "title": title, "content": content}


def _create_generation_version(
    chapter_id: int,
    run_id: str | None,
    content: str,
    summary: str = "",
) -> str | None:
    """创建生成版本记录。"""
    if not chapter_id:
        return None

    word_count = len(content)
    return WorkflowPersistence.create_version(
        chapter_id=chapter_id,
        run_id=run_id,
        content=content,
        word_count=word_count,
        summary=summary,
    )


def _has_persisted_generation_version(run_id: str) -> bool:
    """检查运行是否已经保存过正文版本，避免普通续跑重复落库。"""
    # 步骤 1：按运行 ID 查找版本快照；显式步骤重跑不调用此保护，可产生新版本。
    from app.db.session import get_business_db
    from app.models.business import GenerationVersion

    with get_business_db() as db:
        return db.query(GenerationVersion.id).filter(
            GenerationVersion.run_id == run_id,
        ).first() is not None


def _persist_completed_workflow_output(
    project_id: int,
    chapter_no: int,
    outline_id: int | None,
    chapter_id: int | None,
    result: dict,
) -> dict:
    """统一保存同步、流式及续跑完成的章节结果。

    步骤 1：读取精修最终稿，兼容旧流程的 draft_content。
    步骤 2：保存或创建章节，并把新章节 ID 回填到工作流状态。
    步骤 3：创建正文版本并关联工作流运行记录。
    步骤 4：持久化章节摘要与待审核变化提案。
    """
    session_context = result.setdefault("session_context", {})
    content = session_context.get("final_content") or session_context.get("draft_content", "")
    if not str(content).strip():
        # 步骤 1：completed 但没有正文不是可保存成稿，阻止空版本和空分析进入记忆库。
        raise ValueError("工作流已结束，但没有可保存的最终正文。请从写作步骤重跑。")
    resolved_chapter_id = chapter_id
    version_id = None

    if content:
        saved_chapter = _save_chapter_content(
            project_id,
            chapter_no,
            outline_id,
            chapter_id,
            content,
            status="draft",
        )
        resolved_chapter_id = saved_chapter["chapter_id"]
        session_context["chapter_id"] = resolved_chapter_id

        # 步骤 1：创建版本快照，来源明确指向实际保存的最终正文。
        version_id = _create_generation_version(
            chapter_id=resolved_chapter_id,
            run_id=result.get("run_id"),
            content=content,
            summary=session_context.get("chapter_summary", ""),
        )
        session_context["version_id"] = version_id

    if result.get("run_id") and resolved_chapter_id:
        # 步骤 2：新章节生成时，工作流开始前还没有章节 ID；完成后补上外键。
        from app.db.session import get_business_db
        from app.models.business import WorkflowRun

        with get_business_db() as db:
            run = db.query(WorkflowRun).filter(
                WorkflowRun.run_id == result["run_id"],
                WorkflowRun.project_id == project_id,
            ).first()
            if run:
                run.chapter_id = resolved_chapter_id
                db.commit()

    pending_count = 0
    if resolved_chapter_id:
        # 步骤 3：章节摘要与提案只在工作流成功后落库，正式设定等待人工审核。
        pending_count = _auto_update_memory(
            project_id=project_id,
            chapter_id=resolved_chapter_id,
            chapter_no=chapter_no,
            session_context=session_context,
            run_id=result.get("run_id"),
            version_id=version_id,
        )
    session_context["pending_change_count"] = pending_count
    return {"chapter_id": resolved_chapter_id, "version_id": version_id, "pending_count": pending_count}


def _auto_update_memory(
    project_id: int,
    chapter_id: int | None,
    chapter_no: int,
    session_context: dict,
    run_id: str | None = None,
    version_id: str | None = None,
) -> int:
    """工作流完成后保存章节分析，并生成待审核变化提案。

    步骤 1：读取分析结果并转换为项目内、字段受限的候选变更。
    步骤 2：在业务库事务中更新章节摘要并创建待审核提案。
    步骤 3：记录最终正文的生成统计；正式资料仍等待作者审核后写回。
    """
    if not chapter_id:
        return 0

    mm = MemoryManager(project_id)

    # 步骤 1：分析 Agent 使用开发兜底结果时，仅记录失败状态，不沉淀虚构摘要或提案。
    if session_context.get("analysis_status") == "unavailable":
        from app.db.session import get_business_db
        from app.models.business import GenerationLog

        with get_business_db() as db:
            db.add(GenerationLog(
                project_id=project_id,
                task_type="chapter_analyze",
                request=f"chapter_id={chapter_id}; run_id={run_id or ''}",
                response=session_context.get("analysis_message", "模型服务不可用，未保存分析。"),
                status="failed",
            ))
            db.commit()

        # 即使分析失败，成功生成的正文仍计入使用统计，但不会伪造分析数据。
        content = session_context.get("final_content") or session_context.get("draft_content", "")
        if content:
            mm.record_generation(len(content))
        return 0

    # 步骤 2：从结构化分析解析可审核提案；旧版文本结果不会直接更改资料卡。
    from app.services.chapter_change_proposals import build_proposal_drafts, create_proposals

    structured_analysis = session_context.get("structured_analysis", {})
    entity_catalog = session_context.get("analysis_entity_catalog", {})
    proposal_drafts = build_proposal_drafts(
        structured_analysis,
        entity_catalog,
        chapter_no,
    )

    # 步骤 3：章节摘要和提案同库提交，确保候选来源与摘要保持一致。
    summary = session_context.get("chapter_summary", "")
    pending_count = 0
    if summary or proposal_drafts:
        from app.db.session import get_business_db
        from app.models.business import ChapterSummary

        with get_business_db() as db:
            if summary:
                existing = (
                    db.query(ChapterSummary)
                    .filter(ChapterSummary.chapter_id == chapter_id)
                    .first()
                )
                changes = {
                    "summary": summary,
                    "character_changes": session_context.get("character_changes", ""),
                    "world_changes": session_context.get("world_changes", ""),
                    "new_foreshadowings": session_context.get("new_foreshadowings", ""),
                    "timeline_events": session_context.get("timeline_events", ""),
                    "source_run_id": run_id,
                    "source_version_id": version_id,
                }
                if existing:
                    for key, value in changes.items():
                        setattr(existing, key, value)
                else:
                    db.add(ChapterSummary(chapter_id=chapter_id, **changes))

            # 步骤 4：提案只进入 pending 状态，不自动覆盖人物、组织或其他正式资料。
            if proposal_drafts:
                saved_proposals = create_proposals(
                    db=db,
                    project_id=project_id,
                    chapter_id=chapter_id,
                    run_id=run_id,
                    version_id=version_id,
                    drafts=proposal_drafts,
                )
                pending_count = sum(1 for item in saved_proposals if item["status"] == "pending")
                session_context["pending_change_count"] = pending_count
            db.commit()

    # 步骤 5：将统计与最终正文绑定；精修流程已将正文放在 final_content 中。
    content = session_context.get("final_content") or session_context.get("draft_content", "")
    if content:
        mm.record_generation(len(content))
    return pending_count
