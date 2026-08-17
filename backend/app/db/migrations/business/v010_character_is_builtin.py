"""v010 — 角色表增加 is_builtin 字段，并初始化内置角色。

功能：
- is_builtin：是否为内置角色（不可删除）
- 为每个项目初始化 7 个通用 NPC + 1 主角 + 2 配角
- 内置角色包含自定义属性和人物关系

幂等性：字段已存在则跳过 ALTER；角色已存在则跳过 INSERT。
"""
from __future__ import annotations

import json
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.migrations.common import ensure_columns


# 通用内置角色模板（7个）
BUILTIN_COMMON_CHARACTERS = [
    {
        "name": "路人甲",
        "role_type": "extra",
        "identity": "路人",
        "appearance": "普通、无特征",
        "personality": "",
        "background": "",
        "mbti_primary": "",
        "mbti_secondary": "",
        "status": "active",
        "custom_attributes": [
            {"key": "age", "name": "年龄", "title": "年龄", "value": "30", "description": "中年路人", "chapter_no": None, "change_reason": ""},
            {"key": "cultivation", "name": "修为", "title": "修为", "value": "炼气期", "description": "普通修士", "chapter_no": None, "change_reason": ""},
        ],
    },
    {
        "name": "店小二",
        "role_type": "npc",
        "identity": "店小二、酒馆伙计",
        "appearance": "利落、穿伙计服",
        "personality": "机灵、话多",
        "background": "在城镇酒馆/客栈打工",
        "mbti_primary": "ESFP",
        "mbti_secondary": "",
        "status": "active",
        "custom_attributes": [
            {"key": "age", "name": "年龄", "title": "年龄", "value": "20", "description": "年轻伙计", "chapter_no": None, "change_reason": ""},
            {"key": "skill", "name": "技能", "title": "技能", "value": "察言观色、消息灵通", "description": "酒馆工作的必备技能", "chapter_no": None, "change_reason": ""},
            {"key": "affiliation", "name": "所属", "title": "所属", "value": "悦来客栈", "description": "工作的客栈", "chapter_no": None, "change_reason": ""},
        ],
        "character_relations": [
            {"target_name": "萧寒", "relation_type": "熟识", "depth": 4, "effective_from": 1, "expires_at": None},
        ],
    },
    {
        "name": "守卫",
        "role_type": "npc",
        "identity": "城门守卫、卫兵",
        "appearance": "魁梧、穿盔甲",
        "personality": "严谨、恪尽职守",
        "background": "负责城门/府邸巡逻",
        "mbti_primary": "ISTJ",
        "mbti_secondary": "",
        "status": "active",
        "custom_attributes": [
            {"key": "age", "name": "年龄", "title": "年龄", "value": "35", "description": "壮年守卫", "chapter_no": None, "change_reason": ""},
            {"key": "cultivation", "name": "修为", "title": "修为", "value": "筑基期", "description": "城防军标准修为", "chapter_no": None, "change_reason": ""},
            {"key": "weapon", "name": "武器", "title": "武器", "value": "长枪、佩刀", "description": "标配武器", "chapter_no": None, "change_reason": ""},
            {"key": "loyalty", "name": "忠诚度", "title": "忠诚度", "value": "高", "description": "对城主忠心耿耿", "chapter_no": None, "change_reason": ""},
        ],
        "character_relations": [
            {"target_name": "苏婉清", "relation_type": "熟识", "depth": 3, "effective_from": 1, "expires_at": None},
        ],
    },
    {
        "name": "老者",
        "role_type": "npc",
        "identity": "长者、智者",
        "appearance": "白发苍苍、精神矍铄",
        "personality": "沉稳、睿智",
        "background": "村中/门派中德高望重的老人",
        "mbti_primary": "INFJ",
        "mbti_secondary": "",
        "status": "active",
        "custom_attributes": [
            {"key": "age", "name": "年龄", "title": "年龄", "value": "70", "description": "古稀之年", "chapter_no": None, "change_reason": ""},
            {"key": "cultivation", "name": "修为", "title": "修为", "value": "金丹期", "description": "深藏不露", "chapter_no": None, "change_reason": ""},
            {"key": "wisdom", "name": "智慧", "title": "智慧", "value": "极高", "description": "人生阅历丰富", "chapter_no": None, "change_reason": ""},
            {"key": "identity_hidden", "name": "隐藏身份", "title": "隐藏身份", "value": "前掌门/隐世高人", "description": "真实身份成谜", "chapter_no": None, "change_reason": ""},
        ],
        "character_relations": [
            {"target_name": "萧寒", "relation_type": "忘年交", "depth": 7, "effective_from": 4, "expires_at": None},
            {"target_name": "苏婉清", "relation_type": "长辈", "depth": 7, "effective_from": 1, "expires_at": None},
        ],
    },
    {
        "name": "孩童",
        "role_type": "npc",
        "identity": "村中儿童",
        "appearance": "天真、穿粗布衣裳",
        "personality": "活泼、好奇",
        "background": "",
        "mbti_primary": "ENFP",
        "mbti_secondary": "",
        "status": "active",
        "custom_attributes": [
            {"key": "age", "name": "年龄", "title": "年龄", "value": "8", "description": "垂髫之年", "chapter_no": None, "change_reason": ""},
            {"key": "talent", "name": "天赋", "title": "天赋", "value": "未知", "description": "可能有隐藏天赋", "chapter_no": None, "change_reason": ""},
        ],
    },
    {
        "name": "信使",
        "role_type": "npc",
        "identity": "信使、传令兵",
        "appearance": "精干、风尘仆仆",
        "personality": "守时、话少",
        "background": "负责传递消息",
        "mbti_primary": "ISTP",
        "mbti_secondary": "",
        "status": "active",
        "custom_attributes": [
            {"key": "age", "name": "年龄", "title": "年龄", "value": "25", "description": "青年信使", "chapter_no": None, "change_reason": ""},
            {"key": "cultivation", "name": "修为", "title": "修为", "value": "筑基期", "description": "足以自保", "chapter_no": None, "change_reason": ""},
            {"key": "skill", "name": "技能", "title": "技能", "value": "轻功、匿踪", "description": "信使必备", "chapter_no": None, "change_reason": ""},
            {"key": "speed", "name": "速度", "title": "速度", "value": "快", "description": "脚程极快", "chapter_no": None, "change_reason": ""},
        ],
        "character_relations": [
            {"target_name": "厉风行", "relation_type": "熟识", "depth": 5, "effective_from": None, "expires_at": None},
        ],
    },
    {
        "name": "医者",
        "role_type": "npc",
        "identity": "大夫、药师",
        "appearance": "儒雅、带药箱",
        "personality": "温和、细致",
        "background": "悬壶济世的医者",
        "mbti_primary": "ISFJ",
        "mbti_secondary": "",
        "status": "active",
        "custom_attributes": [
            {"key": "age", "name": "年龄", "title": "年龄", "value": "50", "description": "知命之年", "chapter_no": None, "change_reason": ""},
            {"key": "cultivation", "name": "修为", "title": "修为", "value": "结丹期", "description": "医术与修为并重", "chapter_no": None, "change_reason": ""},
            {"key": "skill", "name": "技能", "title": "技能", "value": "医术、炼丹、解毒", "description": "精通岐黄之术", "chapter_no": None, "change_reason": ""},
            {"key": "medicine_chest", "name": "药箱", "title": "药箱", "value": "珍稀药材齐全", "description": "祖传药箱", "chapter_no": None, "change_reason": ""},
            {"key": "reputation", "name": "名声", "title": "名声", "value": "神医", "description": "救死扶伤无数", "chapter_no": None, "change_reason": ""},
        ],
        "character_relations": [
            {"target_name": "厉风行", "relation_type": "旧识", "depth": 7, "effective_from": None, "expires_at": None},
        ],
    },
]

