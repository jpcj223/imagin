"""工作流引擎（v3.0）。

支持模板化工作流、步骤编排、状态持久化、断点续传。
"""
from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.memory.retriever import MemoryRetriever, format_volume_outline
from .persistence import WorkflowPersistence
from .generation_options import (
    build_skill_guidance,
    normalize_generation_options,
    target_word_range,
)


class WorkflowStatus(str, Enum):
    """工作流执行状态。"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """步骤执行状态。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """工作流步骤定义。"""
    step_id: str
    agent_type: str
    variant: str = "default"
    label: str = ""
    depends_on: list[str] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    input_mapping: dict[str, str] = field(default_factory=dict)  # 从会话记忆映射输入
    output_mapping: dict[str, str] = field(default_factory=dict)  # 输出映射到会话记忆


@dataclass
class WorkflowTemplate:
    """工作流模板。"""
    name: str
    label: str
    description: str = ""
    icon: str = "⚙️"
    steps: list[WorkflowStep] = field(default_factory=list)
    category: str = "general"

    def to_dict(self) -> dict:
        """序列化为字典（用于快照）。"""
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "icon": self.icon,
            "category": self.category,
            "steps": [
                {
                    "step_id": s.step_id,
                    "agent_type": s.agent_type,
                    "variant": s.variant,
                    "label": s.label,
                    "depends_on": s.depends_on,
                    "params": s.params,
                    "input_mapping": s.input_mapping,
                    "output_mapping": s.output_mapping,
                }
                for s in self.steps
            ],
        }


# ============================================================
# 内置工作流模板
# ============================================================

BUILTIN_TEMPLATES: dict[str, WorkflowTemplate] = {
    "quick_write": WorkflowTemplate(
        name="quick_write",
        label="快速写作",
        description="直接生成正文，没有规划和分析。速度最快。",
        icon="🚀",
        category="basic",
        steps=[
            WorkflowStep(
                step_id="writer",
                agent_type="writer",
                variant="fast",
                label="写作",
                params={},
                output_mapping={"content": "draft_content", "source": "draft_source"},
            ),
        ],
    ),
    "smart_mode": WorkflowTemplate(
        name="smart_mode",
        label="智能模式",
        description="先规划再写作，写完自动分析。平衡质量和效率。",
        icon="✨",
        category="basic",
        steps=[
            WorkflowStep(
                step_id="planner",
                agent_type="planner",
                variant="default",
                label="规划",
                output_mapping={"content": "writing_plan"},
            ),
            WorkflowStep(
                step_id="writer",
                agent_type="writer",
                variant="default",
                label="写作",
                depends_on=["planner"],
                output_mapping={"content": "draft_content", "source": "draft_source"},
            ),
            WorkflowStep(
                step_id="analyzer",
                agent_type="analyzer",
                variant="default",
                label="分析",
                depends_on=["writer"],
                # 步骤 1：把写作步骤正文映射到分析器提示词使用的 content 字段。
                input_mapping={"content": "draft_content"},
                output_mapping={
                    "summary": "chapter_summary",
                    "character_changes": "character_changes",
                    "world_changes": "world_changes",
                    "new_foreshadowings": "new_foreshadowings",
                    "timeline_events": "timeline_events",
                    "structured_analysis": "structured_analysis",
                    "analysis_status": "analysis_status",
                    "analysis_message": "analysis_message",
                    "analysis_entity_catalog": "analysis_entity_catalog",
                },
            ),
        ],
    ),
    "deep_creation": WorkflowTemplate(
        name="deep_creation",
        label="深度创作",
        description="完整版流水线：规划→写作→精修→深度分析。",
        icon="🏆",
        category="advanced",
        steps=[
            WorkflowStep(
                step_id="planner",
                agent_type="planner",
                variant="detailed",
                label="详细规划",
                output_mapping={"content": "writing_plan"},
            ),
            WorkflowStep(
                step_id="writer",
                agent_type="writer",
                variant="default",
                label="写作",
                depends_on=["planner"],
                output_mapping={"content": "draft_content", "source": "draft_source"},
            ),
            WorkflowStep(
                step_id="polisher",
                agent_type="polisher",
                variant="default",
                label="精修",
                depends_on=["writer"],
                params={"mode": "flow"},
                # 步骤 1：将草稿映射到精修 Agent 的 original_content 输入。
                input_mapping={"original_content": "draft_content"},
                output_mapping={"content": "polished_content", "source": "polished_source"},
            ),
            WorkflowStep(
                step_id="analyzer",
                agent_type="analyzer",
                variant="deep",
                label="深度分析",
                depends_on=["polisher"],
                # 步骤 1：分析精修后的最终正文，避免仍使用原始草稿或空 content。
                input_mapping={"content": "polished_content"},
                output_mapping={
                    "summary": "chapter_summary",
                    "character_changes": "character_changes",
                    "world_changes": "world_changes",
                    "new_foreshadowings": "new_foreshadowings",
                    "timeline_events": "timeline_events",
                    "structured_analysis": "structured_analysis",
                    "analysis_status": "analysis_status",
                    "analysis_message": "analysis_message",
                    "analysis_entity_catalog": "analysis_entity_catalog",
                },
            ),
        ],
    ),
}


