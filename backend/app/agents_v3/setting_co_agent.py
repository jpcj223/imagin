"""设定共创 Agent。

以对话形式帮助用户完善设定，自动提取结构化信息并写入 L3 项目记忆。
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from app.core.llm import chat_completion
from app.db.session import get_business_db
from app.models.business import Character, Foreshadowing, MemoryItem, SettingChatMessage, WorldSetting
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
        {"key": "keyword", "label": "线索关键词", "category": "识别", "priority": 1},
        {"key": "description", "label": "线索内容", "category": "内容", "priority": 1},
        {"key": "notes", "label": "作者备注", "category": "幕后", "priority": 2},
    ],
}


class SettingCoAgent:
    """设定共创 Agent。

    对话式完善设定，自动提取结构化信息并写入 L3 项目记忆。
    """

    def __init__(self, project_id: int, user_id: int = 1):
        self.project_id = project_id
        self.user_id = user_id

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
            # 步骤 1：目标档案和 L3 记忆在一个事务中更新；两者成功后才报告已沉淀。
            memory_written = self._apply_extracted_fields(
                target_type, target_id, extracted, session_id, target_name
            )

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

            # 步骤 1：只接纳模板内字段，并把模型输出规范成稳定的字符串结构。
            field_by_key = {field["key"]: field for field in fields}
            normalized = []
            for item in extracted if isinstance(extracted, list) else []:
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key") or "")
                template = field_by_key.get(key)
                value = item.get("value")
                if not template or not isinstance(value, (str, int, float)) or not str(value).strip():
                    continue
                # 步骤 2：字段名称使用系统模板，避免模型输出错误标签导致保存或展示失败。
                normalized.append({
                    "key": key,
                    "label": template["label"],
                    "category": template["category"],
                    "value": str(value).strip(),
                    "confidence": item.get("confidence", 0.7),
                    "highlights": [str(tag) for tag in item.get("highlights", []) if isinstance(tag, (str, int, float))]
                    if isinstance(item.get("highlights", []), list) else [],
                })
            return normalized

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
                    f"· {e.get('label') or e.get('key', '设定')}：{str(e.get('value', ''))[:80]}"
                    f"{'（' + '、'.join(str(tag) for tag in e['highlights']) + '）' if e.get('highlights') else ''}<br>"
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
        session_id: str,
        target_name: str,
    ) -> bool:
        """在同一事务内更新目标档案并合并本会话的项目记忆。

        步骤 1：按项目校验目标记录并选择允许更新的字段。
        步骤 2：将提取值写回对应档案，忽略未知字段和空内容。
        步骤 3：按会话查找或创建一条记忆，并合并各轮确认字段。
        步骤 4：一次性提交档案与记忆，避免界面出现半成功状态。
        """
        if target_type not in {"character", "world", "foreshadowing"}:
            return False

        memory_type_by_target = {
            "character": "character",
            "world": "world_setting",
            "foreshadowing": "foreshadowing",
        }

        with get_business_db() as db:
            if target_type == "character":
                target = db.query(Character).filter(
                    Character.id == target_id,
                    Character.project_id == self.project_id,
                ).first()
                field_mapping = {field["key"]: field["key"] for field in SETTING_FIELD_TEMPLATES["character"]}
                replace_fields = {"name"}
            elif target_type == "world":
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
            else:
                target = db.query(Foreshadowing).filter(
                    Foreshadowing.id == target_id,
                    Foreshadowing.project_id == self.project_id,
                ).first()
                field_mapping = {"keyword": "keyword", "description": "description", "notes": "notes"}
                replace_fields = {"keyword"}

            if not target:
                return False

            persisted_fields: dict[str, str] = {}
            for field in extracted:
                key = str(field.get("key") or "")
                value = str(field.get("value") or "").strip()
                column = field_mapping.get(key)
                if not value or not column or not hasattr(target, column):
                    continue

                # 步骤 2：名称和概要字段采用最新明确回答；长文本字段保留已记录的补充事实。
                current_value = getattr(target, column) or ""
                if key in replace_fields or not current_value:
                    merged_value = value
                elif value in current_value:
                    merged_value = current_value
                else:
                    merged_value = f"{current_value}\n{value}"
                setattr(target, column, merged_value)
                template = next(
                    (item for item in SETTING_FIELD_TEMPLATES[target_type] if item["key"] == key),
                    None,
                )
                persisted_fields[key] = value
                field["label"] = field.get("label") or (template["label"] if template else key)

            if not persisted_fields:
                return False

            # 步骤 3：同一会话始终维护一条结构化记忆，避免每轮对话生成重复条目。
            memory_type = memory_type_by_target[target_type]
            memory = db.query(MemoryItem).filter(
                MemoryItem.project_id == self.project_id,
                MemoryItem.user_id == self.user_id,
                MemoryItem.source_type == "setting_co",
                MemoryItem.source_ref == session_id,
                # 步骤 1：兼容旧版统一使用 setting 类型的共创记忆，并在续聊时升级为具体类型。
                MemoryItem.memory_type.in_([memory_type, "setting"]),
            ).first()
            metadata: dict[str, Any] = {}
            if memory and memory.metadata_json:
                try:
                    metadata = json.loads(memory.metadata_json)
                except (TypeError, json.JSONDecodeError):
                    metadata = {}
            field_values = metadata.get("field_values", {})
            if not isinstance(field_values, dict):
                field_values = {}
            labels = metadata.get("field_labels", {})
            if not isinstance(labels, dict):
                labels = {}
            for field in extracted:
                key = str(field.get("key") or "")
                if key in persisted_fields:
                    field_values[key] = persisted_fields[key]
                    labels[key] = field.get("label") or key
            memory_content = "\n".join(
                f"{labels.get(key, key)}：{value}" for key, value in field_values.items()
            )
            memory_metadata = {
                "target_type": target_type,
                "target_id": target_id,
                "field_values": field_values,
                "field_labels": labels,
            }
            memory_title = f"{target_name or '设定'}设定记忆"
            if memory:
                memory.memory_type = memory_type
                memory.title = memory_title
                memory.content = memory_content
                memory.content_summary = memory_content[:240]
                memory.metadata_json = json.dumps(memory_metadata, ensure_ascii=False)
                memory.importance = 75
            else:
                db.add(MemoryItem(
                    memory_id=str(uuid.uuid4()),
                    project_id=self.project_id,
                    user_id=self.user_id,
                    memory_type=memory_type,
                    title=memory_title,
                    content=memory_content,
                    content_summary=memory_content[:240],
                    importance=75,
                    source_type="setting_co",
                    source_ref=session_id,
                    metadata_json=json.dumps(memory_metadata, ensure_ascii=False),
                ))

            # 步骤 4：目标不存在或没有有效提取值时不会报告写入成功。
            db.commit()
            return True

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
                char = db.query(Character).filter(
                    Character.id == target_id,
                    Character.project_id == self.project_id,
                ).first()
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
        if target_type == "foreshadowing":
            with get_business_db() as db:
                item = db.query(Foreshadowing).filter(
                    Foreshadowing.id == target_id,
                    Foreshadowing.project_id == self.project_id,
                ).first()
                if not item:
                    return {}
                data = row_to_dict(item)
                data["name"] = item.keyword
                data["completeness"] = self.calculate_completeness("foreshadowing", data)
                return data
        return {}
