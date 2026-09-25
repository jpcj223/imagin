from __future__ import annotations

from typing import Any

from app.memory.retriever import MemoryRetriever


def build_chapter_context(
    project_id: int,
    chapter_no: int,
    outline_id: int | None = None,
    query: str = "",
    selection: dict[str, list[int]] | None = None,
) -> dict[str, Any]:
    """统一组装章节 Agent 上下文，旧版和 V3 共用同一检索策略。

    步骤 1：将章节号、大纲和用户要求传给项目记忆检索器。
    步骤 2：返回排序后的设定资料、历史摘要和本章可见记忆。
    """
    # 步骤 1：复用生成工作流的记忆检索器，避免预览、旧版与 V3 读取不同资料。
    retriever = MemoryRetriever(project_id)
    return retriever.retrieve_for_chapter(
        chapter_no=chapter_no,
        outline_id=outline_id,
        query=query,
        top_k=10,
        selection=selection,
    )


def build_context_preview(
    project_id: int,
    chapter_no: int,
    outline_id: int | None = None,
    query: str = "",
    selection: dict[str, list[int]] | None = None,
) -> dict[str, Any]:
    """生成章节生成实际会读取的上下文预览。

    步骤 1：调用与生成相同的章节上下文组装入口。
    步骤 2：保留前端需要展示的字段，省略正文和长篇设定详情。
    """
    # 步骤 1：使用与 Agent 相同的检索器、章节边界和用户补充要求。
    context = build_chapter_context(project_id, chapter_no, outline_id, query, selection)
    world = context["world"]
    outline = context["outline"]

    # 步骤 2：压缩成预览卡片所需的数据结构，但列表来源保持与 Agent 输入一致。
    return {
        "chapter_no": chapter_no,
        "outline": {
            "title": outline.get("title", ""),
            "description": outline.get("description", ""),
        },
        "world": {
            "title": world.get("title") or world.get("era", ""),
            "category": world.get("category", ""),
            "rules": world.get("rules", ""),
        },
        "world_settings": [
            {
                "id": item.get("id"),
                "title": item.get("title") or item.get("era", ""),
                "category": item.get("category", ""),
                "importance": item.get("importance", ""),
            }
            for item in context["world_settings"]
        ],
        "characters": [
            {
                "id": item.get("id"),
                "name": item.get("name", ""),
                "role_type": item.get("role_type", ""),
                "motivation": item.get("motivation", ""),
            }
            for item in context["characters"]
        ],
        "organizations": [
            {
                "id": item.get("id"),
                "name": item.get("name", ""),
                "goal": item.get("goal", ""),
                "power_level": item.get("power_level", 0),
                "relations": item.get("relations", []),
            }
            for item in context["organizations"]
        ],
        "foreshadowings": [
            {
                "id": item.get("id"),
                "keyword": item.get("keyword", ""),
                "status": item.get("status", ""),
                "payoff_chapter": item.get("payoff_chapter"),
            }
            for item in context["foreshadowings"]
        ],
        "recent_summaries": [
            {
                "id": item.get("id"),
                "summary": item.get("summary", ""),
                "timeline_events": item.get("timeline_events", ""),
            }
            for item in context["recent_summaries"]
        ],
        "long_term_memories": [
            {
                "memory_id": item.get("memory_id", ""),
                "title": item.get("title") or "",
                "content_summary": (item.get("content_summary") or item.get("content") or "")[:120],
                "importance": item.get("importance") or 0,
                "source_type": item.get("source_type") or "",
            }
            for item in context["long_term_memories"]
        ],
    }
