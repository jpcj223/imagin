"""章节对话改稿应使用长期记忆，并遵守章节时间边界。"""
from __future__ import annotations

import unittest
from contextlib import contextmanager
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents.chapter_edit import _compact_context
from app.db.session import Base
from app.memory.retriever import MemoryRetriever
from app.models.business import Chapter, MemoryItem, Project


class ChapterEditMemoryContextTests(unittest.TestCase):
    def test_compact_context_limits_memory_count_and_text_length(self):
        compact = _compact_context({
            "long_term_memories": [
                {
                    "memory_type": "world_rule",
                    "title": f"记忆{i}" * 100,
                    "content_summary": "潮汐规律" * 100,
                    "source_type": "chapter_analysis" * 10,
                    "source_chapter_no": i,
                }
                for i in range(8)
            ],
        })

        memories = compact["已确认长期记忆"]
        self.assertEqual(len(memories), 6)
        self.assertLessEqual(len(memories[0]["标题"]), 120)
        self.assertLessEqual(len(memories[0]["内容"]), 360)
        self.assertLessEqual(len(memories[0]["来源"]), 40)
        self.assertEqual(memories[0]["来源章节"], 0)

    def test_retriever_excludes_current_and_future_chapter_memories(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = Session(engine, expire_on_commit=False)
        db.add(Project(id=1, name="记忆边界测试"))
        db.flush()
        earlier = Chapter(project_id=1, chapter_no=1, title="前章", content="前章正文")
        current = Chapter(project_id=1, chapter_no=3, title="当前章", content="当前正文")
        future = Chapter(project_id=1, chapter_no=4, title="后章", content="后章正文")
        db.add_all([earlier, current, future])
        db.flush()
        db.add_all([
            MemoryItem(
                memory_id="memory-earlier",
                project_id=1,
                memory_type="world_rule",
                title="前章规律",
                content="已发生的潮汐规律",
                content_summary="潮痕只能保留短时回声",
                source_type="chapter_analysis",
                source_ref=f"chapter:{earlier.id}:proposal:earlier",
            ),
            MemoryItem(
                memory_id="memory-current",
                project_id=1,
                memory_type="world_rule",
                title="当前章结论",
                content="当前章节才发现的规律",
                content_summary="当前章结论",
                source_type="chapter_analysis",
                source_ref=f"chapter:{current.id}:proposal:current",
            ),
            MemoryItem(
                memory_id="memory-future",
                project_id=1,
                memory_type="world_rule",
                title="后章发现",
                content="后续章节才出现的事实",
                content_summary="后章结论",
                source_type="chapter_analysis",
                source_ref=f"chapter:{future.id}:proposal:future",
            ),
            MemoryItem(
                memory_id="memory-manual",
                project_id=1,
                memory_type="writing_preference",
                title="作者偏好",
                content="保留克制的叙事语气",
                content_summary="叙事保持克制",
                source_type="manual",
                source_ref=None,
            ),
        ])
        db.commit()

        @contextmanager
        def test_db():
            yield db

        db_patch = patch("app.memory.retriever.get_business_db", test_db)
        db_patch.start()
        try:
            memories = MemoryRetriever(1)._get_long_term_memories(limit=8, chapter_no=3, query="潮痕")
        finally:
            db_patch.stop()
            db.close()
            engine.dispose()

        by_title = {item["title"]: item for item in memories}
        self.assertIn("前章规律", by_title)
        self.assertIn("作者偏好", by_title)
        self.assertNotIn("当前章结论", by_title)
        self.assertNotIn("后章发现", by_title)
        self.assertEqual(by_title["前章规律"]["source_chapter_no"], 1)
        self.assertIsNone(by_title["作者偏好"]["source_chapter_no"])


if __name__ == "__main__":
    unittest.main()
