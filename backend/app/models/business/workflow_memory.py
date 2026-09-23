"""工作流执行数据模型。"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON, func

from app.db.session import Base


class WorkflowRun(Base):
    """工作流执行记录。"""

    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), unique=True, index=True, nullable=False)

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    outline_id = Column(Integer, nullable=True)

    template_name = Column(String(64), nullable=False, default="")
    template_snapshot = Column(Text, default="")  # JSON 格式的模板快照
    variant_selections = Column(Text, default="")  # JSON 格式的变体选择

    status = Column(String(16), default="pending", index=True)
    current_step = Column(String(64), nullable=True)
    progress = Column(Integer, default=0)  # 0-100

    word_count = Column(Integer, default=0)
    output_preview = Column(Text, default="")
    output_file_path = Column(String(512), nullable=True)
    has_changes = Column(Integer, default=0)  # 0/1

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, default="")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class WorkflowStepRecord(Base):
    """工作流步骤执行记录。"""

    __tablename__ = "workflow_step_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), index=True, nullable=False)
    step_id = Column(String(64), nullable=False)
    step_name = Column(String(128), default="")
    agent_type = Column(String(32), default="")
    variant_name = Column(String(32), default="default")

    status = Column(String(16), default="pending")
    input_snapshot = Column(Text, default="")  # JSON
    output_snapshot = Column(Text, default="")  # JSON
    output_file_path = Column(String(512), nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    token_usage = Column(Text, default="")  # JSON
    llm_calls = Column(Integer, default=0)

    retry_count = Column(Integer, default=0)
    parent_retry_of = Column(String(64), nullable=True)

    error_message = Column(Text, default="")
    error_traceback = Column(Text, default="")

    created_at = Column(DateTime, server_default=func.now())


class GenerationVersion(Base):
    """生成版本。"""

    __tablename__ = "generation_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(String(64), unique=True, nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), index=True, nullable=False)
    run_id = Column(String(64), index=True, nullable=True)

    version_number = Column(Integer, default=1)
    is_current = Column(Integer, default=0)  # 0/1

    content_file_path = Column(String(512), nullable=True)
    word_count = Column(Integer, default=0)
    summary = Column(Text, default="")

    rating = Column(Integer, nullable=True)
    feedback = Column(Text, default="")
    is_favorite = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())


class UserPreference(Base):
    """用户偏好（L4 长期记忆的一部分）。"""

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)

    default_template = Column(String(64), default="smart_mode")
    default_writer_variant = Column(String(32), default="default")
    default_temperature = Column(Integer, default=80)  # 0-200，对应 0.0-2.0
    default_target_word_count = Column(Integer, default=3000)
    auto_sync_level = Column(String(16), default="low_risk_only")

    ui_theme = Column(String(16), default="dark")
    editor_font_size = Column(Integer, default=16)
    quickbar_templates = Column(Text, default="")  # JSON array
    quickbar_variants = Column(Text, default="")  # JSON array

    total_generations = Column(Integer, default=0)
    total_words_generated = Column(Integer, default=0)
    avg_retry_rate = Column(Integer, default=0)  # 百分比
    preferred_hours = Column(Text, default="")  # JSON array

    custom_data = Column(Text, default="{}")  # JSON

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MemoryItem(Base):
    """通用记忆条目。"""

    __tablename__ = "memory_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    memory_id = Column(String(64), unique=True, nullable=False)

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, default=1, index=True)

    memory_type = Column(String(32), index=True, default="")  # character/organization/foreshadow/...
    title = Column(String(255), default="")
    content = Column(Text, default="")
    content_summary = Column(Text, default="")

    metadata_json = Column(Text, default="{}")  # JSON

    importance = Column(Integer, default=50)  # 0-100
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime, nullable=True)

    vector_id = Column(String(64), nullable=True)
    has_vector = Column(Integer, default=0)  # 0/1

    source_type = Column(String(32), default="manual")  # manual/auto_generated/extracted
    source_ref = Column(String(255), nullable=True)

    version = Column(Integer, default=1)
    parent_memory_id = Column(String(64), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
