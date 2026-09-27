"""章节上下文必须带入所属卷纲，并安全忽略无效卷关联。"""
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.agents.context import build_context_preview
from app.agents.workflows import _build_draft_messages, _format_context
from app.agents_v3.presets import create_planner_agent, create_writer_agent
from app.memory.retriever import MemoryRetriever, format_volume_outline
from app.models.business import Chapter, ChapterSummary, Character, Outline, Project
from app.skills.writing.core_planning import CorePlanningSkill
from app.skills.writing.core_writing import CoreWritingSkill


class VolumeOutlineContextTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.db.add_all([
            Project(id=1, name="本项目"),
            Project(id=2, name="其他项目"),
        ])
        self.db.flush()

        self.volume = Outline(
            project_id=1,
            node_type="volume",
            volume_no=2,
            title="潮汐之下",
            description="调查失踪航线并重整船队。",
            extra=json.dumps({
                "core_events": "发现旧航线记录",
                "locations": "雾港与沉船区",
                "climax": "潮汐风暴中救援船队",
                "target_chapters": 30,
                "characters": [99],
            }, ensure_ascii=False),
        )
        self.chapter = Outline(
            project_id=1,
            node_type="chapter",
            chapter_no=8,
            title="旧航线",
            description="检查码头留下的记录。",
            volume_id=None,
        )
        self.db.add_all([self.volume, self.chapter])
        self.db.flush()
        self.chapter.volume_id = self.volume.id
        self.overview = Outline(
            project_id=1,
            node_type="overview",
            title="大纲总览",
            description="船队追查失踪航线，并揭开潮汐异常。",
            extra=json.dumps({
                "target_words": 1000000,
                "target_volumes": 5,
                "target_chapters": 200,
                "pace": "3",
                "core_conflict": "安全与真相的冲突",
                "ending": "船队选择公开真相",
            }, ensure_ascii=False),
        )
        self.previous_volume = Outline(
            project_id=1,
            node_type="volume",
            volume_no=1,
            title="雾港序曲",
            description="船队初入雾港。",
        )
        self.next_volume = Outline(
            project_id=1,
            node_type="volume",
            volume_no=3,
            title="风暴航线",
            description="风暴中寻找失踪船只。",
        )
        self.next_chapter = Outline(
            project_id=1,
            node_type="chapter",
            chapter_no=9,
            title="风暴前夜",
            description="收到风暴预警，为出航做准备。",
            extra=json.dumps({"scene": "雾港灯塔", "conflict": "是否冒险出航"}, ensure_ascii=False),
            volume_id=self.volume.id,
        )
        previous_chapter = Chapter(project_id=1, chapter_no=7, title="归港", content="船队在雾港靠岸，方舟收起海图。")
        self.db.add_all([
            self.overview,
            self.previous_volume,
            self.next_volume,
            self.next_chapter,
            previous_chapter,
            Character(id=99, project_id=1, name="方舟", role_type="supporting"),
        ])
        self.db.flush()
        self.db.add(ChapterSummary(chapter_id=previous_chapter.id, summary="船队带回一份破损航线图。"))
        self.db.commit()

        @contextmanager
        def test_db():
            yield self.db

        self.db_patch = patch("app.memory.retriever.get_business_db", test_db)
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.db.close()
        self.engine.dispose()

    def test_chapter_resolves_only_its_project_volume(self):
        retriever = MemoryRetriever(project_id=1)
        chapter = retriever._get_outline(self.chapter.id, 8)
        volume = retriever._get_volume_outline(chapter["volume_id"])

        self.assertEqual(chapter["title"], "旧航线")
        self.assertEqual(volume["id"], self.volume.id)
        self.assertEqual(volume["volume_no"], 2)
        self.assertEqual(volume["core_events"], "发现旧航线记录")

    def test_missing_cross_project_or_non_volume_reference_is_safe(self):
        retriever = MemoryRetriever(project_id=1)
        self.assertEqual(retriever._get_volume_outline(None), {})

        other_project_volume = Outline(
            project_id=2, node_type="volume", title="其他项目卷",
        )
        not_a_volume = Outline(
            project_id=1, node_type="chapter", title="普通章节节点",
        )
        self.db.add_all([other_project_volume, not_a_volume])
        self.db.commit()

        self.assertEqual(retriever._get_volume_outline(other_project_volume.id), {})
        self.assertEqual(retriever._get_volume_outline(not_a_volume.id), {})

    def test_volume_outline_is_formatted_into_generation_prompt(self):
        volume_outline = {
            "volume_no": 2,
            "title": "潮汐之下",
            "description": "调查失踪航线。",
            "core_events": "发现旧航线记录",
            "locations": "雾港",
            "climax": "风暴救援",
            "target_chapters": 30,
            "characters": [99],
        }
        text = format_volume_outline(volume_outline)
        prompt = MemoryRetriever(1).build_context_prompt({
            "volume_outline": volume_outline,
            "outline": {"title": "旧航线", "description": "检查码头记录。"},
        })

        self.assertIn("核心事件：发现旧航线记录", text)
        self.assertIn("预计章节数：30章", text)
        self.assertIn("本卷指定人物 ID：99", text)
        self.assertIn("=== 当前卷纲（必读） ===", prompt)
        self.assertIn("卷名：潮汐之下", prompt)
        self.assertIn("=== 本章大纲（必读） ===", prompt)
        self.assertIn("标题：旧航线", prompt)

    def test_volume_outline_reaches_legacy_planner_and_writer_contexts(self):
        volume_outline = {
            "volume_no": 2,
            "title": "潮汐之下",
            "description": "调查失踪航线。",
            "core_events": "发现旧航线记录",
        }
        planning_context = CorePlanningSkill().pre_process(
            {"volume_outline": volume_outline, "outline": {"title": "旧航线"}},
            {},
        )
        writing_context = CoreWritingSkill().pre_process(
            {"volume_outline": volume_outline, "outline": {"title": "旧航线"}},
            {},
        )
        legacy_context = _format_context({
            "volume_outline": volume_outline,
            "outline": {"title": "旧航线"},
        })
        planner_prompt = create_planner_agent()._build_messages(planning_context, {})[-1]["content"]
        writer_prompt = create_writer_agent()._build_messages(writing_context, {})[-1]["content"]

        self.assertIn("卷名：潮汐之下", planning_context["volume_outline_text"])
        self.assertIn("当前卷纲（必读）：", planner_prompt)
        self.assertIn("卷名：潮汐之下", planner_prompt)
        self.assertIn("核心事件：发现旧航线记录", writing_context["_writing_context"])
        self.assertIn("发现旧航线记录", writer_prompt)
        self.assertIn("当前卷纲：", legacy_context)
        self.assertIn("发现旧航线记录", legacy_context)

    def test_generation_context_contains_latest_overview_neighboring_volumes_and_chapters(self):
        retriever = MemoryRetriever(1)
        self.volume.description = "最新保存：调查失踪航线并重整船队。"
        self.db.commit()

        context = retriever.retrieve_for_chapter(
            chapter_no=8,
            outline_id=self.chapter.id,
            include_generation_outline_context=True,
        )

        self.assertEqual(context["overview_outline"]["title"], "大纲总览")
        self.assertEqual(context["previous_volume_outline"]["volume_no"], 1)
        self.assertEqual(context["volume_outline"]["description"], "最新保存：调查失踪航线并重整船队。")
        self.assertEqual(context["next_volume_outline"]["volume_no"], 3)
        self.assertEqual(context["next_chapter_outline"]["chapter_no"], 9)
        self.assertEqual(context["previous_chapter"]["chapter_no"], 7)
        self.assertEqual(context["volume_outline"]["characters"], [99])
        self.assertIn(99, {item["id"] for item in context["characters"]})
        self.assertIn("下一章细纲（用于承接和预埋", context["generation_outline_context_text"])
        self.assertIn("不得提前写完下一章事件", context["generation_outline_context_text"])
        self.assertIn("破损航线图", context["generation_outline_context_text"])
        self.assertIn("预计总字数：1000000字", context["generation_outline_context_text"])

    def test_context_preview_matches_the_generation_outline_pack(self):
        preview = build_context_preview(1, 8, self.chapter.id)
        labels = [item["label"] for item in preview["required_context"]]

        self.assertEqual(labels[:6], [
            "大纲总览",
            "前一卷纲",
            "当前卷纲",
            "下一卷纲 · 仅作铺垫",
            "当前章细纲",
            "下一章细纲 · 仅作承接",
        ])
        self.assertIn("上一章衔接", labels)
        self.assertTrue(all("content" in item for item in preview["required_context"]))

    def test_edit_and_analysis_context_does_not_implicitly_read_future_outlines(self):
        context = MemoryRetriever(1).retrieve_for_chapter(8, self.chapter.id)

        self.assertNotIn("generation_outline_context_text", context)
        self.assertNotIn("next_chapter_outline", context)
        self.assertNotIn("overview_outline", context)

    def test_legacy_generation_requests_the_same_continuity_pack_as_preview(self):
        with patch("app.agents.workflows.build_chapter_context", return_value={}) as build_context:
            _build_draft_messages(1, 8, "保持承接", "3", self.chapter.id)

        self.assertTrue(build_context.call_args.kwargs["include_generation_outline_context"])

    def test_generation_continuity_reaches_planner_writer_and_legacy_prompt(self):
        generation_context = "【大纲总览】主线\n【下一章】仅用于预埋，不提前写核心事件"
        planner_context = CorePlanningSkill().pre_process(
            {
                "volume_outline": {"volume_no": 2, "title": "潮汐之下"},
                "outline": {"title": "旧航线"},
                "generation_outline_context_text": generation_context,
            },
            {},
        )
        writing_context = CoreWritingSkill().pre_process(
            {
                "volume_outline": {"volume_no": 2, "title": "潮汐之下"},
                "outline": {"title": "旧航线"},
                "generation_outline_context_text": generation_context,
            },
            {},
        )
        legacy_context = _format_context({
            "volume_outline": {"volume_no": 2, "title": "潮汐之下"},
            "generation_outline_context_text": generation_context,
        })
        planner_prompt = create_planner_agent()._build_messages(planner_context, {})[-1]["content"]
        writer_prompt = create_writer_agent()._build_messages(writing_context, {})[-1]["content"]

        self.assertIn(generation_context, planner_prompt)
        self.assertIn(generation_context, writer_prompt)
        self.assertIn(generation_context, legacy_context)


if __name__ == "__main__":
    unittest.main()
