"""记忆检索器。

混合检索策略：关键词检索 + 结构化查询。
（向量检索后续扩展，当前先用关键词+结构化）
"""
from __future__ import annotations

from typing import Any

from app.db.repository import rows_to_dicts
from app.db.session import get_business_db
from app.models.business import (
    Chapter,
    ChapterSummary,
    Character,
    Foreshadowing,
    MemoryItem,
    Organization,
    WorldSetting,
)


class MemoryRetriever:
    """记忆检索器。

    从项目记忆中检索与当前任务最相关的内容，
    组装成适合注入 LLM Prompt 的格式。
    """

    def __init__(self, project_id: int):
        self.project_id = project_id

    def retrieve_for_chapter(
        self,
        chapter_no: int,
        outline_id: int | None = None,
        query: str = "",
        top_k: int = 10,
    ) -> dict[str, Any]:
        """为章节生成检索相关记忆。

        Args:
            chapter_no: 章节号
            outline_id: 大纲 ID
            query: 查询关键词（从大纲中提取）
            top_k: 返回结果数量上限

        Returns:
            结构化的记忆包，可直接用于构建上下文
        """
        result = {
            "project": self._get_project_info(),
            "world": self._get_world_setting(),
            "outline": self._get_outline(outline_id, chapter_no),
            "characters": self._get_characters(query, top_k=8),
            "organizations": self._get_organizations(query, top_k=5),
            "foreshadowings": self._get_foreshadowings(query, top_k=8),
            "recent_summaries": self._get_recent_summaries(chapter_no, limit=5),
        }
        return result

    def _get_project_info(self) -> dict:
        """获取项目基本信息。"""
        from app.models.business import Project
        with get_business_db() as db:
            row = db.query(Project).filter(Project.id == self.project_id).first()
            if row:
                return {
                    "id": row.id,
                    "name": row.name,
                    "theme": row.theme,
                    "novel_type": row.novel_type,
                    "writing_style": getattr(row, "writing_style", ""),
                    "view_point": getattr(row, "view_point", ""),
                    "pace_level": getattr(row, "pace_level", 3),
                }
            return {}

    def _get_world_setting(self) -> dict:
        """获取世界观设定。"""
        with get_business_db() as db:
            row = (
                db.query(WorldSetting)
                .filter(WorldSetting.project_id == self.project_id)
                .order_by(WorldSetting.id.desc())
                .first()
            )
            if row:
                return {
                    "id": row.id,
                    "title": getattr(row, "title", ""),
                    "era": getattr(row, "era", ""),
                    "category": getattr(row, "category", "other"),
                    "rules": getattr(row, "rules", ""),
                    "geography": getattr(row, "geography", ""),
                    "atmosphere": getattr(row, "atmosphere", ""),
                }
            return {}

    def _get_outline(self, outline_id: int | None, chapter_no: int) -> dict:
        """获取本章大纲。"""
        from app.models.business import Outline
        from sqlalchemy import or_

        with get_business_db() as db:
            if outline_id:
                row = (
                    db.query(Outline)
                    .filter(Outline.id == outline_id, Outline.project_id == self.project_id)
                    .first()
                )
            else:
                row = (
                    db.query(Outline)
                    .filter(
                        Outline.project_id == self.project_id,
                        or_(Outline.chapter_no == chapter_no, Outline.sort_index == chapter_no),
                    )
                    .order_by(Outline.chapter_no.desc(), Outline.id.desc())
                    .first()
                )
            if row:
                return {
                    "id": row.id,
                    "title": row.title,
                    "description": row.description,
                    "chapter_no": row.chapter_no or chapter_no,
                    "status": row.status,
                }
            return {}

    def _get_characters(self, query: str = "", top_k: int = 8) -> list[dict]:
        """获取相关人物。

        当前按重要性和最近修改排序。
        后续可以加入关键词匹配和向量相似度。
        """
        with get_business_db() as db:
            query_obj = db.query(Character).filter(
                Character.project_id == self.project_id
            )

            # 如果有查询词，做简单的关键词匹配
            if query:
                keyword = f"%{query}%"
                from sqlalchemy import or_
                query_obj = query_obj.filter(
                    or_(
                        Character.name.like(keyword),
                        Character.personality.like(keyword),
                        Character.identity.like(keyword),
                    )
                )

            rows = query_obj.order_by(Character.id.desc()).limit(top_k).all()
            return rows_to_dicts(rows)

    def _get_organizations(self, query: str = "", top_k: int = 5) -> list[dict]:
        """获取相关组织。"""
        with get_business_db() as db:
            query_obj = db.query(Organization).filter(
                Organization.project_id == self.project_id
            )

            if query:
                keyword = f"%{query}%"
                from sqlalchemy import or_
                query_obj = query_obj.filter(
                    or_(
                        Organization.name.like(keyword),
                        Organization.goal.like(keyword),
                    )
                )

            rows = query_obj.order_by(Organization.id.desc()).limit(top_k).all()
            return rows_to_dicts(rows)

    def _get_foreshadowings(self, query: str = "", top_k: int = 8) -> list[dict]:
        """获取相关伏笔（待埋+已埋+发展中）。"""
        with get_business_db() as db:
            query_obj = db.query(Foreshadowing).filter(
                Foreshadowing.project_id == self.project_id,
                Foreshadowing.status.in_(["pending", "planted", "developing"]),
            )

            if query:
                keyword = f"%{query}%"
                from sqlalchemy import or_
                query_obj = query_obj.filter(
                    or_(
                        Foreshadowing.keyword.like(keyword),
                        Foreshadowing.description.like(keyword),
                    )
                )

            rows = query_obj.order_by(Foreshadowing.id.desc()).limit(top_k).all()
            return rows_to_dicts(rows)

    def _get_recent_summaries(self, chapter_no: int, limit: int = 5) -> list[dict]:
        """获取最近几章的摘要。"""
        with get_business_db() as db:
            rows = (
                db.query(ChapterSummary)
                .join(Chapter, Chapter.id == ChapterSummary.chapter_id)
                .filter(
                    Chapter.project_id == self.project_id,
                    Chapter.chapter_no < chapter_no,
                )
                .order_by(Chapter.chapter_no.desc())
                .limit(limit)
                .all()
            )
            return rows_to_dicts(rows)

    def build_context_prompt(self, memory_bundle: dict) -> str:
        """把记忆包格式化成 Prompt 文本。

        用于直接注入 LLM 的上下文中。
        """
        project = memory_bundle.get("project", {})
        world = memory_bundle.get("world", {})
        outline = memory_bundle.get("outline", {})
        characters = memory_bundle.get("characters", [])
        organizations = memory_bundle.get("organizations", [])
        foreshadowings = memory_bundle.get("foreshadowings", [])
        recent_summaries = memory_bundle.get("recent_summaries", [])

        lines = []
        lines.append("=== 项目信息 ===")
        lines.append(f"名称：{project.get('name', '')}")
        lines.append(f"类型：{project.get('novel_type', '')}")
        if project.get("writing_style"):
            lines.append(f"风格：{project['writing_style']}")
        lines.append("")

        lines.append("=== 世界观设定 ===")
        if world.get("title") or world.get("era"):
            lines.append(f"背景：{world.get('title') or world.get('era', '')}")
        if world.get("rules"):
            lines.append(f"核心规则：{world['rules']}")
        if not any(world.values()):
            lines.append("（暂无详细设定）")
        lines.append("")

        lines.append("=== 本章大纲 ===")
        if outline.get("title"):
            lines.append(f"标题：{outline['title']}")
        if outline.get("description"):
            lines.append(f"内容：{outline['description']}")
        lines.append("")

        lines.append("=== 出场人物 ===")
        if characters:
            for ch in characters[:6]:
                name = ch.get("name", "未知")
                role = ch.get("role_type", "")
                personality = ch.get("personality", "")
                line = f"- {name}"
                if role:
                    line += f"（{role}）"
                if personality:
                    line += f" - {personality[:30]}"
                lines.append(line)
        else:
            lines.append("（暂无）")
        lines.append("")

        lines.append("=== 相关组织 ===")
        if organizations:
            for org in organizations[:4]:
                name = org.get("name", "")
                org_type = org.get("org_type", "")
                goal = org.get("goal", "")
                line = f"- {name}"
                if org_type:
                    line += f"（{org_type}）"
                if goal:
                    line += f" - {goal[:25]}"
                lines.append(line)
        else:
            lines.append("（暂无）")
        lines.append("")

        lines.append("=== 待处理伏笔 ===")
        if foreshadowings:
            for f in foreshadowings[:6]:
                keyword = f.get("keyword", "")
                status = f.get("status", "")
                desc = f.get("description", "")
                line = f"- [{status}] {keyword}"
                if desc:
                    line += f"：{desc[:30]}"
                lines.append(line)
        else:
            lines.append("（暂无）")
        lines.append("")

        lines.append("=== 前情提要 ===")
        if recent_summaries:
            for i, s in enumerate(recent_summaries[:3]):
                summary = s.get("summary", "")
                if summary:
                    lines.append(f"第{len(recent_summaries)-i}章：{summary[:60]}...")
        else:
            lines.append("（暂无历史章节）")

        return "\n".join(lines)
