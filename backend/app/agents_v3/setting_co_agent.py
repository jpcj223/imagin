"""设定共创 Agent。

以对话形式帮助用户完善设定，自动提取结构化信息并写入 L3 项目记忆。
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from app.core.llm import chat_completion
from app.memory.manager import MemoryManager
from app.db.session import get_business_db
from app.models.business import Character, SettingChatMessage, WorldSetting
from app.db.repository import row_to_dict


# 设定类型对应的字段模板
SETTING_FIELD_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "character": [
        {"key": "name", "label": "姓名", "category": "基础信息", "priority": 1},
        {"key": "identity", "label": "身份", "category": "基础信息", "priority": 1},
        {"key": "appearance", "label": "外貌特征", "category": "外貌", "priority": 2},
        {"key": "personality", "label": "性格特质", "category": "性格", "priority": 2},
        {"key": "background", "label": "背景故事", "category": "背景", "priority": 2},
        {"key": "motivation", "label": "核心动机", "category": "动机", "priority": 2},
        {"key": "weakness", "label": "弱点", "category": "性格", "priority": 3},
        {"key": "secret", "label": "秘密", "category": "背景", "priority": 3},
        {"key": "dialogue_style", "label": "说话风格", "category": "行为", "priority": 3},
        {"key": "relationships", "label": "重要关系", "category": "关系", "priority": 3},
        {"key": "arc", "label": "人物弧光", "category": "发展", "priority": 4},
        {"key": "faction", "label": "所属势力", "category": "身份", "priority": 3},
    ],
    "world": [
        {"key": "name", "label": "世界名称", "category": "基础", "priority": 1},
        {"key": "era", "label": "时代背景", "category": "基础", "priority": 1},
        {"key": "power_system", "label": "力量体系", "category": "体系", "priority": 1},
        {"key": "atmosphere", "label": "整体基调", "category": "氛围", "priority": 2},
        {"key": "synopsis", "label": "世界观简介", "category": "概览", "priority": 2},
        {"key": "core_rules", "label": "核心规则", "category": "规则", "priority": 2},
    ],
    "foreshadowing": [
        {"key": "main_plot", "label": "主线伏笔", "category": "主线", "priority": 1},
        {"key": "character_secrets", "label": "人物秘密", "category": "人物", "priority": 2},
        {"key": "world_mysteries", "label": "世界谜团", "category": "世界", "priority": 3},
    ],
}


class SettingCoAgent:
    """设定共创 Agent。

    对话式完善设定，自动提取结构化信息并写入 L3 项目记忆。
    """

    def __init__(self, project_id: int, user_id: int = 1):
        self.project_id = project_id
        self.user_id = user_id
        self.memory = MemoryManager(project_id, user_id)

    # ------------------------------------------------------------------
    # 生成开场白
    # ------------------------------------------------------------------

    def generate_opening(
        self,
        target_type: str,
        target_name: str = "",
        existing_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """生成对话开场白，分析设定缺口并提出首批问题。

        Args:
            target_type: 设定类型 character/world/foreshadowing
            target_name: 设定对象名称
            existing_data: 已有设定数据

        Returns:
            {
                "message": 开场白内容,
                "thought": 思考过程,
                "missing_fields": 缺失的字段列表,
                "quick_replies": 快速回复建议
            }
        """
        existing = existing_data or {}
        fields = SETTING_FIELD_TEMPLATES.get(target_type, [])

        # 分析已有字段完整度
        filled_fields = []
        missing_fields = []
        for f in fields:
            val = existing.get(f["key"], "")
            if val and str(val).strip():
                filled_fields.append(f)
            else:
                missing_fields.append(f)

        # 按优先级排序缺失字段
        missing_fields.sort(key=lambda x: x["priority"])

        # 选取前 2-3 个高优先级缺失字段作为首批提问
        first_batch = missing_fields[:3]
        first_batch_labels = [f["label"] for f in first_batch]

        type_label = {"character": "角色", "world": "世界观", "foreshadowing": "伏笔"}.get(
            target_type, "设定"
        )

        # 构建已有设定摘要（HTML 列表）
        existing_items_html = ""
        for f in filled_fields[:5]:
            val = str(existing.get(f["key"], ""))[:60]
            if val:
                existing_items_html += f"<li>{f['label']}：{val}</li>\n"

        if not existing_items_html:
            existing_items_html = "<li>（暂无详细信息）</li>\n"

        # 构建问题列表（HTML）
        if first_batch_labels:
            if target_type == "world":
                questions_items = "".join(
                    f"<li>这个世界的<strong>{label}</strong>你希望设定成什么样？"
                    f"{'有没有能体现世界特色的细节？' if i == 0 else ''}</li>\n"
                    for i, label in enumerate(first_batch_labels)
                )
            else:
                questions_items = "".join(
                    f"<li>他/她的<strong>{label}</strong>具体是什么样的？{'有没有标志性的细节？' if i == 0 else ''}</li>\n"
                    for i, label in enumerate(first_batch_labels)
                )
            questions_html = f"""<div class="question-highlight">
              我发现以下几个方面还需要补充，想先和你聊聊：
            </div>
            <ul class="question-list">
              {questions_items}
            </ul>"""
        else:
            questions_html = "<p>看起来设定已经很完整了！还有什么想补充或调整的吗？</p>"

        target_display = target_name or f"这个{type_label}"

        thought = (
            f"分析{type_label}设定完整度："
            f"已填 {len(filled_fields)}/{len(fields)} 字段，"
            f"缺失 {len(missing_fields)} 字段。"
            f"首批提问：{first_batch_labels}"
        )

        quick_replies = []
        if len(first_batch_labels) >= 1:
            quick_replies.append(f"先聊{first_batch_labels[0]}")
        if len(first_batch_labels) >= 2:
            quick_replies.append(f"说说{first_batch_labels[1]}方面")
        if len(missing_fields) > 2:
            quick_replies.append("全部告诉我，你来整理")

        # 富格式 HTML 消息
        message = f"""<div class="thought-tag">💭 正在分析设定缺口</div>
