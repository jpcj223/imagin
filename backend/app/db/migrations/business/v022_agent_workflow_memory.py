"""v022: Agent 工作流与记忆系统表

新增：
- workflow_runs: 工作流执行记录
- workflow_step_records: 步骤执行记录
- generation_versions: 生成版本管理
- user_preferences: 用户偏好（L4 长期记忆）
- memory_items: 通用记忆条目
"""
from __future__ import annotations

from sqlalchemy import text


def upgrade(db) -> None:
    """执行迁移。"""

    # 工作流执行记录表
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS workflow_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL UNIQUE,
            project_id INTEGER NOT NULL,
            chapter_id INTEGER,
            outline_id INTEGER,
            template_name TEXT NOT NULL DEFAULT '',
            template_snapshot TEXT DEFAULT '',
            variant_selections TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            current_step TEXT,
            progress INTEGER DEFAULT 0,
            word_count INTEGER DEFAULT 0,
            output_preview TEXT DEFAULT '',
            output_file_path TEXT,
            has_changes INTEGER DEFAULT 0,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            failed_at TIMESTAMP,
            error_message TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE SET NULL
        )
    """))

    db.execute(text("CREATE INDEX IF NOT EXISTS idx_workflow_runs_run_id ON workflow_runs(run_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_workflow_runs_project_id ON workflow_runs(project_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status)"))

    # 步骤执行记录表
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS workflow_step_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            step_id TEXT NOT NULL,
            step_name TEXT DEFAULT '',
            agent_type TEXT DEFAULT '',
            variant_name TEXT DEFAULT 'default',
            status TEXT DEFAULT 'pending',
            input_snapshot TEXT DEFAULT '',
            output_snapshot TEXT DEFAULT '',
            output_file_path TEXT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            duration_ms INTEGER,
            token_usage TEXT DEFAULT '',
            llm_calls INTEGER DEFAULT 0,
            retry_count INTEGER DEFAULT 0,
            parent_retry_of TEXT,
            error_message TEXT DEFAULT '',
            error_traceback TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    db.execute(text("CREATE INDEX IF NOT EXISTS idx_step_records_run_id ON workflow_step_records(run_id)"))

    # 生成版本表
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS generation_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_id TEXT NOT NULL UNIQUE,
            chapter_id INTEGER NOT NULL,
            run_id TEXT,
            version_number INTEGER DEFAULT 1,
            is_current INTEGER DEFAULT 0,
            content_file_path TEXT,
            word_count INTEGER DEFAULT 0,
            summary TEXT DEFAULT '',
            rating INTEGER,
            feedback TEXT DEFAULT '',
            is_favorite INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
        )
    """))

    db.execute(text("CREATE INDEX IF NOT EXISTS idx_gv_chapter_id ON generation_versions(chapter_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_gv_run_id ON generation_versions(run_id)"))

    # 用户偏好表
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            project_id INTEGER,
            default_template TEXT DEFAULT 'smart_mode',
            default_writer_variant TEXT DEFAULT 'default',
            default_temperature INTEGER DEFAULT 80,
            default_target_word_count INTEGER DEFAULT 3000,
            auto_sync_level TEXT DEFAULT 'low_risk_only',
            ui_theme TEXT DEFAULT 'dark',
            editor_font_size INTEGER DEFAULT 16,
            quickbar_templates TEXT DEFAULT '',
            quickbar_variants TEXT DEFAULT '',
            total_generations INTEGER DEFAULT 0,
            total_words_generated INTEGER DEFAULT 0,
            avg_retry_rate INTEGER DEFAULT 0,
            preferred_hours TEXT DEFAULT '',
            custom_data TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """))

    db.execute(text("CREATE INDEX IF NOT EXISTS idx_up_user_id ON user_preferences(user_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_up_project_id ON user_preferences(project_id)"))

    # 通用记忆条目表
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS memory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id TEXT NOT NULL UNIQUE,
            project_id INTEGER,
            user_id INTEGER DEFAULT 1,
            memory_type TEXT DEFAULT '',
            title TEXT DEFAULT '',
            content TEXT DEFAULT '',
            content_summary TEXT DEFAULT '',
            metadata_json TEXT DEFAULT '{}',
            importance INTEGER DEFAULT 50,
            access_count INTEGER DEFAULT 0,
            last_accessed_at TIMESTAMP,
            vector_id TEXT,
            has_vector INTEGER DEFAULT 0,
            source_type TEXT DEFAULT 'manual',
            source_ref TEXT,
            version INTEGER DEFAULT 1,
            parent_memory_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """))

    db.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_project_id ON memory_items(project_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_user_id ON memory_items(user_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_items(memory_type)"))
