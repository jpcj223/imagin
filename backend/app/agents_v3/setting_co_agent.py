"""设定共创 Agent。

以对话形式帮助用户完善设定，自动提取结构化信息并写入 L3 项目记忆。
"""
from __future__ import annotations

import html
import json
import re
import uuid
from typing import Any

from app.core.llm import chat_completion_with_usage
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
        # 步骤 1：加载最近对话，排除接口刚保存的本轮用户消息，避免提示词重复当前输入。
        history = self._load_history(session_id)
        if history and history[-1].get("role") == "user" and history[-1].get("content") == user_message:
            history = history[:-1]

        # 步骤 2：读取目标档案现状，让 Agent 能围绕已有内容继续补充而不重复盘问。
        existing_data = self.get_setting_detail(target_type, target_id) if target_id else {}

        # 步骤 3：一次模型请求同时理解意图、生成自然回复并提取明确或已确认的设定。
        extracted, conversation, token_usage = self._extract_settings(
            user_message, target_type, history, target_name, existing_data
        )

        # 2. 如果有提取到的设定，写入数据库和记忆
        memory_written = False
        if extracted and target_id:
            # 步骤 1：目标档案和 L3 记忆在一个事务中更新；两者成功后才报告已沉淀。
            memory_written = self._apply_extracted_fields(
                target_type, target_id, extracted, session_id, target_name
            )

        # 3. 生成回复
        reply_result = self._generate_reply(
            target_type=target_type,
            target_name=target_name,
            extracted=extracted,
            memory_written=memory_written,
            assistant_reply=conversation.get("reply", ""),
            intent=conversation.get("intent", "other"),
        )
        quick_replies = conversation.get("quick_replies") or reply_result.get("quick_replies", [])

        return {
            "reply": reply_result["reply"],
            "thought": reply_result["thought"],
            "extracted_fields": extracted,
            "memory_written": memory_written,
            "quick_replies": quick_replies,
            "token_usage": token_usage,
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
                .order_by(SettingChatMessage.id.desc())
                .limit(20)
                .all()
            )
            # 步骤 1：数据库倒序只取最近消息；步骤 2：恢复正序供对话上下文阅读。
            return [row_to_dict(row) for row in reversed(rows)]

    def _extract_settings(
        self,
        user_message: str,
        target_type: str,
        history: list[dict[str, Any]],
        target_name: str,
        existing_data: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, int] | None]:
        """理解本轮对话，生成针对性回复、提取已确认设定并保留模型实际 Token 用量。

        步骤 1：准备最近对话和当前档案作为上下文；步骤 2：一次请求同时产出回复与结构化设定。
        步骤 3：只接纳模板字段，并过滤未经用户确认的创作建议。
        """
        fields = SETTING_FIELD_TEMPLATES.get(target_type, [])
        field_list_str = "\n".join(
            f"- {f['key']} ({f['label']}) - 类别：{f['category']}"
            for f in fields
        )

        type_label = {"character": "角色", "world": "世界观", "foreshadowing": "伏笔"}.get(
            target_type, "设定"
        )

        # 步骤 1：仅传入最近 12 条历史消息和模板字段，避免无关长对话挤占本轮上下文。
        recent_history = []
        for message in history[-12:]:
            role = "作者" if message.get("role") == "user" else "Agent"
            content = re.sub(r"<[^>]*>", " ", str(message.get("content") or ""))
            content = html.unescape(content).strip()
            if content:
                recent_history.append({"role": role, "content": content[:1200]})

        # 步骤 2：只提供本设定模板内已经填写的字段，供 Agent 避免重复提问。
        current_data = existing_data or {}
        current_settings = {
            field["label"]: str(current_data.get(field["key"]) or "")[:500]
            for field in fields
            if current_data.get(field["key"])
        }
        history_json = json.dumps(recent_history, ensure_ascii=False)
        current_settings_json = json.dumps(current_settings, ensure_ascii=False)

        system_prompt = f"""你是一个{type_label}设定共创助手，需要接住作者当前这句话，而不是反复套用通用访谈问题。

可选的字段列表：
{field_list_str}

对话与写回规则：
1. 先理解“本轮用户消息”的具体意图，再参考最近对话和当前档案；不要重复询问档案里已有答案，也不要每次都问性格、细节、过去。
2. 用户明确陈述的事实可以提取。角色日常举止、习惯性动作可归入“性格特质”；说话方式才归入“说话风格”。
3. 如果用户是在要求你举例、给建议或补充一类尚未具体描述的内容（例如“补充小人物常见肢体动作”），请给出 3 到 5 个贴合目标和现有档案的具体候选，并请用户选择；候选只是建议，不能提取或写入档案。
4. 用户后续明确选择、采纳或要求直接加入某个候选时，才可把被选内容作为设定提取。像“用第 2 个”这样的简短回复，要结合历史中的候选理解。
5. 对已经明确的补充直接确认并继续回应当前话题；只有缺少会影响设定的关键信息时，才问最多一个具体问题。不要重启整套角色访谈，也不要擅自编造用户未确认的事实。
6. 回复用自然、简洁的中文，针对本轮具体内容，优先 1 至 3 句；需要列候选时可分行列出。不要输出 HTML。
7. 回复中不要提及内部字段 key、数据库或模型实现；处理摘要由系统根据实际写回结果生成。
8. 候选建议要明确说明“尚未写入，选定后再加入”；不要在回复正文里声称档案或记忆已经保存。

输出 JSON 格式：
{{
  "intent": "supplement|request_suggestion|clarify|question|other",
  "reply": "直接回复作者的中文内容",
  "quick_replies": ["结合当前话题的快捷回复，最多 3 个"],
  "extracted": [
    {{
      "key": "字段key",
      "label": "字段中文名",
      "value": "提取到的值",
      "operation": "append|replace",
      "confidence": 0.9,
      "highlights": ["亮点标签1", "亮点标签2"]
    }}
  ]
}}

只有作者明确要求纠正或替换旧值时 operation 才填 replace，其余补充填 append。highlights 可选。
只输出 JSON，不要 Markdown 代码围栏或其他内容。
"""

        user_prompt = f"""{type_label}名称：{target_name or "未命名"}

当前档案：
{current_settings_json}

最近对话（仅作为理解上下文，不是需要重新提取的本轮输入）：
{history_json}

本轮用户消息：
\"\"\"
{user_message}
\"\"\"

请围绕本轮消息给出自然回复，并提取本轮明确提供或明确采纳的设定。"""

        token_usage: dict[str, int] | None = None
        fallback_conversation = {
            "intent": "unavailable",
            "reply": f"我收到你想补充“{user_message[:60]}”的方向了，不过这次没能完成整理。你可以重试，或告诉我希望补充到哪一方面。",
            "quick_replies": ["重试本轮内容", "我换个说法"],
        }
        try:
            result_text, token_usage = chat_completion_with_usage(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
            )

            # 步骤 1：兼容模型偶尔附带的代码围栏或 JSON 前后说明。
            result_text = result_text.strip()
            if result_text.startswith("```"):
                result_text = result_text.strip("`")
                if result_text.lower().startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            # 步骤 2：从回复中定位 JSON 对象，避免多余说明文字导致本轮提取整体失败。
            json_start = result_text.find("{")
            if json_start < 0:
                raise json.JSONDecodeError("未找到 JSON 对象", result_text, 0)
            result, _ = json.JSONDecoder().raw_decode(result_text[json_start:])
            intent = str(result.get("intent") or "other")
            if intent not in {"supplement", "request_suggestion", "clarify", "question", "other"}:
                intent = "other"
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
                    "operation": "replace" if item.get("operation") == "replace" else "append",
                    "confidence": item.get("confidence", 0.7),
                    "highlights": [str(tag) for tag in item.get("highlights", []) if isinstance(tag, (str, int, float))]
                    if isinstance(item.get("highlights", []), list) else [],
                })
            # 步骤 3：建议意图只用于展示候选；即使模型误附字段，也不允许未确认内容写回档案。
            if intent == "request_suggestion":
                normalized = []

            # 步骤 4：校验回复字段和快捷回复长度，只把可展示的普通文本交给前端。
            reply = result.get("reply")
            if not isinstance(reply, str) or not reply.strip():
                reply = fallback_conversation["reply"]
            quick_replies = result.get("quick_replies", [])
            if not isinstance(quick_replies, list):
                quick_replies = []
            conversation = {
                "intent": intent,
                "reply": reply.strip()[:3000],
                "quick_replies": [
                    text.strip()[:40]
                    for text in quick_replies
                    if isinstance(text, str) and text.strip()
                ][:3],
            }
            return normalized, conversation, token_usage

        except Exception as e:
            # 步骤 1：记录模型结构化输出失败；步骤 2：返回贴合本轮输入的可恢复提示，不套用通用访谈模板。
            print(f"[SettingCoAgent] 提取设定失败: {e}")
            return [], fallback_conversation, token_usage

    def _generate_reply(
        self,
        target_type: str,
        target_name: str,
        extracted: list[dict[str, Any]],
        memory_written: bool,
        assistant_reply: str = "",
        intent: str = "other",
    ) -> dict[str, Any]:
        """整理自然回复、已确认字段和面向作者的处理摘要。

        步骤 1：安全转义模型和档案文本；步骤 2：展示实际提取字段与写回状态。
        步骤 3：根据本轮动作生成可读处理摘要，不展示模型内部字段名。
        """
        type_label = {"character": "角色", "world": "世界观", "foreshadowing": "伏笔"}.get(
            target_type, "设定"
        )
        # 步骤 1：优先显示结合上下文生成的自然回复；转义后才拼入现有安全 HTML 渲染通道。
        safe_reply = html.escape(assistant_reply.strip()) if assistant_reply else "这轮先围绕当前设定继续聊。"
        safe_reply = safe_reply.replace("\n", "<br>")
        reply_parts = [f"<div>{safe_reply}</div>"]

        # 步骤 2：只展示当前实际提取的内容；建议候选没有用户确认时不会出现在写回卡片中。
        if extracted:
            by_category: dict[str, list[dict[str, Any]]] = {}
            for e in extracted:
                cat = e.get("category", "其他")
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(e)

            summary_parts = []
            for cat, items in by_category.items():
                items_html = []
                for item in items:
                    label = html.escape(str(item.get("label") or "设定"))
                    value = html.escape(str(item.get("value") or "")[:240])
                    highlights = item.get("highlights") or []
                    safe_highlights = [html.escape(str(tag)) for tag in highlights]
                    highlight_text = f"（{'、'.join(safe_highlights)}）" if safe_highlights else ""
                    items_html.append(f"· {label}：{value}{highlight_text}<br>")
                summary_parts.append(f"<strong>{html.escape(str(cat))}：</strong><br>{''.join(items_html)}")

            extracted_summary_html = "<br>".join(summary_parts)
            reply_parts.append(
                f"<div class=\"extracted-summary\"><strong>本轮整理</strong><br>{extracted_summary_html}</div>"
            )

            memory_note_html = ""
            if memory_written:
                memory_note_html = f"""<div class="memory-note">
              <span class="icon">✅</span>
              已写入 L3 项目记忆 · {type_label}设定
            </div>"""
                reply_parts.append(memory_note_html)

        # 步骤 3：用实际写回结果生成处理摘要，避免内部 key 和“已保存”状态误报。
        field_labels = list(dict.fromkeys(str(field.get("label") or "设定") for field in extracted))
        target_display = target_name or type_label
        if extracted:
            action = "已同步到档案和项目记忆" if memory_written else "尚未同步到档案"
            thought = f"已为「{target_display}」整理{'、'.join(field_labels)}；{action}。"
        elif intent == "request_suggestion":
            thought = f"识别到你想为「{target_display}」补充创作内容；当前回复提供的是候选建议，尚未写入档案。"
        elif intent == "unavailable":
            thought = "本轮整理未能完成，因此没有修改档案；你可以重试或换种说法。"
        else:
            thought = f"已结合「{target_display}」的已有设定回应本轮内容；没有明确确认的新设定，因此未修改档案。"

        quick_replies = ["继续补充这个方向", "换个设定方向"] if not extracted else ["继续补充其他细节"]

        return {
            "reply": "\n".join(reply_parts),
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
                if key in replace_fields or field.get("operation") == "replace" or not current_value:
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
                # 步骤 1：记忆快照保存档案合并后的完整值，避免只留下本轮增量片段。
                persisted_fields[key] = merged_value
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
