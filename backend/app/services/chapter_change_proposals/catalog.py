"""构建当前项目的实体目录，供章节分析引用名称和 ID。"""

from typing import Any

from sqlalchemy.orm import Session

from app.models.business import (
    Character,
    Foreshadowing,
    Organization,
    OrganizationRelation,
    WorldSetting,
)
from .common import _json_array

def load_entity_catalog(db: Session, project_id: int) -> dict[str, list[dict[str, Any]]]:
    """读取分析用实体索引。

    步骤 1：按项目读取人物、组织、伏笔和设定名称。
    步骤 2：附带人物及组织的结构化关系，用于精确定位关系变化。
    步骤 3：只返回匹配和冲突校验所需字段，控制工作流上下文体积。
    """
    characters = db.query(Character.id, Character.name, Character.character_relations).filter(
        Character.project_id == project_id,
    ).all()
    organizations = db.query(Organization.id, Organization.name).filter(
        Organization.project_id == project_id,
    ).all()
    organization_relations = db.query(OrganizationRelation).filter(
        OrganizationRelation.project_id == project_id,
    ).all()
    foreshadowings = db.query(Foreshadowing.id, Foreshadowing.keyword).filter(
        Foreshadowing.project_id == project_id,
    ).all()
    world_settings = db.query(WorldSetting.id, WorldSetting.title).filter(
        WorldSetting.project_id == project_id,
    ).all()
    return {
        "characters": [
            {
                "id": row.id,
                "name": row.name,
                "character_relations": _json_array(row.character_relations),
            }
            for row in characters
        ],
        "organizations": [{"id": row.id, "name": row.name} for row in organizations],
        "organization_relations": [
            {
                "id": row.id,
                "organization_a_id": row.organization_a_id,
                "organization_b_id": row.organization_b_id,
                "relation_type": row.relation_type,
                "description": row.description or "",
                "effective_from_chapter": row.effective_from_chapter,
                "expires_at_chapter": row.expires_at_chapter,
            }
            for row in organization_relations
        ],
        "foreshadowings": [{"id": row.id, "keyword": row.keyword} for row in foreshadowings],
        "world_settings": [{"id": row.id, "title": row.title} for row in world_settings],
    }
