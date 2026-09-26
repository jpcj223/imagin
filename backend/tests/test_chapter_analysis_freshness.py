"""章节分析正文来源和变化提案审核的回归测试。"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents.context import build_context_preview
from app.db.session import Base
from app.models.business import Chapter, ChapterChangeProposal, Project
from app.services.chapter_change_proposals.drafts import list_proposals
from app.services.chapter_change_proposals.review import review_proposal
from app.services.chapter_content import content_fingerprint, content_has_changed


class ChapterAnalysisFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.db.add(Project(id=1, name="新鲜度测试项目"))
        self.chapter = Chapter(project_id=1, chapter_no=1, title="第1章", content="分析时的正文", status="draft")
        self.db.add(self.chapter)
        self.db.flush()
        self.proposal = ChapterChangeProposal(
            proposal_id="proposal-1",
            proposal_key="proposal-key-1",
            project_id=1,
            chapter_id=self.chapter.id,
            entity_type="memory",
            operation="create",
            target_label="测试记忆",
            proposed_value="{}",
            source_content_hash=content_fingerprint(self.chapter.content),
            status="pending",
        )
        self.db.add(self.proposal)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_fingerprint_distinguishes_changed_text_and_unknown_legacy_source(self):
        self.assertFalse(content_has_changed(content_fingerprint("正文"), "正文"))
        self.assertTrue(content_has_changed(content_fingerprint("旧正文"), "新正文"))
        self.assertIsNone(content_has_changed(None, "无法追溯的正文"))

    def test_changed_chapter_marks_proposal_stale_and_blocks_writeback(self):
        self.chapter.content = "分析后修改的正文"
        self.db.commit()

        items = list_proposals(self.db, 1, self.chapter.id)
        self.assertTrue(items[0]["is_stale"])
        with self.assertRaisesRegex(ValueError, "正文已在分析后修改"):
            review_proposal(self.db, 1, self.chapter.id, "proposal-1", "approve")
        self.assertEqual(self.proposal.status, "pending")

    def test_legacy_proposal_without_source_fingerprint_requires_reanalysis(self):
        self.proposal.source_content_hash = None
        self.db.commit()
        self.assertTrue(list_proposals(self.db, 1, self.chapter.id)[0]["is_stale"])
        with self.assertRaisesRegex(ValueError, "没有正文来源记录"):
            review_proposal(self.db, 1, self.chapter.id, "proposal-1", "approve")

    def test_context_preview_labels_required_manual_recommended_and_system_sources(self):
        fixture = {
            "world": {"title": "世界总览", "rules": "潮汐规律"},
            "outline": {"title": "出航", "description": "整顿船队"},
            "world_settings": [
                {"id": 10, "title": "潮汐", "category": "rule"},
                {"id": 11, "title": "海图", "category": "location"},
                {"id": 12, "title": "航道", "category": "location"},
            ],
            "characters": [{"id": 20, "name": "江澜"}],
            "organizations": [],
            "foreshadowings": [],
            "recent_summaries": [{"id": 30, "summary": "前章内容"}],
            "long_term_memories": [{"memory_id": "m1", "title": "船队规则"}],
        }
        selection = {"world_setting_ids": [10, 11]}
        manual_selection = {"world_setting_ids": [10]}
        with patch("app.agents.context.build_chapter_context", return_value=fixture):
            preview = build_context_preview(1, 2, 9, "", selection, manual_selection)

        self.assertEqual([item["label"] for item in preview["required_context"]], ["本章大纲", "项目世界观"])
        self.assertEqual([item["selection_source"] for item in preview["world_settings"]], [
            "manual", "recommended", "automatic",
        ])
        self.assertEqual(preview["recent_summaries"][0]["selection_source"], "system")
        self.assertEqual(preview["long_term_memories"][0]["selection_source"], "system")


if __name__ == "__main__":
    unittest.main()
