"""章节规划、正文写作、分析沉淀的职责边界回归测试。"""
from __future__ import annotations

import unittest
import threading
from unittest.mock import patch

from app.agents_v3.base import AgentMeta
from app.agents_v3.dynamic import DynamicAgent
from app.agents_v3.presets import (
    create_analyzer_agent,
    create_planner_agent,
    create_polisher_agent,
    create_writer_agent,
)
from app.core.llm import LLMCancelled
from app.skills.writing.core_planning import CorePlanningSkill
from app.skills.writing.core_writing import CoreWritingSkill


class GenerationPromptRoleTests(unittest.TestCase):
    def test_all_smart_mode_steps_support_streaming_for_responsive_cancellation(self):
        agents = [
            create_planner_agent(),
            create_writer_agent(),
            create_polisher_agent(),
            create_analyzer_agent(),
        ]

        self.assertTrue(all(agent.meta.supports_streaming for agent in agents))

    def test_dynamic_agent_does_not_turn_user_cancellation_into_fallback_output(self):
        agent = DynamicAgent(meta=AgentMeta(name="cancel-test", label="取消测试"))
        with patch("app.agents_v3.dynamic.chat_completion_with_usage", side_effect=LLMCancelled("stop")):
            with self.assertRaises(LLMCancelled):
                agent.run({}, {"_cancel_event": threading.Event()})

    def test_planner_prompt_requires_ordered_causal_beats_without_duplicate_outline(self):
        planner = create_planner_agent()
        messages = planner._build_messages(
            {
                "chapter_no": 8,
                "generation_outline_context_text": (
                    "【全书总览】主线\n【前一卷】承接\n【当前卷】本卷目标\n"
                    "【下一卷】远期方向\n【当前章】当前事件\n【下一章】后续钩子"
                ),
                "_planning_context": "【相关人物】\n- 林澄：主角",
                # 旧模板字段即使存在也不应再将整份当前卷纲重复拼进规划 Prompt。
                "volume_outline_text": "不应重复的当前卷全文",
                "outline_title": "不应重复的章标题",
                "outline_desc": "不应重复的章概述",
            },
            {},
        )
        prompt = "\n".join(message["content"] for message in messages)

        self.assertIn("第 8 章", prompt)
        self.assertIn("按顺序列 4-7 步", prompt)
        self.assertIn("行动/冲突、结果或新信息", prompt)
        self.assertIn("下一章事件", prompt)
        self.assertIn("【当前卷】本卷目标", prompt)
        self.assertEqual(prompt.count("【相关人物】\n- 林澄：主角"), 1)
        self.assertEqual(prompt.count("不应重复的当前卷全文"), 0)
        self.assertEqual(prompt.count("不应重复的章标题"), 0)
        self.assertEqual(prompt.count("不应重复的章概述"), 0)

    def test_planner_context_contains_relevant_entities_but_not_resolved_foreshadows(self):
        skill = CorePlanningSkill()
        context = skill.pre_process(
            {
                "generation_outline_context_text": "已包括相邻卷章纲",
                "characters": [{
                    "name": "林澄",
                    "role_type": "主角",
                    "personality": "谨慎而果断",
                    "motivation": "查清失联原因",
                }],
                "foreshadowings": [
                    {"keyword": "无编号海图", "status": "developing", "description": "背面留有旧印记"},
                    {"keyword": "已回收线索", "status": "resolved", "description": "不应再进入规划"},
                ],
                "recent_summaries": [{"chapter_no": 7, "summary": "两人在雾中找到第二份海图"}],
            },
            {},
        )

        self.assertIn("已包括相邻卷章纲", context["generation_outline_context_text"])
        self.assertIn("林澄", context["_planning_context"])
        self.assertIn("查清失联原因", context["_planning_context"])
        self.assertIn("无编号海图", context["_planning_context"])
        self.assertIn("两人在雾中找到第二份海图", context["_planning_context"])
        self.assertNotIn("已回收线索", context["_planning_context"])

    def test_writer_context_includes_outline_once_and_keeps_planner_as_execution_guide(self):
        skill = CoreWritingSkill()
        context = skill.pre_process(
            {
                "project": {"name": "测试项目"},
                "world": {},
                "world_settings": [],
                "volume_outline": {"title": "会被连续纲覆盖的卷"},
                "outline": {"title": "会被连续纲覆盖的章", "description": "会被连续纲覆盖的概要"},
                "generation_outline_context_text": "【总览】\n【当前卷纲】会被连续纲覆盖的卷\n【当前章细纲】会被连续纲覆盖的章",
                "characters": [],
                "organizations": [],
                "foreshadowings": [],
                "recent_summaries": [],
                "long_term_memories": [],
                "writing_plan": "先发现异常，再确认矛盾",
            },
            {},
        )
        writer = create_writer_agent()
        prompt = "\n".join(message["content"] for message in writer._build_messages(
            context,
            {"chapter_no": 8, "target_word_count": 2400, "instruction": "保持克制"},
        ))

        self.assertEqual(context["_writing_context"].count("会被连续纲覆盖的卷"), 1)
        self.assertEqual(context["_writing_context"].count("会被连续纲覆盖的章"), 1)
        self.assertIn("先发现异常，再确认矛盾", prompt)
        self.assertEqual(prompt.count("大纲连续性资料（已包含总览"), 1)
        self.assertIn("不提前写完其核心事件", prompt)
        self.assertNotIn("本章大纲：会被连续纲覆盖的章", prompt)


if __name__ == "__main__":
    unittest.main()
