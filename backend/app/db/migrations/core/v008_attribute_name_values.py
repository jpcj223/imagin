"""核心库迁移 v008 — 属性名称字典值列表扩展。

为 attribute_name 字典的每个属性补充可选值列表（remark 字段，顿号分隔），
用于人物卡片属性管理中，选择属性后自动展示对应的可选值。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """更新 attribute_name 字典项的 remark 为可选值列表。"""
    # 先获取字典 ID
    result = db.execute(
        text("SELECT id FROM sys_dictionaries WHERE dict_code = :code"),
        {"code": "attribute_name"},
    ).fetchone()
    if not result:
        return
    dict_id = result[0]

    # 每个属性对应的值列表（remark 存顿号分隔的值）
    value_map: dict[str, str] = {
        # 修为类
        "kung_fu": "绝顶、宗师级、大师级、精英级、普通、入门、废柴",
        "inner_force": "深厚、充沛、一般、薄弱、全无",
        "cultivation_method": "神级、圣级、天级、地级、玄级、黄级、凡品",
        # 物品类
        "treasure": "神器、仙器、灵宝、法器、凡物",
        "equipment": "传说、史诗、稀有、精良、普通",
        # 能力类
        "skill": "精通、熟练、掌握、入门、未知",
        "superpower": "SS级、S级、A级、B级、C级、D级",
        # 身份类
        "title": "盟主、长老、堂主、执事、弟子、杂役",
        "identity": "嫡子、庶子、养子、私生子、孤儿",
        # 资源类
        "wealth": "富可敌国、家财万贯、家境殷实、小康、清贫、一贫如洗",
        "influence": "一方霸主、举足轻重、小有名气、默默无闻",
        "reputation": "名震天下、声名远扬、小有名气、默默无闻、臭名昭著",
        # 属性类
        "charm": "倾国倾城、绝世容颜、清秀可人、普通、丑陋",
        "intelligence": "绝世天才、聪明绝顶、机智过人、普通、愚笨",
        "constitution": "先天道体、特殊体质、上品、中品、下品、废材",
        "comprehension": "过目不忘、举一反三、一点就通、普通、愚钝",
        "fortune": "天命之子、鸿运当头、运气不错、普通、霉运缠身",
        # 心境类
        "inner_demon": "无、轻微、严重、走火入魔",
        "dao_heart": "圆满、坚定、稳固、动摇、破碎",
        # 血脉类
        "bloodline": "神兽血脉、皇族血脉、世家血脉、普通血脉、杂种血脉",
    }

    for item_value, remark in value_map.items():
        db.execute(text("""
            UPDATE sys_dict_items
            SET remark = :remark
            WHERE dict_id = :dict_id AND item_value = :item_value
        """), {
            "dict_id": dict_id,
            "item_value": item_value,
            "remark": remark,
        })

    db.commit()
