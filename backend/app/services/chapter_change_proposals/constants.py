"""提案领域可修改字段、实体模型和 JSON 字段定义。"""

from app.models.business import (
    Character,
    Foreshadowing,
    MemoryItem,
    Organization,
    OrganizationRelation,
    WorldSetting,
)

# 模型输出只能修改显式列出的业务字段，身份、归属和时间戳由服务管理。
EDITABLE_FIELDS: dict[str, set[str]] = {
    "character": {
        "name", "role_type", "mbti", "mbti_primary", "mbti_secondary", "appearance",
        "personality", "background", "motivation", "arc", "identity", "faction",
        "weakness", "secret", "dialogue_style", "ai_notes", "status",
    },
    "organization": {
        "parent_id", "name", "org_type", "location", "slogan", "description", "level",
        "power_level", "member_count", "status", "hierarchy", "resources", "goal",
        "core_members", "impact", "risk_notes", "hidden_secrets",
        "active_from_chapter", "disbanded_chapter", "hierarchy_system", "hierarchy_levels",
    },
    "organization_relation": {
        "source_org_id", "target_org_id", "relation_type", "description",
        "effective_from_chapter", "expires_at_chapter",
    },
    "foreshadowing": {
        "keyword", "description", "status", "importance", "planted_chapter", "payoff_chapter",
        "resolved_chapter", "effective_from", "expires_at", "notes", "related_character_ids",
        "related_organization_ids", "related_outline_ids", "replaced_by_id",
    },
    "world_setting": {
        "era", "geography", "atmosphere", "rules", "extra", "title", "category", "tags",
        "importance", "related_chapters", "related_characters", "related_organizations",
        "related_foreshadowings", "conflict_notes",
    },
    "memory": {"memory_type", "title", "content", "content_summary", "importance", "metadata_json"},
}

ENTITY_MODELS = {
    "character": Character,
    "organization": Organization,
    "organization_relation": OrganizationRelation,
    "foreshadowing": Foreshadowing,
    "world_setting": WorldSetting,
    "memory": MemoryItem,
}

JSON_FIELDS: dict[str, set[str]] = {
    "character": {"custom_attributes", "org_relations", "character_relations"},
    "relationship": {"character_relations"},
    "organization": {"hierarchy_levels"},
    "memory": {"metadata_json"},
}

RELATION_FIELDS = {"target_id", "relation_type", "depth", "effective_from", "expires_at"}

# 世界观分类与前端分类字典一致，同时保留历史分析结果使用过的值。
WORLD_SETTING_CATEGORIES = {
    "geography", "era", "power_system", "rules", "items", "weapons",
    "medicine", "creatures", "organizations", "other",
    "location", "power", "rule", "taboo", "term",
}
