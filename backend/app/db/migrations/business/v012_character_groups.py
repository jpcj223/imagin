"""v012 — 新增角色分组表，角色表增加 group_id / sort_index 字段。

功能：
- character_groups 表：用户可自定义角色分组
- characters 表新增 group_id（所属分组）和 sort_index（排序权重）
- 为每个项目初始化默认分组（按角色类型）

幂等性：表已存在则跳过创建；字段已存在则跳过 ALTER；默认分组已存在则跳过。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.migrations.common import ensure_columns


def upgrade(db: Session) -> None:
    dialect = db.bind.dialect.name

    # 1. 创建 character_groups 表
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS character_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            group_type VARCHAR(20) NOT NULL DEFAULT 'custom',
            role_type VARCHAR(50) DEFAULT NULL,
            sort_index INTEGER NOT NULL DEFAULT 0,
            color VARCHAR(20) DEFAULT NULL,
            is_builtin BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))

    # 2. 为角色表新增 group_id 和 sort_index 字段
    ensure_columns(db, dialect, "characters", {
        "group_id": "INTEGER DEFAULT NULL",
        "sort_index": "INTEGER DEFAULT 0",
    })

    # 3. 获取所有项目 ID
    result = db.execute(text("SELECT id FROM projects"))
    project_ids = [row[0] for row in result.fetchall()]

    if not project_ids:
        return

    # 4. 为每个项目初始化默认分组
    for project_id in project_ids:
        _init_default_groups(db, project_id)


def _init_default_groups(db: Session, project_id: int) -> None:
    """为项目初始化默认分组（按角色类型）。"""
    # 角色类型 -> 分组名映射
    role_type_groups = [
        ("protagonist", "主角", 1),
        ("supporting", "配角", 2),
        ("antagonist", "反派", 3),
        ("npc", "NPC", 4),
        ("extra", "路人", 5),
        ("other", "其他", 99),
    ]

    for role_type, name, sort_idx in role_type_groups:
        # 检查是否已存在
        existing = db.execute(
            text("""
                SELECT id FROM character_groups
                WHERE project_id = :pid AND role_type = :rt AND is_builtin = 1
                LIMIT 1
            """),
            {"pid": project_id, "rt": role_type}
        ).fetchone()
        if existing:
            continue

        db.execute(
            text("""
                INSERT INTO character_groups
                    (project_id, name, group_type, role_type, sort_index, is_builtin)
                VALUES
                    (:pid, :name, 'default', :rt, :si, 1)
            """),
            {
                "pid": project_id,
                "name": name,
                "rt": role_type,
                "si": sort_idx,
            }
        )

