"""核心库迁移 v007 — 属性描述字典。

添加属性值描述常用标签字典，用于人物卡片属性管理的快速填充。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """添加属性描述字典数据。"""
    dict_id = _get_or_create_dict(db, "attribute_desc", "属性描述", "属性值描述常用标签，可多选快速填充", 26)

    items = [
        # 等级/修为类
        ("绝顶", "peak", 1, "最高等级/巅峰"),
        ("宗师级", "grand_master", 2, "宗师级别"),
        ("大师级", "master", 3, "大师级别"),
        ("精英级", "elite", 4, "精英级别"),
        ("普通", "ordinary", 5, "普通水平"),
        ("入门", "beginner", 6, "初学/入门水平"),
        ("废柴", "trash", 7, "毫无天赋"),
        ("天才", "genius", 8, "天纵奇才"),
        ("妖孽", "monster", 9, "非人的天赋"),

        # 属性品质类
        ("神级", "god_tier", 20, "神级品质"),
        ("圣级", "saint_tier", 21, "圣级品质"),
        ("天级", "heaven_tier", 22, "天级品质"),
        ("地级", "earth_tier", 23, "地级品质"),
        ("玄级", "mystic_tier", 24, "玄级品质"),
        ("黄级", "yellow_tier", 25, "黄级品质"),
        ("凡品", "mortal_tier", 26, "凡俗品质"),
        ("稀有", "rare", 27, "稀有品质"),
        ("传说", "legendary", 28, "传说级"),
        ("史诗", "epic", 29, "史诗级"),

        # 状态/效果类
        ("封印中", "sealed", 40, "力量被封印"),
        ("觉醒中", "awakening", 41, "正在觉醒"),
        ("完全觉醒", "fully_awakened", 42, "完全觉醒状态"),
        ("暴走", "berserk", 43, "失控/暴走状态"),
        ("隐身", "invisible", 44, "隐身能力"),
        ("不死", "immortal", 45, "不死之身"),
        ("再生", "regeneration", 46, "再生能力"),
        ("瞬移", "teleport", 47, "瞬移能力"),
        ("预言", "prophecy", 48, "预知能力"),

        # 身份/称号类
        ("天下第一", "number_one", 60, "天下第一"),
        ("万人敌", "ten_thousand_enemy", 61, "一人可敌万人"),
        ("护国神将", "national_god_general", 62, "国家级武力"),
        ("魔道巨擘", "demon_tyrant", 63, "魔道巨头"),
        ("正道领袖", "righteous_leader", 64, "正道领袖"),
        ("隐世高人", "hermit_expert", 65, "隐居的高手"),
        ("后起之秀", "rising_star", 66, "年轻一代的佼佼者"),
        ("圣女", "saintess", 67, "圣女身份"),
        ("圣子", "holy_son", 68, "圣子身份"),

        # 性格/特质类（属性值描述）
        ("深不可测", "unfathomable", 80, "实力深不可测"),
        ("潜力无限", "unlimited_potential", 81, "潜力巨大"),
        ("成长迅速", "fast_growth", 82, "成长速度快"),
        ("根基扎实", "solid_foundation", 83, "基础扎实"),
        ("悟性极高", "great_comprehension", 84, "领悟能力强"),
        ("福缘深厚", "great_luck", 85, "运气好/福缘深"),
        ("心魔缠身", "inner_demon", 86, "有心魔隐患"),
        ("体质特殊", "special_constitution", 87, "特殊体质"),
        ("血脉稀有", "rare_bloodline", 88, "稀有血脉"),
    ]

    _add_dict_items(db, dict_id, items)


def _get_or_create_dict(db: Session, dict_code: str, dict_name: str, description: str, sort_order: int) -> int:
    """获取或创建字典，返回字典 ID。"""
    result = db.execute(
        text("SELECT id FROM sys_dictionaries WHERE dict_code = :code"),
        {"code": dict_code},
    ).fetchone()
    if result:
        return result[0]

    db.execute(text("""
        INSERT INTO sys_dictionaries (dict_code, dict_name, description, sort_order, status)
        VALUES (:dict_code, :dict_name, :description, :sort_order, 'active')
    """), {
        "dict_code": dict_code,
        "dict_name": dict_name,
        "description": description,
        "sort_order": sort_order,
    })
    result = db.execute(
        text("SELECT id FROM sys_dictionaries WHERE dict_code = :code"),
        {"code": dict_code},
    ).fetchone()
    return result[0]


def _add_dict_items(db: Session, dict_id: int, items: list[tuple[str, str, int, str]]) -> None:
    """批量添加字典项（幂等）。"""
    for item_label, item_value, item_sort, remark in items:
        existing = db.execute(text("""
            SELECT id FROM sys_dict_items
            WHERE dict_id = :dict_id AND item_value = :value
        """), {"dict_id": dict_id, "value": item_value}).fetchone()
        if existing:
            db.execute(text("""
                UPDATE sys_dict_items SET remark = :remark, sort_order = :sort_order
                WHERE id = :id
            """), {
                "id": existing[0],
                "remark": remark,
                "sort_order": item_sort,
            })
            continue

        db.execute(text("""
            INSERT INTO sys_dict_items (dict_id, item_label, item_value, sort_order, status, remark)
            VALUES (:dict_id, :item_label, :item_value, :sort_order, 'active', :remark)
        """), {
            "dict_id": dict_id,
            "item_label": item_label,
            "item_value": item_value,
            "sort_order": item_sort,
            "remark": remark,
        })
    db.commit()
