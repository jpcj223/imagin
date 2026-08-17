"""核心库迁移 v004 — 人物卡片相关字典。

添加 MBTI 类型、人物身份、动机、弱点、对白风格等字典，
用于人物卡片页面的快速选择。
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """添加人物卡片相关字典数据。"""
    _add_mbti_dict(db)
    _add_character_identity_dict(db)
    _add_character_motivation_dict(db)
    _add_character_weakness_dict(db)
    _add_dialogue_style_dict(db)
    _add_personality_trait_dict(db)


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
        existing = db.execute(
            text("SELECT id FROM sys_dict_items WHERE dict_id = :dict_id AND item_value = :value"),
            {"dict_id": dict_id, "value": item_value},
        ).fetchone()
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


def _add_mbti_dict(db: Session) -> None:
    """添加 MBTI 16 型人格字典。"""
    dict_id = _get_or_create_dict(db, "mbti_type", "MBTI 类型", "MBTI 16 型人格分类", 10)

    items = [
        ("INTJ 建筑师", "INTJ", 1, "富有想象力和战略性的思想家，一切皆在计划之中"),
        ("INTP 逻辑学家", "INTP", 2, "具有创造力的发明家，对知识有着止不住的渴望"),
        ("ENTJ 指挥官", "ENTJ", 3, "大胆、富有想象力且意志强大的领导者，总能找到或创造解决办法"),
        ("ENTP 辩论家", "ENTP", 4, "聪明好奇的思想者，不会放弃任何智力上的挑战"),
        ("INFJ 提倡者", "INFJ", 5, "安静而神秘，同时鼓舞人心且不知疲倦的理想主义者"),
        ("INFP 调停者", "INFP", 6, "诗意、善良的利他主义者，总是热情地为正当理由提供帮助"),
        ("ENFJ 主人公", "ENFJ", 7, "富有魅力且鼓舞人心的领导者，有使听众着迷的能力"),
        ("ENFP 竞选者", "ENFP", 8, "热情、有创造力、乐观的社交达人，总能找到理由微笑"),
        ("ISTJ 物流师", "ISTJ", 9, "实际且注重事实的个人，可靠性不容怀疑"),
        ("ISFJ 守卫者", "ISFJ", 10, "非常专注且温暖的守护者，时刻准备着保护爱着的人们"),
        ("ESTJ 总经理", "ESTJ", 11, "出色的管理者，在管理事情或人的方面无与伦比"),
        ("ESFJ 执政官", "ESFJ", 12, "极有同情心、爱社交、受欢迎的人，总是热心帮助别人"),
        ("ISTP 鉴赏家", "ISTP", 13, "大胆而实际的实验家，擅长使用各种工具"),
        ("ISFP 探险家", "ISFP", 14, "灵活、有魅力的艺术家，时刻准备着探索和体验新鲜事物"),
        ("ESTP 企业家", "ESTP", 15, "聪明、精力充沛且善于观察的人，真正享受生活在边缘"),
        ("ESFP 表演者", "ESFP", 16, "自发的、精力充沛的表演者，生活在他们周围永不乏味"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_character_identity_dict(db: Session) -> None:
    """添加人物身份/职业常用选项字典。"""
    dict_id = _get_or_create_dict(db, "character_identity", "人物身份", "人物职业/身份常用选项", 11)

    items = [
        ("学生", "student", 1, "大中小学生"),
        ("教师", "teacher", 2, "老师、教授、导师"),
        ("医生", "doctor", 3, "医生、护士、医疗工作者"),
        ("警察", "police", 4, "警察、刑警、特警"),
        ("军人", "soldier", 5, "士兵、军官、将军"),
        ("程序员", "programmer", 6, "程序员、工程师、技术宅"),
        ("商人", "businessman", 7, "企业家、老板、投资人"),
        ("律师", "lawyer", 8, "律师、检察官、法官"),
        ("记者", "reporter", 9, "记者、编辑、媒体人"),
        ("艺术家", "artist", 10, "画家、音乐家、作家"),
        ("侦探", "detective", 11, "私家侦探、调查员"),
        ("杀手", "assassin", 12, "杀手、刺客、雇佣兵"),
        ("道士", "taoist", 13, "道士、法师、修行者"),
        ("修士", "monk", 14, "和尚、修士、神职人员"),
        ("贵族", "noble", 15, "王子、公主、公爵等贵族"),
        ("皇室", "royal", 16, "皇帝、皇后、王室成员"),
        ("侠客", "swordsman", 17, "侠客、剑客、游侠"),
        ("魔法师", "mage", 18, "魔法师、巫师、术士"),
        ("炼金术士", "alchemist", 19, "炼金术士、科学家"),
        ("奴隶", "slave", 20, "奴隶、仆人、下人"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_character_motivation_dict(db: Session) -> None:
    """添加人物核心动机常用选项字典。"""
    dict_id = _get_or_create_dict(db, "character_motivation", "核心动机", "人物核心动机常用选项", 12)

    items = [
        ("复仇", "revenge", 1, "为亲人/爱人/自己复仇"),
        ("守护", "protect", 2, "守护重要的人或事物"),
        ("寻找真相", "seek_truth", 3, "追寻某个秘密或事件的真相"),
        ("权力", "power", 4, "追求权力、地位或掌控一切"),
        ("财富", "wealth", 5, "追求金钱、财富或资源"),
        ("自由", "freedom", 6, "追求自由，摆脱束缚"),
        ("救赎", "redemption", 7, "为过去的罪行赎罪"),
        ("证明自己", "prove_self", 8, "向他人或自己证明价值"),
        ("寻找归宿", "find_home", 9, "寻找归属感、找到属于自己的地方"),
        ("保护世界", "save_world", 10, "拯救世界、维护和平"),
        ("毁灭世界", "destroy_world", 11, "毁灭世界、建立新秩序"),
        ("爱情", "love", 12, "为了爱情，与爱人在一起"),
        ("友情", "friendship", 13, "为了朋友，兄弟情义"),
        ("亲情", "family", 14, "为了家人，保护亲人"),
        ("求知", "knowledge", 15, "追求知识、探索未知"),
        ("永生", "immortality", 16, "追求永生、长生不老"),
        ("复国", "restore_country", 17, "复兴国家、重建家园"),
        ("逃跑", "escape", 18, "逃避追杀、逃离过去"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_character_weakness_dict(db: Session) -> None:
    """添加人物弱点/缺陷常用选项字典。"""
    dict_id = _get_or_create_dict(db, "character_weakness", "人物弱点", "人物弱点/缺陷常用选项", 13)

    items = [
        ("过于自信", "overconfident", 1, "自负、骄傲、低估对手"),
        ("优柔寡断", "indecisive", 2, "犹豫不决、难以做出决定"),
        ("冲动鲁莽", "impulsive", 3, "做事冲动、不计后果"),
        ("心软善良", "too_kind", 4, "过于善良、容易被利用"),
        ("多疑猜忌", "distrustful", 5, "不信任任何人、猜忌心重"),
        ("固执己见", "stubborn", 6, "固执、不听劝告"),
        ("贪婪", "greedy", 7, "贪财、贪吃、贪婪无度"),
        ("好色", "lustful", 8, "好色、容易被美色迷惑"),
        ("懦弱", "cowardly", 9, "胆小怕事、遇到危险就逃"),
        ("傲慢", "arrogant", 10, "傲慢无礼、看不起别人"),
        ("孤独", "lonely", 11, "害怕孤独、渴望陪伴"),
        ("过去的阴影", "past_trauma", 12, "被过去的创伤困扰"),
        ("重要的人", "loved_one", 13, "重要的人是软肋"),
        ("身体缺陷", "physical_flaw", 14, "身体有残疾或疾病"),
        ("心理缺陷", "mental_flaw", 15, "心理问题、精神不稳定"),
        ("理想主义", "idealistic", 16, "过于理想化、不切实际"),
        ("缺乏经验", "inexperienced", 17, "经验不足、容易受骗"),
        ("嘴硬心软", "tough_soft", 18, "嘴上强硬、内心柔软"),
        ("控制欲强", "control_freak", 19, "控制欲过强、容不得意外"),
        ("完美主义", "perfectionist", 20, "追求完美、容不得瑕疵"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_dialogue_style_dict(db: Session) -> None:
    """添加对白风格常用选项字典。"""
    dict_id = _get_or_create_dict(db, "dialogue_style", "对白风格", "人物对白风格常用选项", 14)

    items = [
        ("简洁冷淡", "cold_concise", 1, "话少、简洁、不带感情"),
        ("幽默风趣", "humorous", 2, "说话幽默、喜欢开玩笑"),
        ("文绉绉", "literary", 3, "说话文雅、喜欢用典故"),
        ("粗俗市井", "vulgar", 4, "说话粗俗、接地气"),
        ("温柔体贴", "gentle", 5, "语气温柔、体贴入微"),
        ("傲娇", "tsundere", 6, "嘴上不饶人、心里很在意"),
        ("腹黑", "scheming", 7, "表面温和、内心算计"),
        ("霸气威严", "domineering", 8, "说话有气势、威严十足"),
        ("怯懦胆小", "timid", 9, "说话小声、唯唯诺诺"),
        ("古灵精怪", "mischievous", 10, "说话调皮、喜欢捉弄人"),
        ("老成持重", "mature", 11, "说话稳重、像个长辈"),
        ("直来直去", "straightforward", 12, "说话直接、不绕弯子"),
        ("阴阳怪气", "sarcastic", 13, "说话带刺、喜欢讽刺"),
        ("口头禅多", "catchphrase", 14, "有标志性的口头禅"),
        ("方言口音", "dialect", 15, "说话带方言口音"),
        ("慢条斯理", "slow_paced", 16, "说话慢悠悠、不慌不忙"),
    ]
    _add_dict_items(db, dict_id, items)


def _add_personality_trait_dict(db: Session) -> None:
    """添加性格特征常用选项字典（多选）。"""
    dict_id = _get_or_create_dict(db, "personality_trait", "性格特征", "人物性格特征标签（可多选）", 15)

    items = [
        ("冷静", "calm", 1, "遇事冷静、不慌不忙"),
        ("热情", "passionate", 2, "热情开朗、充满活力"),
        ("内向", "introverted", 3, "沉默寡言、不善社交"),
        ("外向", "extroverted", 4, "善于社交、朋友众多"),
        ("细心", "careful", 5, "观察细致、注意细节"),
        ("粗心", "careless", 6, "大大咧咧、容易忽略细节"),
        ("善良", "kind", 7, "心地善良、乐于助人"),
        ("邪恶", "evil", 8, "心狠手辣、不择手段"),
        ("勇敢", "brave", 9, "勇敢无畏、敢于冒险"),
        ("胆小", "cowardly", 10, "胆小怕事、畏首畏尾"),
        ("聪明", "smart", 11, "智商高、反应快"),
        ("单纯", "naive", 12, "心思单纯、容易相信别人"),
        ("腹黑", "scheming", 13, "内心有算计、表面看不出来"),
        ("傲娇", "tsundere", 14, "口是心非、外冷内热"),
        ("温柔", "gentle", 15, "性格温柔、待人和善"),
        ("暴躁", "irritable", 16, "脾气暴躁、容易发怒"),
        ("乐观", "optimistic", 17, "积极乐观、充满希望"),
        ("悲观", "pessimistic", 18, "消极悲观、往坏处想"),
        ("固执", "stubborn", 19, "性格固执、听不进劝"),
        ("随和", "easygoing", 20, "随遇而安、好相处"),
    ]
    _add_dict_items(db, dict_id, items)
