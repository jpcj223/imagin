"""工作流引擎（v3.0）。

支持模板化工作流、步骤编排、状态持久化、断点续传。
"""
from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.memory.retriever import MemoryRetriever
from .persistence import WorkflowPersistence


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

    def __init__(
        self,
        project_id: int,
        template_name: str,
        run_id: str | None = None,
        chapter_id: int | None = None,
        outline_id: int | None = None,
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

    def _persist_new_run(self) -> None:
        """持久化新的工作流运行记录。"""
        variant_selections = {
            step.step_id: step.variant for step in self.template.steps
        }
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

        # 恢复步骤状态
        for step_id, status_str in state["step_statuses"].items():
            if step_id in self.step_statuses:
                # 步骤 1：恢复时把上次运行中或失败的步骤重新排队，保留已完成步骤结果。
                # 客户端断开时后端无法收到取消通知，因此数据库里的 running 也必须可重试。
                if status_str in {StepStatus.RUNNING.value, StepStatus.FAILED.value}:
                    self.step_statuses[step_id] = StepStatus.PENDING
                else:
                    self.step_statuses[step_id] = StepStatus(status_str)

        # 恢复步骤结果
        self.step_results = state["step_results"]

        # 恢复会话上下文
        self.session_context = state["session_context"]

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
        context["outline_title"] = base_context.get("outline", {}).get("title", "")
        context["outline_desc"] = base_context.get("outline", {}).get("description", "")

        return context

    @staticmethod
    def _summarize_step_context(context: dict[str, Any]) -> dict[str, Any]:
        """为运行记录提取轻量上下文清单，不持久化完整设定正文。"""
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

        # 步骤 2：使用显式字段名，供前端运行记录展示与未来统计复用。
        return {
            "outline_title": str(context.get("outline_title") or ""),
            "characters": labels("characters", "name"),
            "organizations": labels("organizations", "name"),
            "world_settings": labels("world_settings", "title"),
            "foreshadowings": labels("foreshadowings", "keyword"),
            "recent_chapters": recent_chapters,
            "long_term_memories": labels("long_term_memories", "title"),
        }

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
            if str(result.get("source", "")).startswith("fallback:"):
                result["analysis_status"] = "unavailable"
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
        instruction: str = "",
        rhythm_level: str = "medium",
        context_selection: dict[str, list[int]] | None = None,
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
        self.status = WorkflowStatus.RUNNING
        self.session_context["instruction"] = instruction
        self.session_context["rhythm_level"] = rhythm_level
        if context_selection is not None:
            self.session_context["context_selection"] = context_selection

        WorkflowPersistence.update_run_status(
            run_id=self.run_id,
            status="running",
        )

        from .presets import get_agent

        while True:
            ready_steps = self._get_ready_steps()
            if not ready_steps:
                break

            for step in ready_steps:
                self.step_statuses[step.step_id] = StepStatus.RUNNING
                WorkflowPersistence.update_run_status(
                    self.run_id, "running", current_step=step.step_id
                )

                # 创建步骤记录
                context_preview = {
                    "chapter_no": chapter_no,
                    "outline_id": outline_id,
                    "instruction": instruction,
                    "context_selection": self.session_context.get("context_selection"),
                }
                WorkflowPersistence.create_step_record(
                    run_id=self.run_id,
                    step_id=step.step_id,
                    step_name=step.label,
                    agent_type=step.agent_type,
                    variant_name=step.variant,
                    input_snapshot=context_preview,
                )

                try:
                    # 构建上下文
                    context = self._build_step_context(step, chapter_no, outline_id)
                    # 步骤 1：仅保存实际装配资料的名称摘要，避免记录重复正文或提示词内容。
                    WorkflowPersistence.update_step_record(
                        run_id=self.run_id,
                        step_id=step.step_id,
                        status="running",
                        input_snapshot={
                            **context_preview,
                            "context_summary": self._summarize_step_context(context),
                        },
                    )

                    # 步骤 1：分析前捕获完整项目实体名录，用于把自然语言名称解析成项目内 ID。
                    if step.agent_type == "analyzer":
                        self.session_context["analysis_entity_catalog"] = self._capture_analysis_entity_catalog()

                    # 添加会话记忆中的字段
                    context.update(self.session_context)

                    # 合并步骤参数
                    params = {"instruction": instruction, "rhythm_level": rhythm_level}
                    params.update(step.params)

                    # 创建并执行 Agent
                    # 步骤 2：开发兜底正文不能再进入分析器，避免虚构摘要和设定提案。
                    result = self._fallback_analysis_result() if step.agent_type == "analyzer" else None
                    if result is None:
                        agent = get_agent(step.agent_type, step.variant)
                        result = agent.run(context, params)

                    # 保存结果
                    self._save_step_output(step, result)
                    self.step_statuses[step.step_id] = StepStatus.COMPLETED
                    self._update_progress()

                except Exception as exc:
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
                    return {"status": "failed", "error": str(exc), "run_id": self.run_id}

        # 判断是否所有步骤都完成了
        all_completed = all(
            s == StepStatus.COMPLETED for s in self.step_statuses.values()
        )
        if all_completed:
            # 步骤 1：优先采用精修稿；快速写作和未精修模板回退到草稿。
            self.session_context["final_content"] = (
                self.session_context.get("polished_content")
                or self.session_context.get("draft_content", "")
            )
            self.status = WorkflowStatus.COMPLETED
            WorkflowPersistence.update_run_status(
                self.run_id, "completed", progress=100
            )

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
        instruction: str = "",
        rhythm_level: str = "medium",
        context_selection: dict[str, list[int]] | None = None,
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
        self.status = WorkflowStatus.RUNNING
        self.session_context["instruction"] = instruction
        self.session_context["rhythm_level"] = rhythm_level
        if context_selection is not None:
            self.session_context["context_selection"] = context_selection

        WorkflowPersistence.update_run_status(
            run_id=self.run_id,
            status="running",
        )

        from .presets import get_agent

        while True:
            ready_steps = self._get_ready_steps()
            if not ready_steps:
                break

            for step in ready_steps:
                self.step_statuses[step.step_id] = StepStatus.RUNNING
                WorkflowPersistence.update_run_status(
                    self.run_id, "running", current_step=step.step_id
                )

                # 创建步骤记录
                context_preview = {
                    "chapter_no": chapter_no,
                    "outline_id": outline_id,
                    "instruction": instruction,
                    "context_selection": self.session_context.get("context_selection"),
                }
                WorkflowPersistence.create_step_record(
                    run_id=self.run_id,
                    step_id=step.step_id,
                    step_name=step.label,
                    agent_type=step.agent_type,
                    variant_name=step.variant,
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
                    # 步骤 1：同步路径相同，只保存实际装配资料的名称摘要，不复制设定正文。
                    WorkflowPersistence.update_step_record(
                        run_id=self.run_id,
                        step_id=step.step_id,
                        status="running",
                        input_snapshot={
                            **context_preview,
                            "context_summary": self._summarize_step_context(context),
                        },
                    )

                    # 步骤 1：流式和同步路径使用同一套分析实体目录与 ID 解析输入。
                    if step.agent_type == "analyzer":
                        self.session_context["analysis_entity_catalog"] = self._capture_analysis_entity_catalog()
                    context.update(self.session_context)

                    params = {"instruction": instruction, "rhythm_level": rhythm_level}
                    params.update(step.params)

                    # 步骤 2：兜底正文不调用分析模型；正常内容则执行对应 Agent。
                    fallback_result = self._fallback_analysis_result() if step.agent_type == "analyzer" else None
                    agent = get_agent(step.agent_type, step.variant) if fallback_result is None else None

                    # 流式执行
                    final_result = None
                    if fallback_result is not None:
                        # 步骤 3：保留明确的不可用结果并完成工作流，不调用分析模型。
                        final_result = {"type": "done", **fallback_result}
                    elif hasattr(agent, "run_stream") and agent.meta.supports_streaming:
                        for event in agent.run_stream(context, params):
                            if event.get("type") == "delta":
                                yield {
                                    "type": "delta",
                                    "step_id": step.step_id,
                                    "content": event.get("content", ""),
                                }
                            elif event.get("type") == "done":
                                final_result = event
                            elif event.get("type") == "error":
                                raise Exception(event.get("message", "Unknown error"))
                    else:
                        # 不支持流式，同步执行
                        result = agent.run(context, params)
                        final_result = {"type": "done", **result}

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
                    return

        # 完成
        all_completed = all(
            s == StepStatus.COMPLETED for s in self.step_statuses.values()
        )
        if all_completed:
            # 步骤 1：让同步与流式工作流共用同一份最终正文定义。
            self.session_context["final_content"] = (
                self.session_context.get("polished_content")
                or self.session_context.get("draft_content", "")
            )
            self.status = WorkflowStatus.COMPLETED
            WorkflowPersistence.update_run_status(
                self.run_id, "completed", progress=100
            )

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
