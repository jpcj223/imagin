"""核心库迁移 v020 — 扩展组织背景模板字典，增加更多类型模板。"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """扩展 org_background 字典，增加更多背景模板。"""

    result = db.execute(
        text("SELECT id FROM sys_dictionaries WHERE dict_code = 'org_background'")
    ).fetchone()
    if not result:
        return
    dict_id = result[0]

    # 保留原有模板，新增更多模板
    # 新模板编号从 200 开始（原有最高 602）
    items = [
        # ===== 修仙/武侠新增 =====
        ("魔道邪派", "sect_evil", 105, "active",
         "适用类型: sect,gang\n被正道视为邪魔外道的门派，修炼的功法诡异霸道，行事乖张。虽然被正道排斥，但实力强横，门徒众多，在暗处掌控着不小的势力。",
         ),
        ("剑宗世家", "sect_sword", 106, "active",
         "适用类型: sect,family_clan\n以剑入道的剑道世家/门派，历代皆有剑道天才出世。门派剑法独步天下，门人行事磊落，在江湖中威望极高。",
         ),
        ("丹道宗门", "sect_alchemy", 107, "active",
         "适用类型: sect,merchant_guild\n以炼丹闻名天下的宗门，门人大多精通医术丹道。虽然战力不算顶尖，但因为手握丹药资源，各方势力都要给几分薄面。",
         ),
        ("佛门古刹", "sect_buddhist", 108, "active",
         "适用类型: sect,church\n传承千年的佛门圣地，寺中高僧辈出。佛法精深，慈悲为怀，但也有护法金刚之力。在乱世中常常救助百姓。",
         ),
        ("游侠联盟", "sect_roaming", 109, "active",
         "适用类型: sect,adventurer_guild,gang\n由江湖游侠自发组成的松散联盟，没有严格的门规。成员来去自由，但遇事时一呼百应，行侠仗义。",
         ),

        # ===== 家族/世家新增 =====
        ("将门之后", "family_military", 205, "active",
         "适用类型: family_clan,military\n世代从军的武将世家，家族子弟皆精通兵戈。家族在军中根基深厚，门生故吏遍布朝野。",
         ),
        ("书香门第", "family_scholar", 206, "active",
         "适用类型: family_clan,academy\n代代读书传家的书香门第，家族中科举入仕者众多。虽不掌兵权，但在士林和朝堂上影响力巨大。",
         ),
        ("医道世家", "family_medical", 207, "active",
         "适用类型: family_clan,hospital\n祖传医术的医药世家，有独家秘方和医术传承。家族世代行医，救人无数，在民间口碑极佳。",
         ),
        ("皇族旁支", "family_royal", 208, "active",
         "适用类型: family_clan,kingdom\n皇室宗亲的旁支血脉，虽不继承大统，但也是天潢贵胄。家族中既有纨绔子弟，也有暗中布局的能人。",
         ),
        ("商贾巨富", "family_merchant", 209, "active",
         "适用类型: family_clan,merchant_guild\n世代经商的豪富家族，家财万贯，产业遍布各地。虽然社会地位不高，但财富足以通神，各方势力都要仰仗其财力。",
         ),

        # ===== 帮派/江湖新增 =====
        ("绿林好汉", "gang_greenwood", 404, "active",
         "适用类型: gang,adventurer_guild\n占山为王的绿林好汉，劫富济贫，替天行道。成员多为被逼上梁山的好汉，重情重义，在底层民众中颇有声望。",
         ),
        ("水匪/海盗", "gang_pirate", 405, "active",
         "适用类型: gang,mafia\n盘踞水上的匪帮，专干杀人越货的勾当。组织严密，行踪飘忽，官府屡剿不灭。",
         ),
        ("乞丐帮", "gang_beggar", 406, "active",
         "适用类型: gang,intelligence\n看似不起眼的乞丐帮派，实则遍布天下，消息灵通。帮众三教九流无所不有，是江湖上最大的情报来源。",
         ),
        ("戏班/杂技团", "gang_troupe", 407, "active",
         "适用类型: gang,mysterious\n表面是走南闯北的戏班子，实际上是一个江湖组织。成员个个身怀绝技，以唱戏为掩护执行秘密任务。",
         ),

        # ===== 公司/企业新增 =====
        ("科技独角兽", "company_tech_unicorn", 304, "active",
         "适用类型: company,research_institute\n成立不久但估值惊人的科技公司，拥有核心技术专利。创始人是业界传奇，公司文化激进且充满活力。",
         ),
        ("传统国企", "company_soe", 305, "active",
         "适用类型: company,government\n体量庞大的国有企业，关系盘根错节。虽然效率不高，但资源雄厚，背景深厚，不是轻易能撼动的。",
         ),
        ("家族财阀", "company_chaebol", 306, "active",
         "适用类型: company,family_clan\n由家族掌控的巨型财阀，旗下产业涉及各行各业。在国家经济中占据举足轻重的地位，甚至能影响政策走向。",
         ),
        ("传媒帝国", "company_media", 307, "active",
         "适用类型: company,media\n掌控多家媒体渠道的传媒巨头，拥有巨大的舆论话语权。能够引导公众认知，甚至影响选举和政局。",
         ),

        # ===== 黑帮/社团新增 =====
        ("三合会/洪门", "mafia_triads", 408, "active",
         "适用类型: mafia,gang\n历史悠久的传统帮派组织，有严格的帮规和等级制度。势力渗透各行各业，黑白两道通吃。",
         ),
        ("意大利黑手党", "mafia_mafia", 409, "active",
         "适用类型: mafia,family_clan\n家族式管理的黑手党组织，以「家族」为单位运作。行事隐秘，讲究缄默法则，内部忠诚度极高。",
         ),
        ("雅库扎", "mafia_yakuza", 410, "active",
         "适用类型: mafia,gang\n日本传统黑帮组织，有严格的辈分和等级制度。组织半公开化，甚至与政界有千丝万缕的联系。",
         ),

        # ===== 军方/政府新增 =====
        ("特种部队", "military_spec_ops", 610, "active",
         "适用类型: military\n军中精锐的特种作战部队，成员皆为万里挑一的精英。执行最危险的任务，直接对最高层负责。",
         ),
        ("情报安全局", "military_intelligence", 611, "active",
         "适用类型: intelligence,government,military\n国家情报安全机构，负责国内外情报收集和反间谍工作。权力极大，手段隐秘，无所不在。",
         ),
        ("秘密警察", "military_secret_police", 612, "active",
         "适用类型: government,mysterious\n不被官方承认的秘密警察组织，负责处理各种「麻烦事」。手段狠辣，不受法律约束，令人闻风丧胆。",
         ),

        # ===== 科研/学术新增 =====
        ("疯狂科学家团队", "research_mad", 603, "active",
         "适用类型: research_institute,mysterious,company\n由一群离经叛道的科学家组成的研究团队，进行着各种突破伦理底线的研究。被主流科学界排斥，但确实取得了惊人的成果。",
         ),
        ("生物科技公司", "research_biotech", 604, "active",
         "适用类型: research_institute,company,pharmaceutical\n专注于生物科技和基因工程的公司/研究所，掌握着前沿的生物技术。其研究方向既可能造福人类，也可能打开潘多拉魔盒。",
         ),
        ("AI实验室", "research_ai", 605, "active",
         "适用类型: research_institute,company\n专注于人工智能研发的实验室，在通用人工智能领域取得了突破性进展。其研发的AI系统已经开始产生自我意识...",
         ),

        # ===== 神秘组织新增 =====
        ("上古遗族", "mysterious_ancient_race", 503, "active",
         "适用类型: mysterious,family_clan\n传承自上古时代的神秘种族，拥有常人不具备的特殊能力。隐居在世人罕至之地，守护着上古时代的秘密。",
         ),
        ("轮回组织", "mysterious_reincarnation", 504, "active",
         "适用类型: mysterious,church\n一个相信轮回转世的神秘组织，据说核心成员能够带着前世记忆转生。他们在历史长河中反复出现，似乎在等待着什么。",
         ),
        ("时间管理局", "mysterious_time_agency", 505, "active",
         "适用类型: mysterious,government\n传说中能够操控时间的神秘机构，负责维护时间线的稳定。其成员来自不同时代，身份成谜。",
         ),
        ("维度管理局", "mysterious_dimension", 506, "active",
         "适用类型: mysterious,research_institute\n管理不同维度/平行世界之间往来的神秘组织，防止维度入侵和混乱。其存在本身就是最高机密。",
         ),

        # ===== 教会/信仰新增 =====
        ("异端裁判所", "church_inquisition", 701, "active",
         "适用类型: church,knight_order\n教会下属的异端审判机构，负责追捕和审判异教徒。手段残酷，权力极大，在宗教狂热时期令人闻风丧胆。",
         ),
        ("隐修会", "church_esoteric", 702, "active",
         "适用类型: church,mysterious\n教会内部的秘密结社，掌握着不公开的秘传教义。据说他们守护着真正的神谕，只有核心成员才能接触最深的秘密。",
         ),
        ("德鲁伊教团", "church_druid", 703, "active",
         "适用类型: church,sect\n崇拜自然的古老德鲁伊教团，与自然融为一体，能够操控植物和动物。隐居在古老的森林中，很少与外界往来。",
         ),

        # ===== 冒险者/佣兵新增 =====
        ("佣兵团", "adventurer_mercenary", 801, "active",
         "适用类型: adventurer_guild,military,gang\n拿钱办事的雇佣兵组织，只要给钱什么任务都接。团内成员良莠不齐，但整体战力不俗，是各方势力都要拉拢的对象。",
         ),
        ("猎人公会", "adventurer_hunter", 802, "active",
         "适用类型: adventurer_guild,assassin_guild\n专门接受猎杀委托的公会，从猎杀魔兽到暗杀目标无所不包。公会有严格的评级制度，顶级猎人的身价堪比一支军队。",
         ),
        ("探险家协会", "adventurer_explorer", 803, "active",
         "适用类型: adventurer_guild,merchant_guild\n由探险家组成的协会，专门探索未知区域、寻找失落的宝藏。成员多为富有冒险精神的亡命之徒。",
         ),

        # ===== 盗贼/黑市新增 =====
        ("盗贼公会", "thieves_guild", 804, "active",
         "适用类型: thieves_guild,mafia,gang\n组织严密的盗贼行会，有自己的规矩和地盘。小偷小摸、江洋大盗、销赃洗钱一条龙，在地下世界势力极大。",
         ),
        ("黑市联盟", "thieves_black_market", 805, "active",
         "适用类型: thieves_guild,merchant_guild,mafia\n掌控地下黑市的联盟组织，凡是合法渠道买不到的东西，在这里都能找到。消息灵通，手眼通天。",
         ),
        ("情报贩子", "thieves_info_broker", 806, "active",
         "适用类型: intelligence,thieves_guild\n专门贩卖情报的组织，没有立场，谁出钱就卖给谁。掌握的情报量惊人，是各方势力又恨又离不开的存在。",
         ),

        # ===== 教育/医疗新增 =====
        ("医学院/医院联盟", "medical_alliance", 901, "active",
         "适用类型: hospital,research_institute,academy\n由各大医院和医学院组成的联盟，掌控着医疗资源和医师资格认证。在医疗界一言九鼎，人脉遍布整个医疗体系。",
         ),
        ("艺术学院", "academy_art", 902, "active",
         "适用类型: academy,media\n知名的艺术学院，培养了无数艺术家。学院不仅是教育机构，也是艺术界的风向标，影响力远超教育领域。",
         ),

        # ===== 其他/综合 =====
        ("公会联盟", "other_guild_alliance", 905, "active",
         "适用类型: merchant_guild,adventurer_guild,other\n由多个行业公会联合组成的联盟，协调各行业利益，维护行业秩序。联盟势力庞大，甚至能与官方分庭抗礼。",
         ),
        ("反抗军/革命军", "other_rebellion", 906, "active",
         "适用类型: military,gang,mysterious\n反抗现有政权的革命/起义组织，目前处于地下活动状态。虽然实力不如正规军，但得到了不少民众的支持。",
         ),
        ("中立仲裁机构", "other_arbitration", 907, "active",
         "适用类型: government,independent,other\n独立于各方势力的中立仲裁机构，负责调解各方争端。因为立场公正，得到了大多数势力的认可和尊重。",
         ),
        ("娱乐集团", "other_entertainment", 908, "active",
         "适用类型: company,media\n大型娱乐传媒集团，旗下艺人众多，掌控着娱乐圈的话语权。表面光鲜亮丽，暗地里也有不少见不得光的交易。",
         ),
        ("体育俱乐部/战队", "other_sports", 909, "active",
         "适用类型: company,other\n知名的体育俱乐部/电竞战队，拥有大量粉丝和商业价值。背后往往有大财团支持，影响力远不止于赛场。",
         ),
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
