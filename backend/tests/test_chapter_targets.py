"""章节下一章解析规则的回归测试。"""
import unittest
from unittest.mock import patch
from fastapi import HTTPException

from app.services.chapter_targets import require_next_chapter_target, resolve_next_chapter_target


class ResolveNextChapterTargetTests(unittest.TestCase):
    def test_uses_saved_outline_order_and_skips_volume_nodes(self):
        result = resolve_next_chapter_target(
            [
                {"id": 8, "node_type": "volume", "title": "第一卷"},
                {"id": 12, "node_type": "chapter", "chapter_no": 2, "sort_index": 2, "title": "后章"},
                {"id": 11, "node_type": "chapter", "chapter_no": 1, "sort_index": 1, "title": "先章"},
            ],
            [{"id": 91, "outline_id": 11, "chapter_no": 1, "content": "已有正文"}],
        )

        self.assertEqual(result["outline_id"], 12)
        self.assertEqual(result["chapter_no"], 2)
        self.assertEqual(result["outline_title"], "后章")

    def test_reuses_blank_draft_for_next_outline(self):
        result = resolve_next_chapter_target(
            [{"id": 2, "node_type": "chapter", "chapter_no": 1, "title": "序章"}],
            [{"id": 7, "outline_id": 2, "chapter_no": 1, "content": "  "}],
        )

        self.assertTrue(result["available"])
        self.assertEqual(result["chapter_id"], 7)

    def test_outline_identity_survives_chapter_number_reordering(self):
        result = resolve_next_chapter_target(
            [
                {"id": 20, "node_type": "chapter", "chapter_no": 1, "title": "拖动后的第一章"},
                {"id": 10, "node_type": "chapter", "chapter_no": 2, "title": "拖动后的第二章"},
            ],
            [
                # 旧章节号已经过时，稳定的 outline_id 仍能正确识别已有正文。
                {"id": 55, "outline_id": 10, "chapter_no": 1, "content": "第二章正文"},
            ],
        )

        self.assertEqual(result["outline_id"], 20)

    def test_legacy_chapter_number_is_only_used_when_unique(self):
        unique = resolve_next_chapter_target(
            [{"id": 2, "node_type": "chapter", "chapter_no": 1}],
            [{"id": 3, "outline_id": None, "chapter_no": 1, "content": "旧正文"}],
        )
        ambiguous = resolve_next_chapter_target(
            [
                {"id": 2, "node_type": "chapter", "chapter_no": 1},
                {"id": 4, "node_type": "chapter", "chapter_no": 1},
            ],
            [{"id": 3, "outline_id": None, "chapter_no": 1, "content": "旧正文"}],
        )

        self.assertFalse(unique["available"])
        self.assertTrue(ambiguous["available"])
        self.assertIsNone(ambiguous["chapter_id"])

    def test_explains_missing_or_exhausted_outlines(self):
        missing = resolve_next_chapter_target([], [])
        exhausted = resolve_next_chapter_target(
            [{"id": 1, "node_type": "chapter", "chapter_no": 1}],
            [{"id": 5, "outline_id": 1, "content": "正文"}],
        )

        self.assertFalse(missing["available"])
        self.assertIn("补充章节大纲", missing["reason"])
        self.assertFalse(exhausted["available"])
        self.assertIn("下一章大纲", exhausted["reason"])


class RequireNextChapterTargetTests(unittest.TestCase):
    def setUp(self):
        self.target = {
            "available": True,
            "reason": "",
            "outline_id": 9,
            "chapter_no": 4,
            "chapter_id": 81,
        }

    @patch("app.services.chapter_targets.get_project_next_chapter_target")
    def test_returns_canonical_target_when_request_is_current(self, get_target):
        get_target.return_value = self.target

        result = require_next_chapter_target(1, outline_id=9, chapter_no=4, chapter_id=81)

        self.assertIs(result, self.target)

    @patch("app.services.chapter_targets.get_project_next_chapter_target")
    def test_rejects_old_or_stale_chapter_targets(self, get_target):
        get_target.return_value = self.target

        for outline_id, chapter_no, chapter_id in ((8, 4, None), (9, 3, None), (9, 4, 80)):
            with self.subTest(outline_id=outline_id, chapter_no=chapter_no, chapter_id=chapter_id):
                with self.assertRaises(HTTPException) as error:
                    require_next_chapter_target(1, outline_id, chapter_no, chapter_id)
                self.assertEqual(error.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
