"""工作流持久化层。

负责工作流执行状态的读写、断点续传、历史记录查询。
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import DATA_DIR
from app.db.session import get_business_db
from app.models.business.chapter import Chapter
from app.models.business.workflow_memory import (
    GenerationVersion,
    WorkflowRun,
    WorkflowStepRecord,
)
from app.db.repository import row_to_dict, rows_to_dicts

# 版本内容存储目录
VERSIONS_DIR = DATA_DIR / "versions"


def _get_version_file_path(chapter_id: int, version_id: str) -> Path:
    """获取版本内容文件路径。"""
    chapter_dir = VERSIONS_DIR / str(chapter_id)
    chapter_dir.mkdir(parents=True, exist_ok=True)
    return chapter_dir / f"{version_id}.txt"


def _save_version_content(chapter_id: int, version_id: str, content: str) -> str:
    """保存版本内容到文件，返回相对路径。"""
    file_path = _get_version_file_path(chapter_id, version_id)
    file_path.write_text(content, encoding="utf-8")
    return str(file_path.relative_to(DATA_DIR))


def _read_version_content(content_file_path: str) -> str:
    """从文件读取版本内容。"""
    if not content_file_path:
        return ""
    full_path = DATA_DIR / content_file_path
    if not full_path.exists():
        return ""
    return full_path.read_text(encoding="utf-8")


class WorkflowPersistence:
    """工作流持久化管理器。"""

    # ----------------------------------------------------------
    # 工作流运行记录
    # ----------------------------------------------------------

    @staticmethod
    def create_run(
        project_id: int,
        template_name: str,
        template_snapshot: dict,
        variant_selections: dict | None = None,
        chapter_id: int | None = None,
        outline_id: int | None = None,
    ) -> str:
        """创建工作流运行记录。

        Returns:
            run_id
        """
        run_id = str(uuid.uuid4())
        with get_business_db() as db:
            run = WorkflowRun(
                run_id=run_id,
                project_id=project_id,
                chapter_id=chapter_id,
                outline_id=outline_id,
                template_name=template_name,
                template_snapshot=json.dumps(template_snapshot, ensure_ascii=False),
                variant_selections=json.dumps(variant_selections or {}, ensure_ascii=False),
                status="pending",
                progress=0,
                started_at=datetime.utcnow(),
            )
            db.add(run)
            db.commit()
        return run_id

    @staticmethod
    def update_run_status(
        run_id: str,
        status: str,
        current_step: str | None = None,
        progress: int | None = None,
        word_count: int | None = None,
        output_preview: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """更新工作流运行状态。"""
        with get_business_db() as db:
            run = db.query(WorkflowRun).filter(WorkflowRun.run_id == run_id).first()
            if not run:
                return

            run.status = status
            if current_step is not None:
                run.current_step = current_step
            if progress is not None:
                run.progress = progress
            if word_count is not None:
                run.word_count = word_count
            if output_preview is not None:
                run.output_preview = output_preview[:500]  # 限制长度
            if error_message is not None:
                run.error_message = error_message

            if status == "running" and run.started_at is None:
                run.started_at = datetime.utcnow()
            if status == "running":
                # 步骤 1：重试失败的运行时清除旧错误和结束时间，历史失败仍保留在步骤记录中。
                run.error_message = ""
                run.failed_at = None
                run.completed_at = None
            if status == "completed":
                run.completed_at = datetime.utcnow()
            if status == "failed":
                run.failed_at = datetime.utcnow()

            db.commit()

    @staticmethod
    def get_run(run_id: str) -> dict | None:
        """获取工作流运行记录。"""
        with get_business_db() as db:
            run = db.query(WorkflowRun).filter(WorkflowRun.run_id == run_id).first()
            if run:
                data = row_to_dict(run)
                # 解析 JSON 字段
                if data.get("template_snapshot"):
                    try:
                        data["template_snapshot"] = json.loads(data["template_snapshot"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if data.get("variant_selections"):
                    try:
                        data["variant_selections"] = json.loads(data["variant_selections"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                return data
            return None

    @staticmethod
    def list_runs(
        project_id: int,
        chapter_id: int | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """列出工作流运行记录。"""
        with get_business_db() as db:
            query = db.query(WorkflowRun).filter(WorkflowRun.project_id == project_id)
            if chapter_id:
                query = query.filter(WorkflowRun.chapter_id == chapter_id)
            if status:
                query = query.filter(WorkflowRun.status == status)
            rows = (
                query.order_by(WorkflowRun.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
            return rows_to_dicts(rows)

    # ----------------------------------------------------------
    # 步骤记录
    # ----------------------------------------------------------

    @staticmethod
    def create_step_record(
        run_id: str,
        step_id: str,
        step_name: str = "",
        agent_type: str = "",
        variant_name: str = "default",
        input_snapshot: dict | None = None,
    ) -> None:
        """创建步骤执行记录。"""
        with get_business_db() as db:
            record = WorkflowStepRecord(
                run_id=run_id,
                step_id=step_id,
                step_name=step_name,
                agent_type=agent_type,
                variant_name=variant_name,
                status="running",
                input_snapshot=json.dumps(input_snapshot or {}, ensure_ascii=False),
                started_at=datetime.utcnow(),
            )
            db.add(record)
            db.commit()

    @staticmethod
    def update_step_record(
        run_id: str,
        step_id: str,
        status: str,
        input_snapshot: dict | None = None,
        output_snapshot: dict | None = None,
        output_file_path: str | None = None,
        error_message: str | None = None,
        error_traceback: str | None = None,
        token_usage: dict | None = None,
        llm_calls: int | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """更新步骤执行记录。

        步骤 1：定位当前运行中该步骤的最近一次尝试。
        步骤 2：只更新调用方提供的输入、输出、用量与错误字段。
        步骤 3：步骤结束时记录完成时间和真实运行时长。
        """
        with get_business_db() as db:
            record = (
                db.query(WorkflowStepRecord)
                .filter(
                    WorkflowStepRecord.run_id == run_id,
                    WorkflowStepRecord.step_id == step_id,
                )
                .order_by(WorkflowStepRecord.id.desc())
                .first()
            )
            if not record:
                return

            record.status = status
            if input_snapshot is not None:
                record.input_snapshot = json.dumps(input_snapshot, ensure_ascii=False)
            if output_snapshot is not None:
                record.output_snapshot = json.dumps(output_snapshot, ensure_ascii=False)
            if output_file_path is not None:
                record.output_file_path = output_file_path
            if error_message is not None:
                record.error_message = error_message
            if error_traceback is not None:
                record.error_traceback = error_traceback
            if token_usage is not None:
                record.token_usage = json.dumps(token_usage, ensure_ascii=False)
            if llm_calls is not None:
                record.llm_calls = llm_calls
            if duration_ms is not None:
                record.duration_ms = duration_ms

            if status in ("completed", "failed", "skipped"):
                record.completed_at = datetime.utcnow()
                if record.started_at:
                    delta = record.completed_at - record.started_at
                    record.duration_ms = int(delta.total_seconds() * 1000)

            db.commit()

    @staticmethod
    def reset_steps_from(run_id: str, step_ids: list[str]) -> None:
        """批量重置步骤状态为 pending，清除输出和错误信息。

        用于「从某步骤重跑」功能。
        """
        if not step_ids:
            return
        with get_business_db() as db:
            records = (
                db.query(WorkflowStepRecord)
                .filter(
                    WorkflowStepRecord.run_id == run_id,
                    WorkflowStepRecord.step_id.in_(step_ids),
                )
                .all()
            )
            for record in records:
                record.status = "pending"
                record.output_snapshot = None
                record.output_file_path = None
                record.error_message = None
                record.error_traceback = None
                record.started_at = None
                record.completed_at = None
                record.duration_ms = None
            db.commit()

    @staticmethod
    def get_step_records(run_id: str) -> list[dict]:
        """获取工作流的所有步骤记录。"""
        with get_business_db() as db:
            rows = (
                db.query(WorkflowStepRecord)
                .filter(WorkflowStepRecord.run_id == run_id)
                .order_by(WorkflowStepRecord.id.asc())
                .all()
            )
            result = []
            for row in rows:
                data = row_to_dict(row)
                # 解析 JSON 字段
                for field in ("input_snapshot", "output_snapshot", "token_usage"):
                    if data.get(field):
                        try:
                            data[field] = json.loads(data[field])
                        except (json.JSONDecodeError, TypeError):
                            pass
                result.append(data)
            return result

    # ----------------------------------------------------------
    # 生成版本
    # ----------------------------------------------------------

    @staticmethod
    def create_version(
        chapter_id: int,
        run_id: str | None = None,
        content: str = "",
        word_count: int = 0,
        summary: str = "",
        version_number: int | None = None,
    ) -> str:
        """创建生成版本。

        Returns:
            version_id
        """
        version_id = str(uuid.uuid4())
        with get_business_db() as db:
            # 计算版本号
            if version_number is None:
                max_ver = (
                    db.query(GenerationVersion)
                    .filter(GenerationVersion.chapter_id == chapter_id)
                    .count()
                )
                version_number = max_ver + 1

            # 先把其他版本的 is_current 设为 0
            db.query(GenerationVersion).filter(
                GenerationVersion.chapter_id == chapter_id
            ).update({"is_current": 0})

            # 保存内容到文件
            content_file_path = _save_version_content(chapter_id, version_id, content) if content else None

            version = GenerationVersion(
                version_id=version_id,
                chapter_id=chapter_id,
                run_id=run_id,
                version_number=version_number,
                is_current=1,
                content_file_path=content_file_path,
                word_count=word_count,
                summary=summary[:500] if summary else "",
            )
            db.add(version)
            db.commit()

        return version_id

    @staticmethod
    def apply_chapter_edit(
        project_id: int,
        chapter_id: int,
        expected_content: str,
        revised_content: str,
        summary: str = "",
    ) -> dict | None:
        """原子应用对话改稿并保留正文版本；原稿不匹配时拒绝覆盖。"""
        version_id = str(uuid.uuid4())
        with get_business_db() as db:
            chapter = (
                db.query(Chapter)
                .filter(Chapter.id == chapter_id, Chapter.project_id == project_id)
                .with_for_update()
                .first()
            )
            if not chapter or (chapter.content or "") != expected_content:
                return None

            # 步骤 1：在数据库更新本身重复校验原稿，避免两个编辑请求同时通过前置读取。
            changed_rows = db.query(Chapter).filter(
                Chapter.id == chapter_id,
                Chapter.project_id == project_id,
                Chapter.content == expected_content,
            ).update(
                {"content": revised_content, "status": "draft"},
                synchronize_session=False,
            )
            if changed_rows != 1:
                db.rollback()
                return None

            latest_version = (
                db.query(GenerationVersion.version_number)
                .filter(GenerationVersion.chapter_id == chapter_id)
                .order_by(GenerationVersion.version_number.desc())
                .first()
            )
            version_number = (latest_version[0] if latest_version else 0) + 1
            content_file_path = _save_version_content(chapter_id, version_id, revised_content)

            # 步骤 2：在同一数据库事务中更新版本指针并保存版本快照。
            db.query(GenerationVersion).filter(
                GenerationVersion.chapter_id == chapter_id
            ).update({"is_current": 0})
            db.add(GenerationVersion(
                version_id=version_id,
                chapter_id=chapter_id,
                run_id=None,
                version_number=version_number,
                is_current=1,
                content_file_path=content_file_path,
                word_count=len(revised_content),
                summary=summary[:500] if summary else "对话改稿",
            ))
            db.commit()

        return {
            "chapter_id": chapter_id,
            "version_id": version_id,
            "version_number": version_number,
            "word_count": len(revised_content),
        }

    @staticmethod
    def get_version_content(version_id: str) -> str:
        """获取版本的完整内容。"""
        with get_business_db() as db:
            version = (
                db.query(GenerationVersion)
                .filter(GenerationVersion.version_id == version_id)
                .first()
            )
            if not version or not version.content_file_path:
                return ""
            return _read_version_content(version.content_file_path)

    @staticmethod
    def get_versions(chapter_id: int, limit: int = 10) -> list[dict]:
        """获取章节的生成版本列表。"""
        with get_business_db() as db:
            rows = (
                db.query(GenerationVersion)
                .filter(GenerationVersion.chapter_id == chapter_id)
                .order_by(GenerationVersion.version_number.desc())
                .limit(limit)
                .all()
            )
            return rows_to_dicts(rows)

    @staticmethod
    def set_current_version(chapter_id: int, version_id: str) -> dict:
        """设置当前版本，并回滚章节内容到该版本。

        Returns:
            {"success": bool, "content": str, "version": dict | None}
        """
        with get_business_db() as db:
            version = (
                db.query(GenerationVersion)
                .filter(
                    GenerationVersion.chapter_id == chapter_id,
                    GenerationVersion.version_id == version_id,
                )
                .first()
            )
            if not version:
                return {"success": False, "content": "", "version": None}

            # 取消其他版本的当前标记
            db.query(GenerationVersion).filter(
                GenerationVersion.chapter_id == chapter_id
            ).update({"is_current": 0})

            version.is_current = 1

            # 读取版本内容
            content = _read_version_content(version.content_file_path) if version.content_file_path else ""

            # 回滚章节内容
            chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
            if chapter and content:
                chapter.content = content

            db.commit()

            return {
                "success": True,
                "content": content,
                "version": row_to_dict(version),
            }

    # ----------------------------------------------------------
    # 断点续传：恢复工作流状态
    # ----------------------------------------------------------

    @staticmethod
    def restore_workflow_state(run_id: str) -> dict | None:
        """从数据库恢复工作流状态。

        Returns:
            状态字典，包含:
            - run_info: 工作流运行信息
            - step_statuses: 步骤状态字典
            - step_results: 步骤结果字典
            - session_context: 会话上下文
        """
        run = WorkflowPersistence.get_run(run_id)
        if not run:
            return None

        step_records = WorkflowPersistence.get_step_records(run_id)

        step_statuses: dict[str, str] = {}
        step_results: dict[str, dict[str, Any]] = {}
        session_context: dict[str, Any] = {}

        # 步骤 1：同一步骤可能因重试或重跑有多条记录，只恢复最后一次尝试。
        latest_records = {record["step_id"]: record for record in step_records}
        template_snapshot = run.get("template_snapshot") or {}
        step_configs = {
            step.get("step_id"): step
            for step in template_snapshot.get("steps", [])
            if step.get("step_id")
        }

        # 步骤 2：按模板的 output_mapping 还原工作流共享状态，而不是把 Agent 原始字段名误当会话键。
        for step_id, record in latest_records.items():
            step_statuses[step_id] = record["status"]

            if record["status"] == "completed" and record.get("output_snapshot"):
                step_results[step_id] = record["output_snapshot"]
                output = record["output_snapshot"]
                if isinstance(output, dict):
                    mapping = step_configs.get(step_id, {}).get("output_mapping", {})
                    for result_key, session_key in mapping.items():
                        if result_key in output:
                            session_context[session_key] = output[result_key]

        # 步骤 3：从最近步骤的输入快照恢复作者选中的上下文资料，供断点续跑保持一致。
        for record in reversed(step_records):
            input_snapshot = record.get("input_snapshot")
            if isinstance(input_snapshot, dict) and "context_selection" in input_snapshot:
                session_context["context_selection"] = input_snapshot["context_selection"]
                break

        return {
            "run_info": run,
            "step_statuses": step_statuses,
            "step_results": step_results,
            "session_context": session_context,
        }
