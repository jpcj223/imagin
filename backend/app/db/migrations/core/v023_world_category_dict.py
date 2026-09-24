"""核心库迁移 v023：补齐世界观分类字典。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.core import SysDictItem, SysDictionary


WORLD_CATEGORIES = [
    ("地理环境", "geography", 10, "大陆、城市、地形与重要地点"),
    ("时代背景", "era", 20, "世界所处时代与历史背景"),
    ("力量体系", "power_system", 30, "修炼、魔法、科技或异能体系"),
    ("世界规则", "rules", 40, "世界运行规律与基础法则"),
    ("重要物品", "items", 50, "影响剧情或世界设定的重要物品"),
    ("武器装备", "weapons", 60, "武器、防具及其他关键装备"),
    ("药品丹药", "medicine", 70, "药品、丹药与特殊消耗品"),
    ("种族生物", "creatures", 80, "种族、异兽与特殊生物"),
    ("组织势力", "organizations", 90, "世界中的组织、国家与势力设定"),
    ("其他设定", "other", 100, "不属于其他分类的世界设定"),
]


def upgrade(db: Session) -> None:
    """创建世界观分类字典，并补入缺少的默认分类。"""
    # 步骤 1：查找或创建字典；保留用户已有字典及其自定义项。
    dictionary = (
        db.query(SysDictionary)
        .filter(SysDictionary.dict_code == "world_category")
        .first()
    )
    if dictionary is None:
        dictionary = SysDictionary(
            dict_code="world_category",
            dict_name="世界观分类",
            description="世界设定条目的分类",
            sort_order=7,
            status="active",
        )
        db.add(dictionary)
        db.flush()

    # 步骤 2：按分类值补缺，迁移重复执行时不会覆盖或重复创建自定义数据。
    existing_values = {
        row[0]
        for row in db.query(SysDictItem.item_value)
        .filter(SysDictItem.dict_id == dictionary.id)
        .all()
    }
    for label, value, sort_order, remark in WORLD_CATEGORIES:
        if value in existing_values:
            continue
        db.add(
            SysDictItem(
                dict_id=dictionary.id,
                item_label=label,
                item_value=value,
                sort_order=sort_order,
                status="active",
                remark=remark,
            )
        )

    db.flush()
