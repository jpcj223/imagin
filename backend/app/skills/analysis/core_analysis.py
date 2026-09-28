"""核心分析 Skill。

Analyzer Agent 的核心能力，抽取章节摘要等基础信息。
"""
from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from app.schemas.chapter_analysis import ChapterAnalysis
from app.skills.base import BaseSkill, SkillMeta
from app.skills.registry import SkillRegistry


@SkillRegistry.register("core_analysis")
class CoreAnalysisSkill(BaseSkill):
    """核心分析 Skill。

    抽取章节摘要、世界观变化、时间线事件等基础信息。
    """

    meta = SkillMeta(
        name="core_analysis",
        label="核心分析",
        description="抽取章节摘要、世界观变化、时间线等基础信息",
        category="analysis",
        agent_types=["analyzer"],
        priority=10,
        is_core=True,
    )

    prompt_fragment = """
请分析本章正文，并且只输出一个合法 JSON 对象，不要加 Markdown 代码块或解释。
按下面结构填写；没有内容时使用空字符串或空数组：
{
  "summary": "200 字以内的章节摘要",
  "character_changes": [{"name": "人物名", "operation": "update", "changes": {"personality": "仅填写确实改变的人物卡字段"}, "rationale": "变化理由", "evidence": "正文依据"}],
  "relationships": [{"source_name": "关系发起方", "target_name": "关系另一方", "operation": "create", "relation_type": "关系描述", "depth": 3, "effective_from": 1, "expires_at": null, "rationale": "变化理由", "evidence": "正文依据"}],
  "organization_changes": [{"name": "组织名", "operation": "update", "changes": {"goal": "仅填写确实改变的组织字段"}, "rationale": "变化理由", "evidence": "正文依据"}],
  "organization_relations": [{"source_name": "关系发起组织", "target_name": "关系另一组织", "operation": "create", "relation_type": "alliance", "description": "关系说明", "effective_from_chapter": 1, "expires_at_chapter": null, "rationale": "变化理由", "evidence": "正文依据"}],
  "foreshadowing_changes": [{"keyword": "伏笔关键词", "operation": "create", "target_keyword": null, "changes": {"keyword": "伏笔关键词", "description": "伏笔内容", "status": "planted"}, "rationale": "作用", "evidence": "正文依据"}],
  "world_changes": [{"title": "设定名称", "operation": "update", "changes": {"rules": "仅填写确实新增或修正的设定字段"}, "rationale": "变化理由", "evidence": "正文依据"}],
  "timeline_events": [{"title": "事件标题", "content": "事件经过", "importance": 60}]
}

约束：
1. 仅输出正文明确支持的变化，不把推测写成事实；evidence 使用能定位变化的短句。
2. 已有实体使用 update；只有确认为新人物/组织/伏笔/设定时才使用 create。
3. 人物 changes 只使用人物卡字段：name、role_type、mbti、mbti_primary、mbti_secondary、appearance、personality、background、motivation、arc、identity、faction、weakness、secret、dialogue_style、ai_notes、status。
4. 组织 changes 只使用组织资料字段：parent_id、name、org_type、location、slogan、description、level、power_level、member_count、status、hierarchy、resources、goal、core_members、impact、risk_notes、hidden_secrets、active_from_chapter、disbanded_chapter、hierarchy_system、hierarchy_levels。
5. 组织同盟/敌对关系变化单独写入 organization_relations；source_name 和 target_name 必须是上下文中的组织名称，relation_type 只能是 alliance 或 hostility。已有组织对关系更新时用 update，并填写 target_effective_from_chapter 以定位原关系；不允许把旧的 allies/enemies 文本字段当作结构化关系变化。
6. 伏笔 changes 只使用 keyword、description、status、importance、planted_chapter、payoff_chapter、effective_from、expires_at、notes、related_character_ids、related_organization_ids、related_outline_ids、replaced_by_id。status 只能是 pending、planted、developing、payoff_pending、resolved、abandoned；resolved 表示正文已明确完成回收。
7. 世界观 changes 只使用 era、geography、atmosphere、rules、extra、title、category、tags、importance、related_chapters、related_characters、related_organizations、related_foreshadowings、conflict_notes。
   category 使用 geography、era、power_system、rules、items、weapons、medicine、creatures、organizations、other 之一。
8. relationships 描述人物关系新增或明确变化；已有 source-target 关系变化时使用 update，相同关系不要重复提出；人物名必须与上下文资料或正文中的明确新人物一致，不编造数据库 ID。
9. 纯情绪或短暂动作不改写人物卡；可以作为时间线事件记录。
""".strip()

    produced_outputs = [
        "summary", "character_changes", "world_changes", "new_foreshadowings",
        "timeline_events", "structured_analysis", "organization_relations",
    ]

    def pre_process(self, context, params):
        """把章节相关的项目资料整理成分析上下文，帮助实体名称精确对齐。

        步骤 1：保留正文提及或作者手动选中的人物、组织、设定和伏笔。
        步骤 2：压缩保留字段，供变化识别时对照。
        步骤 3：将精简实体目录注入分析提示词。
        """
        world = context.get("world") or {}
        chapter_text = str(context.get("content") or context.get("draft_content") or "")
        folded_text = chapter_text.casefold()
        manual_selection = context.get("manual_context_selection") or {}
        selected_context = context.get("context_selection") or {}
        selected_ids_by_category = {
            category: {
                str(item_id)
                for source in (selected_context, manual_selection)
                for item_id in (source.get(category) or [])
            }
            for category in (
                "character_ids", "organization_ids", "world_setting_ids", "foreshadowing_ids"
            )
        }

        def is_selected(item: dict[str, Any], category: str) -> bool:
            item_id = item.get("id")
            return item_id is not None and str(item_id) in selected_ids_by_category.get(category, set())

        def is_relevant(item: dict[str, Any], category: str, fields: tuple[str, ...]) -> bool:
            if is_selected(item, category):
                return True
            return any(
                len(term) >= 2 and term.casefold() in folded_text
                for term in (str(item.get(field) or "").strip() for field in fields)
            )

        def relevant_items(key: str, category: str, fields: tuple[str, ...]) -> list[dict[str, Any]]:
            values = context.get(key)
            if not isinstance(values, list):
                return []
            return [
                item for item in values
                if isinstance(item, dict) and is_relevant(item, category, fields)
            ]

        def compact(value: Any, limit: int = 240) -> str:
            return str(value or "").strip()[:limit]

        def compact_relations(value: Any) -> list[str | dict[str, str]]:
            if not isinstance(value, list):
                return []
            compacted = []
            for relation in value[:8]:
                if isinstance(relation, dict):
                    compacted.append({
                        str(key): compact(item, 120)
                        for key, item in list(relation.items())[:6]
                    })
                else:
                    compacted.append(compact(relation, 120))
            return compacted

        world_settings = relevant_items("world_settings", "world_setting_ids", ("title",))
        character_items = relevant_items("characters", "character_ids", ("name",))
        organizations = relevant_items("organizations", "organization_ids", ("name",))
        foreshadowings = relevant_items("foreshadowings", "foreshadowing_ids", ("keyword",))
        character_names = {
            item.get("id"): item.get("name", "")
            for item in character_items
            if item.get("id") is not None
        }
        references = {
            "characters": [
                {
                    "name": compact(item.get("name"), 80),
                    "identity": compact(item.get("identity"), 120),
                    "faction": compact(item.get("faction"), 100),
                    "status": compact(item.get("status"), 60),
                    "personality": compact(item.get("personality"), 240),
                    "relationships": [
                        {
                            "target_name": compact(
                                relation.get("target_name")
                                or character_names.get(relation.get("target_id"), ""), 80
                            ),
                            "relation_type": compact(relation.get("relation_type"), 80),
                        }
                        for relation in _read_relation_list(item.get("character_relations"))[:8]
                        if isinstance(relation, dict)
                    ],
                }
                for item in character_items
            ],
            "organizations": [
                {
                    "name": compact(item.get("name"), 100),
                    "org_type": compact(item.get("org_type"), 80),
                    "status": compact(item.get("status"), 60),
                    "goal": compact(item.get("goal"), 240),
                    "relations": compact_relations(item.get("relations")),
                } for item in organizations
            ],
            "foreshadowings": [
                {
                    "keyword": compact(item.get("keyword"), 100),
                    "status": compact(item.get("status"), 60),
                    "description": compact(item.get("description"), 260),
                } for item in foreshadowings
            ],
            "world": {
                key: compact(world.get(key), 400)
                for key in ("title", "era", "geography", "atmosphere", "rules", "extra")
            },
            "world_settings": [
                {
                    key: compact(item.get(key), 360)
                    for key in ("title", "era", "category", "geography", "atmosphere", "rules", "extra")
                }
                for item in world_settings
            ],
        }
        processed = dict(context)
        # 只注入正文提及的实体与作者手动指定的资料，避免把整个项目名录重复塞入分析请求。
        processed["_analysis_reference_context"] = json.dumps(
            references, ensure_ascii=False, separators=(",", ":")
        )
        return processed

    def post_process(self, result, context, params):
        """按步骤解析结构化 JSON；兼容旧版章节分析文本输出。"""
        analysis_text = result.get("analysis_text", "")
        if not analysis_text:
            return result

        # 步骤 1：尝试提取并验证新的结构化分析契约。
        structured = _parse_structured_analysis(analysis_text)
        if structured:
            data = structured.model_dump()
            # 保留关系字段是否由模型明确给出，更新关系时不把未提及的深度/期限重置成默认值。
            data["relationships"] = [
                item.model_dump(exclude_unset=True)
                for item in structured.relationships
            ]
            data["organization_relations"] = [
                item.model_dump(exclude_unset=True)
                for item in structured.organization_relations
            ]
            result["structured_analysis"] = data
            result["summary"] = data["summary"]
            result["character_changes"] = _render_json(data["character_changes"])
            result["world_changes"] = _render_json(data["world_changes"])
            result["new_foreshadowings"] = _render_json(data["foreshadowing_changes"])
            result["timeline_events"] = _render_json(data["timeline_events"])
            return result

        # 步骤 2：旧模板或开发模式兜底文本仍按原有段落解析，且不会生成自动提案。
        result["structured_analysis"] = {}
        result["summary"] = _extract_section(analysis_text, "章节摘要") or analysis_text
        result["character_changes"] = _extract_section(analysis_text, "人物变化")
        result["world_changes"] = _extract_section(analysis_text, "世界观变化")
        result["new_foreshadowings"] = _extract_section(analysis_text, "新增伏笔")
        result["timeline_events"] = _extract_section(analysis_text, "时间线事件")

        return result