你好！我正在梳理「{target_display}」的{type_label}设定。目前已有的信息包括：
<ul class="question-list" style="margin-top: 8px;">
{existing_items_html}</ul>
{questions_html}
你可以一次回答多个，也可以先挑一个深入聊～"""

        return {
            "message": message,
            "thought": thought,
            "missing_fields": [f["key"] for f in missing_fields],
            "filled_fields": [f["key"] for f in filled_fields],
            "completeness": int(len(filled_fields) / max(len(fields), 1) * 100),
            "quick_replies": quick_replies,
        }

    # ------------------------------------------------------------------
    # 处理用户消息，生成回复 + 提取设定
    # ------------------------------------------------------------------

    def process_user_message(
        self,
        session_id: str,
        user_message: str,
        target_type: str,
        target_id: int | None = None,
        target_name: str = "",
    ) -> dict[str, Any]:
        """处理用户消息，生成回复并提取设定。

        Args:
            session_id: 会话 ID
            user_message: 用户输入内容
            target_type: 设定类型
            target_id: 目标对象 ID（如角色 ID）
            target_name: 目标名称

        Returns:
            {
                "reply": Agent 回复,
                "thought": 思考过程,
                "extracted_fields": 提取到的字段列表 [{key, label, value}],
                "memory_written": 是否写入了记忆,
                "quick_replies": 快速回复建议
            }
        """
        # 获取历史消息
        history = self._load_history(session_id)

        # 1. 用 LLM 提取设定字段
        extracted = self._extract_settings(user_message, target_type, history, target_name)

        # 2. 如果有提取到的设定，写入数据库和记忆
        memory_written = False
        if extracted and target_id:
            self._apply_extracted_fields(target_type, target_id, extracted)
            # 步骤 1：将本轮确认提取出的事实实际写入项目记忆，再向界面报告成功。
            memory_content = "\n".join(
                f"{field.get('label') or field.get('key')}：{field.get('value')}"
                for field in extracted
            )
            try:
                self.memory.store_memory(
                    memory_type="setting",
                    title=f"{target_name or '设定'}设定补充",
                    content=memory_content,
                    importance=75,
                    source_type="setting_co",
                    source_ref=session_id,
                    metadata={"target_type": target_type, "target_id": target_id},
                )
                memory_written = True
            except Exception as exc:
                # 步骤 2：记忆写入失败不回滚已保存的设定字段，也不伪报成功。
                print(f"[SettingCoAgent] 写入项目记忆失败: {exc}")

        # 3. 生成回复
        reply_result = self._generate_reply(
            user_message=user_message,
            target_type=target_type,
            target_name=target_name,
            extracted=extracted,
            history=history,
            memory_written=memory_written,
        )

        return {
            "reply": reply_result["reply"],
            "thought": reply_result["thought"],
            "extracted_fields": extracted,
            "memory_written": memory_written,
            "quick_replies": reply_result.get("quick_replies", []),
        }

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _load_history(self, session_id: str) -> list[dict[str, Any]]:
        """加载对话历史。"""
        with get_business_db() as db:
            rows = (
                db.query(SettingChatMessage)
                .filter(SettingChatMessage.session_id == session_id)
                .order_by(SettingChatMessage.id.asc())
                .limit(20)
                .all()
            )
            return [row_to_dict(r) for r in rows]

    def _extract_settings(
        self,
        user_message: str,
        target_type: str,
        history: list[dict[str, Any]],
        target_name: str,
    ) -> list[dict[str, Any]]:
        """从用户消息中提取设定字段。

        先用 LLM 提取，返回结构化的字段列表。
        """
        fields = SETTING_FIELD_TEMPLATES.get(target_type, [])
        field_list_str = "\n".join(
            f"- {f['key']} ({f['label']}) - 类别：{f['category']}"
            for f in fields
        )

        type_label = {"character": "角色", "world": "世界观", "foreshadowing": "伏笔"}.get(
            target_type, "设定"
        )

        system_prompt = f"""你是一个{type_label}设定提取助手。
