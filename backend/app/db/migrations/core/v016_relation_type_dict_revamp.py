"""核心库迁移 v016 — 优化关系类型字典。

重新设计 relation_type 字典：
- 按大类分组：亲情、爱情、友情、敌对、职场/组织、恩情/仇恨、其他
- 名称更通俗通用，描述更清晰
- value 使用英文语义化命名
- 保持向后兼容（已有数据的 relation_type 是 label 文本，不依赖字典项 ID）
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """更新关系类型字典项（全量替换为优化版）。"""

    # 查找字典 ID
    result = db.execute(
        text("SELECT id FROM sys_dictionaries WHERE dict_code = 'relation_type'")
    ).fetchone()
    if not result:
        return
    dict_id = result[0]

    # 先删除原有字典项
    db.execute(
        text("DELETE FROM sys_dict_items WHERE dict_id = :dict_id"),
        {"dict_id": dict_id},
    )

    # 新的关系类型（按大类排序，更通用通俗）
    # 格式：(label, value, sort_order, status, remark)
    items = [
        # —— 亲情类（10-19）——
        ("父子", "father_son", 10, "active", "父亲与儿子的血缘关系"),
        ("母女", "mother_daughter", 11, "active", "母亲与女儿的血缘关系"),
        ("父女", "father_daughter", 12, "active", "父亲与女儿的血缘关系"),
        ("母子", "mother_son", 13, "active", "母亲与儿子的血缘关系"),
        ("兄弟", "brothers", 14, "active", "哥哥与弟弟的关系"),
        ("姐妹", "sisters", 15, "active", "姐姐与妹妹的关系"),
        ("兄妹/姐弟", "sibling", 16, "active", "兄弟姐妹的统称"),
        ("祖孙", "grandparent_grandchild", 17, "active", "祖父母/外祖父母与孙辈"),
        ("叔侄/舅甥", "uncle_nephew", 18, "active", "叔伯/舅舅与侄子/外甥"),
        ("养父母子女", "adoptive", 19, "active", "养父母与养子女的关系"),

        # —— 爱情类（20-29）——
        ("恋人", "lovers", 20, "active", "情侣/恋爱关系"),
        ("夫妻", "spouses", 21, "active", "已婚/配偶关系"),
        ("前任", "ex", 22, "active", "前任恋人/前任配偶"),
        ("暗恋", "crush", 23, "active", "一方暗恋另一方，对方不知情"),
        ("单恋", "unrequited", 24, "active", "一方爱慕另一方，对方知晓但不接受"),
        ("暧昧", "ambiguous", 25, "active", "关系模糊，互相有意但未明说"),
        ("知己", "soulmate", 26, "active", "精神契合的灵魂知己"),

        # —— 友情类（30-39）——
        ("挚友", "best_friend", 30, "active", "最好的朋友，生死之交"),
        ("朋友", "friend", 31, "active", "普通朋友关系"),
        ("义兄弟/义姐妹", "sworn_sibling", 32, "active", "结义的兄弟/姐妹"),
        ("忘年交", "intergenerational_friend", 33, "active", "年龄差距大的好朋友"),
        ("同门", "same_school", 34, "active", "同一师门的师兄弟/师姐妹"),
        ("旧识", "old_acquaintance", 35, "active", "以前认识的人，关系尚可"),
        ("熟识", "acquaintance", 36, "active", "认识但不太熟"),
        ("陌生人", "stranger", 37, "active", "互不认识"),

        # —— 敌对类（40-49）——
        ("死敌", "mortal_enemy", 40, "active", "势不两立的仇敌"),
        ("仇敌", "enemy", 41, "active", "有仇恨的敌人"),
        ("竞争对手", "rival", 42, "active", "在同一领域竞争的对手"),

        # —— 职场/组织类（50-59）——
        ("上下级", "superior_subordinate", 50, "active", "上司与下属的关系"),
        ("同事", "colleague", 51, "active", "一起工作的同事"),
        ("主仆", "master_servant", 52, "active", "主人与仆人/侍从"),
        ("师徒", "master_disciple", 53, "active", "师父与徒弟的师徒关系"),
        ("盟友", "ally", 54, "active", "同盟/合作关系，利益一致"),

        # —— 恩情/债务类（60-69）——
        ("救命之恩", "life_saver", 60, "active", "救过对方性命的恩人"),
        ("杀亲之仇", "family_killer", 61, "active", "有杀害亲人的血海深仇"),
        ("有恩", "benefactor", 62, "active", "对另一方有恩情"),
        ("有仇", "grudge", 63, "active", "双方有过节/仇恨"),
        ("亏欠", "indebted", 64, "active", "一方对另一方有所亏欠"),

        # —— 其他（90-99）——
        ("其他", "other", 99, "active", "以上未涵盖的其他关系"),
    ]

    for label, value, sort_order, status, remark in items:
        db.execute(
            text(
                """INSERT INTO sys_dict_items
                   (dict_id, item_label, item_value, sort_order, status, remark, created_at)
                   VALUES (:dict_id, :item_label, :item_value, :sort_order, :status, :remark,
                           datetime('now'))"""
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


def downgrade(db: Session) -> None:
    """回滚：无需精确回滚。"""
    pass
