"""v013 — 为 NPC 内置角色补充人物关系（反向关系回显）。

背景：v010/v011 只为 TEST_CHARACTERS（主角+配角）建立了正向关系，
NPC 角色虽然被别人关联，但自己的 character_relations 为空，
导致人物卡片上看不到关系数据。

功能：
- 为老者、店小二、守卫、医者、信使等被关联的 NPC 补充反向关系
- 孩童、路人甲没有被关联，保持为空（正常）

幂等性：只更新 character_relations 为空的角色，已有数据的不覆盖。
"""
from __future__ import annotations

import json
from sqlalchemy import text
from sqlalchemy.orm import Session


# NPC 的反向关系定义（从主角/配角的关系中推导）
NPC_RELATIONS = {
    "老者": [
        {"target_name": "萧寒", "relation_type": "忘年交", "depth": 7, "effective_from": 4, "expires_at": None},
        {"target_name": "苏婉清", "relation_type": "长辈", "depth": 7, "effective_from": 1, "expires_at": None},
    ],
    "店小二": [
        {"target_name": "萧寒", "relation_type": "熟识", "depth": 4, "effective_from": 1, "expires_at": None},
    ],
    "守卫": [
        {"target_name": "苏婉清", "relation_type": "熟识", "depth": 3, "effective_from": 1, "expires_at": None},
    ],
    "医者": [
        {"target_name": "厉风行", "relation_type": "旧识", "depth": 7, "effective_from": None, "expires_at": None},
    ],
    "信使": [
        {"target_name": "厉风行", "relation_type": "熟识", "depth": 5, "effective_from": None, "expires_at": None},
    ],
}


def upgrade(db: Session) -> None:
    # 获取所有项目 ID
    result = db.execute(text("SELECT id FROM projects"))
    project_ids = [row[0] for row in result.fetchall()]

    if not project_ids:
        return

    for project_id in project_ids:
        # 获取该项目下所有内置角色的 id/name 映射
        rows = db.execute(
            text("""
                SELECT id, name, character_relations
                FROM characters
                WHERE project_id = :pid AND is_builtin = 1
            """),
            {"pid": project_id}
        ).fetchall()
        name_to_id = {row[1]: row[0] for row in rows}
        id_to_rels = {row[0]: row[2] for row in rows}

        for npc_name, relations in NPC_RELATIONS.items():
            npc_id = name_to_id.get(npc_name)
            if not npc_id:
                continue

            # 检查是否已有关系数据
            current_rels = id_to_rels.get(npc_id, "[]")
            if current_rels and current_rels != "[]":
                continue  # 已有数据，跳过

            # 将 target_name 转换为 target_id
            relations_with_id = []
            for rel in relations:
                target_id = name_to_id.get(rel["target_name"])
                if target_id:
                    relations_with_id.append({
                        "target_id": target_id,
                        "relation_type": rel["relation_type"],
                        "depth": rel["depth"],
                        "effective_from": rel.get("effective_from"),
                        "expires_at": rel.get("expires_at"),
                    })

            if relations_with_id:
                db.execute(
                    text("""
                        UPDATE characters
                        SET character_relations = :rels
                        WHERE id = :id
                    """),
                    {
                        "id": npc_id,
                        "rels": json.dumps(relations_with_id, ensure_ascii=False),
                    }
                )
