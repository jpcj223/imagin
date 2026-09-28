"""章节生成设置及可续跑中断的回归测试。"""
from __future__ import annotations

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.agents_v3.generation_options import (
    DEFAULT_GENERATION_OPTIONS,
    normalize_generation_options,
    target_word_range,
)
from app.agents_v3.workflow_engine import (
    StepStatus,
    WorkflowEngine,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTemplate,
)
from app.agents_v3.persistence import WorkflowPersistence
from app.agents_v3.presets import create_writer_agent


class GenerationOptionsTests(unittest.TestCase):
    def test_defaults_and_bounds_are_normalized(self):
        self.assertEqual(
            normalize_generation_options(None), DEFAULT_GENERATION_OPTIONS
        )
        normalized = normalize_generation_options({
            "writer_variant": "not-a-variant",
            "temperature": 8,
            "target_word_count": 100,
            "active_skills": ["emotion", "unknown", "emotion", 1],
        })
        self.assertEqual(normalized["writer_variant"], "default")
        self.assertEqual(normalized["temperature"], 2.0)
        self.assertEqual(normalized["target_word_count"], 500)
        self.assertEqual(normalized["active_skills"], ["emotion"])

    def test_writer_controls_change_real_agent_parameters(self):
        engine = WorkflowEngine.__new__(WorkflowEngine)
        engine.generation_options = normalize_generation_options({
            "writer_variant": "shuangwen",
            "temperature": 1.1,
            "target_word_count": 4200,
            "active_skills": ["character", "foreshadow"],
        })
        writer = WorkflowStep(step_id="writer", agent_type="writer", variant="default")
        planner = WorkflowStep(step_id="planner", agent_type="planner", variant="detailed")

        variant, params = engine._step_variant_and_params(writer, "avoid repetition", "fast")
        self.assertEqual(variant, "shuangwen")
        self.assertEqual(params["temperature"], 1.1)
        self.assertEqual(params["target_word_count"], 4200)
        self.assertEqual(params["target_word_min"], 3780)
        self.assertEqual(params["target_word_max"], 4620)
        self.assertEqual(params["max_tokens"], 7392)
        self.assertIn("人物", params["writing_skill_guidance"])
        self.assertIn("伏笔", params["writing_skill_guidance"])
        self.assertNotIn("世界观", params["writing_skill_guidance"])
        self.assertEqual(engine._step_variant_and_params(planner, "", "medium")[0], "detailed")

    def test_writer_prompt_contains_selected_style_length_and_focus(self):
        writer = create_writer_agent("shuangwen")
        messages = writer._build_messages(
            {"chapter_no": 7, "writing_plan": "推进冲突", "_writing_context": "当前设定"},
            {
                "rhythm_level": "fast",
                "target_word_count": 2400,
                "target_word_min": 2160,
                "target_word_max": 2640,
                "writing_skill_guidance": "- 按本章大纲推进。\n- 适度回收伏笔。",
                "instruction": "保持克制",
            },
        )
        prompt = "\n".join(message["content"] for message in messages)
        self.assertIn("字数目标：2400 字；验收范围 2160-2640 字", prompt)
        self.assertIn("正文去除空白后的字符数", prompt)
        self.assertIn("适度回收伏笔", prompt)
        self.assertIn("保持克制", prompt)
        self.assertIn("当前设定", prompt)

    def test_word_range_uses_ten_percent_and_rounds_inward(self):
        self.assertEqual(target_word_range(3000), (2700, 3300))
        self.assertEqual(target_word_range(2401), (2161, 2641))

    def test_paused_step_restores_as_pending_with_saved_options(self):
        engine = WorkflowEngine.__new__(WorkflowEngine)
        engine.run_id = "paused-run-test"
        engine.template = WorkflowTemplate(name="quick_write", label="快速写作")
        engine.status = WorkflowStatus.PENDING
        engine.generation_options = normalize_generation_options(None)
        engine.step_statuses = {"writer": StepStatus.PENDING}

        state = {
            "run_info": {
                "status": "paused",
                "variant_selections": {
                    "generation_options": {
                        "writer_variant": "wenqing",
                        "temperature": 0.6,
                        "target_word_count": 2400,
                        "active_skills": ["emotion"],
                    }
                },
            },
            "step_statuses": {"writer": "paused"},
            "step_results": {},
            "session_context": {"interrupted_partial_content": "未完成片段"},
        }
        with patch.object(WorkflowPersistence, "restore_workflow_state", return_value=state):
            engine._restore_from_db()

        self.assertEqual(engine.status, WorkflowStatus.PAUSED)
        self.assertEqual(engine.step_statuses["writer"], StepStatus.PENDING)
        self.assertEqual(engine.generation_options["writer_variant"], "wenqing")
        self.assertEqual(engine.session_context["interrupted_partial_content"], "未完成片段")

    def test_user_pause_keeps_partial_output_and_does_not_complete_step(self):
        class StreamingAgent:
            meta = SimpleNamespace(supports_streaming=True)

            def run_stream(self, _context, _params):
                yield {"type": "delta", "content": "先到的正文"}
                yield {"type": "delta", "content": "不应继续写入"}
                yield {"type": "done", "content": "完整正文"}

        engine = WorkflowEngine.__new__(WorkflowEngine)
        engine.project_id = 1
        engine.run_id = "pause-stream-test"
        engine.template = WorkflowTemplate(
            name="quick_write",
            label="快速写作",
            steps=[WorkflowStep(step_id="writer", agent_type="writer", label="写作")],
        )
        engine.status = WorkflowStatus.PENDING
        engine.generation_options = normalize_generation_options(None)
        engine.session_context = {}
        engine.step_results = {}
        engine.step_statuses = {"writer": StepStatus.PENDING}
        engine._cancel_event = threading.Event()
        engine._build_step_context = lambda *_args: {}

        with (
            patch.object(WorkflowPersistence, "resume_run", return_value=True),
            patch.object(WorkflowPersistence, "update_run_status") as update_run,
            patch.object(WorkflowPersistence, "create_step_record"),
            patch.object(WorkflowPersistence, "update_step_record") as update_step,
            patch("app.agents_v3.presets.get_agent", return_value=StreamingAgent()),
        ):
            events = engine.run_stream(chapter_no=1)
            self.assertEqual(next(events)["type"], "step_start")
            # 流式正文前会先发送本步骤实际加载的资料和配置快照。
            self.assertEqual(next(events)["type"], "step_context")
            first_delta = next(events)
            self.assertEqual(first_delta["type"], "delta")
            self.assertEqual(first_delta["content"], "先到的正文")
            engine._cancel_event.set()
            final_event = next(events)

        self.assertEqual(final_event["type"], "workflow_done")
        self.assertEqual(final_event["status"], "paused")
        self.assertEqual(final_event["session_context"]["interrupted_partial_content"], "先到的正文")
        self.assertEqual(engine.step_statuses["writer"], StepStatus.PAUSED)
        self.assertNotIn("writer", engine.step_results)
        self.assertEqual(update_step.call_args.kwargs["status"], "paused")
        self.assertTrue(any(call.kwargs.get("status") == "paused" for call in update_run.call_args_list))


if __name__ == "__main__":
    unittest.main()
