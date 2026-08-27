"""核心库迁移 v019 — 组织详情预设字典（地点/口号/背景/目标/隐藏设定）。"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def _ensure_dict(db: Session, code: str, name: str, desc: str) -> int:
    result = db.execute(
        text("SELECT id FROM sys_dictionaries WHERE dict_code = :code"),
        {"code": code},
    ).fetchone()
    if not result:
        db.execute(
            text(
                """
                INSERT INTO sys_dictionaries
                (dict_code, dict_name, description, status, created_at)
                VALUES (:code, :name, :desc, 'active', datetime('now'))
                """
            ),
            {"code": code, "name": name, "desc": desc},
        )
        result = db.execute(
            text("SELECT id FROM sys_dictionaries WHERE dict_code = :code"),
            {"code": code},
        ).fetchone()
    return result[0]


def _insert_items(db: Session, dict_id: int, items: list[tuple]) -> None:
    db.execute(
        text("DELETE FROM sys_dict_items WHERE dict_id = :dict_id"),
        {"dict_id": dict_id},
    )
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


def upgrade(db: Session) -> None:
    """新增 5 个组织详情预设字典。"""

    # ============================================================
    # 1. 地点 / 势力范围
    # ============================================================
    dict_id = _ensure_dict(db, "org_location", "组织地点预设", "组织所在地/势力范围的常用地名预设")

    items = [
        # 修仙/武侠
        ("昆仑山", "kunlun_mountain", 101, "active", "适用类型: sect"),
        ("峨眉山", "emei_mountain", 102, "active", "适用类型: sect"),
        ("武当山", "wudang_mountain", 103, "active", "适用类型: sect"),
        ("少林寺", "shaolin_temple", 104, "active", "适用类型: sect"),
        ("青城山", "qingcheng_mountain", 105, "active", "适用类型: sect"),
        ("华山", "huashan_mountain", 106, "active", "适用类型: sect"),
        ("蓬莱仙岛", "penglai_island", 107, "active", "适用类型: sect"),
        ("南疆十万大山", "southern_mountains", 108, "active", "适用类型: sect,gang"),
        ("西域大漠", "western_desert", 109, "active", "适用类型: sect,gang"),
        ("东海之滨", "east_sea_coast", 110, "active", "适用类型: sect,merchant_guild"),

        # 家族/世家
        ("京城/帝都", "capital_city", 201, "active", "适用类型: family_clan,government,military"),
        ("江南水乡", "jiangnan_region", 202, "active", "适用类型: family_clan,merchant_guild"),
        ("燕北苦寒之地", "yanbei_region", 203, "active", "适用类型: family_clan,military"),
        ("蜀中盆地", "shu_basin", 204, "active", "适用类型: family_clan,sect"),
        ("荆州/中原腹地", "central_plains", 205, "active", "适用类型: family_clan,merchant_guild"),

        # 现代/都市
        ("北京", "beijing", 301, "active", "适用类型: company,government,military,media,research_institute,hospital,academy"),
        ("上海", "shanghai", 302, "active", "适用类型: company,merchant_guild,media,hospital,academy"),
        ("深圳", "shenzhen", 303, "active", "适用类型: company,research_institute,tech_company"),
        ("杭州", "hangzhou", 304, "active", "适用类型: company,internet"),
        ("广州", "guangzhou", 305, "active", "适用类型: company,merchant_guild,hospital"),
        ("香港", "hong_kong", 306, "active", "适用类型: company,mafia,merchant_guild,media"),
        ("硅谷", "silicon_valley", 307, "active", "适用类型: company,research_institute"),
        ("华尔街", "wall_street", 308, "active", "适用类型: company,merchant_guild"),

        # 黑帮/社团
        ("地下黑市", "black_market", 401, "active", "适用类型: mafia,gang,thieves_guild"),
        ("码头/港口", "dock_area", 402, "active", "适用类型: mafia,merchant_guild"),
        ("老城/旧街区", "old_town", 403, "active", "适用类型: mafia,gang"),
        ("废弃工业区", "abandoned_factory", 404, "active", "适用类型: mafia,gang,mysterious"),

        # 奇幻/西方
        ("王都/帝都", "royal_capital", 501, "active", "适用类型: kingdom,church,knight_order,mage_guild"),
        ("精灵森林", "elf_forest", 502, "active", "适用类型: sect,mysterious"),
        ("矮人山脉", "dwarf_mountain", 503, "active", "适用类型: knight_order,merchant_guild"),
        ("地下城", "underground_city", 504, "active", "适用类型: thieves_guild,mafia,mysterious"),
        ("魔法塔", "magic_tower", 505, "active", "适用类型: mage_guild,mysterious"),
        ("冒险者公会总部", "adventurer_hq", 506, "active", "适用类型: adventurer_guild"),
        ("光明神殿", "light_temple", 507, "active", "适用类型: church,knight_order"),
        ("黑暗深渊", "dark_abyss", 508, "active", "适用类型: mysterious,mysterious"),

        # 通用
        ("偏远小镇", "remote_town", 901, "active", "适用类型: independent,other"),
        ("边境要塞", "border_fortress", 902, "active", "适用类型: military,knight_order"),
        ("荒岛/孤岛", "isolated_island", 903, "active", "适用类型: mysterious,independent"),
        ("虚空/异次元", "void_dimension", 904, "active", "适用类型: mysterious"),
    ]
    _insert_items(db, dict_id, items)

    # ============================================================
    # 2. 宗旨 / 口号
    # ============================================================
    dict_id = _ensure_dict(db, "org_slogan", "组织宗旨口号", "组织宗旨/口号的常用预设")

    items = [
        # 修仙门派
        ("替天行道，除魔卫道", "tianti_xingdao", 101, "active", "适用类型: sect,knight_order"),
        ("道法自然，无为而治", "dao_faziran", 102, "active", "适用类型: sect"),
        ("众生皆苦，普度世人", "pusheng_shiren", 103, "active", "适用类型: sect,church"),
        ("侠之大者，为国为民", "xia_zhidazhe", 104, "active", "适用类型: sect,gang"),
        ("逍遥天地间，不问世事", "xiaoyao_tiandi", 105, "active", "适用类型: sect,independent"),
        ("传承道统，光大门楣", "chuancheng_daotong", 106, "active", "适用类型: sect,family_clan"),

        # 家族/世家
        ("自强不息，厚德载物", "ziqiang_buxi", 201, "active", "适用类型: family_clan,company"),
        ("诚信为本，义字当先", "chengxin_wei ben", 202, "active", "适用类型: family_clan,merchant_guild,company"),
        ("血脉荣耀，不容有失", "xuemai_rongyao", 203, "active", "适用类型: family_clan"),
        ("百年世家，稳如磐石", "bainian_shijia", 204, "active", "适用类型: family_clan"),

        # 帮派/江湖
        ("有福同享，有难同当", "youfu_tongxiang", 301, "active", "适用类型: gang,mafia,adventurer_guild"),
        ("人不犯我，我不犯人", "ren_bu fan wo", 302, "active", "适用类型: gang,mafia"),
        ("兄弟齐心，其利断金", "xiongdi_qixin", 303, "active", "适用类型: gang,mafia"),
        ("劫富济贫，替天行道", "jiefu_jipin", 304, "active", "适用类型: gang,thieves_guild"),
        ("拿人钱财，与人消灾", "nareng_qiancai", 305, "active", "适用类型: assassin_guild,mercenary"),

        # 商会/商业
        ("诚信经营，童叟无欺", "chengxin_jingying", 401, "active", "适用类型: merchant_guild,company"),
        ("货通天下，利射四海", "huotong_tianxia", 402, "active", "适用类型: merchant_guild"),
        ("顾客就是上帝", "customer_god", 403, "active", "适用类型: company,hospital"),
        ("科技创新，改变世界", "tech_innovation", 404, "active", "适用类型: company,research_institute"),

        # 杀手/情报
        ("一击必杀，绝不失手", "yiji_bisha", 501, "active", "适用类型: assassin_guild"),
        ("只有死人才能保守秘密", "dead_keep_secret", 502, "active", "适用类型: assassin_guild,intelligence"),
        ("无所不知，无所不晓", "wusuo_buzhi", 503, "active", "适用类型: intelligence"),
        ("千里之外，决胜于帷幄", "qianli_zhiwai", 504, "active", "适用类型: intelligence,strategist"),

        # 军队/官方
        ("保家卫国，死而后已", "baojia_weiguo", 601, "active", "适用类型: military,knight_order,government"),
        ("军令如山，誓死不从", "junling_rushan", 602, "active", "适用类型: military,knight_order"),
        ("为人民服务", "serve_people", 603, "active", "适用类型: government,hospital,academy"),

        # 教会/信仰
        ("信仰即是力量", "faith_power", 701, "active", "适用类型: church"),
        ("光明永恒，黑暗退散", "light_eternal", 702, "active", "适用类型: church,knight_order"),
        ("神爱世人", "god_loves_world", 703, "active", "适用类型: church"),

        # 科研/学术
        ("求真求实，探索未知", "qiuzhen_qiushi", 801, "active", "适用类型: research_institute,academy"),
        ("知识就是力量", "knowledge_power", 802, "active", "适用类型: academy,research_institute,mage_guild"),
        ("学海无涯，天道酬勤", "xuehai_wuya", 803, "active", "适用类型: academy,school"),
    ]
    _insert_items(db, dict_id, items)

    # ============================================================
    # 3. 背景描述模板
    # ============================================================
    dict_id = _ensure_dict(db, "org_background", "组织背景模板", "组织背景描述的参考模板")

    items = [
        # 门派类
        ("千年古派", "sect_ancient", 101, "active",
         "适用类型: sect\n创建于千年前，开山祖师道法通玄，留下无数传说。门派历经数代兴衰，底蕴深厚，门下弟子遍布天下。虽不常出世，但每逢天下大乱必有传人出山。",
         ),
        ("新兴势力", "sect_new", 102, "active",
         "适用类型: sect,gang\n近数十年才崛起的新兴势力，门主天纵奇才，短短数十年便将门派发展壮大。因其行事风格激进，与老牌势力多有摩擦。",
         ),
        ("隐世传承", "sect_hidden", 103, "active",
         "适用类型: sect,mysterious\n隐居于深山秘境之中，不与外界往来。门规森严，弟子极少踏足尘世，但传承的功法极为古老神秘。",
         ),
        ("正邪之间", "sect_neutral", 104, "active",
         "适用类型: sect,gang\n亦正亦邪，行事全凭本心。不被正道所容，也不与邪派同流。门人行事风格独特，江湖评价两极分化。",
         ),

        # 家族类
        ("百年望族", "family_prestigious", 201, "active",
         "适用类型: family_clan\n传承数百年的世家大族，族中人才辈出，在朝野都有深远影响力。家族家规森严，注重血脉纯正。",
         ),
        ("新晋暴发", "family_new_rich", 202, "active",
         "适用类型: family_clan,merchant_guild\n近几十年才发迹的家族，凭借商业天赋或机缘巧合迅速积累财富。底蕴不足，但势头强劲。",
         ),
        ("没落世家", "family_declining", 203, "active",
         "适用类型: family_clan\n曾经显赫一时的世家，如今日渐没落。虽然架子还在，但内囊空虚，正面临前所未有的危机。",
         ),

        # 公司类
        ("行业巨头", "company_giant", 301, "active",
         "适用类型: company\n行业内的龙头企业，市场占有率极高，拥有强大的研发能力和销售网络。公司资金雄厚，人才济济。",
         ),
        ("创业新贵", "company_startup", 302, "active",
         "适用类型: company,research_institute\n成立不久的初创公司，凭借创新技术或独特商业模式迅速崛起，是资本市场的宠儿。",
         ),
        ("家族企业", "company_family", 303, "active",
         "适用类型: company,family_clan\n由家族掌控的企业，决策权集中在家族成员手中。企业文化带有浓厚的家族色彩。",
         ),

        # 黑帮/社团
        ("老牌社团", "mafia_old", 401, "active",
         "适用类型: mafia,gang\n传承几代人的老牌黑社会组织，势力根深蒂固，黑白两道都吃得开。行事风格老练，讲究规矩。",
         ),
        ("新兴帮派", "mafia_new", 402, "active",
         "适用类型: mafia,gang\n近年来崛起的新兴帮派，行事狠辣，扩张迅速。因为动了老牌势力的蛋糕，冲突不断。",
         ),
        ("义字当头", "mafia_honor", 403, "active",
         "适用类型: gang,mafia\n虽然混迹黑道，但讲究江湖道义，不欺凌弱小，不奸淫掳掠。在底层民众中口碑不错。",
         ),

        # 神秘组织
        ("隐秘存在", "mysterious_secret", 501, "active",
         "适用类型: mysterious\n没有人知道这个组织的具体情况，它的存在本身就是一个谜。只在历史的关键时刻若隐若现。",
         ),
        ("古老传承", "mysterious_ancient", 502, "active",
         "适用类型: mysterious,sect\n传承自上古时代的神秘组织，守护着某个不为人知的秘密。组织成员身份隐秘，行事低调。",
         ),

        # 科研/学术
        ("顶尖学府", "academy_top", 601, "active",
         "适用类型: academy,research_institute,school\n国内顶尖的学术机构，汇聚了各领域的精英学者。科研实力雄厚，培养了无数人才。",
         ),
        ("秘密实验室", "research_secret", 602, "active",
         "适用类型: research_institute,mysterious\n表面上是普通的科研机构，实际上在进行一些不为人知的秘密研究。",
         ),
    ]
    _insert_items(db, dict_id, items)

    # ============================================================
    # 4. 组织目标模板
    # ============================================================
    dict_id = _ensure_dict(db, "org_goal_template", "组织目标模板", "组织目标/发展方向的参考模板")

    items = [
        ("统一江湖/称霸武林", "goal_unify_world", 101, "active", "适用类型: sect,gang,mafia"),
        ("寻找传说中的至宝", "goal_find_treasure", 102, "active", "适用类型: sect,mysterious,merchant_guild"),
        ("守护某个秘密/传承", "goal_guard_secret", 103, "active", "适用类型: sect,mysterious,family_clan"),
        ("颠覆现有秩序", "goal_overthrow_order", 104, "active", "适用类型: gang,mafia,mysterious"),
        ("追求至高武道/大道", "goal_pursue_dao", 105, "active", "适用类型: sect,independent"),
        ("积累财富/富可敌国", "goal_wealth", 201, "active", "适用类型: merchant_guild,company,family_clan"),
        ("扩张势力/抢占市场", "goal_expansion", 202, "active", "适用类型: company,mafia,sect"),
        ("科技改变世界", "goal_tech_change", 203, "active", "适用类型: research_institute,company"),
        ("保家卫国/守护一方", "goal_protect", 301, "active", "适用类型: military,knight_order,sect"),
        ("传播信仰/普度众生", "goal_spread_faith", 302, "active", "适用类型: church,sect"),
        ("维持秩序/平衡各方", "goal_balance", 303, "active", "适用类型: government,intelligence,sect"),
        ("复仇/讨回血债", "goal_revenge", 401, "active", "适用类型: gang,family_clan,assassin_guild"),
        ("寻找真相/揭开谜团", "goal_truth", 402, "active", "适用类型: intelligence,mysterious,research_institute"),
        ("长生不老/永生不死", "goal_immortality", 403, "active", "适用类型: sect,mysterious,research_institute"),
        ("称霸世界/统治全球", "goal_dominate", 501, "active", "适用类型: kingdom,military,mafia,mysterious"),
        ("拯救世界/阻止灾难", "goal_save_world", 502, "active", "适用类型: knight_order,church,sect"),
        ("自由自在/逍遥快活", "goal_freedom", 503, "active", "适用类型: independent,adventurer_guild"),
    ]
    _insert_items(db, dict_id, items)

    # ============================================================
    # 5. 隐藏设定模板
    # ============================================================
    dict_id = _ensure_dict(db, "org_secret_template", "组织隐藏设定模板", "组织隐藏设定/暗线的参考模板")

    items = [
        ("内部有内奸/卧底", "secret_mole", 101, "active",
         "适用类型: sect,mafia,military,intelligence\n组织高层内部潜伏着其他势力的卧底，一直在泄露核心机密。",
         ),
        ("真实目的与表面不同", "secret_true_goal", 102, "active",
         "适用类型: mysterious,sect,church,intelligence\n组织对外宣称的目标只是幌子，真正的目的完全不同，甚至截然相反。",
         ),
        ("创建者还活着/在幕后操控", "secret_founder_alive", 103, "active",
         "适用类型: sect,family_clan,mysterious\n组织的创始人并没有死，而是一直在幕后操控一切，现任掌门/家主只是傀儡。",
         ),
        ("有致命的弱点/隐患", "secret_weakness", 104, "active",
         "适用类型: sect,company,mafia\n组织表面风光无限，实际上有一个致命的弱点，一旦暴露就会万劫不复。",
         ),
        ("在寻找某个东西/人", "secret_searching", 105, "active",
         "适用类型: sect,mysterious,merchant_guild\n组织一直在秘密寻找某样东西或某个人，为此不惜一切代价。",
         ),
        ("与某个神秘势力有勾结", "secret_alliance", 106, "active",
         "适用类型: government,mafia,sect,church\n组织暗地里与某个不为人知的势力有合作，互相利用。",
         ),
        ("组织已经被控制/渗透", "secret_infiltrated", 107, "active",
         "适用类型: sect,company,government,mafia\n组织高层已经被某个势力渗透控制，正在被牵着鼻子走而不自知。",
         ),
        ("有一个惊天秘密", "secret_big_secret", 108, "active",
         "适用类型: family_clan,sect,mysterious\n组织守护着一个足以颠覆世界的惊天秘密，只有最高层才知道真相。",
         ),
        ("核心成员有双重身份", "secret_double_identity", 109, "active",
         "适用类型: sect,mafia,intelligence,assassin_guild\n组织的核心成员拥有不为人知的双重身份，甚至可能是敌方的人。",
         ),
        ("组织正在走向灭亡", "secret_dying", 110, "active",
         "适用类型: family_clan,sect,company\n表面看似风光，实际上组织已经在走下坡路，内部问题重重，随时可能分崩离析。",
         ),
    ]
    _insert_items(db, dict_id, items)

    db.commit()
