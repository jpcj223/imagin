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

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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


class WorkflowResumeRequest(BaseModel):
    """断点续传请求。"""
    run_id: str
    chapter_no: int
    outline_id: int | None = None
    instruction: str = ""
    rhythm_level: str = "medium"
    restart_from_step_id: str | None = None  # 从指定步骤开始重跑（可选）


class AgentGenerateRequest(BaseModel):
    """单个 Agent 调用请求。"""
    project_id: int
    chapter_no: int
    outline_id: int | None = None
    agent_type: str = "writer"
    variant: str = "default"
    instruction: str = ""
    rhythm_level: str = "medium"


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
    )

    # 保存到章节表（向后兼容）
    content = result.get("session_context", {}).get("draft_content", "")
    if content and payload.chapter_id:
        _save_chapter_content(
            payload.project_id,
            payload.chapter_no,
            payload.outline_id,
            payload.chapter_id,
            content,
            status="draft",
        )
        # 创建生成版本
        _create_generation_version(
            chapter_id=payload.chapter_id,
            run_id=result.get("run_id"),
            content=content,
            summary=result.get("session_context", {}).get("chapter_summary", ""),
        )

    # 工作流完成后自动更新记忆
    if result.get("status") == "completed":
        _auto_update_memory(
            project_id=payload.project_id,
            chapter_id=payload.chapter_id,
            chapter_no=payload.chapter_no,
            session_context=result.get("session_context", {}),
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
            ):
                # 收集正文内容用于保存
                if event.get("type") == "delta" and event.get("step_id") == "writer":
                    content_buffer.append(event.get("content", ""))

                # 记录最终结果
                if event.get("type") == "workflow_done":
                    final_result = event

                yield json.dumps(event, ensure_ascii=False) + "\n"

            # 工作流完成后保存
            if content_buffer and payload.chapter_id:
                content = "".join(content_buffer)
                chapter_info = _save_chapter_content(
                    payload.project_id,
                    payload.chapter_no,
                    payload.outline_id,
                    payload.chapter_id,
                    content,
                    status="draft",
                )

                # 创建生成版本
                summary = ""
                if final_result:
                    summary = final_result.get("session_context", {}).get("chapter_summary", "")
                _create_generation_version(
                    chapter_id=payload.chapter_id,
                    run_id=final_result.get("run_id") if final_result else None,
                    content=content,
                    summary=summary,
                )

                # 自动更新记忆
                if final_result and final_result.get("status") == "completed":
                    _auto_update_memory(
                        project_id=payload.project_id,
                        chapter_id=payload.chapter_id,
                        chapter_no=payload.chapter_no,
                        session_context=final_result.get("session_context", {}),
                    )

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

            for event in engine.run_stream(
                chapter_no=payload.chapter_no,
                outline_id=payload.outline_id,
                instruction=payload.instruction,
                rhythm_level=payload.rhythm_level,
            ):
                yield json.dumps(event, ensure_ascii=False) + "\n"

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
    """调用单个 Agent（同步）。"""
    from app.memory.retriever import MemoryRetriever

    retriever = MemoryRetriever(payload.project_id)
    context = retriever.retrieve_for_chapter(
        chapter_no=payload.chapter_no,
        outline_id=payload.outline_id,
    )
    context["chapter_no"] = payload.chapter_no
    context["instruction"] = payload.instruction
    context["rhythm_level"] = payload.rhythm_level

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
    """保存章节内容（复用现有逻辑，兼容旧 API）。"""
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
                .filter(Chapter.project_id == project_id, Chapter.chapter_no == chapter_no)
                .order_by(Chapter.id.desc())
                .first()
            )

        if chapter:
            chapter.outline_id = outline_id
            chapter.chapter_no = chapter_no
            chapter.title = title
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


def _auto_update_memory(
    project_id: int,
    chapter_id: int | None,
    chapter_no: int,
    session_context: dict,
) -> None:
    """工作流完成后自动更新记忆。

    1. 如果有章节摘要，写入 chapter_summary 表
    2. 记录生成统计
    """
    if not chapter_id:
        return

    mm = MemoryManager(project_id)

    # 1. 写入章节摘要
    summary = session_context.get("chapter_summary", "")
    if summary:
        from app.db.session import get_business_db
        from app.models.business import ChapterSummary

        with get_business_db() as db:
            existing = (
                db.query(ChapterSummary)
                .filter(ChapterSummary.chapter_id == chapter_id)
                .first()
            )
            if existing:
                existing.summary = summary
                existing.character_changes = session_context.get("character_changes", "")
                existing.world_changes = session_context.get("world_changes", "")
                db.commit()
            else:
                cs = ChapterSummary(
                    chapter_id=chapter_id,
                    summary=summary,
                    character_changes=session_context.get("character_changes", ""),
                    world_changes=session_context.get("world_changes", ""),
                )
                db.add(cs)
                db.commit()

    # 2. 更新统计数据
    content = session_context.get("draft_content", "")
    if content:
        mm.record_generation(len(content))