从用户的描述中提取结构化的{type_label}设定字段。

可选的字段列表：
{field_list_str}

请仔细阅读用户的描述，提取出对应字段的值。
如果某个字段在描述中没有明确提到，不要提取。
提取的值要忠实于原文，不要编造。

输出 JSON 格式：
{{
  "extracted": [
    {{
      "key": "字段key",
      "label": "字段中文名",
      "value": "提取到的值",
      "confidence": 0.9,
      "highlights": ["亮点标签1", "亮点标签2"]
    }}
  ]
}}

highlights 是可选的，如果提取的内容有特殊价值（如伏笔潜力、情感锚点等），可以加标签。
"""

        user_prompt = f"""{type_label}名称：{target_name or "未命名"}

用户描述：
\"\"\"
{user_message}
\"\"\"

请提取其中的{type_label}设定字段。只输出 JSON，不要其他内容。"""

        try:
            result_text = chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
            )

            # 解析 JSON
            result_text = result_text.strip()
            # 有时模型会包裹 ```json 代码块
            if result_text.startswith("```"):
                result_text = result_text.strip("`")
                if result_text.lower().startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            result = json.loads(result_text)
            extracted = result.get("extracted", [])

            # 过滤掉无效项
            valid_keys = {f["key"] for f in fields}
            extracted = [
                e for e in extracted
                if e.get("key") in valid_keys and e.get("value")
            ]

            return extracted

        except Exception as e:
            # LLM 调用失败时返回空
            print(f"[SettingCoAgent] 提取设定失败: {e}")
            return []

    def _generate_reply(
        self,
        user_message: str,
        target_type: str,
        target_name: str,
        extracted: list[dict[str, Any]],
        history: list[dict[str, Any]],
        memory_written: bool,
    ) -> dict[str, Any]:
        """生成 Agent 回复。"""
        type_label = {"character": "角色", "world": "世界观", "foreshadowing": "伏笔"}.get(
            target_type, "设定"
        )

        # 如果有提取到字段
        if extracted:
            # 按类别分组
            by_category: dict[str, list[dict[str, Any]]] = {}
            for e in extracted:
                cat = e.get("category", "其他")
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(e)

            # 构建梳理卡片 HTML
            summary_parts = []
            for cat, items in by_category.items():
                items_html = "".join(
                    f"· {e['label']}：{e['value'][:80]}"
                    f"{'（' + '、'.join(e['highlights']) + '）' if e.get('highlights') else ''}<br>"
                    for e in items
                )
                summary_parts.append(
                    f"<strong>{cat}：</strong><br>{items_html}"
                )

            extracted_summary_html = "<br>".join(summary_parts)

            memory_note_html = ""
            if memory_written:
                memory_note_html = f"""<div class="memory-note">
              <span class="icon">✅</span>
              已写入 L3 项目记忆 · {type_label}设定
            </div>"""

            # 基于第一个提取字段追问
            follow_up_html = ""
            if extracted and len(extracted) > 0:
                first_label = extracted[0]["label"]
                follow_up_html = f"""<div style="margin-top: 12px;">
              关于「{first_label}」——它有没有什么<strong>特殊的故事</strong>？比如那次事件有没有影响他的性格或修炼之路？我觉得这可以成为一个很好的情感伏笔。
            </div>"""

            reply = f"""<div class="thought-tag">✨ 正在提炼关键信息</div>
很棒！这些细节很有画面感。我来梳理一下你说的：

<div style="margin-top: 10px; padding: 10px 12px; background: rgba(99, 102, 241, 0.08); border-radius: 6px; font-size: 12px; line-height: 1.8;">
{extracted_summary_html}
</div>

{memory_note_html}