# 测试角色：1主角 + 2配角
TEST_CHARACTERS = [
    {
        "name": "萧寒",
        "role_type": "protagonist",
        "identity": "修仙者、宗门弟子",
        "faction": "青云门",
        "appearance": "剑眉星目、一袭青衫、气质清冷",
        "personality": "坚韧、隐忍、外冷内热",
        "background": "出身贫寒，自幼父母双亡，被青云门收入门下",
        "motivation": "守护重要的人、探寻身世之谜",
        "weakness": "过于执着、容易自责",
        "secret": "体内封印着上古凶兽残魂",
        "dialogue_style": "话少、简洁、言出必行",
        "arc": "从默默无闻的小弟子成长为一代宗师",
        "mbti_primary": "INTJ",
        "mbti_secondary": "INFJ",
        "status": "active",
        "chapters": "1, 3-10, 15-20",
        "custom_attributes": [
            {"key": "age", "name": "年龄", "title": "年龄", "value": "16", "description": "初入宗门时的年龄", "chapter_no": "1", "change_reason": "入门"},
            {"key": "age", "name": "年龄", "title": "年龄", "value": "18", "description": "宗门大比时", "chapter_no": "10", "change_reason": "两年后"},
            {"key": "cultivation", "name": "修为", "title": "修为", "value": "炼气期三层", "description": "入门修为", "chapter_no": "1", "change_reason": "刚入门"},
            {"key": "cultivation", "name": "修为", "title": "修为", "value": "筑基期", "description": "突破筑基", "chapter_no": "5-6", "change_reason": "秘境奇遇"},
            {"key": "cultivation", "name": "修为", "title": "修为", "value": "结丹期", "description": "宗门大比后突破", "chapter_no": "15", "change_reason": "生死历练"},
            {"key": "weapon", "name": "武器", "title": "武器", "value": "青锋剑", "description": "入门佩剑", "chapter_no": "1", "change_reason": "宗门配发"},
            {"key": "weapon", "name": "武器", "title": "武器", "value": "诛仙剑", "description": "上古神剑，得自秘境", "chapter_no": "5-6", "change_reason": "秘境传承"},
            {"key": "skill", "name": "功法", "title": "功法", "value": "青云心法", "description": "宗门基础心法", "chapter_no": "1", "change_reason": "入门所学"},
            {"key": "skill", "name": "功法", "title": "功法", "value": "九转玄功", "description": "上古传承功法", "chapter_no": "5", "change_reason": "秘境所得"},
            {"key": "special_body", "name": "特殊体质", "title": "特殊体质", "value": "混沌道体", "description": "万中无一的修炼体质", "chapter_no": "10", "change_reason": "体质觉醒"},
        ],
        "character_relations": [
            {"target_name": "苏婉清", "relation_type": "恋人", "depth": 9, "effective_from": 3, "expires_at": None},
            {"target_name": "厉风行", "relation_type": "亦师亦友", "depth": 8, "effective_from": 2, "expires_at": None},
            {"target_name": "老者", "relation_type": "忘年交", "depth": 7, "effective_from": 4, "expires_at": None},
            {"target_name": "店小二", "relation_type": "熟识", "depth": 4, "effective_from": 1, "expires_at": None},
        ],
    },
    {
        "name": "苏婉清",
        "role_type": "supporting",
        "identity": "青云门大师姐、宗门圣女",
        "faction": "青云门",
        "appearance": "绝世容颜、白衣胜雪、气质出尘",
        "personality": "外柔内刚、聪慧、有担当",
        "background": "青云门掌门之女，天赋异禀",
        "motivation": "维护宗门、追寻剑道极致",
        "weakness": "过于在意他人期待",
        "secret": "对主角暗生情愫",
        "dialogue_style": "温和有礼、言辞得体",
        "arc": "从温室花朵蜕变为能独当一面的强者",
        "mbti_primary": "INFJ",
        "mbti_secondary": "ENFJ",
        "status": "active",
        "chapters": "2, 4-12, 16-20",
        "custom_attributes": [
            {"key": "age", "name": "年龄", "title": "年龄", "value": "17", "description": "初登场年龄", "chapter_no": "2", "change_reason": "初次登场"},
            {"key": "age", "name": "年龄", "title": "年龄", "value": "19", "description": "宗门大比时", "chapter_no": "10", "change_reason": "两年后"},
            {"key": "cultivation", "name": "修为", "title": "修为", "value": "筑基期巅峰", "description": "天才弟子", "chapter_no": "2", "change_reason": "初登场"},
            {"key": "cultivation", "name": "修为", "title": "修为", "value": "结丹期", "description": "宗门大比前突破", "chapter_no": "8", "change_reason": "闭关突破"},
            {"key": "weapon", "name": "武器", "title": "武器", "value": "流云剑", "description": "掌门所赐佩剑", "chapter_no": "2", "change_reason": "成年礼"},
            {"key": "skill", "name": "功法", "title": "功法", "value": "冰心诀", "description": "青云门镇派功法之一", "chapter_no": "2", "change_reason": "嫡传功法"},
            {"key": "status_in_faction", "name": "宗门地位", "title": "宗门地位", "value": "圣女、大师姐", "description": "下一任掌门继承人", "chapter_no": None, "change_reason": ""},
            {"key": "talent", "name": "天赋", "title": "天赋", "value": "剑心通明", "description": "百年一遇的剑道奇才", "chapter_no": None, "change_reason": ""},
        ],
        "character_relations": [
            {"target_name": "萧寒", "relation_type": "恋人", "depth": 9, "effective_from": 5, "expires_at": None},
            {"target_name": "厉风行", "relation_type": "朋友", "depth": 6, "effective_from": 3, "expires_at": None},
            {"target_name": "老者", "relation_type": "长辈", "depth": 7, "effective_from": 1, "expires_at": None},
            {"target_name": "守卫", "relation_type": "熟识", "depth": 3, "effective_from": 1, "expires_at": None},
        ],
    },
    {
        "name": "厉风行",
        "role_type": "supporting",
        "identity": "散修、游侠",
        "faction": "",
        "appearance": "身形魁梧、伤疤累累、气质豪迈",
        "personality": "豪爽、重义气、不拘小节",
        "background": "行走江湖的散修，与主角亦师亦友",
        "motivation": "快意恩仇、守护朋友",
        "weakness": "冲动、好酒",
        "secret": "曾是名门大弟子，因变故被逐出师门",
        "dialogue_style": "粗犷直率、爱开玩笑",
        "arc": "从逃避过去到直面心魔",
        "mbti_primary": "ESTP",
        "mbti_secondary": "ESFP",
        "status": "active",
        "chapters": "2, 5-8, 11-18",
        "custom_attributes": [
            {"key": "age", "name": "年龄", "title": "年龄", "value": "28", "description": "初登场年龄", "chapter_no": "2", "change_reason": "初次登场"},
            {"key": "cultivation", "name": "修为", "title": "修为", "value": "结丹期", "description": "散修中的强者", "chapter_no": "2", "change_reason": "初登场"},
            {"key": "cultivation", "name": "修为", "title": "修为", "value": "元婴期", "description": "解开旧伤封印后突破", "chapter_no": "12-13", "change_reason": "心结解开"},
            {"key": "weapon", "name": "武器", "title": "武器", "value": "玄铁重刀", "description": "随身宝刀", "chapter_no": "2", "change_reason": "惯用武器"},
            {"key": "skill", "name": "功法", "title": "功法", "value": "狂风刀法", "description": "自创刀法", "chapter_no": "2", "change_reason": "行走江湖所创"},
            {"key": "previous_faction", "name": "前宗门", "title": "前宗门", "value": "天刀门", "description": "曾是天刀门大弟子", "chapter_no": None, "change_reason": ""},
            {"key": "injury", "name": "旧伤", "title": "旧伤", "value": "心脉受损", "description": "被逐出师门时留下的伤", "chapter_no": "1-12", "change_reason": "旧伤困扰"},
        ],
        "character_relations": [
            {"target_name": "萧寒", "relation_type": "亦师亦友", "depth": 8, "effective_from": 2, "expires_at": None},
            {"target_name": "苏婉清", "relation_type": "朋友", "depth": 6, "effective_from": 3, "expires_at": None},
            {"target_name": "医者", "relation_type": "旧识", "depth": 7, "effective_from": None, "expires_at": None},
            {"target_name": "信使", "relation_type": "熟识", "depth": 5, "effective_from": None, "expires_at": None},
        ],
    },
]


