"""章节改稿会话的持久化和并发保护测试。"""
from __future__ import annotations

import unittest
from contextlib import contextmanager
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.business import Chapter, Project
from app.services.chapter_edit_sessions import (
    create_chapter_edit_session,
    get_chapter_edit_session,
    list_chapter_edit_sessions,
    save_chapter_edit_session,
)


class ChapterEditSessionPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        factory = sessionmaker(self.engine, expire_on_commit=False)
        self.db = factory()
        self.db.add(Project(id=1, name="会话测试项目"))
        self.db.add(Chapter(project_id=1, chapter_no=1, title="第1章", content="正文", status="draft"))
        self.db.commit()

        @contextmanager
        def test_db():
            yield self.db

        self.patch_db = patch("app.services.chapter_edit_sessions.get_business_db", test_db)
        self.patch_db.start()

    def tearDown(self):
        self.patch_db.stop()
        self.db.close()
        self.engine.dispose()

    def test_sessions_restore_state_and_reject_stale_revisions(self):
        created = create_chapter_edit_session(1, 1)
        self.assertEqual(created["state"]["scope"], "chapter")
        self.assertEqual(created["revision"], 1)

        state = {
            "scope": "selection",
            "messages": [{"id": "m1", "role": "user", "content": "精简这段"}],
            "candidate": {"expectedContent": "原文", "proposedContent": "新文"},
        }
        saved = save_chapter_edit_session(
            project_id=1,
            chapter_id=1,
            session_id=created["session_id"],
            expected_revision=1,
            title="精简这段",
            state=state,
        )
        self.assertEqual(saved["revision"], 2)
        self.assertEqual(saved["state"], state)

        stale = save_chapter_edit_session(
            project_id=1,
            chapter_id=1,
            session_id=created["session_id"],
            expected_revision=1,
            title="旧标签页",
            state={"scope": "chapter", "messages": [], "candidate": None},
        )
        self.assertTrue(stale["conflict"])
        self.assertEqual(stale["title"], "精简这段")
        self.assertEqual(get_chapter_edit_session(1, 1, created["session_id"])["revision"], 2)
        self.assertEqual(len(list_chapter_edit_sessions(1, 1)), 1)

    def test_sessions_cannot_be_read_under_another_project(self):
        created = create_chapter_edit_session(1, 1)
        self.assertIsNone(get_chapter_edit_session(2, 1, created["session_id"]))


if __name__ == "__main__":
    unittest.main()
