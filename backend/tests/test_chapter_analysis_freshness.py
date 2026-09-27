"""章节分析正文来源和变化提案审核的回归测试。"""
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents.context import build_context_preview
from app.db.session import Base
from app.models.business import Chapter, ChapterChangeProposal, MemoryItem, Project
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
            version_id="version-source-1",
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

    def test_approved_memory_is_traceable_listable_and_idempotent(self):
        self.proposal.proposed_value = json.dumps({
            "memory_type": "world_rule",
            "title": "潮痕回声限制",
            "content": "潮痕设备只能读取短时回声。",
            "content_summary": "潮痕设备读取回声有时间限制。",
            "importance": 80,
            "metadata_json": {"source": "analysis"},
        }, ensure_ascii=False)
        self.db.commit()

        result = review_proposal(self.db, 1, self.chapter.id, "proposal-1", "approve")
        self.db.commit()
        self.assertFalse(result["idempotent"])

        memory = self.db.query(MemoryItem).filter_by(id=self.proposal.applied_entity_id).one()
        self.assertEqual(memory.project_id, 1)
        self.assertEqual(memory.memory_type, "world_rule")
        self.assertEqual(memory.title, "潮痕回声限制")
        self.assertEqual(memory.content, "潮痕设备只能读取短时回声。")
        self.assertEqual(memory.source_type, "chapter_analysis")
        self.assertEqual(memory.source_ref, f"chapter:{self.chapter.id}:proposal:proposal-1")
        provenance = json.loads(memory.metadata_json)["analysis_provenance"]
        self.assertEqual(provenance, {
            "chapter_id": self.chapter.id,
            "chapter_no": 1,
            "version_id": "version-source-1",
            "source_content_hash": content_fingerprint(self.chapter.content),
            "proposal_id": "proposal-1",
        })

        repeated = review_proposal(self.db, 1, self.chapter.id, "proposal-1", "approve")
        self.assertTrue(repeated["idempotent"])
        self.assertEqual(self.db.query(MemoryItem).filter_by(project_id=1).count(), 1)

        @contextmanager
        def test_db():
            yield self.db

        with patch("app.db.session.get_business_db", test_db):
            from app.api.agents_v3 import list_memory_items

            listed = list_memory_items(project_id=1, keyword="proposal-1")
        self.assertEqual(listed["total"], 1)
        self.assertEqual(listed["all_total"], 1)
        self.assertEqual(listed["items"][0]["source_ref"], memory.source_ref)
        self.assertEqual(listed["items"][0]["memory_type"], "world_rule")

    def test_rejected_memory_proposal_does_not_write_long_term_memory(self):
        self.proposal.proposed_value = json.dumps({
            "memory_type": "world_rule",
            "title": "不应写入",
            "content": "只有审核确认后才写入。",
        }, ensure_ascii=False)
        self.db.commit()

        result = review_proposal(self.db, 1, self.chapter.id, "proposal-1", "reject")
        self.db.commit()

        self.assertEqual(result["proposal"]["status"], "rejected")
        self.assertEqual(self.db.query(MemoryItem).filter_by(project_id=1).count(), 0)

    def test_memory_metadata_requires_object_shape(self):
        self.proposal.proposed_value = json.dumps({
            "memory_type": "world_rule",
            "title": "不合法元数据",
            "content": "元数据只能是对象。",
            "metadata_json": ["错误结构"],
        }, ensure_ascii=False)
        self.db.commit()

        with self.assertRaisesRegex(ValueError, "metadata_json 必须是 JSON 对象"):
            review_proposal(self.db, 1, self.chapter.id, "proposal-1", "approve")
        self.db.rollback()
        self.assertEqual(self.proposal.status, "pending")
        self.assertEqual(self.db.query(MemoryItem).filter_by(project_id=1).count(), 0)

    def test_context_preview_labels_required_manual_recommended_and_system_sources(self):
        fixture = {
            "volume_outline": {
                "id": 8,
                "title": "潮汐之下",
                "volume_no": 1,
                "description": "第一卷描述",
                "core_events": "整顿船队",
                "locations": "雾港",
                "climax": "发现旧航线",
            },
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

        self.assertEqual([item["label"] for item in preview["required_context"]], [
            "大纲总览", "当前卷纲", "当前章细纲", "项目世界观",
        ])
        current_volume = next(item for item in preview["required_context"] if item["label"] == "当前卷纲")
        self.assertIn("发现旧航线", current_volume["content"])
        self.assertEqual(preview["volume_outline"]["id"], 8)
        self.assertEqual([item["selection_source"] for item in preview["world_settings"]], [
            "manual", "recommended", "automatic",
        ])
        self.assertEqual(preview["recent_summaries"][0]["selection_source"], "system")
        self.assertEqual(preview["long_term_memories"][0]["selection_source"], "system")


if __name__ == "__main__":
    unittest.main()
