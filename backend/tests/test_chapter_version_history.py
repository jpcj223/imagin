"""章节版本恢复、来源和收藏的回归测试。"""
from __future__ import annotations

import unittest
from contextlib import contextmanager
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents_v3.persistence import WorkflowPersistence
from app.db.session import Base
from app.models.business import Chapter, GenerationVersion, Project


class ChapterVersionHistoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.db.add(Project(id=1, name="版本测试项目"))
        self.chapter = Chapter(project_id=1, chapter_no=1, title="第1章", content="当前正文", status="draft")
        self.db.add(self.chapter)
        self.db.flush()
        self.contents = {"v1.txt": "历史正文", "v2.txt": "当前正文"}
        self.db.add_all([
            GenerationVersion(
                version_id="version-old",
                chapter_id=self.chapter.id,
                version_number=1,
                is_current=0,
                content_file_path="v1.txt",
                word_count=4,
                summary="早期稿",
                source_type="generated",
            ),
            GenerationVersion(
                version_id="version-current",
                chapter_id=self.chapter.id,
                version_number=2,
                is_current=1,
                content_file_path="v2.txt",
                word_count=4,
                summary="现行稿",
                source_type="dialogue_edit",
            ),
        ])
        self.db.commit()

        @contextmanager
        def session_scope():
            yield self.db

        def save_content(chapter_id: int, version_id: str, content: str) -> str:
            self.contents[version_id] = content
            return version_id

        self.patches = [
            patch("app.agents_v3.persistence.get_business_db", session_scope),
            patch("app.agents_v3.persistence._save_version_content", save_content),
            patch("app.agents_v3.persistence._read_version_content", lambda path: self.contents[path]),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.db.close()
        self.engine.dispose()

    def test_restore_creates_new_current_version_without_rewriting_history(self):
        result = WorkflowPersistence.set_current_version(self.chapter.id, "version-old")

        self.assertTrue(result["success"])
        self.assertTrue(result["restored"])
        self.assertEqual(result["content"], "历史正文")
        self.assertEqual(self.chapter.content, "历史正文")
        versions = self.db.query(GenerationVersion).filter(
            GenerationVersion.chapter_id == self.chapter.id,
        ).order_by(GenerationVersion.version_number.asc()).all()
        self.assertEqual([item.version_number for item in versions], [1, 2, 3])
        self.assertEqual([item.is_current for item in versions], [0, 0, 1])
        self.assertEqual(versions[0].version_id, "version-old")
        self.assertEqual(versions[0].source_type, "generated")
        self.assertEqual(versions[2].source_type, "restored")
        self.assertEqual(versions[2].source_version_id, "version-old")
        self.assertEqual(self.contents[versions[2].content_file_path], "历史正文")

    def test_manual_snapshot_requires_exact_saved_content_and_is_idempotent(self):
        snapshot = WorkflowPersistence.create_manual_version(self.chapter.id, "当前正文")
        self.assertEqual(snapshot["source_type"], "dialogue_edit")
        self.assertEqual(snapshot["version_id"], "version-current")
        self.assertIsNone(WorkflowPersistence.create_manual_version(self.chapter.id, "过期草稿"))

    def test_version_content_and_favorite_are_scoped_to_the_chapter(self):
        self.assertIsNone(WorkflowPersistence.get_version_content(self.chapter.id + 10, "version-old"))
        self.assertEqual(WorkflowPersistence.get_version_content(self.chapter.id, "version-old"), "历史正文")
        favorite = WorkflowPersistence.set_version_favorite(self.chapter.id, "version-old", True)
        self.assertEqual(favorite["is_favorite"], 1)
        self.assertIsNone(WorkflowPersistence.set_version_favorite(self.chapter.id + 10, "version-old", False))

    def test_restore_rejects_a_stale_editor_snapshot(self):
        result = WorkflowPersistence.set_current_version(
            self.chapter.id,
            "version-old",
            expected_content="编辑区旧快照",
        )

        self.assertFalse(result["success"])
        self.assertTrue(result["conflict"])
        self.assertEqual(self.chapter.content, "当前正文")
        self.assertEqual(self.db.query(GenerationVersion).count(), 2)


if __name__ == "__main__":
    unittest.main()
