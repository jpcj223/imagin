"""为伏笔看板准备可重复导入的生命周期样例。"""
from __future__ import annotations

import argparse

from app.db.session import get_business_db
from app.models.business import Character, Foreshadowing, Organization, Project
from app.services.foreshadowing_history import (
    capture_foreshadowing_snapshot,
    record_foreshadowing_history,
)


# 样例使用项目中已存在的人物和组织 ID；章节号代表后续测试剧情节点。
DEMO_ITEMS = [
    ("雾港无潮之夜", "连续七日没有潮汐，海底旧城的钟声却在子夜准时响起。", "pending", "high", None, 12, None, 1, None, "主线谜团：适合测试待埋设与重要性筛选。", "8,13", "3,8"),
    ("空白航海图", "一张没有海岸线的航海图会在月光下显出通往归墟的路线。", "pending", "high", None, 18, None, 1, None, "尚未正式出场，供测试从待埋设推进到已埋设。", "10,16", "7,9"),
    ("缺页的巡检档案", "雾港巡检司的旧档案少了同一天的三页，借阅记录显示是已故巡检签走。", "pending", "medium", None, 15, None, 1, None, "调查线索，后续揭示档案与密探司有关。", "9,33", "4,7"),
    ("会说人话的海兽", "被捕获的幼年海兽反复说出一个从未公开的旧姓。", "pending", "medium", None, 22, None, 2, None, "用于测试角色与组织关联筛选。", "5,35", "5,17"),
    ("灯塔第三盏灯", "灯塔每晚只点亮两盏灯，但远海船只都声称看见第三盏灯在指引方向。", "planted", "high", 1, 16, None, 1, None, "第一章已出现异常灯光，等待后续提供更多证据。", "8,10", "7,3"),
    ("旧铜铃的潮痕", "顾长渊随身铜铃内侧有新鲜海盐痕迹，他却坚称多年未曾靠海。", "planted", "medium", 2, 20, None, 2, None, "已埋设人物细节，测试人物关联及章节显示。", "12,18", "3"),
    ("账册上的双重印记", "玄鲸商会账册同一笔货款盖有商会与沉船打捞局的印记。", "planted", "medium", 3, 21, None, 3, None, "引出两组织之间未公开的交易。", "14,32", "11,13"),
    ("从未寄出的家书", "苏婉清保存着一封写给陌生人的家书，落款日期晚于寄信人去世之日。", "planted", "low", 4, 14, None, 4, None, "低重要性支线，测试卡片风险排序。", "9,18", ""),
    ("盐井里的军令", "镇海军缴获的敌方军令使用了本朝尚未启用的密语格式。", "developing", "high", 5, 24, None, 5, None, "军令已出现两次，逐步指向有人泄露新式密语。", "10,21,37", "5,6"),
    ("无影的第十三名乘客", "每次渡船清点乘客都比登船时少一人，但船票总数没有变化。", "developing", "high", 6, 26, None, 6, None, "三名证人描述的失踪者都是同一副面孔。", "13,16,39", "3,14"),
    ("会倒着走的沙漏", "海雾山观星台的沙漏在每次日食前倒流一刻钟。", "developing", "medium", 7, 30, None, 7, None, "与世界规则和时间线记忆关联的长期线索。", "22,26", "8"),
    ("被抹去的王庭使者", "鲛人王庭的来访记录有一整年被刮去，守门人仍记得那位使者的名字。", "developing", "medium", 8, 28, None, 8, None, "组织外交线已露出矛盾，计划在中段揭晓。", "16,23", "14,15"),
    ("海图背面的血字", "海图背面的字迹经比对属于三十年前失踪的船长，内容是“不要救我”。", "payoff_pending", "high", 2, 10, None, 2, None, "信息已齐，计划第十章揭示船长主动留在归墟。", "8,29", "9,13"),
    ("巡检司密室的空椅", "密室里一直为一个不存在于编制的人保留座位，所有人都回避解释。", "payoff_pending", "high", 3, 12, None, 3, None, "相关证据已收齐，回收后会改变主角对巡检司的判断。", "9,33", "4"),
    ("失踪的潮汐刻度", "潮汐议会的主钟被人为拨慢，负责校准的记录员在三日后主动认罪。", "payoff_pending", "medium", 4, 14, None, 4, None, "口供与物证不一致，待第十四章完成回收。", "10,20", "3"),
    ("信使从未抵达的终点", "信使每月按时报告抵达北岸，却没有任何人见过北岸收件人。", "payoff_pending", "medium", 5, 16, None, 5, None, "目标地点已确认，准备回收路线谜团。", "6,38", "4,5"),
    ("海底石碑的归来者", "石碑预言的归来者并非某个英雄，而是每代都会出现的身份空缺。", "resolved", "high", 1, 9, 9, 1, 9, "第九章已揭示“归来者”指承担名字的人；测试已回收与历史记录。", "8,13,22", "8,9"),
    ("无人认领的黑伞", "黑伞连续出现在三起案件现场，伞骨刻着受害者都认识的暗号。", "resolved", "medium", 2, 8, 8, 2, 8, "第八章确认是叶惊鸿留下的追踪标记。", "11,29", "7"),
    ("纸船里的药方", "纸船中每次出现一张药方，配方都能治好下一位病人的症状。", "resolved", "low", 1, 6, 6, 1, 6, "第六章揭示周药师借此引导主角找到失落药库。", "7,34", "10,12"),
    ("被调换的祭词", "祭典前夜有人调换祭词，改动处恰好删去了关于海雾退去的预言。", "resolved", "medium", 3, 11, 11, 3, 11, "第十一章查明祭司会为保护族人主动隐瞒预言。", "16,23", "15"),
    ("废弃的北线航道", "一条从未发生事故的航道因旧地图标注而被永久封禁。", "abandoned", "low", 4, None, None, 4, 9, "原定支线已取消，记录废弃原因以测试归档筛选。", "39", "13"),
    ("第二枚同心玉", "两位主角各持半枚玉佩，拼合后图案与当前主线无关。", "abandoned", "low", 5, None, None, 5, 12, "删去双生身世设定，保留道具作为普通信物。", "8,9", ""),
    ("空置的第三巡防营", "第三巡防营名册人数始终为零，却持续领用军饷和装备。", "abandoned", "medium", 6, None, None, 6, 13, "与新的军政主线冲突，已改由密探司暗线承接。", "10,21", "6,7"),
    ("会重复的梦境", "路人甲反复梦见一扇蓝门，醒来后能说出门后发生的事。", "abandoned", "medium", 7, None, None, 7, 15, "测试废弃状态保留关联但不进入生成上下文。", "1", ""),
]


