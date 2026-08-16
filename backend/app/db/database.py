from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR.parent / "data"
DB_PATH = DATA_DIR / "yixiang.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """读取表的现有字段，用于幂等迁移判断。"""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    """为旧库补齐新增字段。

    SQLite 的轻量迁移以 ADD COLUMN 为主；每次启动都检查字段是否存在，
    因此重复启动不会破坏旧数据，也不会重复添加字段。
    """
    existing = _existing_columns(conn, table)
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db() -> None:
    """初始化 SQLite 表结构。

    第一版先使用轻量 schema，让核心创作闭环尽快可运行；复杂向量记忆后续再扩展。
    """
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                theme TEXT DEFAULT '',
                novel_type TEXT DEFAULT '',
                target_words INTEGER DEFAULT 2500,
                synopsis TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS model_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                base_url TEXT NOT NULL,
                api_key TEXT NOT NULL,
                model TEXT NOT NULL,
                is_active INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS world_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                era TEXT DEFAULT '',
                geography TEXT DEFAULT '',
                atmosphere TEXT DEFAULT '',
                rules TEXT DEFAULT '',
                extra TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS outlines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                node_type TEXT DEFAULT 'chapter',
                status TEXT DEFAULT 'draft',
                volume_no INTEGER,
                chapter_no INTEGER,
                sort_index INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                outline_id INTEGER,
                chapter_no INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(outline_id) REFERENCES outlines(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS chapter_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id INTEGER NOT NULL,
                summary TEXT DEFAULT '',
                character_changes TEXT DEFAULT '',
                world_changes TEXT DEFAULT '',
                new_foreshadowings TEXT DEFAULT '',
                timeline_events TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                role_type TEXT DEFAULT 'supporting',
                mbti TEXT DEFAULT '',
                appearance TEXT DEFAULT '',
                personality TEXT DEFAULT '',
                background TEXT DEFAULT '',
                motivation TEXT DEFAULT '',
                arc TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                org_type TEXT DEFAULT '',
                location TEXT DEFAULT '',
                slogan TEXT DEFAULT '',
                description TEXT DEFAULT '',
                level INTEGER DEFAULT 1,
                power_level INTEGER DEFAULT 5,
                member_count INTEGER DEFAULT 0,
                status TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS foreshadowings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                importance TEXT DEFAULT 'medium',
                planted_chapter INTEGER,
                payoff_chapter INTEGER,
                effective_from INTEGER,
                expires_at INTEGER,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS generation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                task_type TEXT NOT NULL,
                request TEXT DEFAULT '',
                response TEXT DEFAULT '',
                status TEXT DEFAULT 'success',
                error TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """
        )

        # 资料工作台第二版新增的结构化字段。它们都给默认值，保证旧库可直接升级。
        _ensure_columns(
            conn,
            "world_settings",
            {
                "title": "TEXT DEFAULT ''",
                "category": "TEXT DEFAULT 'other'",
                "tags": "TEXT DEFAULT ''",
                "importance": "TEXT DEFAULT 'medium'",
                "related_chapters": "TEXT DEFAULT ''",
                "related_characters": "TEXT DEFAULT ''",
                "related_organizations": "TEXT DEFAULT ''",
                "related_foreshadowings": "TEXT DEFAULT ''",
                "conflict_notes": "TEXT DEFAULT ''",
            },
        )
        _ensure_columns(
            conn,
            "characters",
            {
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
            },
        )
        _ensure_columns(
            conn,
            "organizations",
            {
                "hierarchy": "TEXT DEFAULT ''",
                "resources": "TEXT DEFAULT ''",
                "goal": "TEXT DEFAULT ''",
                "core_members": "TEXT DEFAULT ''",
                "allies": "TEXT DEFAULT ''",
                "enemies": "TEXT DEFAULT ''",
                "impact": "TEXT DEFAULT ''",
                "risk_notes": "TEXT DEFAULT ''",
            },
        )
        _ensure_columns(
            conn,
            "foreshadowings",
            {
                "related_character_ids": "TEXT DEFAULT ''",
                "related_organization_ids": "TEXT DEFAULT ''",
                "related_outline_ids": "TEXT DEFAULT ''",
            },
        )

        # ------------------------------------------------------------------
        # 第三版迁移：蛙趣原型优化扩展
        # 全部走幂等字段补充 + 启动时旧数据兼容，不删除任何已有字段。
        # ------------------------------------------------------------------
        _ensure_columns(
            conn,
            "characters",
            {
                # MBTI 双类型：主类型 + 辅助类型，支持塑造更立体的角色性格。
                "mbti_primary": "TEXT DEFAULT ''",
                "mbti_secondary": "TEXT DEFAULT ''",
                # 动态属性系统：JSON 数组，用户可自定义添加任何属性，
                # 解决"人物扩展难"问题，适配玄幻/都市/科幻等不同题材。
                "custom_attributes": "TEXT DEFAULT '[]'",
                # 组织关系结构化：JSON 数组，替代旧的 organization_ids 纯文本。
                # 每条含 org_id / position / loyalty，旧数据启动时自动迁移。
                "org_relations": "TEXT DEFAULT '[]'",
                # 人物关系结构化：JSON 数组，替代旧的 related_character_ids 纯文本。
                # 每条含 target_id / relation_type / depth / effective_from / expires_at，
                # 支持关系随剧情演变（生效/失效章节）。
                "character_relations": "TEXT DEFAULT '[]'",
            },
        )
        _ensure_columns(
            conn,
            "organizations",
            {
                # 隐藏设定：仅作者可见的秘密/暗线，区分表里设定。
                "hidden_secrets": "TEXT DEFAULT ''",
                # 主效起始章节：组织主要活跃的起始章节号。
                "active_from_chapter": "INTEGER",
                # 覆灭/解散章节：组织在哪一章覆灭或解散，NULL 表示一直有效。
                "disbanded_chapter": "INTEGER",
            },
        )
        _ensure_columns(
            conn,
            "foreshadowings",
            {
                # 被替代伏笔 ID：支持伏笔之间的迭代替换关系（旧伏笔被新伏笔替代）。
                "replaced_by_id": "INTEGER",
            },
        )
        _ensure_columns(
            conn,
            "projects",
            {
                # 默认节奏等级：1-平淡 / 2-渐入 / 3-适中 / 4-紧凑 / 5-高潮。
                # 作为项目级默认值，单章生成时可覆盖。
                "pace_level": "INTEGER DEFAULT 3",
                # 叙事视角：第一人称/第三人称有限/第三人称全知/第二人称。
                # 影响 AI 生成时的叙述角度和代词使用。
                "view_point": "TEXT DEFAULT ''",
                # 文风基调：严肃/轻松/热血/治愈/暗黑/史诗/其他。
                # 作为全局写作风格参考，可被单章设置覆盖。
                "writing_style": "TEXT DEFAULT ''",
            },
        )
        _ensure_columns(
            conn,
            "model_configs",
            {
                # 采样温度：0-2，越高越随机，越低越确定。
                "temperature": "REAL DEFAULT 0.7",
                # 最大输出 token 数：限制单次回复长度，NULL 表示使用模型默认。
                "max_tokens": "INTEGER",
                # nucleus 采样：0-1，只考虑累计概率 top_p 的 token。
                "top_p": "REAL DEFAULT 0.9",
                # 频率惩罚：-2 到 2，正值抑制重复 token。
                "frequency_penalty": "REAL DEFAULT 0",
                # 存在惩罚：-2 到 2，正值鼓励引入新话题。
                "presence_penalty": "REAL DEFAULT 0",
                # 代理地址：可选，格式如 http://127.0.0.1:7890。
                # 为空时走系统默认或直连。
                "proxy_url": "TEXT DEFAULT ''",
            },
        )

        # ---- 旧数据兼容迁移（幂等，可重复执行） ----
        _migrate_character_old_relations(conn)

        row = conn.execute("SELECT id FROM projects LIMIT 1").fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO projects (name, theme, novel_type, synopsis)
                VALUES (?, ?, ?, ?)
                """,
                ("臆想创作示例项目", "未设置", "长篇网文", "从这里开始搭建你的第一本小说。"),
            )


def _migrate_character_old_relations(conn: sqlite3.Connection) -> None:
    """人物旧关系数据的幂等迁移。

    将旧版逗号分隔的 ID 字段迁移到结构化 JSON 数组字段：
    - mbti → mbti_primary
    - organization_ids → org_relations（每条默认职位"成员"、忠诚值5）
    - related_character_ids → character_relations（每条默认类型"其他"、深度3）

    幂等保证：只在"新字段为空且旧字段有值"时才迁移，
    因此重复启动、用户手动清空新字段后重启都不会出错。
    旧字段永久保留不删除，作为回退保险。
    """
    import json

    # 先确认字段都存在（极端情况下迁移顺序可能变化）。
    existing = _existing_columns(conn, "characters")
    required = {"mbti", "mbti_primary", "organization_ids", "org_relations",
                "related_character_ids", "character_relations"}
    if not required.issubset(existing):
        return

    rows = conn.execute(
        """
        SELECT id, mbti, organization_ids, related_character_ids,
               mbti_primary, org_relations, character_relations
        FROM characters
        """
    ).fetchall()

    for row in rows:
        updates: dict[str, str] = {}

        # 1. MBTI 旧值迁移到主类型
        if (row["mbti_primary"] == "" or row["mbti_primary"] is None) and row["mbti"]:
            updates["mbti_primary"] = row["mbti"]

        # 2. 组织关系：逗号分隔 ID → JSON 数组
        if (row["org_relations"] == "[]" or row["org_relations"] == "" or row["org_relations"] is None) and row["organization_ids"]:
            ids = [s.strip() for s in row["organization_ids"].split(",") if s.strip().isdigit()]
            if ids:
                relations = [
                    {"org_id": int(id_), "position": "成员", "loyalty": 5}
                    for id_ in ids
                ]
                updates["org_relations"] = json.dumps(relations, ensure_ascii=False)

        # 3. 人物关系：逗号分隔 ID → JSON 数组
        if (row["character_relations"] == "[]" or row["character_relations"] == "" or row["character_relations"] is None) and row["related_character_ids"]:
            ids = [s.strip() for s in row["related_character_ids"].split(",") if s.strip().isdigit()]
            if ids:
                relations = [
                    {"target_id": int(id_), "relation_type": "其他", "depth": 3,
                     "effective_from": None, "expires_at": None}
                    for id_ in ids
                ]
                updates["character_relations"] = json.dumps(relations, ensure_ascii=False)

        if updates:
            sets = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(
                f"UPDATE characters SET {sets} WHERE id = ?",
                (*updates.values(), row["id"]),
            )

