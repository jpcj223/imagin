"""核心库迁移 v017 — 新增组织类型字典。"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """新增 org_type 字典。"""

    result = db.execute(
        text("SELECT id FROM sys_dictionaries WHERE dict_code = 'org_type'")
    ).fetchone()

    if not result:
        db.execute(
            text(
                """
                INSERT INTO sys_dictionaries
                (dict_code, dict_name, description, status, created_at, updated_at)
                VALUES ('org_type', '组织类型', '组织/势力的类型分类', 'active',
                        datetime('now'), datetime('now'))
                """
            )
        )
        result = db.execute(
            text("SELECT id FROM sys_dictionaries WHERE dict_code = 'org_type'")
        ).fetchone()

    dict_id = result[0]

    # 先清空已有字典项
    db.execute(
        text("DELETE FROM sys_dict_items WHERE dict_id = :dict_id"),
        {"dict_id": dict_id},
    )

    # 组织类型字典项（通用、通俗、覆盖多种题材）
    items = [
        # —— 修仙/武侠类（10-19）——
        ("门派/宗门", "sect", 10, "active", "修仙/武侠题材的修炼门派"),
        ("家族/世家", "family_clan", 11, "active", "以血缘为纽带的家族势力"),
        ("帮派/帮会", "gang", 12, "active", "江湖帮派、武林帮会"),
        ("商会/商行", "merchant_guild", 13, "active", "商业联盟、商贾组织"),
        ("杀手组织", "assassin_guild", 14, "active", "暗杀、刺客、赏金猎人组织"),
        ("情报组织", "intelligence", 15, "active", "情报收集、间谍网络"),

        # —— 现代/都市类（20-29）——
        ("公司/企业", "company", 20, "active", "商业公司、企业集团"),
        ("政府机构", "government", 21, "active", "官方政府部门、机构"),
        ("军方/特种部队", "military", 22, "active", "军队、特种作战部队"),
        ("黑帮/社团", "mafia", 23, "active", "黑社会组织、地下社团"),
        ("科研机构", "research_institute", 24, "active", "实验室、研究院、科技公司"),
        ("学校/学院", "academy", 25, "active", "学校、学院、培训机构"),
        ("医院/医疗机构", "hospital", 26, "active", "医院、诊所、医疗组织"),
        ("媒体/出版社", "media", 27, "active", "新闻媒体、出版社、互联网公司"),

        # —— 奇幻/西方类（30-39）——
        ("骑士团", "knight_order", 30, "active", "骑士团、圣殿骑士等武装组织"),
        ("魔法公会", "mage_guild", 31, "active", "魔法师协会、魔法学院"),
        ("冒险者公会", "adventurer_guild", 32, "active", "冒险者协会、佣兵公会"),
        ("教会/教廷", "church", 33, "active", "宗教组织、教廷、神殿"),
        ("王国/帝国", "kingdom", 34, "active", "国家政权、王室势力"),
        ("盗贼公会", "thieves_guild", 35, "active", "盗贼协会、地下黑市组织"),

        # —— 其他（90-99）——
        ("神秘组织", "mysterious", 90, "active", "身份不明的神秘组织"),
        ("散修/自由人", "independent", 91, "active", "无组织、独来独往"),
        ("其他", "other", 99, "active", "其他类型的组织"),
    ]

    for label, value, sort_order, status, remark in items:
        db.execute(
            text(
                """
                INSERT INTO sys_dict_items
                (dict_id, item_label, item_value, sort_order, status, remark, created_at)
                VALUES (:dict_id, :item_label, :item_value, :sort_order, :status, :remark,
                        datetime('now'))
                """
            ),
            {
                "dict_id": dict_id,
                "item_label": label,
                "item_value": value,
                "sort_order": sort_order,
                "status": status,
                "remark": remark,
            },
        )

    db.commit()