def upgrade(db: Session) -> None:
    dialect = db.bind.dialect.name

    # 1. 确保 is_builtin 字段存在
    ensure_columns(db, dialect, "characters", {
        "is_builtin": "BOOLEAN DEFAULT 0",
    })

    # 2. 获取所有项目 ID
    result = db.execute(text("SELECT id FROM projects"))
    project_ids = [row[0] for row in result.fetchall()]

    if not project_ids:
        return

    # 3. 为每个项目插入内置角色（幂等：已存在则跳过）
    all_characters = BUILTIN_COMMON_CHARACTERS + TEST_CHARACTERS
    for project_id in project_ids:
        for char in all_characters:
            # 检查该项目下是否已存在同名内置角色
            existing = db.execute(
                text("""
                    SELECT id FROM characters
                    WHERE project_id = :pid AND name = :name AND is_builtin = 1
                    LIMIT 1
                """),
                {"pid": project_id, "name": char["name"]}
            ).fetchone()
            if existing:
                continue

            char_data = {
                "project_id": project_id,
                "name": char["name"],
                "role_type": char["role_type"],
                "identity": char.get("identity", ""),
                "faction": char.get("faction", ""),
                "appearance": char.get("appearance", ""),
                "personality": char.get("personality", ""),
                "background": char.get("background", ""),
                "motivation": char.get("motivation", ""),
                "weakness": char.get("weakness", ""),
                "secret": char.get("secret", ""),
                "dialogue_style": char.get("dialogue_style", ""),
                "arc": char.get("arc", ""),
                "mbti_primary": char.get("mbti_primary", ""),
                "mbti_secondary": char.get("mbti_secondary", ""),
                "chapters": char.get("chapters", ""),
                "custom_attributes": json.dumps(char.get("custom_attributes", []), ensure_ascii=False),
                "org_relations": "[]",
                "character_relations": "[]",  # 占位，后面统一建立关系
                "ai_notes": "",
                "status": char.get("status", "active"),
                "is_builtin": True,
            }

            columns = ", ".join(char_data.keys())
            placeholders = ", ".join([f":{k}" for k in char_data.keys()])
            db.execute(
                text(f"INSERT INTO characters ({columns}) VALUES ({placeholders})"),
                char_data
            )

        # 4. 建立内置角色之间的人物关系
        _build_builtin_relations(db, project_id)


