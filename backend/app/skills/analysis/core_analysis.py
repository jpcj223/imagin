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
6. 伏笔 changes 只使用 keyword、description、status、importance、planted_chapter、payoff_chapter、effective_from、expires_at、notes、related_character_ids、related_organization_ids、related_outline_ids、replaced_by_id。
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
        """步骤 1：把章节相关的项目资料整理成分析上下文，帮助实体名称精确对齐。"""
        world = context.get("world") or {}
        character_items = [item for item in context.get("characters", []) if isinstance(item, dict)]
        character_names = {
            item.get("id"): item.get("name", "")
            for item in character_items
            if item.get("id") is not None
        }
        references = {
            "characters": [
                {
                    "name": item.get("name", ""),
                    "identity": item.get("identity", ""),
                    "faction": item.get("faction", ""),
                    "status": item.get("status", ""),
                    "personality": item.get("personality", ""),
                    "relationships": [
                        {
                            "target_name": relation.get("target_name")
                            or character_names.get(relation.get("target_id"), ""),
                            "relation_type": relation.get("relation_type", ""),
                        }
                        for relation in _read_relation_list(item.get("character_relations"))[:12]
                        if isinstance(relation, dict)
                    ],
                }
                for item in character_items
            ],
            "organizations": [
                {
                    "name": item.get("name", ""),
                    "org_type": item.get("org_type", ""),
                    "status": item.get("status", ""),
                    "goal": item.get("goal", ""),
                    "relations": item.get("relations", []),
                }
                for item in context.get("organizations", [])
                if isinstance(item, dict)
            ],
            "foreshadowings": [
                {
                    "keyword": item.get("keyword", ""),
                    "status": item.get("status", ""),
                    "description": item.get("description", ""),
                }
                for item in context.get("foreshadowings", [])
                if isinstance(item, dict)
            ],
            "world": {
                key: world.get(key, "")
                for key in ("title", "era", "geography", "atmosphere", "rules", "extra")
            },
        }
        processed = dict(context)
        # Agent 基类会把这个字段追加到 Prompt，正文原始上下文仍保留在 workflow state。
        processed["_analysis_reference_context"] = json.dumps(references, ensure_ascii=False, indent=2)
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
