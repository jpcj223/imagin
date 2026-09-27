"""对话改稿流式响应与中断行为测试。"""
from __future__ import annotations

import unittest
import json
from unittest.mock import patch

from app.agents.chapter_edit import _prepare_chapter_edit_messages, propose_chapter_edit_stream


class ChapterEditStreamTests(unittest.TestCase):
    def test_prompt_uses_recent_dialogue_and_selected_project_context(self):
        context = {
            "outline": {"title": "沉城", "description": "沿旧航线调查"},
            "world": {"rules": "潮痕只能保留短时回声"},
            "characters": [{"name": "江澜", "identity": "打捞员", "motivation": "查清记录"}],
            "organizations": [],
            "foreshadowings": [],
            "recent_summaries": [{"summary": "刚发现旧航道标记"}],
            "long_term_memories": [{
                "memory_type": "world_rule",
                "title": "潮痕规律",
                "content_summary": "潮痕只能保留短时回声。",
                "source_type": "chapter_analysis",
                "source_chapter_no": 1,
            }],
        }
        conversation = [
            {"role": "user", "content": f"历史轮次{i}"}
            for i in range(10)
        ]
        selection = {"character_ids": [4], "organization_ids": [3]}

        with patch("app.agents.chapter_edit.build_chapter_context", return_value=context) as build_context:
            messages, scope, _, _ = _prepare_chapter_edit_messages(
                project_id=1,
                chapter_no=3,
                chapter_title="潮痕",
                outline_id=9,
                content="潮痕只能保留短时回声。",
                scope="chapter",
                selection_start=None,
                selection_end=None,
                instruction="延续上文，但保持设定一致",
                conversation=conversation,
                context_selection=selection,
            )

        payload = json.loads(messages[-1]["content"])
        self.assertEqual(scope, "chapter")
        self.assertEqual([turn["content"] for turn in payload["对话上下文"]], [f"历史轮次{i}" for i in range(2, 10)])
        self.assertEqual(payload["相关设定"]["本章大纲"]["标题"], "沉城")
        self.assertEqual(payload["相关设定"]["前情摘要"], ["刚发现旧航道标记"])
        self.assertEqual(payload["相关设定"]["已确认长期记忆"], [{
            "类别": "world_rule",
            "标题": "潮痕规律",
            "内容": "潮痕只能保留短时回声。",
            "来源": "chapter_analysis",
            "来源章节": 1,
        }])
        build_context.assert_called_once_with(1, 3, 9, query="延续上文，但保持设定一致", selection=selection)

    def test_stream_returns_only_status_then_structured_candidate(self):
        response = (
            '{"action":"proposal","reply":"已压缩重复描写。",'
            '"candidate_text":"更紧凑的正文"}'
        )

        def model_stream(*_args, **_kwargs):
            yield {"type": "delta", "content": response[:30]}
            yield {"type": "delta", "content": response[30:]}
            yield {"type": "usage", "usage": {"total_tokens": 42}}

        with (
            patch("app.agents.chapter_edit._prepare_chapter_edit_messages", return_value=([{"role": "user", "content": ""}], "chapter", None, None)),
            patch("app.agents.chapter_edit.chat_completion_stream_with_usage", side_effect=model_stream),
        ):
            events = list(propose_chapter_edit_stream())

        self.assertEqual(events[0]["type"], "stage")
        self.assertIn("相关记忆", events[0]["stage"])
        self.assertIn("本会话历史", events[0]["stage"])
        self.assertTrue(all("content" not in event for event in events[:-1]))
        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(events[-1]["candidate_text"], "更紧凑的正文")
        self.assertEqual(events[-1]["usage"]["total_tokens"], 42)

    def test_closing_dialogue_generator_closes_model_stream(self):
        closed = []

        def model_stream(*_args, **_kwargs):
            try:
                yield {"type": "delta", "content": "partial"}
                yield {"type": "delta", "content": "more"}
            finally:
                closed.append(True)

        with (
            patch("app.agents.chapter_edit._prepare_chapter_edit_messages", return_value=([{"role": "user", "content": ""}], "chapter", None, None)),
            patch("app.agents.chapter_edit.chat_completion_stream_with_usage", side_effect=model_stream),
        ):
            events = propose_chapter_edit_stream()
            self.assertEqual(next(events)["type"], "stage")
            self.assertEqual(next(events)["type"], "progress")
            events.close()

        self.assertEqual(closed, [True])


if __name__ == "__main__":
    unittest.main()
