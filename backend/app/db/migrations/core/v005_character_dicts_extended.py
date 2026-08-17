"""核心库迁移 v005 — 人物卡片扩展字典。

添加阵营、外貌特征、背景故事、隐藏秘密、人物弧光、属性名、
组织层级、AI备注标签、人物关系类型等字典。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """添加人物卡片扩展字典数据。"""
    _add_faction_dict(db)
    _add_appearance_dict(db)
    _add_background_dict(db)
    _add_secret_dict(db)
    _add_arc_dict(db)
    _add_attribute_name_dict(db)
    _add_org_position_dict(db)
    _add_ai_notes_dict(db)
    _add_relation_type_dict(db)


def _get_or_create_dict(db: Session, dict_code: str, dict_name: str, description: str, sort_order: int) -> int:
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
    for item_label, item_value, item_sort, remark in items:
        existing = db.execute(
            text("SELECT id FROM sys_dict_items WHERE dict_id = :dict_id AND item_value = :value"),
            {"dict_id": dict_id, "value": item_value},
        ).fetchone()
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


def _add_faction_dict(db: Session) -> None:
    """阵营/所属势力字典。"""
    dict_id = _get_or_create_dict(db, "character_faction", "阵营势力", "人物所属阵营/势力常用选项", 20)

    items = [
        ("主角团", "protagonist_group", 1, "主角所在的团队或阵营"),
        ("中立", "neutral", 2, "保持中立，不明确站队"),
        ("敌对势力", "antagonist_faction", 3, "与主角对立的阵营"),
        ("官方势力", "authority", 4, "政府、朝廷、官方机构"),
        ("江湖门派", "sect", 5, "武林门派、江湖势力"),
        ("商业家族", "merchant_family", 6, "以商业为主的家族势力"),
        ("黑帮/地下组织", "underworld", 7, "地下世界、黑帮组织"),
        ("宗教组织", "religion", 8, "教会、教派、宗教团体"),
        ("军方", "military", 9, "军队、军方势力"),
        ("学院/学派", "academy", 10, "学院、学派、研究机构"),
        ("散修/自由人", "freelance", 11, "无所属，自由行动"),
        ("皇室/王族", "royal", 12, "皇室、王族成员"),
        ("贵族世家", "noble", 13, "贵族家族、世家大族"),
        ("情报组织", "intelligence", 14, "情报机构、间谍组织"),
        ("杀手组织", "assassin_guild", 15, "刺客联盟、杀手公会"),
        ("商会", "merchant_guild", 16, "商人联盟、商会"),
        ("公会", "guild", 17, "冒险者公会、佣兵公会"),
        ("反叛军", "rebellion", 18, "反抗军、起义军"),
        ("魔族/妖族", "demon", 19, "魔族、妖族等非人种族"),
        ("神族/仙族", "divine", 20, "神族、仙族等超凡存在"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_appearance_dict(db: Session) -> None:
    """外貌特征关键字字典。"""
    dict_id = _get_or_create_dict(db, "character_appearance", "外貌特征", "外貌特征关键字，可多选组合", 21)

    items = [
        ("高瘦", "tall_thin", 1, "身材高大瘦削"),
        ("矮胖", "short_fat", 2, "身材矮小肥胖"),
        ("健美", "muscular", 3, "身材健硕、肌肉发达"),
        ("娇小", "petite", 4, "身材娇小玲珑"),
        ("长发及腰", "long_hair", 5, "头发很长"),
        ("短发利落", "short_hair", 6, "短发、干净利落"),
        ("白发", "white_hair", 7, "白色或银白色头发"),
        ("红发", "red_hair", 8, "红色或火红色头发"),
        ("黑发", "black_hair", 9, "黑色头发"),
        ("金发", "blonde", 10, "金色头发"),
        ("戴眼镜", "glasses", 11, "戴眼镜"),
        ("有伤疤", "scar", 12, "脸上或身上有明显伤疤"),
        ("戴面具", "mask", 13, "常年戴着面具"),
        ("穿长袍", "robe", 14, "常穿长袍"),
        ("穿西装", "suit", 15, "常穿西装"),
        ("穿军装", "military_uniform", 16, "常穿军装"),
        ("气质清冷", "cold_aura", 17, "气质清冷、疏离感强"),
        ("气质温润", "gentle_aura", 18, "气质温润、平易近人"),
        ("眼神锐利", "sharp_eyes", 19, "眼神锐利逼人"),
        ("笑容温暖", "warm_smile", 20, "笑容温暖有感染力"),
        ("声音低沉", "deep_voice", 21, "声音低沉磁性"),
        ("声音清冷", "cold_voice", 22, "声音清冷淡漠"),
        ("左手戴表", "watch", 23, "左手戴手表"),
        ("戴戒指", "ring", 24, "戴戒指"),
        ("戴耳环", "earring", 25, "戴耳环"),
        ("拄拐杖", "cane", 26, "拄着拐杖"),
        ("佩剑", "sword", 27, "腰间佩剑"),
        ("驼背", "hunchback", 28, "身形佝偻"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_background_dict(db: Session) -> None:
    """背景故事关键字字典。"""
    dict_id = _get_or_create_dict(db, "character_background", "背景故事", "背景故事关键字标签，可多选", 22)

    items = [
        ("孤儿", "orphan", 1, "从小失去父母，由他人抚养或独自长大"),
        ("名门之后", "noble_birth", 2, "出身名门望族，家世显赫"),
        ("寒门出身", "humble_birth", 3, "出身贫寒，靠自己努力"),
        ("皇室血脉", "royal_blood", 4, "拥有皇室血统"),
        ("师徒传承", "master_disciple", 5, "师从某位高人，继承衣钵"),
        ("家道中落", "family_decline", 6, "家族曾经辉煌，后来败落"),
        ("穿越者", "transmigrated", 7, "从现代或异世界穿越而来"),
        ("重生者", "reincarnated", 8, "带着前世记忆重生"),
        ("混血", "mixed_blood", 9, "两种不同种族的混血"),
        ("天才", "genius", 10, "天生就拥有超越常人的天赋"),
        ("废柴", "trash", 11, "被认为是废柴，实际有隐情"),
        ("隐世高手", "hidden_master", 12, "表面普通，实则深藏不露"),
        ("复仇者", "avenger", 13, "背负血海深仇，一心复仇"),
        ("失忆", "amnesia", 14, "失去了过去的记忆"),
        ("被诅咒", "cursed", 15, "身上带有某种诅咒"),
        ("天选之人", "chosen_one", 16, "被命运选中的人"),
        ("实验体", "experiment", 17, "曾经是实验对象"),
        ("私生子/女", "illegitimate", 18, "非婚生子女"),
        ("养女/养子", "adopted", 19, "被收养的孩子"),
        ("逃亡者", "fugitive", 20, "被追杀，一直在逃亡"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_secret_dict(db: Session) -> None:
    """隐藏秘密关键字字典。"""
    dict_id = _get_or_create_dict(db, "character_secret", "隐藏秘密", "人物隐藏的秘密标签，可多选", 23)

    items = [
        ("真实身份", "true_identity", 1, "表面身份是假的，有真实身份"),
        ("双重人格", "split_personality", 2, "有双重或多重人格"),
        ("卧底", "undercover", 3, "潜伏在敌方阵营的卧底"),
        ("性别伪装", "gender_disguise", 4, "女扮男装或男扮女装"),
        ("暗恋某人", "secret_love", 5, "偷偷喜欢着某个人"),
        ("身世之谜", "origin_mystery", 6, "自己的身世是个谜"),
        ("身患绝症", "terminal_illness", 7, "得了不治之症，时日无多"),
        ("武功尽失", "powerless", 8, "失去了修为/能力，但装作没事"),
        ("弑亲之罪", "kinslayer", 9, "曾经杀死过自己的亲人"),
        ("背叛过挚友", "betrayal", 10, "曾经背叛过最好的朋友"),
        ("非人类", "not_human", 11, "表面是人，实际不是人类"),
        ("穿越者身份", "transmigrator_secret", 12, "穿越者的身份不能暴露"),
        ("重生者身份", "reincarnator_secret", 13, "重生者的身份不能暴露"),
        ("系统拥有者", "system_owner", 14, "拥有系统/金手指"),
        ("秘密任务", "secret_mission", 15, "正在执行一项秘密任务"),
        ("私生子/女身份", "illegitimate_secret", 16, "私生子/女的身份是秘密"),
        ("被毁容", "disfigured", 17, "容貌被毁，用面具或易容遮盖"),
        ("失明/失聪", "disabled", 18, "有不为人知的残疾"),
        ("与敌人有染", "enemy_affair", 19, "与敌方人物有秘密联系"),
        ("宝藏秘密", "treasure_secret", 20, "知道某个宝藏的秘密"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_arc_dict(db: Session) -> None:
    """人物弧光类型字典。"""
    dict_id = _get_or_create_dict(db, "character_arc", "人物弧光", "人物成长变化的类型，可多选", 24)

    items = [
        ("成长弧", "growth", 1, "从弱小到强大，能力与心性同步成长"),
        ("堕落弧", "fall", 2, "从正义善良走向黑暗堕落"),
        ("救赎弧", "redemption", 3, "从罪恶中走出来，寻求救赎"),
        ("觉醒弧", "awakening", 4, "从麻木/平凡中觉醒，认清真相"),
        ("黑化弧", "dark_turn", 5, "因某种刺激从白转黑"),
        ("洗白弧", "white_turn", 6, "反派被感化或洗白"),
        ("迷失弧", "lost", 7, "在过程中迷失自我"),
        ("找回自我弧", "find_self", 8, "重新找回真正的自己"),
        ("信念崩塌弧", "belief_crash", 9, "一直坚信的东西被打破"),
        ("信念重建弧", "belief_rebuild", 10, "信念崩塌后重建新的信念"),
        ("牺牲弧", "sacrifice", 11, "最终为了某事牺牲自己"),
        ("传承弧", "legacy", 12, "将自己的一切传承给下一代"),
        ("复仇弧", "revenge", 13, "从受害者到复仇者的转变"),
        ("放下弧", "let_go", 14, "从执着到放下的释然"),
        ("责任弧", "responsibility", 15, "从不负责任到承担责任"),
        ("孤独弧", "loneliness", 16, "从热闹喧嚣走向孤独"),
        ("归宿弧", "belonging", 17, "从漂泊流浪到找到归宿"),
        ("变强弧", "power_up", 18, "纯粹的力量提升型成长"),
        ("心性成长弧", "maturity", 19, "心智从不成熟到成熟"),
        ("身份转变弧", "identity_shift", 20, "身份/立场发生根本转变"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_attribute_name_dict(db: Session) -> None:
    """自定义属性名称常用字典。"""
    dict_id = _get_or_create_dict(db, "attribute_name", "属性名称", "自定义属性常用名称", 25)

    items = [
        ("武功", "kung_fu", 1, "武功/修为等级"),
        ("内力", "inner_force", 2, "内力/真气/灵力"),
        ("功法", "cultivation_method", 3, "修炼功法/秘籍"),
        ("宝物", "treasure", 4, "随身宝物/神器"),
        ("技能", "skill", 5, "特殊技能/能力"),
        ("装备", "equipment", 6, "装备/武器"),
        ("异能", "superpower", 7, "超能力/异能"),
        ("职称", "title", 8, "职位/头衔/称号"),
        ("身份", "identity", 9, "特殊身份"),
        ("财富", "wealth", 10, "财产/财富值"),
        ("势力", "influence", 11, "势力/影响力"),
        ("声望", "reputation", 12, "声望/名望"),
        ("魅力", "charm", 13, "魅力值"),
        ("智力", "intelligence", 14, "智力/谋略"),
        ("体质", "constitution", 15, "体质/根骨"),
        ("悟性", "comprehension", 16, "悟性/领悟力"),
        ("气运", "fortune", 17, "气运/运气"),
        ("心魔", "inner_demon", 18, "心魔/执念"),
        ("道心", "dao_heart", 19, "道心/心境"),
        ("血脉", "bloodline", 20, "血脉/血统"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_org_position_dict(db: Session) -> None:
    """组织职位/层级字典。"""
    dict_id = _get_or_create_dict(db, "org_position", "组织职位", "组织内部职位层级，通用模板", 26)

    items = [
        ("盟主/掌门", "leader", 1, "最高领导者"),
        ("副盟主/副掌门", "deputy_leader", 2, "第二号人物"),
        ("长老", "elder", 3, "长老/元老级人物"),
        ("堂主/殿主", "hall_master", 4, "分堂/分殿负责人"),
        ("护法", "guardian", 5, "护法/守护者"),
        ("执事", "deacon", 6, "执事/管事"),
        ("核心弟子", "core_disciple", 7, "核心成员/核心弟子"),
        ("内门弟子", "inner_disciple", 8, "内门成员"),
        ("外门弟子", "outer_disciple", 9, "外门成员"),
        ("杂役", "servant", 10, "杂役/下人"),
        ("客卿", "guest_elder", 11, "客卿/客座长老"),
        ("供奉", "enshrined", 12, "供奉/护国法师"),
        ("卧底", "spy", 13, "卧底/内奸"),
        ("堂主夫人", "madam", 14, "首领的夫人/丈夫"),
        ("少盟主", "young_master", 15, "少主/继承人"),
        ("总管", "steward", 16, "大总管/管家"),
        ("军师", "strategist", 17, "军师/谋士"),
        ("医师", "healer", 18, "医师/药师"),
        ("情报负责人", "intel_head", 19, "情报部门负责人"),
        ("执法队长", "enforcer", 20, "执法/纪律部门负责人"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_ai_notes_dict(db: Session) -> None:
    """AI 一致性备注关键字字典。"""
    dict_id = _get_or_create_dict(db, "ai_notes", "AI一致性备注", "AI生成时需注意的一致性标签，可多选", 27)

    items = [
        ("称呼固定", "fixed_address", 1, "对特定人的称呼固定不变"),
        ("口癖固定", "speech_quirk", 2, "有固定的口头禅或语气词"),
        ("第一人称固定", "first_person", 3, "自称固定（如本座、贫道、我）"),
        ("性格极端冷静", "ultra_calm", 4, "极端冷静，几乎不流露情绪"),
        ("说话简洁", "concise_speech", 5, "话少，能用一个字不说两个字"),
        ("说话绕弯", "roundabout", 6, "说话喜欢绕弯子，不直接"),
        ("绝对理性", "absolute_rational", 7, "做决定绝对理性，不受感情影响"),
        ("极度护短", "protective", 8, "对自己人极度护短"),
        ("讨厌谎言", "hates_lying", 9, "厌恶被欺骗和谎言"),
        ("信守承诺", "keeps_promises", 10, "一诺千金，说到做到"),
        ("有恩必报", "grateful", 11, "滴水之恩涌泉相报"),
        ("有仇必报", "vengeful", 12, "有仇必报，心狠手辣"),
        ("尊重强者", "respects_strong", 13, "尊重强者，蔑视弱者"),
        ("怜悯弱者", "sympathizes_weak", 14, "同情弱者，乐于助人"),
        ("不杀生", "no_kill", 15, "不轻易杀人，有底线"),
        ("杀伐果断", "ruthless", 16, "杀伐果断，毫不留情"),
        ("爱财如命", "loves_money", 17, "极其贪财，见钱眼开"),
        ("好美色", "loves_beauty", 18, "贪恋美色，风流成性"),
        ("洁癖", "clean_freak", 19, "有洁癖，极度爱干净"),
        ("路痴", "directionless", 20, "方向感极差，容易迷路"),
        ("吃货", "foodie", 21, "喜欢美食，吃货属性"),
        ("嗜睡", "sleepy", 22, "贪睡，随时能睡着"),
        ("怕麻烦", "hates_trouble", 23, "怕麻烦，多一事不如少一事"),
        ("傲娇", "tsundere", 24, "口是心非，傲娇属性"),
        ("腹黑", "scheming", 25, "外表温和内心腹黑"),
        ("天然黑", "naturally_evil", 26, "天然黑，无意识地坑人"),
        ("反差萌", "contrast_cute", 27, "外表与内在有巨大反差"),
        ("玻璃心", "fragile", 28, "内心脆弱，容易受伤"),
        ("死傲娇", "hard_tsundere", 29, "极度傲娇，死不承认"),
        ("老顽童", "old_kid", 30, "年纪大但心态像小孩"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_relation_type_dict(db: Session) -> None:
    """人物关系类型字典。"""
    dict_id = _get_or_create_dict(db, "relation_type", "人物关系类型", "人物之间的关系类型", 28)

    items = [
        ("父子", "father_son", 1, "父亲与儿子"),
        ("母女", "mother_daughter", 2, "母亲与女儿"),
        ("兄弟", "brothers", 3, "兄弟关系"),
        ("姐妹", "sisters", 4, "姐妹关系"),
        ("师徒", "master_disciple", 5, "师父与徒弟"),
        ("恋人", "lovers", 6, "情侣/恋人关系"),
        ("夫妻", "spouses", 7, "夫妻/配偶"),
        ("挚友", "best_friend", 8, "最好的朋友"),
        ("盟友", "ally", 9, "同盟/合作关系"),
        ("仇敌", "enemy", 10, "死敌/仇敌"),
        ("竞争对手", "rival", 11, "竞争对手"),
        ("上下级", "superior_subordinate", 12, "上司与下属"),
        ("主仆", "master_servant", 13, "主人与仆人"),
        ("养父子", "adoptive", 14, "养父/养母与养子/养女"),
        ("叔侄", "uncle_nephew", 15, "叔叔/伯伯与侄子/侄女"),
        ("祖孙", "grandparent_grandchild", 16, "祖父母与孙辈"),
        ("同门", "same_school", 17, "同门师兄弟/师姐妹"),
        ("暧昧", "ambiguous", 18, "关系暧昧，未明说"),
        ("单恋", "unrequited", 19, "单相思"),
        ("亏欠", "indebted", 20, "一方对另一方有亏欠"),
        ("救命之恩", "life_saver", 21, "救命恩人"),
        ("杀亲之仇", "family_killer", 22, "有杀亲之仇"),
        ("知己", "soulmate_platonic", 23, "精神知己，柏拉图式"),
        ("义兄弟", "sworn_brothers", 24, "结义兄弟/姐妹"),
        ("其他", "other", 25, "其他关系"),
    ]
    _add_dict_items(db, dict_id, items)