def _build_builtin_relations(db: Session, project_id: int) -> None:
    """为内置角色建立人物关系（根据名字查找 ID）。"""
    # 获取所有内置角色的 id 和 name
    rows = db.execute(
        text("""
            SELECT id, name FROM characters
            WHERE project_id = :pid AND is_builtin = 1
        """),
        {"pid": project_id}
    ).fetchall()
    name_to_id = {row[1]: row[0] for row in rows}

    # 为每个有 character_relations 定义的角色更新关系字段
    all_chars = BUILTIN_COMMON_CHARACTERS + TEST_CHARACTERS
    for char in all_chars:
        relations = char.get("character_relations", [])
        if not relations:
            continue

        char_id = name_to_id.get(char["name"])
        if not char_id:
            continue

        # 将 target_name 转换为 target_id
        relations_with_id = []
        for rel in relations:
            target_id = name_to_id.get(rel["target_name"])
            if target_id:
                relations_with_id.append({
                    "target_id": target_id,
                    "relation_type": rel["relation_type"],
                    "depth": rel["depth"],
                    "effective_from": rel.get("effective_from"),
                    "expires_at": rel.get("expires_at"),
                })

        if relations_with_id:
            db.execute(
                text("""
                    UPDATE characters
                    SET character_relations = :relations
                    WHERE id = :id
                """),
                {
                    "id": char_id,
                    "relations": json.dumps(relations_with_id, ensure_ascii=False),
                }
            )

