"""核心库迁移 v006 — 关系摘要字典。

添加关系摘要常用标签字典，用于人物卡片关系摘要字段的快速选择。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """添加关系摘要字典数据。"""
    dict_id = _get_or_create_dict(db, "relation_summary", "关系摘要", "人物关系类型速查标签，可多选", 28)

    items = [
        # 血缘亲属
        ("父子", "father_son", 1, "父子关系"),
        ("母女", "mother_daughter", 2, "母女关系"),
        ("父女", "father_daughter", 3, "父女关系"),
        ("母子", "mother_son", 4, "母子关系"),
        ("兄弟", "brothers", 5, "兄弟关系"),
        ("姐妹", "sisters", 6, "姐妹关系"),
        ("青梅竹马", "childhood_sweethearts", 7, "从小一起长大"),
        ("养父子", "adopted_father_son", 8, "收养的父子/母女关系"),
        ("义兄妹", "sworn_siblings", 9, "结拜的兄妹/姐弟"),
        ("祖孙", "grandparent_grandchild", 10, "祖父母与孙辈"),
        ("叔侄", "uncle_nephew", 11, "叔伯与侄辈"),

        # 情感关系
        ("恋人", "lovers", 20, "恋爱关系"),
        ("暗恋", "unrequited_love", 21, "单方面喜欢"),
        ("暧昧", "ambiguous", 22, "暧昧不清"),
        ("前任", "ex", 23, "前任恋人"),
        ("情敌", "love_rival", 24, "感情上的对手"),
        ("婚约", "engagement", 25, "有婚约在身"),
        ("夫妻", "spouses", 26, "已婚夫妇"),
        ("单恋", "one_sided_love", 27, "单相思"),

        # 师徒/上下级
        ("师徒", "master_apprentice", 40, "师父与徒弟"),
        ("上下级", "superior_subordinate", 41, "领导与下属"),
        ("同门派", "same_sect", 42, "同一门派/组织"),
        ("同窗", "classmates", 43, "同学关系"),
        ("战友", "comrades_in_arms", 44, "一起战斗过"),
        ("主仆", "master_servant", 45, "主人与仆人"),
        ("同门", "same_school", 46, "同门师兄弟/师姐妹"),

        # 友情/敌对
        ("挚友", "best_friend", 60, "最好的朋友"),
        ("盟友", "ally", 61, "利益同盟"),
        ("宿敌", "arch_enemy", 62, "长期的对手"),
        ("竞争对手", "rival", 63, "竞争关系"),
        ("忘年交", "friends_despite_age_gap", 64, "跨年龄的友谊"),
        ("知己", "soulmate_platonic", 65, "精神知己"),
        ("仇敌", "enemy", 66, "死敌/仇敌"),

        # 特殊羁绊
        ("救命恩人", "savior", 80, "救过对方性命"),
        ("亏欠", "indebted", 81, "对对方有亏欠"),
        ("宿怨", "long_standing_grudge", 82, "长期的怨恨"),
        ("替身", "replacement", 83, "被当作某人的替代品"),
        ("命运共同体", "destiny_bond", 84, "命运紧密相连"),
        ("杀亲之仇", "family_killer", 85, "有杀亲之仇"),
        ("义兄弟", "sworn_brothers", 86, "结义兄弟/姐妹"),
        ("救命之恩", "life_saver", 87, "救命恩人"),
        ("其他", "other", 99, "其他关系"),
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
        # 检查是否已存在
        existing = db.execute(text("""
            SELECT id FROM sys_dict_items
            WHERE dict_id = :dict_id AND item_value = :value
        """), {"dict_id": dict_id, "value": item_value}).fetchone()
        if existing:
            # 更新 remark
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