def seed_project(project_id: int, apply: bool) -> tuple[int, int]:
    """检查项目依赖并按缺少项补入伏笔样例。

    步骤 1：验证目标项目和样例引用的人物、组织都存在。
    步骤 2：按固定测试前缀跳过已存在样例，避免重复插入。
    步骤 3：应用模式下在同一事务中创建伏笔与初始历史快照。
    """
    created = 0
    skipped = 0
    with get_business_db() as db:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"项目 {project_id} 不存在")

        character_ids = {
            row.id for row in db.query(Character.id).filter(Character.project_id == project_id).all()
        }
        organization_ids = {
            row.id for row in db.query(Organization.id).filter(Organization.project_id == project_id).all()
        }

        for (keyword, description, status, importance, planted, payoff, resolved,
             effective, expires, notes, related_characters, related_organizations) in DEMO_ITEMS:
            if db.query(Foreshadowing.id).filter(
                Foreshadowing.project_id == project_id,
                Foreshadowing.keyword == f"【看板测试】{keyword}",
            ).first():
                skipped += 1
                continue

            character_refs = [int(value) for value in related_characters.split(",") if value]
            organization_refs = [int(value) for value in related_organizations.split(",") if value]
            if any(value not in character_ids for value in character_refs):
                raise ValueError(f"样例“{keyword}”引用了当前项目中不存在的人物")
            if any(value not in organization_ids for value in organization_refs):
                raise ValueError(f"样例“{keyword}”引用了当前项目中不存在的组织")

            created += 1
            if not apply:
                continue

            item = Foreshadowing(
                project_id=project_id,
                keyword=f"【看板测试】{keyword}",
                description=description,
                status=status,
                importance=importance,
                planted_chapter=planted,
                payoff_chapter=payoff,
                resolved_chapter=resolved,
                effective_from=effective,
                expires_at=expires,
                notes=notes,
                related_character_ids=",".join(str(value) for value in character_refs),
                related_organization_ids=",".join(str(value) for value in organization_refs),
                related_outline_ids="",
            )
            db.add(item)
            db.flush()
            record_foreshadowing_history(
                db=db,
                item=item,
                source_type="demo_seed",
                operation="create",
                before_snapshot={},
                after_snapshot=capture_foreshadowing_snapshot(item),
                rationale="为伏笔看板交互和生命周期测试准备的样例数据。",
            )

        if apply:
            db.commit()
        print(f"项目：{project.name}（ID {project.id}）")
        print(f"新增：{created} 条；已存在跳过：{skipped} 条；运行模式：{'写入' if apply else '预览'}")
    return created, skipped


def main() -> None:
    """解析命令行参数并执行预览或写入。

    步骤 1：要求调用者显式指定项目 ID。
    步骤 2：默认只预览，只有添加 --apply 才修改数据库。
    步骤 3：用退出码表达准备失败，方便后续自动化调用。
    """
    parser = argparse.ArgumentParser(description="导入伏笔看板测试样例（默认仅预览）")
    parser.add_argument("--project-id", type=int, required=True, help="样例所属项目 ID")
    parser.add_argument("--apply", action="store_true", help="确认写入本地业务库")
    args = parser.parse_args()

    try:
        seed_project(args.project_id, args.apply)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