{follow_up_html if follow_up_html else "还有什么想补充的吗？"}"""

            quick_replies = [
                "有故事，继续深挖",
                "跳过，聊下一个",
                "帮我润色一下",
            ]

            thought = f"提取到 {len(extracted)} 个设定字段: {[e['key'] for e in extracted]}"

        else:
            # 没有提取到明确字段，引导用户多说一些
            reply = f"""收到～你说的内容我记下了。

为了更好地帮你完善{type_label}设定，能再多说一些细节吗？比如：
<ul class="question-list">
  <li>这个{type_label}的核心特点是什么？</li>
  <li>有没有什么标志性的细节或习惯？</li>
  <li>他/她/它的过去有什么重要的经历？</li>
</ul>
想到什么说什么就好，我来帮你整理～"""

            quick_replies = [
                f"聊聊{type_label}的过去",
                "说说性格特点",
                "给我几个问题引导我",
            ]
            thought = "用户消息中未提取到明确设定字段，引导用户提供更多信息"

        return {
            "reply": reply,
            "thought": thought,
            "quick_replies": quick_replies,
        }

    def _apply_extracted_fields(
        self,
        target_type: str,
        target_id: int,
        extracted: list[dict[str, Any]],
    ) -> None:
        """将提取到的字段写入数据库。"""
        if target_type not in {"character", "world"}:
            return

        with get_business_db() as db:
            if target_type == "character":
                target = db.query(Character).filter(Character.id == target_id).first()
                field_mapping = {field["key"]: field["key"] for field in SETTING_FIELD_TEMPLATES["character"]}
                replace_fields = {"name"}
            else:
                target = (
                    db.query(WorldSetting)
                    .filter(
                        WorldSetting.id == target_id,
                        WorldSetting.project_id == self.project_id,
                    )
                    .first()
                )
                # 步骤 1：世界共创字段映射到世界观总览现有列，和页面保存结构保持一致。
                field_mapping = {
                    "name": "title",
                    "era": "era",
                    "power_system": "geography",
                    "atmosphere": "atmosphere",
                    "synopsis": "rules",
                    "core_rules": "extra",
                }
                replace_fields = {"name", "era", "power_system", "atmosphere"}

            if not target:
                return

            for field in extracted:
                key = field["key"]
                value = field["value"]
                column = field_mapping.get(key)
                if not column or not hasattr(target, column):
                    continue

                # 步骤 2：名称和概要字段采用最新明确回答；长文本字段保留已记录的补充事实。
                current_value = getattr(target, column) or ""
                if key in replace_fields or not current_value or value in current_value:
                    merged_value = value
                else:
                    merged_value = f"{current_value}\n{value}"
                setattr(target, column, merged_value)

            db.commit()

    @staticmethod
    def _world_data_from_row(world: WorldSetting) -> dict[str, Any]:
        """将世界观总览数据库列映射为共创 Agent 使用的字段。"""
        return {
            "id": world.id,
            "name": world.title or "",
            "era": world.era or "",
            "power_system": world.geography or "",
            "atmosphere": world.atmosphere or "",
            "synopsis": world.rules or "",
            "core_rules": world.extra or "",
        }

    # ------------------------------------------------------------------
    # 计算设定完整度
    # ------------------------------------------------------------------

    def calculate_completeness(
        self,
        target_type: str,
        target_data: dict[str, Any],
    ) -> int:
        """计算设定完整度百分比。"""
        fields = SETTING_FIELD_TEMPLATES.get(target_type, [])
        if not fields:
            return 0

        filled = 0
        for f in fields:
            val = target_data.get(f["key"], "")
            if val and str(val).strip():
                filled += 1

        return int(filled / len(fields) * 100)

    # ------------------------------------------------------------------
    # 获取设定详情（供右侧卡片展示）
    # ------------------------------------------------------------------

    def get_setting_detail(
        self,
        target_type: str,
        target_id: int,
    ) -> dict[str, Any]:
        """获取设定对象的详细数据。"""
        if target_type == "character":
            with get_business_db() as db:
                char = db.query(Character).filter(Character.id == target_id).first()
                if not char:
                    return {}
                data = row_to_dict(char)
                # 计算完整度
                completeness = self.calculate_completeness("character", data)
                data["completeness"] = completeness
                return data
        if target_type == "world":
            with get_business_db() as db:
                world = (
                    db.query(WorldSetting)
                    .filter(
                        WorldSetting.id == target_id,
                        WorldSetting.project_id == self.project_id,
                    )
                    .first()
                )
                if not world:
                    return {}
                data = self._world_data_from_row(world)
                data["completeness"] = self.calculate_completeness("world", data)
                return data
        return {}