class WorkflowEngine:
    """工作流引擎。

    负责执行工作流模板，管理会话上下文，持久化执行状态。
    支持断点续传：从 run_id 恢复未完成的工作流。
    """

    _cancel_events: dict[str, threading.Event] = {}
    _cancel_events_lock = threading.Lock()
    _execution_locks: dict[str, threading.Lock] = {}
    _execution_locks_lock = threading.Lock()

    @classmethod
    def _event_for_run(cls, run_id: str) -> threading.Event:
        with cls._cancel_events_lock:
            return cls._cancel_events.setdefault(run_id, threading.Event())

    @classmethod
    def _event_for_execution(cls, run_id: str) -> threading.Event:
        """为恢复后的新一轮执行换新信号，避免旧请求被续跑清除取消状态。"""
        with cls._cancel_events_lock:
            event = cls._cancel_events.get(run_id)
            if event is None or event.is_set():
                event = threading.Event()
                cls._cancel_events[run_id] = event
            return event

    @classmethod
    def _release_cancel_event(cls, run_id: str, event: threading.Event) -> None:
        """释放终态运行的取消信号，避免长时间运行后累积事件对象。"""
        with cls._cancel_events_lock:
            if cls._cancel_events.get(run_id) is event:
                cls._cancel_events.pop(run_id, None)

    @classmethod
    def _acquire_execution_lock(cls, run_id: str) -> threading.Lock | None:
        """同一工作流只允许一个流式执行，防止超时后续传叠加模型请求。"""
        with cls._execution_locks_lock:
            lock = cls._execution_locks.get(run_id)
            if lock is not None and lock.locked():
                return None
            if lock is None:
                lock = threading.Lock()
                cls._execution_locks[run_id] = lock
            lock.acquire()
            return lock

    @classmethod
    def _release_execution_lock(cls, run_id: str, lock: threading.Lock) -> None:
        """在锁表互斥区内释放并移除锁，避免释放/重建之间出现双执行竞态。"""
        with cls._execution_locks_lock:
            if cls._execution_locks.get(run_id) is lock:
                lock.release()
                cls._execution_locks.pop(run_id, None)

    @classmethod
    def request_pause(cls, run_id: str) -> bool:
        """请求正在执行的流式工作流暂停，并保留最近的未完成步骤。"""
        event = cls._event_for_run(run_id)
        event.set()
        if not WorkflowPersistence.pause_run(run_id):
            cls._release_cancel_event(run_id, event)
            return False
        return True

    def __init__(
        self,
        project_id: int,
        template_name: str,
        run_id: str | None = None,
        chapter_id: int | None = None,
        outline_id: int | None = None,
        generation_options: dict[str, Any] | None = None,
    ):
        """初始化工作流引擎。

        Args:
            project_id: 项目 ID
            template_name: 模板名称
            run_id: 工作流运行 ID（用于断点续传）
            chapter_id: 章节 ID
            outline_id: 大纲 ID
        """
        self.project_id = project_id
        self.template_name = template_name
        self.chapter_id = chapter_id
        self.outline_id = outline_id
        self.generation_options = normalize_generation_options(generation_options)

        if template_name not in BUILTIN_TEMPLATES:
            raise ValueError(f"Template '{template_name}' not found")

        self.template = BUILTIN_TEMPLATES[template_name]
        self.memory_retriever = MemoryRetriever(project_id)

        # 状态初始化
        self.session_context: dict[str, Any] = {}  # L2 会话记忆
        self.step_results: dict[str, dict[str, Any]] = {}
        self.step_statuses: dict[str, StepStatus] = {
            step.step_id: StepStatus.PENDING for step in self.template.steps
        }

        if run_id:
            # 断点续传：从数据库恢复状态
            self.run_id = run_id
            self.status = WorkflowStatus.PAUSED
            self._restore_from_db()
        else:
            # 新建工作流
            self.run_id = ""
            self.status = WorkflowStatus.PENDING
            self._persist_new_run()
        self._cancel_event = self._event_for_execution(self.run_id)

    def _pause_active_step(self, step: WorkflowStep, partial_content: str = "") -> None:
        """保存当前步骤的中断状态和已有正文片段。"""
        self.step_statuses[step.step_id] = StepStatus.PAUSED
        self.status = WorkflowStatus.PAUSED
        if partial_content:
            self.session_context["interrupted_partial_content"] = partial_content
        WorkflowPersistence.update_step_record(
            run_id=self.run_id,
            step_id=step.step_id,
            status="paused",
            output_snapshot={"partial_content": partial_content},
            error_message="用户中断，等待继续生成",
        )
        WorkflowPersistence.update_run_status(
            run_id=self.run_id,
            status="paused",
            word_count=len(partial_content),
            output_preview=partial_content,
        )

    def _persist_new_run(self) -> None:
        """持久化新的工作流运行记录。"""
        variant_selections = {
            step.step_id: step.variant for step in self.template.steps
        }
        variant_selections["generation_options"] = self.generation_options
        # 使用类的静态方法创建记录
        # 步骤 1：以持久化层实际生成的 ID 作为本次引擎 ID。
        # 保证运行状态、步骤记录、续跑和章节版本引用指向同一条记录。
        self.run_id = WorkflowPersistence.create_run(
            project_id=self.project_id,
            template_name=self.template_name,
            template_snapshot=self.template.to_dict(),
            variant_selections=variant_selections,
            chapter_id=self.chapter_id,
            outline_id=self.outline_id,
        )
        # 步骤记录在步骤开始时才创建，这里不需要预创建

    def _restore_from_db(self) -> None:
        """从数据库恢复工作流状态。"""
        state = WorkflowPersistence.restore_workflow_state(self.run_id)
        if not state:
            raise ValueError(f"Run '{self.run_id}' not found")

        run_info = state["run_info"]
        self.status = WorkflowStatus(run_info.get("status", "paused"))
        stored_selections = run_info.get("variant_selections") or {}
        stored_options = stored_selections.get("generation_options")
        if stored_options:
            self.generation_options = normalize_generation_options(stored_options)

        # 恢复步骤状态
        for step_id, status_str in state["step_statuses"].items():
            if step_id in self.step_statuses:
                # 步骤 1：恢复时把上次运行中或失败的步骤重新排队，保留已完成步骤结果。
                # 客户端断开时后端无法收到取消通知，因此数据库里的 running 也必须可重试。
                if status_str in {
                    StepStatus.RUNNING.value,
                    StepStatus.FAILED.value,
                    StepStatus.PAUSED.value,
                }:
                    self.step_statuses[step_id] = StepStatus.PENDING
                else:
                    self.step_statuses[step_id] = StepStatus(status_str)

        # 恢复步骤结果
        self.step_results = state["step_results"]

        # 恢复会话上下文
        self.session_context = state["session_context"]
        if self.session_context.get("generation_options"):
            self.generation_options = normalize_generation_options(
                self.session_context["generation_options"]
            )

        # 步骤 2：续跑时保持工作流可执行状态；已完成步骤仍由快照恢复，不会重复生成。
        if self.status in {WorkflowStatus.RUNNING, WorkflowStatus.FAILED}:
            self.status = WorkflowStatus.PAUSED

    def restart_from_step(self, step_id: str) -> None:
        """从指定步骤开始重跑。

        将指定步骤及其所有下游依赖步骤重置为 PENDING 状态，
        并清除对应的步骤结果和会话上下文中的输出映射。

        Args:
            step_id: 要重跑的步骤 ID
        """
        if step_id not in self.step_statuses:
            raise ValueError(f"Step '{step_id}' not found in template")

        # 找出所有需要重置的步骤（指定步骤 + 所有依赖它的下游步骤）
        to_reset = self._get_downstream_steps(step_id)
        to_reset.add(step_id)

        # 重置状态和结果
        for sid in to_reset:
            self.step_statuses[sid] = StepStatus.PENDING
            if sid in self.step_results:
                del self.step_results[sid]
        if "analyzer" in to_reset:
            # 步骤 1：重跑分析时重新读取实体名录，避免沿用旧审核上下文。
            self.session_context.pop("analysis_entity_catalog", None)

        # 从会话上下文中移除这些步骤的输出
        for step in self.template.steps:
            if step.step_id in to_reset and step.output_mapping:
                for _, ctx_key in step.output_mapping.items():
                    if ctx_key in self.session_context:
                        del self.session_context[ctx_key]

        # 更新状态为运行中
        self.status = WorkflowStatus.RUNNING

        # 持久化更新
        WorkflowPersistence.reset_steps_from(self.run_id, list(to_reset))
        WorkflowPersistence.update_run_status(self.run_id, "running")

    def _get_downstream_steps(self, step_id: str) -> set[str]:
        """获取所有依赖指定步骤的下游步骤（递归）。"""
        downstream: set[str] = set()
        for step in self.template.steps:
            if step_id in step.depends_on:
                downstream.add(step.step_id)
                # 递归查找下游的下游
                downstream.update(self._get_downstream_steps(step.step_id))
        return downstream

    def _get_ready_steps(self) -> list[WorkflowStep]:
        """获取所有可以执行的步骤（依赖都已完成）。"""
        ready = []
        for step in self.template.steps:
            if self.step_statuses[step.step_id] != StepStatus.PENDING:
                continue
            # 检查所有依赖是否完成
            deps_met = all(
                self.step_statuses.get(dep) == StepStatus.COMPLETED
                for dep in step.depends_on
            )
            if deps_met:
                ready.append(step)
        return ready

    def _build_step_context(self, step: WorkflowStep, chapter_no: int, outline_id: int | None) -> dict[str, Any]:
        """构建步骤的输入上下文。

        使用 MemoryRetriever 从 L3 项目记忆获取数据，
        并从 L2 会话记忆映射补充输入。
        """
        # 从记忆系统获取上下文（L3 项目记忆）
        query = self.session_context.get("instruction", "")
        base_context = self.memory_retriever.retrieve_for_chapter(
            chapter_no=chapter_no,
            outline_id=outline_id,
            query=query,
            top_k=10,
            selection=self.session_context.get("context_selection"),
            include_generation_outline_context=step.agent_type in {"planner", "writer"},
        )

        # 从会话记忆中映射输入（L2 会话记忆）
        mapped_inputs = {}
        for ctx_key, sess_key in step.input_mapping.items():
            if sess_key in self.session_context:
                mapped_inputs[ctx_key] = self.session_context[sess_key]

        # 合并
        context = {**base_context, **mapped_inputs}

        # 补充常用字段
        context["chapter_no"] = chapter_no
        context["outline_id"] = outline_id
        context["volume_outline_text"] = format_volume_outline(base_context.get("volume_outline"))
        context["generation_outline_context_text"] = base_context.get("generation_outline_context_text", "")
        context["volume_title"] = base_context.get("volume_outline", {}).get("title", "")
        context["outline_title"] = base_context.get("outline", {}).get("title", "")
        context["outline_desc"] = base_context.get("outline", {}).get("description", "")

        return context

    def _step_variant_and_params(
        self,
        step: WorkflowStep,
        instruction: str,
        rhythm_level: str,
    ) -> tuple[str, dict[str, Any]]:
        """应用本次生成选项，只覆盖写作步骤的风格和模型参数。"""
        variant = (
            self.generation_options["writer_variant"]
            if step.agent_type == "writer"
            else step.variant
        )
        params: dict[str, Any] = {
            "instruction": instruction,
            "rhythm_level": rhythm_level,
            **step.params,
        }
        if step.agent_type == "writer":
            target_min, target_max = target_word_range(self.generation_options["target_word_count"])
            params.update({
                "temperature": self.generation_options["temperature"],
                "target_word_count": self.generation_options["target_word_count"],
                "target_word_min": target_min,
                "target_word_max": target_max,
                # 中文正文的 Token/字符比不固定，保留余量避免硬截断；篇幅由 Prompt 明确约束。
                "max_tokens": min(
                    20000,
                    max(1024, int(target_max * 1.6)),
                ),
                "writing_skill_guidance": build_skill_guidance(
                    self.generation_options["active_skills"]
                ),
            })
        return variant, params

    def _summarize_step_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """提取实际装入步骤上下文的资料清单，不持久化完整设定正文。"""
        selection = self.session_context.get("context_selection") or {}
        manual_selection = self.session_context.get("manual_context_selection") or {}

        def source_for(category: str, item_id: Any) -> str:
            if item_id in set(manual_selection.get(category) or []):
                return "手动选择"
            if item_id in set(selection.get(category) or []):
                return "页面已选/推荐"
            return "系统匹配"

        def source_items(key: str, category: str, label: str, name_field: str, detail_fields: tuple[str, ...] = ()) -> list[dict[str, Any]]:
            values = context.get(key)
            if not isinstance(values, list):
                return []
            result = []
            for item in values:
                if not isinstance(item, dict):
                    continue
                name = item.get(name_field)
                if name in (None, ""):
                    continue
                detail = next((str(item.get(field)).strip() for field in detail_fields if item.get(field)), "")
                result.append({
                    "category": label,
                    "id": item.get("id"),
                    "name": str(name),
                    "source": source_for(category, item.get("id")),
                    "summary": detail[:220],
                })
            return result

        # 步骤 1：只提取名称和章节号，保留作者判断本步骤资料来源所需的信息。
        def labels(key: str, field: str) -> list[str]:
            values = context.get(key)
            if not isinstance(values, list):
                return []
            return [
                str(item[field])
                for item in values
                if isinstance(item, dict) and item.get(field) not in (None, "")
            ]

        recent_summaries = context.get("recent_summaries")
        recent_chapters = [
            str(item["chapter_no"])
            for item in recent_summaries
            if isinstance(item, dict) and item.get("chapter_no") is not None
        ] if isinstance(recent_summaries, list) else []

        outline_segments = []
        for key, label, field, detail_fields in (
            ("overview_outline", "大纲总览", "title", ("description",)),
            ("previous_volume_outline", "前一卷纲", "title", ("description", "core_events")),
            ("volume_outline", "当前卷纲", "title", ("description", "core_events", "climax")),
            ("next_volume_outline", "下一卷纲", "title", ("description", "core_events")),
            ("outline", "当前单章细纲", "title", ("description",)),
            ("next_chapter_outline", "下一章单章细纲", "title", ("description",)),
        ):
            item = context.get(key)
            if isinstance(item, dict) and item:
                detail = "\n".join(str(item.get(name)).strip() for name in detail_fields if item.get(name))
                outline_segments.append({
                    "label": label,
                    "title": str(item.get(field) or label),
                    "chapter_no": item.get("chapter_no"),
                    "summary": detail[:260],
                })
        previous_chapter = context.get("previous_chapter")
        if isinstance(previous_chapter, dict) and previous_chapter:
            previous_detail = "\n".join(
                str(previous_chapter.get(key)).strip()
                for key in ("summary", "ending_excerpt")
                if previous_chapter.get(key)
            )
            outline_segments.append({
                "label": "紧邻上一章",
                "title": f"第{previous_chapter.get('chapter_no', '')}章 {previous_chapter.get('title', '')}".strip(),
                "chapter_no": previous_chapter.get("chapter_no"),
                "summary": previous_detail[:260],
            })

        sources = []
        sources.extend(source_items("characters", "character_ids", "人物", "name", ("identity", "personality", "background", "motivation")))
        sources.extend(source_items("organizations", "organization_ids", "组织", "name", ("description", "goal", "location")))
        sources.extend(source_items("world_settings", "world_setting_ids", "世界观", "title", ("rules", "geography", "atmosphere")))
        sources.extend(source_items("foreshadowings", "foreshadowing_ids", "伏笔", "keyword", ("description", "notes")))

        if isinstance(recent_summaries, list):
            sources.extend({
                "category": "前情摘要",
                "name": f"第{item.get('chapter_no', '')}章",
                "source": "最近章节",
                "summary": str(item.get("summary") or "")[:220],
            } for item in recent_summaries if isinstance(item, dict))
        if isinstance(previous_chapter, dict) and previous_chapter:
            sources.append({
                "category": "上一章衔接",
                "name": f"第{previous_chapter.get('chapter_no', '')}章 {previous_chapter.get('title', '')}".strip(),
                "source": "紧邻章节",
                "summary": str(previous_chapter.get("ending_excerpt") or previous_chapter.get("summary") or "")[:220],
            })
        memories = context.get("long_term_memories")
        if isinstance(memories, list):
            sources.extend({
                "category": "长期记忆",
                "name": str(item.get("title") or "未命名记忆"),
                "source": "项目记忆检索",
                "summary": str(item.get("content_summary") or item.get("content") or "")[:220],
            } for item in memories if isinstance(item, dict))

        project = context.get("project") or {}

        # 步骤 2：使用显式字段名，供前端运行记录展示与未来统计复用。
        return {
            "project_name": str(project.get("name") or ""),
            "project_settings": {
                "novel_type": str(project.get("novel_type") or ""),
                "writing_style": str(project.get("writing_style") or ""),
                "view_point": str(project.get("view_point") or ""),
                "pace_level": project.get("pace_level"),
            },
            "volume_title": str(context.get("volume_title") or ""),
            "outline_title": str(context.get("outline_title") or ""),
            "outline_segments": outline_segments,
            "sources": sources,
            "characters": labels("characters", "name"),
            "organizations": labels("organizations", "name"),
            "world_settings": labels("world_settings", "title"),
            "foreshadowings": labels("foreshadowings", "keyword"),
            "recent_chapters": recent_chapters,
            "long_term_memories": labels("long_term_memories", "title"),
        }

    def _effective_step_settings(
        self,
        step: WorkflowStep,
        variant: str,
        params: dict[str, Any],
        rhythm_level: str,
        agent: Any | None,
        model_called: bool = True,
    ) -> dict[str, Any]:
        """记录步骤真正交给 Agent/模型的白名单配置，避免快照包含凭据。"""
        agent_params = getattr(agent, "params", {}) if agent is not None else {}
        effective_params = {**agent_params, **params}
        settings: dict[str, Any] = {
            "agent_type": step.agent_type,
            "variant": variant,
            "rhythm_level": rhythm_level,
            "model_called": model_called,
            "agent_skills": [
                getattr(getattr(skill, "meta", None), "label", "")
                or getattr(getattr(skill, "meta", None), "name", "")
                for skill in getattr(agent, "skills", [])
            ],
        }
        if step.agent_type == "writer":
            settings["target_word_count"] = effective_params.get("target_word_count")
            settings["generation_skills"] = self.generation_options.get("active_skills", [])
        if model_called:
            from app.core.llm import get_effective_llm_settings

            llm_overrides = {
                key: effective_params.get(key)
                for key in ("temperature", "max_tokens")
            }
            settings["model"] = get_effective_llm_settings(llm_overrides)
        return settings

    def _capture_analysis_entity_catalog(self) -> dict[str, list[dict[str, Any]]]:
        """读取项目实体名称和 ID，供结构化分析结果安全解析实体引用。"""
        from app.db.session import get_business_db
        from app.services.chapter_change_proposals import load_entity_catalog

        # 步骤 1：读取当前项目全部可引用实体；图谱视图的截断列表不适合作为解析目录。
        with get_business_db() as db:
            # 步骤 2：只把匹配需要的 ID 和名称放进运行状态，避免复制整份设定正文。
            return load_entity_catalog(db, self.project_id)

    def _fallback_analysis_result(self) -> dict[str, Any] | None:
        """判断分析正文是否来自开发兜底稿，并生成不可沉淀的明确结果。

        步骤 1：按最终分析正文选择精修稿或写作稿的来源标记。
        步骤 2：若正文是开发兜底文本，则跳过模型分析并返回不可用状态。
        """
        # 步骤 1：精修稿继承写作稿事实，即使精修 Agent 成功也不能把兜底正文当成真实章节。
        sources = [self.session_context.get("draft_source", "")]
        if self.session_context.get("polished_content"):
            sources.append(self.session_context.get("polished_source", ""))
        if not any(str(source).startswith("fallback:") for source in sources):
            return None

        return {
            "content": "",
            "analysis_text": "",
            "summary": "",
            "character_changes": "",
            "world_changes": "",
            "new_foreshadowings": "",
            "timeline_events": "",
            "structured_analysis": {},
            "analysis_status": "unavailable",
            "analysis_message": "本章正文来自开发模式兜底稿，未运行章节分析；配置模型后请重新生成并分析。",
            "source": "fallback: 正文来源为开发模式兜底稿",
        }

    def _save_step_output(self, step: WorkflowStep, result: dict[str, Any]) -> None:
        """保存步骤输出到会话记忆和数据库。"""
        # 步骤 1：阻止空写作/精修结果被标记为完成并继续流入版本保存。
        if step.agent_type in {"writer", "polisher"} and not str(result.get("content", "")).strip():
            raise ValueError(f"{step.label or step.step_id}未返回正文内容")

        if step.agent_type == "analyzer":
            # 步骤 2：模型调用失败时，兜底文本只用于界面诊断，不能成为正式章节分析。
            source = str(result.get("source", ""))
            if source.startswith(("fallback:", "timeout:")):
                result["analysis_status"] = "unavailable"
                if source.startswith("timeout:"):
                    result["analysis_message"] = source.removeprefix("timeout:").strip()
                else:
                    result.setdefault("analysis_message", "模型服务不可用，本次未保存章节分析；配置模型后可重新分析。")
                result["summary"] = ""
                result["character_changes"] = ""
                result["world_changes"] = ""
                result["new_foreshadowings"] = ""
                result["timeline_events"] = ""
                result["structured_analysis"] = {}
            else:
                result.setdefault("analysis_status", "completed")
                result.setdefault("analysis_message", "")
            # 步骤 3：将实体解析目录随分析输出一起持久化，断点续跑后仍可解析提案。
            result.setdefault(
                "analysis_entity_catalog",
                self.session_context.get("analysis_entity_catalog", {}),
            )
        self.step_results[step.step_id] = result

        # 按映射保存到会话记忆
        for result_key, sess_key in step.output_mapping.items():
            if result_key in result:
                self.session_context[sess_key] = result[result_key]

        # 持久化步骤结果
        output_for_db = {k: v for k, v in result.items() if k != "type"}
        WorkflowPersistence.update_step_record(
            run_id=self.run_id,
            step_id=step.step_id,
            status="completed",
            output_snapshot=output_for_db,
            # 步骤 4：记录供应商实际用量；空对象表示供应商未提供 Token 统计，避免残留重跑前的数字。
            token_usage=result.get("token_usage") or {},
            llm_calls=result.get("llm_calls", 0),
        )

    def _update_progress(self) -> None:
        """更新工作流进度。"""
        total = len(self.step_statuses)
        completed = sum(
            1 for s in self.step_statuses.values()
            if s == StepStatus.COMPLETED
        )
        progress = int(completed / total * 100) if total > 0 else 0

        # 计算字数
        word_count = 0
        content = self.session_context.get("draft_content", "")
        if content:
            word_count = len(content)

        # 输出预览
        output_preview = content[:200] if content else ""

        WorkflowPersistence.update_run_status(
            run_id=self.run_id,
            status=self.status.value,
            progress=progress,
            word_count=word_count,
            output_preview=output_preview,
        )

    def run(
        self,
        chapter_no: int,
        outline_id: int | None = None,
        instruction: str | None = None,
        rhythm_level: str | None = None,
        context_selection: dict[str, list[int]] | None = None,
        manual_context_selection: dict[str, list[int]] | None = None,
        generation_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """同步执行工作流。

        Args:
            chapter_no: 章节号
            outline_id: 大纲 ID
            instruction: 用户补充要求
            rhythm_level: 节奏等级

        Returns:
            最终结果字典
        """
        if generation_options is not None:
            self.generation_options = normalize_generation_options(generation_options)
        self.status = (
            WorkflowStatus.PAUSED
            if self._cancel_event.is_set()
            else WorkflowStatus.RUNNING
        )
        if instruction is not None:
            self.session_context["instruction"] = instruction
        if rhythm_level is not None:
            self.session_context["rhythm_level"] = rhythm_level
        instruction = str(self.session_context.get("instruction") or "")
        rhythm_level = str(self.session_context.get("rhythm_level") or "medium")
        self.session_context["generation_options"] = self.generation_options
        if context_selection is not None:
            self.session_context["context_selection"] = context_selection
        if manual_context_selection is not None:
            self.session_context["manual_context_selection"] = manual_context_selection

        if not self._cancel_event.is_set() and not WorkflowPersistence.resume_run(self.run_id):
            WorkflowPersistence.update_run_status(run_id=self.run_id, status="running")
        if self._cancel_event.is_set():
            WorkflowPersistence.update_run_status(run_id=self.run_id, status="paused")

        from .presets import get_agent

        while True:
            ready_steps = self._get_ready_steps()
            if not ready_steps:
                break

            for step in ready_steps:
                if self._cancel_event.is_set():
                    self.status = WorkflowStatus.PAUSED
                    break
                self.step_statuses[step.step_id] = StepStatus.RUNNING
                WorkflowPersistence.update_run_status(
                    self.run_id, "running", current_step=step.step_id
                )

                # 创建步骤记录
                step_variant, params = self._step_variant_and_params(
                    step, instruction, rhythm_level
                )
                context_preview = {
                    "chapter_no": chapter_no,
                    "outline_id": outline_id,
                    "instruction": instruction,
                    "context_selection": self.session_context.get("context_selection"),
                    "manual_context_selection": self.session_context.get("manual_context_selection"),
                    "generation_options": self.generation_options,
                    "rhythm_level": rhythm_level,
                }
                WorkflowPersistence.create_step_record(
                    run_id=self.run_id,
                    step_id=step.step_id,
                    step_name=step.label,
                    agent_type=step.agent_type,
                    variant_name=step_variant,
                    input_snapshot=context_preview,
                )

                try:
                    # 构建上下文
                    context = self._build_step_context(step, chapter_no, outline_id)
                    # 步骤 1：分析前捕获完整项目实体名录，用于把自然语言名称解析成项目内 ID。
                    if step.agent_type == "analyzer":
                        self.session_context["analysis_entity_catalog"] = self._capture_analysis_entity_catalog()

                    # 添加会话记忆中的字段
                    context.update(self.session_context)

                    # 步骤 2：生成一份可核对的上下文与实际设置清单，不保存完整正文或敏感配置。
                    fallback_result = self._fallback_analysis_result() if step.agent_type == "analyzer" else None
                    agent = get_agent(step.agent_type, step_variant) if fallback_result is None else None
                    effective_settings = self._effective_step_settings(
                        step, step_variant, params, rhythm_level, agent,
                        model_called=fallback_result is None,
                    )
                    input_snapshot = {
                        **context_preview,
                        "context_summary": self._summarize_step_context(context),
                        "effective_settings": effective_settings,
                    }
                    WorkflowPersistence.update_step_record(
                        run_id=self.run_id,
                        step_id=step.step_id,
                        status="running",
                        input_snapshot=input_snapshot,
                        # 先记录已进入模型调用步骤的尝试；即使中断或失败，也保留本次调用计数。
                        llm_calls=1 if effective_settings["model_called"] else 0,
                    )

                    if self._cancel_event.is_set():
                        self._pause_active_step(step)
                        break

                    # 合并步骤参数
                    # 创建并执行 Agent
                    # 步骤 2：开发兜底正文不能再进入分析器，避免虚构摘要和设定提案。
                    result = fallback_result
                    if result is None and agent is not None:
                        result = agent.run(
                            context,
                            {**params, "_cancel_event": self._cancel_event},
                        )

                    if self._cancel_event.is_set():
                        partial_content = str(
                            (result or {}).get("content") or ""
                        ) if step.agent_type in {"writer", "polisher"} else ""
                        self._pause_active_step(step, partial_content)
                        break

                    # 保存结果
                    self._save_step_output(step, result)
                    self.step_statuses[step.step_id] = StepStatus.COMPLETED
                    self._update_progress()

                except Exception as exc:
                    if self._cancel_event.is_set():
                        self._pause_active_step(step)
                        break
                    self.step_statuses[step.step_id] = StepStatus.FAILED
                    self.status = WorkflowStatus.FAILED
                    self.session_context["error"] = str(exc)

                    WorkflowPersistence.update_step_record(
                        run_id=self.run_id,
                        step_id=step.step_id,
                        status="failed",
                        error_message=str(exc),
                    )
                    WorkflowPersistence.update_run_status(
                        run_id=self.run_id,
                        status="failed",
                        error_message=str(exc),
                    )
                    self._release_cancel_event(self.run_id, self._cancel_event)
                    return {"status": "failed", "error": str(exc), "run_id": self.run_id}

            if self.status == WorkflowStatus.PAUSED:
                break

        # 判断是否所有步骤都完成了
        all_completed = all(
            s == StepStatus.COMPLETED for s in self.step_statuses.values()
        )
        if self._cancel_event.is_set():
            self.status = WorkflowStatus.PAUSED
        if all_completed and self.status != WorkflowStatus.PAUSED:
            # 步骤 1：优先采用精修稿；快速写作和未精修模板回退到草稿。
            self.session_context["final_content"] = (
                self.session_context.get("polished_content")
                or self.session_context.get("draft_content", "")
            )
            self.status = WorkflowStatus.COMPLETED
            WorkflowPersistence.update_run_status(
                self.run_id, "completed", progress=100
            )

        self._release_cancel_event(self.run_id, self._cancel_event)
        return {
            "status": self.status.value,
            "run_id": self.run_id,
            "session_context": self.session_context,
            "step_statuses": {k: v.value for k, v in self.step_statuses.items()},
        }

    def run_stream(
        self,
        chapter_no: int,
        outline_id: int | None = None,
        instruction: str | None = None,
        rhythm_level: str | None = None,
        context_selection: dict[str, list[int]] | None = None,
        manual_context_selection: dict[str, list[int]] | None = None,
        generation_options: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """带运行互斥保护的流式执行入口。"""
        lock = self._acquire_execution_lock(self.run_id)
        if lock is None:
            yield {
                "type": "error",
                "message": "该工作流仍有模型请求在执行，当前续传未启动；请等待原请求结束后刷新状态。",
            }
            return
        try:
            yield from self._run_stream_unlocked(
                chapter_no=chapter_no,
                outline_id=outline_id,
                instruction=instruction,
                rhythm_level=rhythm_level,
                context_selection=context_selection,
                manual_context_selection=manual_context_selection,
                generation_options=generation_options,
            )
        finally:
            self._release_execution_lock(self.run_id, lock)

    def _run_stream_unlocked(
        self,
        chapter_no: int,
        outline_id: int | None = None,
        instruction: str | None = None,
        rhythm_level: str | None = None,
        context_selection: dict[str, list[int]] | None = None,
        manual_context_selection: dict[str, list[int]] | None = None,
        generation_options: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """流式执行工作流。

        Yields:
            事件字典:
            - {"type": "step_start", "step_id": ..., "label": ...}
            - {"type": "delta", "step_id": ..., "content": ...}
            - {"type": "step_done", "step_id": ..., "result": ...}
            - {"type": "workflow_done", "status": ...}
            - {"type": "error", "message": ...}
        """
        if generation_options is not None:
            self.generation_options = normalize_generation_options(generation_options)
        self.status = (
            WorkflowStatus.PAUSED
            if self._cancel_event.is_set()
            else WorkflowStatus.RUNNING
        )
        if instruction is not None:
            self.session_context["instruction"] = instruction
        if rhythm_level is not None:
            self.session_context["rhythm_level"] = rhythm_level
        instruction = str(self.session_context.get("instruction") or "")
        rhythm_level = str(self.session_context.get("rhythm_level") or "medium")
        self.session_context["generation_options"] = self.generation_options
        if context_selection is not None:
            self.session_context["context_selection"] = context_selection
        if manual_context_selection is not None:
            self.session_context["manual_context_selection"] = manual_context_selection

        if not self._cancel_event.is_set() and not WorkflowPersistence.resume_run(self.run_id):
            WorkflowPersistence.update_run_status(run_id=self.run_id, status="running")
        if self._cancel_event.is_set():
            WorkflowPersistence.update_run_status(run_id=self.run_id, status="paused")

        from .presets import get_agent

        while True:
            ready_steps = self._get_ready_steps()
            if not ready_steps:
                break

            for step in ready_steps:
                if self._cancel_event.is_set():
                    self.status = WorkflowStatus.PAUSED
                    break
                self.step_statuses[step.step_id] = StepStatus.RUNNING
                WorkflowPersistence.update_run_status(
                    self.run_id, "running", current_step=step.step_id
                )

                # 创建步骤记录
                step_variant, params = self._step_variant_and_params(
                    step, instruction, rhythm_level
                )
                context_preview = {
                    "chapter_no": chapter_no,
                    "outline_id": outline_id,
                    "instruction": instruction,
                    "context_selection": self.session_context.get("context_selection"),
                    "manual_context_selection": self.session_context.get("manual_context_selection"),
                    "generation_options": self.generation_options,
                    "rhythm_level": rhythm_level,
                }
                WorkflowPersistence.create_step_record(
                    run_id=self.run_id,
                    step_id=step.step_id,
                    step_name=step.label,
                    agent_type=step.agent_type,
                    variant_name=step_variant,
                    input_snapshot=context_preview,
                )

                yield {
                    "type": "step_start",
                    "step_id": step.step_id,
                    "label": step.label,
                    "run_id": self.run_id,
                }

                try:
                    context = self._build_step_context(step, chapter_no, outline_id)
                    # 步骤 1：流式和同步路径使用同一套分析实体目录与 ID 解析输入。
                    if step.agent_type == "analyzer":
                        self.session_context["analysis_entity_catalog"] = self._capture_analysis_entity_catalog()
                    context.update(self.session_context)

                    # 步骤 2：兜底正文不调用分析模型；正常内容则执行对应 Agent。
                    fallback_result = self._fallback_analysis_result() if step.agent_type == "analyzer" else None
                    agent = get_agent(step.agent_type, step_variant) if fallback_result is None else None
                    context_summary = self._summarize_step_context(context)
                    effective_settings = self._effective_step_settings(
                        step, step_variant, params, rhythm_level, agent,
                        model_called=fallback_result is None,
                    )
                    WorkflowPersistence.update_step_record(
                        run_id=self.run_id,
                        step_id=step.step_id,
                        status="running",
                        input_snapshot={
                            **context_preview,
                            "context_summary": context_summary,
                            "effective_settings": effective_settings,
                        },
                        # 中断时也保留已开始步骤的模型调用尝试数。
                        llm_calls=1 if effective_settings["model_called"] else 0,
                    )
                    # 步骤 3：前端即时展示本步骤真正组装的资料与生效配置。
                    yield {
                        "type": "step_context",
                        "step_id": step.step_id,
                        "context_summary": context_summary,
                        "effective_settings": effective_settings,
                    }

                    # 用户可能在资料装配期间点击中断；不要在中断请求后再启动模型调用。
                    if self._cancel_event.is_set():
                        self._pause_active_step(step)
                        break

                    # 流式执行
                    final_result = None
                    if fallback_result is not None:
                        # 步骤 3：保留明确的不可用结果并完成工作流，不调用分析模型。
                        final_result = {"type": "done", **fallback_result}
                    elif hasattr(agent, "run_stream") and agent.meta.supports_streaming:
                        partial_chunks: list[str] = []
                        last_partial_checkpoint = 0
                        agent_stream = iter(agent.run_stream(
                            context,
                            {**params, "_cancel_event": self._cancel_event},
                        ))
                        for event in agent_stream:
                            if self._cancel_event.is_set():
                                break
                            if event.get("type") == "delta":
                                if step.agent_type in {"writer", "polisher"}:
                                    partial_chunks.append(event.get("content", ""))
                                    partial_content = "".join(partial_chunks)
                                    # 定期保存未完成正文，刷新或断连时仍能恢复。
                                    if len(partial_content) - last_partial_checkpoint >= 500:
                                        WorkflowPersistence.update_step_record(
                                            run_id=self.run_id,
                                            step_id=step.step_id,
                                            status="running",
                                            output_snapshot={"partial_content": partial_content},
                                        )
                                        last_partial_checkpoint = len(partial_content)
                                yield {
                                    "type": "delta",
                                    "step_id": step.step_id,
                                    "content": event.get("content", ""),
                                }
                            elif event.get("type") == "done":
                                final_result = event
                            elif event.get("type") == "error":
                                raise Exception(event.get("message", "Unknown error"))
                        if self._cancel_event.is_set():
                            close_stream = getattr(agent_stream, "close", None)
                            if close_stream:
                                close_stream()
                            partial_content = "".join(partial_chunks)
                            self._pause_active_step(step, partial_content)
                            break
                    else:
                        # 不支持流式，同步执行
                        result = agent.run(
                            context,
                            {**params, "_cancel_event": self._cancel_event},
                        )
                        final_result = {"type": "done", **result}

                    if self.status == WorkflowStatus.PAUSED:
                        break

                    if final_result is None:
                        final_result = {"type": "done", "content": ""}

                    # 保存结果
                    self._save_step_output(step, final_result)
                    self.step_statuses[step.step_id] = StepStatus.COMPLETED
                    self._update_progress()

                    yield {
                        "type": "step_done",
                        "step_id": step.step_id,
                        "result": {k: v for k, v in final_result.items() if k != "type"},
                    }

                except Exception as exc:
                    if self._cancel_event.is_set():
                        partial_content = str(
                            self.session_context.get("interrupted_partial_content") or ""
                        )
                        self._pause_active_step(step, partial_content)
                        break
                    self.step_statuses[step.step_id] = StepStatus.FAILED
                    self.status = WorkflowStatus.FAILED

                    WorkflowPersistence.update_step_record(
                        run_id=self.run_id,
                        step_id=step.step_id,
                        status="failed",
                        error_message=str(exc),
                    )
                    WorkflowPersistence.update_run_status(
                        run_id=self.run_id,
                        status="failed",
                        error_message=str(exc),
                    )

                    yield {"type": "error", "step_id": step.step_id, "message": str(exc)}
                    self._release_cancel_event(self.run_id, self._cancel_event)
                    return

                if self.status == WorkflowStatus.PAUSED:
                    break

            if self.status == WorkflowStatus.PAUSED:
                break

        # 完成
        all_completed = all(
            s == StepStatus.COMPLETED for s in self.step_statuses.values()
        )
        # 即使用户在最后一个 token 已到达后立即点击中断，也不把运行报成完成。
        if self._cancel_event.is_set():
            self.status = WorkflowStatus.PAUSED
        if all_completed and self.status != WorkflowStatus.PAUSED:
            # 步骤 1：让同步与流式工作流共用同一份最终正文定义。
            self.session_context["final_content"] = (
                self.session_context.get("polished_content")
                or self.session_context.get("draft_content", "")
            )
            self.status = WorkflowStatus.COMPLETED
            WorkflowPersistence.update_run_status(
                self.run_id, "completed", progress=100
            )

        self._release_cancel_event(self.run_id, self._cancel_event)
        yield {
            "type": "workflow_done",
            "status": self.status.value,
            "run_id": self.run_id,
            "session_context": self.session_context,
            "step_statuses": {k: v.value for k, v in self.step_statuses.items()},
        }


def list_templates() -> list[dict]:
    """列出所有可用工作流模板。"""
    return [
        {
            "name": t.name,
            "label": t.label,
            "description": t.description,
            "icon": t.icon,
            "category": t.category,
            "step_count": len(t.steps),
        }
        for t in BUILTIN_TEMPLATES.values()
    ]
