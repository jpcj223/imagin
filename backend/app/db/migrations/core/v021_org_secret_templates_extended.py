"""核心库迁移 v021 — 扩展组织隐藏设定/暗线字典。"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def upgrade(db: Session) -> None:
    """扩展 org_secret_template 字典，增加更多暗线模板。"""

    result = db.execute(
        text("SELECT id FROM sys_dictionaries WHERE dict_code = 'org_secret_template'")
    ).fetchone()
    if not result:
        return
    dict_id = result[0]

    items = [
        # ===== 权力/阴谋类 =====
        ("幕后掌控者", "secret_puppeteer", 101, "active",
         "适用类型: mysterious,mafia,company,government\n组织表面上的领袖只是傀儡，真正的掌控者另有其人。"
         "这位幕后人物身份成谜，可能是早已「死去」的前辈，也可能是某个不起眼的小人物。"
         "只有极少数核心成员知道真相。",
         ),
        ("双重身份", "secret_double_identity", 102, "active",
         "适用类型: intelligence,mysterious,assassin_guild,mafia\n组织核心成员都有着合法的表面身份，可能是商人、官员、学者甚至是敌对势力的成员。"
         "他们在明面上扮演着各自的角色，暗地里却为组织执行任务。",
         ),
        ("高层内鬼", "secret_mole_high", 103, "active",
         "适用类型: intelligence,mafia,company,mysterious\n组织在最高层安插了自己的人——可能是政要、企业高管、皇室成员。"
         "这个内鬼的身份是最高机密，即使是组织内部也只有极少数人知道。",
         ),
        ("借壳重生", "secret_reincarnated_org", 104, "active",
         "适用类型: mysterious,mafia,sect,gang\n这个组织其实是某个早已覆灭的旧组织换了个名字重新出现的。"
         "核心成员、目标、甚至对手都没有变，只是换了一层皮继续活动。",
         ),

        # ===== 禁忌/秘密类 =====
        ("禁忌实验", "secret_forbidden_experiment", 201, "active",
         "适用类型: research_institute,company,mysterious,sect\n组织在秘密进行着被明令禁止的实验——人体实验、禁忌法术、基因改造、时空穿越……"
         "实验目的可能是追求永生、制造超级战士，或是更疯狂的目标。",
         ),
        ("禁忌功法/技术", "secret_forbidden_art", 202, "active",
         "适用类型: sect,research_institute,mysterious\n组织掌握着一种威力巨大但代价惨重的禁忌功法/技术。"
         "修炼/使用它会付出惨痛的代价——折寿、走火入魔、失去人性，但为了力量，组织仍在秘密传承。",
         ),
        ("神器/至宝下落", "secret_sacred_treasure", 203, "active",
         "适用类型: sect,church,family_clan,mysterious\n组织守护着一件传说中的神器/至宝，它的存在本身就是最高机密。"
         "这件宝物可能拥有毁天灭地的力量，也可能封印着某种可怕的存在。",
         ),
        ("诅咒/血脉秘密", "secret_curse_bloodline", 204, "active",
         "适用类型: family_clan,sect,mysterious,church\n组织成员背负着世代相传的诅咒/血脉秘密。"
         "这既是他们力量的来源，也是他们悲剧的根源。外人只知其强大，不知其代价。",
         ),
        ("长生/永生秘密", "secret_immortality", 205, "active",
         "适用类型: sect,church,mysterious,research_institute\n组织掌握着长生/永生的秘密——可能是功法、丹药、仪式，也可能是科技手段。"
         "但永生的代价极其高昂，只有极少数核心成员能够享用。",
         ),

        # ===== 真相/颠覆类 =====
        ("世界真相", "secret_world_truth", 301, "active",
         "适用类型: mysterious,church,research_institute,government\n组织知道这个世界的「真相」——世界可能是虚拟的、人类可能是被圈养的、"
         "历史可能被篡改过……这个真相比任何阴谋都更令人绝望。",
         ),
        ("预言/末日", "secret_prophecy", 302, "active",
         "适用类型: church,mysterious,government,sect\n组织掌握着一个关于未来的预言——末日即将降临、大劫将至、某位关键人物将改变世界。"
         "组织的一切行动都是为了应对（或促成）这个预言。",
         ),
        ("历史被篡改", "secret_rewritten_history", 303, "active",
         "适用类型: mysterious,government,academy,church\n世人所知的历史是假的。真正的历史被这个组织篡改/抹去了。"
         "他们抹去的那段历史中隐藏着足以颠覆现有秩序的秘密。",
         ),
        ("敌人是自己人", "secret_enemy_within", 304, "active",
         "适用类型: mysterious,military,intelligence,mafia\n组织最大的敌人/竞争对手，其实是从本组织分裂出去的。"
         "两边同源同根，却因为理念分歧而分道扬镳，成为了死敌。",
         ),
        ("创世/灭世计划", "secret_creation_destruction", 305, "active",
         "适用类型: mysterious,church,research_institute,government\n组织的终极目标是毁灭现有世界/秩序，然后创造一个全新的世界。"
         "他们认为只有彻底打碎旧世界，才能建立真正美好的新世界。",
         ),

        # ===== 身份/起源类 =====
        ("非人起源", "secret_nonhuman_origin", 401, "active",
         "适用类型: mysterious,sect,family_clan,church\n组织的创始人/核心成员并非人类——可能是妖族、精灵、神明、外星人、人工智能……"
         "他们以人的形态在人类社会中活动，真实身份是最高机密。",
         ),
        ("穿越者/重生者组织", "secret_reborn_group", 402, "active",
         "适用类型: mysterious,company,sect,government\n这个组织的核心成员都是穿越者/重生者。"
         "他们来自不同的时代/世界，因为某种原因聚集在一起，利用「先知」优势布局天下。",
         ),
        ("梦境/幻想真实", "secret_dream_real", 403, "active",
         "适用类型: mysterious,church,research_institute\n组织发现梦境/幻想中的世界是真实存在的，并且可以与之产生联系甚至干涉。"
         "他们在暗中研究通往那个世界的方法，而这可能带来灾难。",
         ),
        ("系统/金手指来源", "secret_system_source", 404, "active",
         "适用类型: mysterious,sect,company,research_institute\n那些拥有「系统」「金手指」的人，他们的力量其实来源于这个组织。"
         "组织可能是在进行某种实验，也可能是在挑选继承者。",
         ),

        # ===== 利益/黑幕类 =====
        ("黑白通吃", "secret_both_sides", 501, "active",
         "适用类型: mafia,government,company,military\n组织表面上是白道（官方/正派），暗地里也是黑道的掌控者。"
         "正邪两边都是他们在操控，所谓的对立只是演给世人看的戏。",
         ),
        ("养寇自重", "secret_feed_enemy", 502, "active",
         "适用类型: military,government,mysterious,mafia\n组织最大的敌人其实是他们自己「养」的。"
         "为了维持自身的存在和地位，他们需要一个足够强大的敌人，所以会暗中扶持对手。",
         ),
        ("暗中交易", "secret_shadow_deal", 503, "active",
         "适用类型: company,government,mafia,merchant_guild\n组织与各方势力都有秘密交易，包括表面上的敌人。"
         "这些交易涉及利益交换、情报共享、甚至出卖盟友，一旦曝光将万劫不复。",
         ),
        ("资金来源黑幕", "secret_dark_funding", 504, "active",
         "适用类型: company,church,sect,mafia\n组织光鲜的表面背后，资金来源其实见不得光——贩毒、贩卖人口、走私军火、政治献金……"
         "为了维持庞大的开支，他们无所不用其极。",
         ),

        # ===== 内部矛盾类 =====
        ("内部分裂", "secret_internal_split", 601, "active",
         "适用类型: sect,company,mafia,government\n组织内部已经严重分裂，几大派系明争暗斗，表面上的团结只是假象。"
         "一旦外部压力消失，内斗就会立刻爆发，甚至可能导致组织瓦解。",
         ),
        ("继承人之争", "secret_succession", 602, "active",
         "适用类型: family_clan,sect,company,mafia\n组织最高领袖的位置面临继承危机。几位候选人为了争位暗中角力，"
         "各自拉拢势力，组织内部暗流涌动，一场内乱在所难免。",
         ),
        ("叛徒潜伏", "secret_traitor", 603, "active",
         "适用类型: intelligence,military,sect,mafia\n组织内部出了叛徒，而且地位不低。"
         "高层已经察觉但不知道是谁，正在暗中调查。整个组织人人自危，互相猜忌。",
         ),
        ("上代恩怨", "secret_past_grudge", 604, "active",
         "适用类型: family_clan,sect,mafia,church\n组织与某个死敌的恩怨源于上一代甚至更久远的秘密。"
         "真正的原因早已被掩埋，现在的仇恨只是惯性，只有少数老人知道当年的真相。",
         ),

        # ===== 特殊能力/设定类 =====
        ("契约/誓言约束", "secret_contract_binding", 701, "active",
         "适用类型: mysterious,sect,church,mafia\n组织成员都立下了某种无法违背的契约/誓言——可能是魔法契约、血誓、"
         "也可能是掌握着每个人的把柄。一旦背叛，代价惨重。",
         ),
        ("共同秘密绑定", "secret_shared_secret", 702, "active",
         "适用类型: mafia,gang,mysterious,sect\n组织成员因为共同参与/见证了某件不可告人的事情而绑定在一起。"
         "这件事是他们的「投名状」，一旦曝光所有人都要完蛋，所以他们不得不抱团。",
         ),
        ("洗脑/精神控制", "secret_mind_control", 703, "active",
         "适用类型: mysterious,church,research_institute,government\n组织成员的忠诚度并非出于自愿，而是被洗脑/精神控制了。"
         "核心层用某种手段（药物、法术、催眠、芯片）控制着下层成员的思想。",
         ),
        ("人格分裂/多重身份", "secret_split_personality", 704, "active",
         "适用类型: mysterious,intelligence,assassin_guild,research_institute\n组织的核心人物有着多重人格/身份，不同人格执行不同的任务，"
         "甚至各个人格之间不知道彼此的存在。",
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
