"""核心库迁移 v018 — 新增组织核心资源字典。"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """新增 org_resource 字典。"""

    result = db.execute(
        text("SELECT id FROM sys_dictionaries WHERE dict_code = 'org_resource'")
    ).fetchone()

    if not result:
        db.execute(
            text(
                """
                INSERT INTO sys_dictionaries
                (dict_code, dict_name, description, status, created_at)
                VALUES ('org_resource', '组织资源类型', '组织/势力拥有的核心资源类型', 'active',
                        datetime('now'))
                """
            )
        )
        result = db.execute(
            text("SELECT id FROM sys_dictionaries WHERE dict_code = 'org_resource'")
        ).fetchone()

    dict_id = result[0]

    # 先清空已有字典项
    db.execute(
        text("DELETE FROM sys_dict_items WHERE dict_id = :dict_id"),
        {"dict_id": dict_id},
    )

    # 组织资源类型（通用、通俗、覆盖多种题材）
    items = [
        # —— 修仙/武侠类（10-19）——
        ("天材地宝", "treasure", 10, "active", "灵药、矿石、法宝等珍稀资源"),
        ("修炼功法", "cultivation_art", 11, "active", "秘籍、功法、心法、武技"),
        ("灵脉/福地", "spiritual_land", 12, "active", "灵气充沛的修炼宝地"),
        ("丹器阵法", "alchemy_array", 13, "active", "炼丹、炼器、阵法能力"),
        ("灵兽/妖兽", "spirit_beast", 14, "active", "灵兽、坐骑、妖兽军团"),

        # —— 经济资源（20-29）——
        ("资金/财富", "wealth", 20, "active", "金钱、财宝、产业"),
        ("地盘/领地", "territory", 21, "active", "地盘、据点、领地控制"),
        ("商业网络", "business_network", 22, "active", "商铺、商队、贸易渠道"),
        ("情报网络", "intelligence", 23, "active", "谍报、眼线、情报收集"),
        ("人脉关系", "connections", 24, "active", "人脉、背景、官场关系"),

        # —— 人员/战力（30-39）——
        ("高手战力", "experts", 30, "active", "顶级战力、高手、强者"),
        ("军队/部众", "army", 31, "active", "军队、部众、门徒数量"),
        ("特殊人才", "special_talent", 32, "active", "炼丹师、炼器师、医师等"),
        ("死士/暗卫", "assassins", 33, "active", "死士、暗卫、暗杀力量"),

        # —— 科技/现代（40-49）——
        ("科技研发", "technology", 40, "active", "科研能力、技术储备"),
        ("武器装备", "weapons", 41, "active", "武器、装备、军火"),
        ("医疗能力", "medical", 42, "active", "医疗、医药、救治能力"),
        ("信息系统", "it_system", 43, "active", "黑客、网络、数据系统"),

        # —— 特殊能力（50-59）——
        ("神秘力量", "mystic_power", 50, "active", "神秘、未知的特殊力量"),
        ("魔法/异能", "magic_power", 51, "active", "魔法、异能、超自然能力"),
        ("血脉/传承", "bloodline", 52, "active", "血脉、传承、特殊体质"),

        # —— 其他（90-99）——
        ("声望/名望", "prestige", 90, "active", "名声、威望、江湖地位"),
        ("底蕴/积累", "heritage", 91, "active", "历史底蕴、多年积累"),
        ("其他", "other", 99, "active", "其他类型的资源"),
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
