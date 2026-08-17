"""v011 — 为已有的内置角色填充自定义属性和人物关系。

背景：v010 迁移已创建内置角色，但早期版本不含 custom_attributes / character_relations
数据，导致已执行过 v010 的数据库中内置角色属性为空。

功能：
- 扫描所有项目，为每个 is_builtin=1 且 custom_attributes 为空的内置角色
  根据名字回填属性数据
- 回填人物关系数据

幂等性：只更新 custom_attributes = '[]' 或为空的角色，已有数据的不覆盖。
"""
from __future__ import annotations

import json
from sqlalchemy import text
from sqlalchemy.orm import Session

# 复用 v010 的数据定义
from app.db.migrations.business.v010_character_is_builtin import (
    BUILTIN_COMMON_CHARACTERS,
    TEST_CHARACTERS,
    _build_builtin_relations,
)


def upgrade(db: Session) -> None:
    # 获取所有项目 ID
    result = db.execute(text("SELECT id FROM projects"))
    project_ids = [row[0] for row in result.fetchall()]

    if not project_ids:
        return

    all_char_defs = BUILTIN_COMMON_CHARACTERS + TEST_CHARACTERS
    # 按名字索引定义
    defs_by_name = {c["name"]: c for c in all_char_defs}

    for project_id in project_ids:
        # 找出该项目下所有内置角色
        rows = db.execute(
            text("""
                SELECT id, name, custom_attributes
                FROM characters
                WHERE project_id = :pid AND is_builtin = 1
            """),
            {"pid": project_id}
        ).fetchall()

        for row in rows:
            char_id, char_name, custom_attrs_str = row
            # 检查属性是否为空（空字符串、'[]'、None 都视为空）
            attrs_empty = (
                custom_attrs_str is None
                or custom_attrs_str == ""
                or custom_attrs_str == "[]"
            )
            if not attrs_empty:
                continue  # 已有数据，跳过

            char_def = defs_by_name.get(char_name)
            if not char_def:
                continue

            # 回填 custom_attributes
            attrs = char_def.get("custom_attributes", [])
            if attrs:
                db.execute(
                    text("""
                        UPDATE characters
                        SET custom_attributes = :attrs
                        WHERE id = :id
                    """),
                    {
                        "id": char_id,
                        "attrs": json.dumps(attrs, ensure_ascii=False),
                    }
                )

        # 回填人物关系（复用 v010 的构建函数）
        # 先检查是否已有关系数据，避免覆盖
        rel_rows = db.execute(
            text("""
                SELECT id, character_relations
                FROM characters
                WHERE project_id = :pid AND is_builtin = 1
            """),
            {"pid": project_id}
        ).fetchall()

        all_empty = all(
            r[1] is None or r[1] == "" or r[1] == "[]"
            for r in rel_rows
        )

        if all_empty:
            _build_builtin_relations(db, project_id)
