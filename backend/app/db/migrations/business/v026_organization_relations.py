"""v026：组织同盟与敌对关系结构化，并迁移可识别的旧名称关系。"""
from __future__ import annotations

import json
import re

from sqlalchemy import text


def upgrade(db) -> None:
    """创建组织关系表，并把旧文本中能准确匹配的组织名称转换为关系记录。

    步骤 1：按当前数据库方言创建带外键和查询索引的新表。
    步骤 2：读取旧版 allies/enemies 文本，并只转换项目内唯一匹配的组织。
    步骤 3：跳过互相矛盾的旧关系；仅从旧字段移除已成功迁移的标签。
    """
    dialect = db.bind.dialect.name
    if dialect == "sqlite":
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS organization_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                organization_a_id INTEGER NOT NULL,
                organization_b_id INTEGER NOT NULL,
                relation_type VARCHAR(32) NOT NULL DEFAULT 'alliance',
                description TEXT DEFAULT '',
                effective_from_chapter INTEGER,
                expires_at_chapter INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(organization_a_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY(organization_b_id) REFERENCES organizations(id) ON DELETE CASCADE
            )
        """))
    else:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS organization_relations (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                project_id INTEGER NOT NULL,
                organization_a_id INTEGER NOT NULL,
                organization_b_id INTEGER NOT NULL,
                relation_type VARCHAR(32) NOT NULL DEFAULT 'alliance',
                description TEXT DEFAULT '',
                effective_from_chapter INTEGER,
                expires_at_chapter INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(organization_a_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY(organization_b_id) REFERENCES organizations(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

    # MySQL 不支持 CREATE INDEX IF NOT EXISTS，因此先读取索引名再补建。
    from sqlalchemy import inspect
    existing_indexes = {item["name"] for item in inspect(db.bind).get_indexes("organization_relations")}
    for index_name, organization_column in (
        ("idx_org_relations_project_a", "organization_a_id"),
        ("idx_org_relations_project_b", "organization_b_id"),
    ):
        if index_name not in existing_indexes:
            db.execute(text(
                f"CREATE INDEX {index_name} ON organization_relations(project_id, {organization_column})"
            ))

    rows = db.execute(text(
        "SELECT id, project_id, name, allies, enemies FROM organizations"
    )).fetchall()
    organizations_by_project: dict[int, list[dict]] = {}
    for row in rows:
        item = dict(row._mapping)
        organizations_by_project.setdefault(item["project_id"], []).append(item)

    candidates: dict[tuple[int, int, int], set[str]] = {}
    lookup_by_project: dict[int, tuple[dict[int, dict], dict[str, list[int]]]] = {}
    for project_id, organizations in organizations_by_project.items():
        by_id = {int(item["id"]): item for item in organizations}
        by_name: dict[str, list[int]] = {}
        for item in organizations:
            by_name.setdefault(str(item["name"] or "").strip().casefold(), []).append(int(item["id"]))
        lookup_by_project[project_id] = (by_id, by_name)

        for item in organizations:
            for legacy_field, relation_type in (("allies", "alliance"), ("enemies", "hostility")):
                for target_id in _resolve_legacy_targets(item.get(legacy_field), by_id, by_name):
                    if target_id == int(item["id"]):
                        continue
                    first_id, second_id = sorted((int(item["id"]), target_id))
                    candidates.setdefault((project_id, first_id, second_id), set()).add(relation_type)

    migrated_relation_types: dict[tuple[int, int, int], str] = {}
    for (project_id, first_id, second_id), relation_types in candidates.items():
        # 旧字段可能互相矛盾；保留原文，避免擅自判断同盟或敌对的真实状态。
        if len(relation_types) != 1:
            continue
        exists = db.execute(text("""
            SELECT id FROM organization_relations
            WHERE project_id = :project_id
              AND organization_a_id = :first_id
              AND organization_b_id = :second_id
              AND relation_type = :relation_type
              AND effective_from_chapter IS NULL
            LIMIT 1
        """), {
            "project_id": project_id,
            "first_id": first_id,
            "second_id": second_id,
            "relation_type": next(iter(relation_types)),
        }).first()
        if exists:
            if len(relation_types) == 1:
                migrated_relation_types[(project_id, first_id, second_id)] = next(iter(relation_types))
            continue
        db.execute(text("""
            INSERT INTO organization_relations
                (project_id, organization_a_id, organization_b_id, relation_type, description)
            VALUES (:project_id, :first_id, :second_id, :relation_type, '')
        """), {
            "project_id": project_id,
            "first_id": first_id,
            "second_id": second_id,
            "relation_type": next(iter(relation_types)),
        })
        migrated_relation_types[(project_id, first_id, second_id)] = next(iter(relation_types))

    # 步骤 4：清理已经迁移的旧标签，避免新关系被删除后旧文本又显示成未匹配数据。
    for project_id, organizations in organizations_by_project.items():
        by_id, by_name = lookup_by_project[project_id]
        for item in organizations:
            changes = {}
            for field_name, relation_type in (("allies", "alliance"), ("enemies", "hostility")):
                remaining = []
                for token in _legacy_tokens(item.get(field_name)):
                    target_ids = _resolve_legacy_targets(token, by_id, by_name)
                    if len(target_ids) == 1:
                        target_id = next(iter(target_ids))
                        first_id, second_id = sorted((int(item["id"]), target_id))
                        if migrated_relation_types.get((project_id, first_id, second_id)) == relation_type:
                            continue
                    remaining.append(token)
                normalized = "、".join(remaining)
                if normalized != (item.get(field_name) or ""):
                    changes[field_name] = normalized
            if changes:
                db.execute(text("""
                    UPDATE organizations
                    SET allies = :allies, enemies = :enemies
                    WHERE id = :organization_id AND project_id = :project_id
                """), {
                    "allies": changes.get("allies", item.get("allies") or ""),
                    "enemies": changes.get("enemies", item.get("enemies") or ""),
                    "organization_id": item["id"],
                    "project_id": project_id,
                })


def _resolve_legacy_targets(value: str | None, by_id: dict[int, dict], by_name: dict[str, list[int]]) -> set[int]:
    """将旧文本标签解析为项目内唯一组织 ID；不猜测模糊匹配。"""
    if not value:
        return set()
    resolved: set[int] = set()
    for token in _legacy_tokens(value):
        if token.isdigit() and int(token) in by_id:
            resolved.add(int(token))
            continue
        matches = by_name.get(token.casefold(), [])
        if len(matches) == 1:
            resolved.add(matches[0])
    return resolved


def _legacy_tokens(value: str | None) -> list[str]:
    """拆分旧标签字段，兼容 JSON 数组与中英文标点分隔格式。"""
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        parsed = None
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [token.strip() for token in re.split(r"[、,，;；\n]+", value) if token.strip()]
