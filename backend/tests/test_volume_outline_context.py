"""章节上下文必须带入所属卷纲，并安全忽略无效卷关联。"""
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.agents.workflows import _format_context
from app.agents_v3.presets import create_planner_agent, create_writer_agent
from app.memory.retriever import MemoryRetriever, format_volume_outline
from app.models.business import Outline, Project
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
        }
        text = format_volume_outline(volume_outline)
        prompt = MemoryRetriever(1).build_context_prompt({
            "volume_outline": volume_outline,
            "outline": {"title": "旧航线", "description": "检查码头记录。"},
        })

        self.assertIn("核心事件：发现旧航线记录", text)
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


if __name__ == "__main__":
    unittest.main()
