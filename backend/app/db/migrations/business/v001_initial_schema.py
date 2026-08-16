"""v001 — 业务库初始 schema。

创建所有业务表（项目、世界观、大纲、章节、角色、组织、伏笔、生成日志等），
并插入种子数据。

幂等性：全部使用 CREATE TABLE IF NOT EXISTS，并对旧库补齐缺失字段，
保证从任何历史版本升级都不会出错。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    dialect = db.bind.dialect.name  # 'sqlite' or 'mysql'

    # ------------------------------------------------------------------
    # 1. projects 项目表
    # ------------------------------------------------------------------
    if dialect == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT '',
                theme TEXT DEFAULT '',
                novel_type TEXT DEFAULT '',
                target_words INTEGER DEFAULT 2500,
                synopsis TEXT DEFAULT '',
                pace_level INTEGER DEFAULT 3,
                view_point TEXT DEFAULT '',
                writing_style TEXT DEFAULT '',
                user_id INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(255) NOT NULL DEFAULT '',
                theme VARCHAR(255) DEFAULT '',
                novel_type VARCHAR(64) DEFAULT '',
                target_words INTEGER DEFAULT 2500,
                synopsis TEXT DEFAULT '',
                pace_level INTEGER DEFAULT 3,
                view_point VARCHAR(64) DEFAULT '',
                writing_style VARCHAR(64) DEFAULT '',
                user_id INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    _ensure_columns(db, dialect, "projects", {
        "pace_level": "INTEGER DEFAULT 3",
        "view_point": "TEXT DEFAULT ''",
        "writing_style": "TEXT DEFAULT ''",
        "user_id": "INTEGER DEFAULT 1",
    })

    # ------------------------------------------------------------------
    # 2. world_settings 世界观设定表
    # ------------------------------------------------------------------
    if dialect == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS world_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                era TEXT DEFAULT '',
                geography TEXT DEFAULT '',
                atmosphere TEXT DEFAULT '',
                rules TEXT DEFAULT '',
                extra TEXT DEFAULT '',
                title TEXT DEFAULT '',
                category TEXT DEFAULT 'other',
                tags TEXT DEFAULT '',
                importance TEXT DEFAULT 'medium',
                related_chapters TEXT DEFAULT '',
                related_characters TEXT DEFAULT '',
                related_organizations TEXT DEFAULT '',
                related_foreshadowings TEXT DEFAULT '',
                conflict_notes TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS world_settings (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                project_id INTEGER NOT NULL,
                era TEXT DEFAULT '',
                geography TEXT DEFAULT '',
                atmosphere TEXT DEFAULT '',
                rules TEXT DEFAULT '',
                extra TEXT DEFAULT '',
                title VARCHAR(255) DEFAULT '',
                category VARCHAR(32) DEFAULT 'other',
                tags TEXT DEFAULT '',
                importance VARCHAR(16) DEFAULT 'medium',
                related_chapters TEXT DEFAULT '',
                related_characters TEXT DEFAULT '',
                related_organizations TEXT DEFAULT '',
                related_foreshadowings TEXT DEFAULT '',
                conflict_notes TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    _ensure_columns(db, dialect, "world_settings", {
        "title": "TEXT DEFAULT ''",
        "category": "TEXT DEFAULT 'other'",
        "tags": "TEXT DEFAULT ''",
        "importance": "TEXT DEFAULT 'medium'",
        "related_chapters": "TEXT DEFAULT ''",
        "related_characters": "TEXT DEFAULT ''",
        "related_organizations": "TEXT DEFAULT ''",
        "related_foreshadowings": "TEXT DEFAULT ''",
        "conflict_notes": "TEXT DEFAULT ''",
    })

    # ------------------------------------------------------------------
    # 3. outlines 大纲表
    # ------------------------------------------------------------------
    if dialect == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS outlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                node_type TEXT DEFAULT 'chapter',
                status TEXT DEFAULT 'draft',
                volume_no INTEGER,
                chapter_no INTEGER,
                sort_index INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS outlines (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                project_id INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL DEFAULT '',
                node_type VARCHAR(16) DEFAULT 'chapter',
                status VARCHAR(16) DEFAULT 'draft',
                volume_no INTEGER,
                chapter_no INTEGER,
                sort_index INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    # ------------------------------------------------------------------
    # 4. chapters 章节表
    # ------------------------------------------------------------------
    if dialect == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                outline_id INTEGER,
                chapter_no INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                content TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(outline_id) REFERENCES outlines(id) ON DELETE SET NULL
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                project_id INTEGER NOT NULL,
                outline_id INTEGER,
                chapter_no INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL DEFAULT '',
                content TEXT DEFAULT '',
                status VARCHAR(16) DEFAULT 'draft',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(outline_id) REFERENCES outlines(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    # ------------------------------------------------------------------
    # 5. chapter_summaries 章节摘要表
    # ------------------------------------------------------------------
    if dialect == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS chapter_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id INTEGER NOT NULL,
                summary TEXT DEFAULT '',
                character_changes TEXT DEFAULT '',
                world_changes TEXT DEFAULT '',
                new_foreshadowings TEXT DEFAULT '',
                timeline_events TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS chapter_summaries (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                chapter_id INTEGER NOT NULL,
                summary TEXT DEFAULT '',
                character_changes TEXT DEFAULT '',
                world_changes TEXT DEFAULT '',
                new_foreshadowings TEXT DEFAULT '',
                timeline_events TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    # ------------------------------------------------------------------
    # 6. characters 角色表
    # ------------------------------------------------------------------
    if dialect == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                role_type TEXT DEFAULT 'supporting',
                mbti TEXT DEFAULT '',
                appearance TEXT DEFAULT '',
                personality TEXT DEFAULT '',
                background TEXT DEFAULT '',
                motivation TEXT DEFAULT '',
                arc TEXT DEFAULT '',
                identity TEXT DEFAULT '',
                faction TEXT DEFAULT '',
                weakness TEXT DEFAULT '',
                secret TEXT DEFAULT '',
                dialogue_style TEXT DEFAULT '',
                relationships TEXT DEFAULT '',
                chapters TEXT DEFAULT '',
                organization_ids TEXT DEFAULT '',
                related_character_ids TEXT DEFAULT '',
                ai_notes TEXT DEFAULT '',
                mbti_primary TEXT DEFAULT '',
                mbti_secondary TEXT DEFAULT '',
                custom_attributes TEXT DEFAULT '[]',
                org_relations TEXT DEFAULT '[]',
                character_relations TEXT DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                project_id INTEGER NOT NULL,
                name VARCHAR(255) NOT NULL DEFAULT '',
                role_type VARCHAR(32) DEFAULT 'supporting',
                mbti VARCHAR(16) DEFAULT '',
                appearance TEXT DEFAULT '',
                personality TEXT DEFAULT '',
                background TEXT DEFAULT '',
                motivation TEXT DEFAULT '',
                arc TEXT DEFAULT '',
                identity TEXT DEFAULT '',
                faction TEXT DEFAULT '',
                weakness TEXT DEFAULT '',
                secret TEXT DEFAULT '',
                dialogue_style TEXT DEFAULT '',
                relationships TEXT DEFAULT '',
                chapters TEXT DEFAULT '',
                organization_ids TEXT DEFAULT '',
                related_character_ids TEXT DEFAULT '',
                ai_notes TEXT DEFAULT '',
                mbti_primary VARCHAR(16) DEFAULT '',
                mbti_secondary VARCHAR(16) DEFAULT '',
                custom_attributes TEXT DEFAULT '[]',
                org_relations TEXT DEFAULT '[]',
                character_relations TEXT DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    _ensure_columns(db, dialect, "characters", {
        "identity": "TEXT DEFAULT ''",
        "faction": "TEXT DEFAULT ''",
        "weakness": "TEXT DEFAULT ''",
        "secret": "TEXT DEFAULT ''",
        "dialogue_style": "TEXT DEFAULT ''",
        "relationships": "TEXT DEFAULT ''",
        "chapters": "TEXT DEFAULT ''",
        "organization_ids": "TEXT DEFAULT ''",
        "related_character_ids": "TEXT DEFAULT ''",
        "ai_notes": "TEXT DEFAULT ''",
        "mbti_primary": "TEXT DEFAULT ''",
        "mbti_secondary": "TEXT DEFAULT ''",
        "custom_attributes": "TEXT DEFAULT '[]'",
        "org_relations": "TEXT DEFAULT '[]'",
        "character_relations": "TEXT DEFAULT '[]'",
    })

    # ------------------------------------------------------------------
    # 7. organizations 组织表
    # ------------------------------------------------------------------
    if dialect == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                org_type TEXT DEFAULT '',
                location TEXT DEFAULT '',
                slogan TEXT DEFAULT '',
                description TEXT DEFAULT '',
                level INTEGER DEFAULT 1,
                power_level INTEGER DEFAULT 5,
                member_count INTEGER DEFAULT 0,
                status TEXT DEFAULT '',
                hierarchy TEXT DEFAULT '',
                resources TEXT DEFAULT '',
                goal TEXT DEFAULT '',
                core_members TEXT DEFAULT '',
                allies TEXT DEFAULT '',
                enemies TEXT DEFAULT '',
                impact TEXT DEFAULT '',
                risk_notes TEXT DEFAULT '',
                hidden_secrets TEXT DEFAULT '',
                active_from_chapter INTEGER,
                disbanded_chapter INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                project_id INTEGER NOT NULL,
                name VARCHAR(255) NOT NULL DEFAULT '',
                org_type VARCHAR(64) DEFAULT '',
                location TEXT DEFAULT '',
                slogan TEXT DEFAULT '',
                description TEXT DEFAULT '',
                level INTEGER DEFAULT 1,
                power_level INTEGER DEFAULT 5,
                member_count INTEGER DEFAULT 0,
                status VARCHAR(32) DEFAULT '',
                hierarchy TEXT DEFAULT '',
                resources TEXT DEFAULT '',
                goal TEXT DEFAULT '',
                core_members TEXT DEFAULT '',
                allies TEXT DEFAULT '',
                enemies TEXT DEFAULT '',
                impact TEXT DEFAULT '',
                risk_notes TEXT DEFAULT '',
                hidden_secrets TEXT DEFAULT '',
                active_from_chapter INTEGER,
                disbanded_chapter INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    _ensure_columns(db, dialect, "organizations", {
        "hierarchy": "TEXT DEFAULT ''",
        "resources": "TEXT DEFAULT ''",
        "goal": "TEXT DEFAULT ''",
        "core_members": "TEXT DEFAULT ''",
        "allies": "TEXT DEFAULT ''",
        "enemies": "TEXT DEFAULT ''",
        "impact": "TEXT DEFAULT ''",
        "risk_notes": "TEXT DEFAULT ''",
        "hidden_secrets": "TEXT DEFAULT ''",
        "active_from_chapter": "INTEGER",
        "disbanded_chapter": "INTEGER",
    })

    # ------------------------------------------------------------------
    # 8. foreshadowings 伏笔表
    # ------------------------------------------------------------------
    if dialect == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS foreshadowings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                keyword TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                status TEXT DEFAULT 'pending',
                importance TEXT DEFAULT 'medium',
                planted_chapter INTEGER,
                payoff_chapter INTEGER,
                effective_from INTEGER,
                expires_at INTEGER,
                notes TEXT DEFAULT '',
                related_character_ids TEXT DEFAULT '',
                related_organization_ids TEXT DEFAULT '',
                related_outline_ids TEXT DEFAULT '',
                replaced_by_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS foreshadowings (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                project_id INTEGER NOT NULL,
                keyword VARCHAR(255) NOT NULL DEFAULT '',
                description TEXT NOT NULL,
                status VARCHAR(16) DEFAULT 'pending',
                importance VARCHAR(16) DEFAULT 'medium',
                planted_chapter INTEGER,
                payoff_chapter INTEGER,
                effective_from INTEGER,
                expires_at INTEGER,
                notes TEXT DEFAULT '',
                related_character_ids TEXT DEFAULT '',
                related_organization_ids TEXT DEFAULT '',
                related_outline_ids TEXT DEFAULT '',
                replaced_by_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    _ensure_columns(db, dialect, "foreshadowings", {
        "related_character_ids": "TEXT DEFAULT ''",
        "related_organization_ids": "TEXT DEFAULT ''",
        "related_outline_ids": "TEXT DEFAULT ''",
        "replaced_by_id": "INTEGER",
    })

    # ------------------------------------------------------------------
    # 9. generation_logs 生成日志表
    # ------------------------------------------------------------------
    if dialect == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS generation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                task_type TEXT NOT NULL DEFAULT '',
                request TEXT DEFAULT '',
                response TEXT DEFAULT '',
                status TEXT DEFAULT 'success',
                error TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS generation_logs (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                project_id INTEGER NOT NULL,
                task_type VARCHAR(64) NOT NULL DEFAULT '',
                request TEXT DEFAULT '',
                response TEXT DEFAULT '',
                status VARCHAR(16) DEFAULT 'success',
                error TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    # ------------------------------------------------------------------
    # 种子数据：示例项目
    # ------------------------------------------------------------------
    result = db.execute(text("SELECT id FROM projects LIMIT 1")).fetchone()
    if result is None:
        db.execute(text("""
            INSERT INTO projects (name, theme, novel_type, synopsis, user_id)
            VALUES (:name, :theme, :novel_type, :synopsis, :user_id)
        """), {
            "name": "臆想创作示例项目",
            "theme": "未设置",
            "novel_type": "长篇网文",
            "synopsis": "从这里开始搭建你的第一本小说。",
            "user_id": 1,
        })


# ---------------------------------------------------------------------------
# 工具函数：幂等补齐字段
# ---------------------------------------------------------------------------
def _existing_columns(db: Session, dialect: str, table: str) -> set[str]:
    """读取表的现有字段名集合。"""
    if dialect == "sqlite":
        rows = db.execute(text(f"PRAGMA table_info({table})")).fetchall()
        # PRAGMA table_info 返回的列：cid, name, type, notnull, dflt_value, pk
        return {row[1] for row in rows}
    else:
        # MySQL / MariaDB
        rows = db.execute(text(f"DESCRIBE {table}")).fetchall()
        return {row[0] for row in rows}


def _ensure_columns(db: Session, dialect: str, table: str, columns: dict[str, str]) -> None:
    """为旧库补齐新增字段（幂等）。

    columns: {字段名: 类型定义（不含列名）}
    """
    existing = _existing_columns(db, dialect, table)
    for name, definition in columns.items():
        if name not in existing:
            db.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