def _read_relation_list(value: Any) -> list[Any]:
    """解析人物卡中的关系 JSON，兼容 ORM 返回文本和已解析列表。"""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _parse_structured_analysis(text: str) -> ChapterAnalysis | None:
    """兼容纯 JSON、带代码围栏 JSON 和 JSON 前后有少量说明的模型输出。"""
    candidate = text.strip()
    fence = chr(96) * 3
    if candidate.startswith(fence):
        # 步骤 1：剥除模型有时附加的 Markdown 代码围栏。
        lines = candidate.splitlines()
        if lines and lines[0].startswith(fence):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith(fence):
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    start = candidate.find("{")
    if start < 0:
        return None
    try:
        # 步骤 2：只取第一个完整 JSON 对象，忽略模型意外附加的尾部文字。
        parsed, _ = json.JSONDecoder().raw_decode(candidate[start:])
        # 步骤 3：通过 Pydantic 契约检查字段类型并填入可选字段默认值。
        return ChapterAnalysis.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError, TypeError):
        return None


def _render_json(value: Any) -> str:
    """将结构化变化存入兼容旧版文本列的 JSON 字符串。"""
    return json.dumps(value, ensure_ascii=False, indent=2)


def _extract_section(text: str, title: str) -> str:
    """从分析文本中提取指定小节。"""
    marker = f"【{title}】"
    start = text.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    # 找下一个【】标记
    next_marker = re.search(r"【[^】]+】", text[start:])
    end = start + next_marker.start() if next_marker else len(text)
    return text[start:end].strip()
