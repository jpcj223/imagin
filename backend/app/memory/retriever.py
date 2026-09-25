"""记忆检索器。

混合检索策略：关键词检索 + 结构化查询。
（向量检索后续扩展，当前先用关键词+结构化）
"""
from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import func, or_

from app.db.repository import rows_to_dicts
from app.db.session import get_business_db
from app.models.business import (
    Chapter,
    ChapterSummary,
    Character,
    Foreshadowing,
    MemoryItem,
    Organization,
    OrganizationRelation,
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
        selection: dict[str, list[int]] | None = None,
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
        # 步骤 1：先读取本章大纲，再与用户要求合并为统一相关性文本。
        outline = self._get_outline(outline_id, chapter_no)
        relevance_text = "\n".join(
            part for part in (query, outline.get("title", ""), outline.get("description", "")) if part
        )

        # 步骤 2：读取作者选择的实体 ID；未提供类别时保留自动推荐策略。
        selection = selection or None
        selected_character_ids = self._selection_ids(selection, "character_ids")
        selected_organization_ids = self._selection_ids(selection, "organization_ids")
        selected_world_ids = self._selection_ids(selection, "world_setting_ids")
        selected_foreshadowing_ids = self._selection_ids(selection, "foreshadowing_ids")

        # 步骤 3：用同一检索文本排序人物、组织和伏笔，不因关键词不完全匹配而筛空。
        characters = self._get_characters(
            relevance_text,
            top_k=8,
            chapter_no=chapter_no,
            selected_ids=selected_character_ids,
        )
        character_ids = {item.get("id") for item in characters if item.get("id") is not None}
        character_org_ids: set[int] = set()
        for item in characters:
            character_org_ids.update(self._parse_related_ids(item.get("organization_ids")))
        organizations = self._get_organizations(
            relevance_text,
            top_k=5,
            chapter_no=chapter_no,
            linked_organization_ids=character_org_ids,
            selected_ids=selected_organization_ids,
        )
        world_settings = self._get_world_settings(
            selected_ids=selected_world_ids,
            query=relevance_text,
            chapter_no=chapter_no,
        )
        foreshadowings = self._get_foreshadowings(
            relevance_text,
            chapter_no=chapter_no,
            top_k=8,
            outline_id=outline_id,
            character_ids=character_ids,
            organization_ids={item.get("id") for item in organizations if item.get("id") is not None},
            selected_ids=selected_foreshadowing_ids,
        )

        # 步骤 4：只取本章之前可见的已确认记忆，防止补写旧章时读到未来信息。
        result = {
            "project": self._get_project_info(),
            "world": world_settings[0] if world_settings else {},
            "world_settings": world_settings,
            "outline": outline,
            "characters": characters,
            "organizations": organizations,
            "foreshadowings": foreshadowings,
            "recent_summaries": self._get_recent_summaries(chapter_no, limit=5),
            "long_term_memories": self._get_long_term_memories(
                limit=8, chapter_no=chapter_no, query=relevance_text
            ),
        }
        return result

    @staticmethod
    def _selection_ids(selection: dict[str, list[int]] | None, key: str) -> set[int] | None:
        """读取作者固定优先级的实体 ID；空列表表示没有固定优先项。"""
        # 步骤 1：保留接口是否提交此类别的区别；两种情况都会补充自动推荐。
        if selection is None or key not in selection:
            return None

        # 步骤 2：清理传入值，只接收整数 ID。
        result: set[int] = set()
        for item in selection.get(key) or []:
            try:
                result.add(int(item))
            except (TypeError, ValueError):
                continue
        return result

    @staticmethod
    def _ranked_context_items(items: list[dict], top_k: int) -> list[dict]:
        """完整保留强关联资料，再按相关度补足普通推荐项。

        步骤 1：优先取手动选择、正文点名或结构化关联命中的资料。
        步骤 2：用剩余名额补充排序靠前的普通候选。
        步骤 3：移除仅供检索排序使用的临时字段。
        """
        # 步骤 1：先统一按总相关度排序，保持强关联资料内部顺序稳定。
        items.sort(key=lambda item: (item.get("_context_rank", 0), item.get("id", 0)), reverse=True)
        pinned = [item for item in items if item.get("_context_pinned")]
        recommended = [item for item in items if not item.get("_context_pinned")]

        # 步骤 2：强关联数量可超过默认上限；普通推荐只填充剩余空间。
        selected = pinned + recommended[:max(0, top_k - len(pinned))]

        # 步骤 3：提示词和预览只接收业务字段，不泄漏内部排序标记。
        for item in selected:
            item.pop("_context_rank", None)
            item.pop("_context_pinned", None)
        return selected

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
        # 步骤 1：为只支持单条世界观的旧调用方保留兼容入口。
        settings = self._get_world_settings()
        return settings[0] if settings else {}

    def _get_world_settings(
        self,
        selected_ids: set[int] | None = None,
        limit: int = 5,
        query: str = "",
        chapter_no: int | None = None,
    ) -> list[dict]:
        """读取作者所选及按本章内容推荐的世界观条目。

        步骤 1：读取项目设定，确保作者选中的旧条目也不会被候选条数截掉。
        步骤 2：按手动选择、章节关联、正文相关度和重要性排序。
        """
        with get_business_db() as db:
            # 步骤 1：作者可能明确选择较早创建的设定，因此读取整个项目的候选条目。
            db_query = db.query(WorldSetting).filter(WorldSetting.project_id == self.project_id)
            rows = db_query.order_by(WorldSetting.id.desc()).all()
            items = []
            for row in rows:
                items.append({
                    "id": row.id,
                    "title": getattr(row, "title", ""),
                    "era": getattr(row, "era", ""),
                    "category": getattr(row, "category", "other"),
                    "rules": getattr(row, "rules", ""),
                    "geography": getattr(row, "geography", ""),
                    "atmosphere": getattr(row, "atmosphere", ""),
                    "extra": getattr(row, "extra", ""),
                    "tags": getattr(row, "tags", ""),
                    "importance": getattr(row, "importance", "medium"),
                    "related_chapters": getattr(row, "related_chapters", ""),
                    "related_characters": getattr(row, "related_characters", ""),
                    "related_organizations": getattr(row, "related_organizations", ""),
                    "related_foreshadowings": getattr(row, "related_foreshadowings", ""),
                    "conflict_notes": getattr(row, "conflict_notes", ""),
                })

        # 步骤 2：作者选择项置顶，再结合关联章节、主题相关度和重要性补足上下文。
        importance_rank = {"high": 3, "高": 3, "核心": 3, "medium": 2, "中": 2, "low": 1, "低": 1}
        items.sort(
            key=lambda item: (
                100 if selected_ids is not None and item.get("id") in selected_ids else 0,
                80 if chapter_no is not None and self._chapter_is_listed(item.get("related_chapters"), chapter_no) else 0,
                self._overlap_score(
                    query,
                    " ".join(str(item.get(field) or "") for field in (
                        "title", "era", "category", "tags", "rules", "geography",
                        "atmosphere", "extra", "conflict_notes",
                    )),
                    maximum=30,
                ),
                importance_rank.get(str(item.get("importance") or ""), 0),
                item.get("id", 0),
            ),
            reverse=True,
        )
        return items[:max(limit, len(selected_ids or set()))]

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

    @staticmethod
    def _normalize_text(value: Any) -> str:
        """统一比较文本格式，忽略大小写和空白差异。"""
        return re.sub(r"\s+", "", str(value or "")).lower()

    @staticmethod
    def _chapter_is_listed(value: Any, chapter_no: int) -> bool:
        """判断章节号是否出现在明确章节号或数字范围中。

        步骤 1：匹配单章编号。
        步骤 2：匹配“3-8”“第 3 至 8 章”等范围。
        """
        text = str(value or "")
        if re.search(rf"(?<!\d){re.escape(str(chapter_no))}(?!\d)", text):
            return True

        for match in re.finditer(r"(?<!\d)(\d+)\s*[-~至到]\s*(\d+)(?!\d)", text):
            start, end = int(match.group(1)), int(match.group(2))
            if min(start, end) <= chapter_no <= max(start, end):
                return True
        return False

    @classmethod
    def _overlap_score(cls, query: str, candidate: str, maximum: int = 30) -> int:
        """用字符二元组计算轻量中文相关度，作为实体关联之外的排序补充。"""
        # 步骤 1：去除标点空白并拆出连续字符片段，避免单字造成大量误匹配。
        raw_query = str(query or "")
        if len(raw_query) > 4000:
            raw_query = raw_query[:2500] + raw_query[-1500:]
        query_text = re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", cls._normalize_text(raw_query))
        candidate_text = re.sub(
            r"[^0-9a-z\u4e00-\u9fff]", "", cls._normalize_text(str(candidate or "")[:8000])
        )
        if len(query_text) < 2 or len(candidate_text) < 2:
            return 0

        # 步骤 2：以二元组交集计分，并按候选文本长度归一，避免长资料天然占优。
        # 步骤 3：限制候选长度，避免长设定天然占优并控制记忆库排序成本。
        query_pairs = {query_text[index:index + 2] for index in range(len(query_text) - 1)}
        candidate_pairs = {candidate_text[index:index + 2] for index in range(len(candidate_text) - 1)}
        ratio = len(query_pairs & candidate_pairs) / max(1, len(candidate_pairs))
        return min(maximum, round(ratio * maximum))

    @staticmethod
    def _parse_related_ids(value: Any) -> set[int]:
        """解析 JSON 列表或逗号分隔的关联 ID。"""
        # 步骤 1：优先读取结构化 JSON；旧数据格式异常时回退到逗号分隔解析。
        if isinstance(value, list):
            raw_values = value
        else:
            text = str(value or "").strip()
            if not text:
                return set()
            try:
                decoded = json.loads(text)
                if isinstance(decoded, list):
                    raw_values = decoded
                elif isinstance(decoded, str):
                    raw_values = re.split(r"[,，;；\s]+", decoded)
                else:
                    raw_values = [decoded]
            except (json.JSONDecodeError, TypeError):
                raw_values = re.split(r"[,，;；\s]+", text)

        # 步骤 2：只保留正整数，忽略空值和其他说明文本。
        result: set[int] = set()
        for item in raw_values:
            try:
                result.add(int(item))
            except (TypeError, ValueError):
                continue
        return result

    def _get_characters(
        self,
        query: str = "",
        top_k: int = 8,
        chapter_no: int | None = None,
        selected_ids: set[int] | None = None,
    ) -> list[dict]:
        """按本章明确提及、出场章节和角色类型排序，保留核心人物兜底。"""
        with get_business_db() as db:
            # 步骤 1：取项目内全部人物后在应用层排序，不用整句补充要求作为 SQL 硬过滤条件。
            query_obj = db.query(Character).filter(Character.project_id == self.project_id)
            rows = query_obj.order_by(Character.sort_index.asc(), Character.id.desc()).all()
            items = rows_to_dicts(rows)

        # 步骤 2：优先保留用户明确提到的人物和主角，再用章节线索及资料相似度补足。
        query_text = self._normalize_text(query)
        for item in items:
            name = self._normalize_text(item.get("name"))
            role_type = self._normalize_text(item.get("role_type"))
            role_score = 24 if role_type in {"main", "protagonist", "主角", "主线角色"} else 0
            explicit_score = 120 if name and name in query_text else 0
            selected_score = 200 if selected_ids is not None and item.get("id") in selected_ids else 0
            chapter_score = (
                20
                if chapter_no is not None and self._chapter_is_listed(item.get("chapters"), chapter_no)
                else 0
            )
            profile = " ".join(
                str(item.get(field) or "")
                for field in (
                    "identity", "personality", "motivation", "background", "faction",
                    "appearance", "arc", "weakness", "secret", "dialogue_style",
                )
            )
            relevance_score = self._overlap_score(query, profile, maximum=20)
            inactive_score = -12 if str(item.get("status") or "").lower() in {"inactive", "archived", "停用", "隐藏"} else 0
            item["_context_rank"] = selected_score + explicit_score + role_score + chapter_score + relevance_score + inactive_score
            item["_context_pinned"] = bool(
                selected_score
                or explicit_score
                or (role_score and not inactive_score)
            )

        return self._ranked_context_items(items, top_k)

    def _get_organizations(
        self,
        query: str = "",
        top_k: int = 5,
        chapter_no: int = 1,
        linked_organization_ids: set[int] | None = None,
        selected_ids: set[int] | None = None,
    ) -> list[dict]:
        """获取本章仍有效的相关组织，以及有效的组织关系。"""
        with get_business_db() as db:
            query_obj = db.query(Organization).filter(
                Organization.project_id == self.project_id
            )
            query_obj = query_obj.filter(
                (Organization.active_from_chapter.is_(None))
                | (Organization.active_from_chapter <= chapter_no)
            ).filter(
                (Organization.disbanded_chapter.is_(None))
                | (Organization.disbanded_chapter >= chapter_no)
            )

            # 步骤 1：读取所有在本章有效的组织，之后按选择、名称、人物关联和描述相关度排序。
            rows = query_obj.order_by(Organization.id.desc()).all()
            items = rows_to_dicts(rows)
            query_text = self._normalize_text(query)
            linked_organization_ids = linked_organization_ids or set()
            for item in items:
                name = self._normalize_text(item.get("name"))
                explicit_score = 120 if name and name in query_text else 0
                selected_score = 200 if selected_ids is not None and item.get("id") in selected_ids else 0
                linked_score = 45 if item.get("id") in linked_organization_ids else 0
                profile = " ".join(
                    str(item.get(field) or "")
                    for field in ("goal", "description", "location", "resources", "slogan")
                )
                try:
                    power_score = max(0, min(20, int(item.get("power_level") or 0) * 2))
                except (TypeError, ValueError):
                    power_score = 0
                item["_context_rank"] = (
                    selected_score
                    + explicit_score
                    + linked_score
                    + power_score
                    + self._overlap_score(query, profile, maximum=25)
                )
                item["_context_pinned"] = bool(selected_score or explicit_score or linked_score)
            items = self._ranked_context_items(items, top_k)
            organization_ids = [item["id"] for item in items]
            if not organization_ids:
                return items

            # 步骤 1：按本章章节号筛选关系，跳过尚未生效或已经失效的势力关系。
            active_organization_ids = [
                row.id
                for row in db.query(Organization.id).filter(
                    Organization.project_id == self.project_id,
                    (Organization.active_from_chapter.is_(None))
                    | (Organization.active_from_chapter <= chapter_no),
                    (Organization.disbanded_chapter.is_(None))
                    | (Organization.disbanded_chapter >= chapter_no),
                ).all()
            ]
            relations = db.query(OrganizationRelation).filter(
                OrganizationRelation.project_id == self.project_id,
                (
                    OrganizationRelation.organization_a_id.in_(organization_ids)
                    | OrganizationRelation.organization_b_id.in_(organization_ids)
                ),
                (OrganizationRelation.effective_from_chapter.is_(None))
                | (OrganizationRelation.effective_from_chapter <= chapter_no),
                (OrganizationRelation.expires_at_chapter.is_(None))
                | (OrganizationRelation.expires_at_chapter >= chapter_no),
                OrganizationRelation.organization_a_id.in_(active_organization_ids),
                OrganizationRelation.organization_b_id.in_(active_organization_ids),
            ).order_by(OrganizationRelation.id.asc()).all()
            related_ids = {
                org_id
                for relation in relations
                for org_id in (relation.organization_a_id, relation.organization_b_id)
            }
            names = {
                row.id: row.name
                for row in db.query(Organization.id, Organization.name).filter(
                    Organization.project_id == self.project_id,
                    Organization.id.in_(related_ids),
                ).all()
            }

            # 步骤 2：双向挂载关系，保证从任何一方检索组织时都能读到同盟和敌对状态。
            by_organization: dict[int, list[dict]] = {}
            for relation in relations:
                for current_id, target_id in (
                    (relation.organization_a_id, relation.organization_b_id),
                    (relation.organization_b_id, relation.organization_a_id),
                ):
                    by_organization.setdefault(current_id, []).append({
                        "target_org_id": target_id,
                        "target_org_name": names.get(target_id, ""),
                        "relation_type": relation.relation_type,
                        "description": relation.description or "",
                        "effective_from_chapter": relation.effective_from_chapter,
                        "expires_at_chapter": relation.expires_at_chapter,
                    })
            for item in items:
                item["relations"] = by_organization.get(item["id"], [])
            return items

    def _get_foreshadowings(
        self,
        query: str = "",
        chapter_no: int | None = None,
        top_k: int = 8,
        outline_id: int | None = None,
        character_ids: set[int] | None = None,
        organization_ids: set[int] | None = None,
        selected_ids: set[int] | None = None,
    ) -> list[dict]:
        """获取当前章节有效的伏笔（待埋、已埋、发展中和待回收）。"""
        with get_business_db() as db:
            query_obj = db.query(Foreshadowing).filter(
                Foreshadowing.project_id == self.project_id,
                Foreshadowing.status.in_(["pending", "planted", "developing", "payoff_pending"]),
            )

            # 步骤 1：按生效和失效章节筛选；计划回收只作提醒，不从上下文中提前剔除。
            if chapter_no is not None:
                query_obj = query_obj.filter(
                    func.coalesce(Foreshadowing.effective_from, Foreshadowing.planted_chapter, 1) <= chapter_no,
                    or_(Foreshadowing.expires_at.is_(None), Foreshadowing.expires_at >= chapter_no),
                )

            # 步骤 2：关联伏笔和作者选择项优先，名称和补充要求只用于增权，不作排除。
            rows = query_obj.order_by(Foreshadowing.id.desc()).all()
            items = rows_to_dicts(rows)
            query_text = self._normalize_text(query)
            character_ids = character_ids or set()
            organization_ids = organization_ids or set()
            status_scores = {
                "payoff_pending": 18,
                "developing": 14,
                "planted": 10,
                "pending": 6,
            }
            importance_scores = {"high": 16, "medium": 10, "low": 4, "核心": 16, "高": 16, "中": 10, "低": 4}
            for item in items:
                keyword = self._normalize_text(item.get("keyword"))
                explicit_score = 120 if keyword and keyword in query_text else 0
                selected_score = 200 if selected_ids is not None and item.get("id") in selected_ids else 0
                outline_score = 65 if outline_id in self._parse_related_ids(item.get("related_outline_ids")) else 0
                related_characters = self._parse_related_ids(item.get("related_character_ids"))
                character_score = 35 if related_characters & character_ids else 0
                related_organizations = self._parse_related_ids(item.get("related_organization_ids"))
                organization_score = 30 if related_organizations & organization_ids else 0
                profile = " ".join(
                    str(item.get(field) or "")
                    for field in ("keyword", "description", "notes")
                )
                item["_context_rank"] = (
                    selected_score
                    + explicit_score
                    + outline_score
                    + character_score
                    + organization_score
                    + status_scores.get(str(item.get("status") or ""), 0)
                    + importance_scores.get(str(item.get("importance") or ""), 0)
                    + self._overlap_score(query, profile, maximum=20)
                )
                item["_context_pinned"] = bool(
                    selected_score or explicit_score or outline_score or character_score or organization_score
                )
            return self._ranked_context_items(items, top_k)

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

    def _get_long_term_memories(
        self, limit: int = 8, chapter_no: int | None = None, query: str = ""
    ) -> list[dict]:
        """读取本章可见的已确认记忆，过滤未来来源后按重要性和相关性排序。"""
        with get_business_db() as db:
            # 步骤 1：多取一批候选记忆，以便过滤未来章节来源后仍有足够上下文。
            rows = (
                db.query(MemoryItem)
                .filter(MemoryItem.project_id == self.project_id)
                .order_by(MemoryItem.importance.desc(), MemoryItem.updated_at.desc())
                .limit(max(limit * 20, 100))
                .all()
            )
            items = rows_to_dicts(rows)
            source_chapter_ids = {
                int(match.group(1))
                for item in items
                if (match := re.search(r"(?:^|:)chapter:(\d+)(?::|$)", str(item.get("source_ref") or "")))
            }
            chapter_numbers = {
                row.id: row.chapter_no
                for row in db.query(Chapter.id, Chapter.chapter_no).filter(
                    Chapter.project_id == self.project_id,
                    Chapter.id.in_(source_chapter_ids or {-1}),
                ).all()
            }

        # 步骤 2：剔除来源为当前章或后续章节的记忆，避免补写时提前读到后文。
        visible_items = []
        query_text = self._normalize_text(query)
        for item in items:
            match = re.search(r"(?:^|:)chapter:(\d+)(?::|$)", str(item.get("source_ref") or ""))
            source_chapter_no = chapter_numbers.get(int(match.group(1))) if match else None
            if chapter_no is not None and source_chapter_no is not None and source_chapter_no >= chapter_no:
                continue

            # 步骤 3：先按记忆重要度排序，再将与本章大纲/补充要求直接相关的条目提到前面。
            title = str(item.get("title") or "")
            content = str(item.get("content_summary") or item.get("content") or "")
            exact_score = 80 if self._normalize_text(title) and self._normalize_text(title) in query_text else 0
            relevance_score = self._overlap_score(query, f"{title} {content}", maximum=24)
            item["_context_rank"] = exact_score + relevance_score + max(0, int(item.get("importance") or 0)) // 4
            visible_items.append(item)

        visible_items.sort(key=lambda item: (item.get("_context_rank", 0), item.get("updated_at") or ""), reverse=True)
        selected = visible_items[:limit]
        for item in selected:
            item.pop("_context_rank", None)
        return selected

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
        long_term_memories = memory_bundle.get("long_term_memories", [])

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
                relations = org.get("relations", [])
                if relations:
                    relation_labels = [
                        f"{'盟友' if relation.get('relation_type') == 'alliance' else '敌对'}：{relation.get('target_org_name', '')}"
                        for relation in relations[:6]
                        if relation.get("target_org_name")
                    ]
                    if relation_labels:
                        line += " - 势力关系：" + "、".join(relation_labels)
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

        lines.append("")
        lines.append("=== 已确认长期记忆 ===")
        if long_term_memories:
            for memory in long_term_memories[:8]:
                title = memory.get("title", "")
                content = memory.get("content_summary") or memory.get("content", "")
                if title or content:
                    lines.append(f"- {title}：{content[:120]}")
        else:
            lines.append("（暂无已确认的长期记忆）")

        return "\n".join(lines)
