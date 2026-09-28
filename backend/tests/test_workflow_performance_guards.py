"""工作流慢请求上限、重复续传互斥与分析上下文裁剪回归测试。"""
from __future__ import annotations

import json
import threading
import time
import unittest
from unittest.mock import patch

from app.agents_v3.base import AgentMeta
from app.agents_v3.dynamic import DynamicAgent
from app.agents_v3.presets import create_analyzer_agent
from app.agents_v3.persistence import WorkflowPersistence
from app.agents_v3.workflow_engine import WorkflowEngine
from app.core.llm import LLMTimeout, _watch_response_cancellation, chat_completion_stream_with_usage
from app.skills.analysis.core_analysis import CoreAnalysisSkill


class WorkflowPerformanceGuardTests(unittest.TestCase):
    def test_llm_response_watcher_closes_on_absolute_deadline(self):
        class Response:
            closed = False

            def close(self):
                self.closed = True

        response = Response()
        stop_watching = _watch_response_cancellation(
            response,
            cancel_event=None,
            deadline=time.monotonic() + 0.08,
        )
        time.sleep(0.16)

        self.assertEqual(stop_watching(), "timeout")
        self.assertTrue(response.closed)

    def test_stream_timeout_is_absolute_even_when_provider_sends_heartbeats(self):
        class HeartbeatResponse:
            def __init__(self):
                self.closed = threading.Event()

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

            def __iter__(self):
                while not self.closed.wait(0.01):
                    yield b": keep-alive\n"

            def close(self):
                self.closed.set()

        response = HeartbeatResponse()
        config = {
            "model": "qwen-test",
            "base_url": "https://example.invalid/v1",
            "api_key": "test-key",
        }
        with patch("app.core.llm.get_active_model_config", return_value=config), patch(
            "app.core.llm._make_urlopen", return_value=response
        ), patch("app.core.llm._resolve_request_timeout", return_value=0.08):
            with self.assertRaisesRegex(LLMTimeout, "总耗时超过"):
                list(chat_completion_stream_with_usage([{"role": "user", "content": "test"}]))

        self.assertTrue(response.closed.is_set())

    def test_analyzer_timeout_is_shorter_than_other_generation_steps(self):
        analyzer = create_analyzer_agent()

        self.assertEqual(analyzer.params["_request_timeout_seconds"], 120)

    def test_timed_out_analyzer_discards_partial_structured_output(self):
        agent = DynamicAgent(
            meta=AgentMeta(name="analyzer-test", label="分析测试", agent_type="analyzer")
        )

        def partial_then_timeout(*_args, **_kwargs):
            yield {"type": "delta", "content": '{"summary":"不完整'}
            raise LLMTimeout("模拟超时")

        with patch(
            "app.agents_v3.dynamic.chat_completion_stream_with_usage",
            side_effect=partial_then_timeout,
        ) as model_stream:
            events = list(agent.run_stream({"content": "已完成章节"}, {"_request_timeout_seconds": 120}))

        self.assertEqual([event["type"] for event in events], ["done"])
        self.assertEqual(events[0]["content"], "")
        self.assertTrue(events[0]["source"].startswith("timeout:"))
        model_stream.assert_called_once()
        self.assertEqual(model_stream.call_args.kwargs["request_timeout_seconds"], 120)

    def test_timed_out_analysis_is_saved_as_unavailable_not_successful_memory(self):
        engine = WorkflowEngine.__new__(WorkflowEngine)
        engine.run_id = "analyzer-timeout-test"
        engine.session_context = {"analysis_entity_catalog": {"characters": []}}
        engine.step_results = {}
        step = type(
            "Step",
            (),
            {"agent_type": "analyzer", "step_id": "analyzer", "output_mapping": {}},
        )()
        result = {
            "source": "timeout: 模型请求总耗时超过 120 秒",
            "summary": "不应保留的摘要",
            "structured_analysis": {"summary": "不应沉淀"},
            "token_usage": None,
        }

        with patch.object(WorkflowPersistence, "update_step_record"):
            engine._save_step_output(step, result)

        self.assertEqual(result["analysis_status"], "unavailable")
        self.assertEqual(result["analysis_message"], "模型请求总耗时超过 120 秒")
        self.assertEqual(result["summary"], "")
        self.assertEqual(result["structured_analysis"], {})

    def test_same_workflow_cannot_run_two_streams_at_once(self):
        engine = WorkflowEngine.__new__(WorkflowEngine)
        engine.run_id = "workflow-lock-test"
        calls = [{"type": "step_start", "step_id": "writer"}]

        with patch.object(
            WorkflowEngine,
            "_run_stream_unlocked",
            side_effect=lambda **_kwargs: iter(calls),
        ):
            first = engine.run_stream(chapter_no=1)
            self.assertEqual(next(first)["type"], "step_start")

            concurrent = list(engine.run_stream(chapter_no=1))
            self.assertEqual(concurrent[0]["type"], "error")
            self.assertIn("仍有模型请求", concurrent[0]["message"])

            self.assertEqual(list(first), [])
            later = list(engine.run_stream(chapter_no=1))
            self.assertEqual(later[0]["type"], "step_start")

    def test_analyzer_context_keeps_mentioned_and_manually_selected_entities(self):
        skill = CoreAnalysisSkill()
        context = {
            "content": "江澜和玄鲸商会潜入海底，发现潮汐定位标。",
            "characters": [
                {"id": 1, "name": "江澜", "personality": "谨慎"},
                {"id": 2, "name": "林岚", "personality": "外向"},
            ],
            "organizations": [
                {"id": 7, "name": "玄鲸商会", "goal": "控制航道"},
                {"id": 8, "name": "远航局", "goal": "维护航道"},
            ],
            "world_settings": [
                {"id": 11, "title": "潮汐定位标", "rules": "随潮汐偏移"},
                {"id": 12, "title": "旧式信号灯", "rules": "以闪烁报码"},
            ],
            "foreshadowings": [
                {"id": 21, "keyword": "潮汐定位标", "description": "位置反复偏移"},
                {"id": 22, "keyword": "旧式信号灯", "description": "深海信号"},
            ],
            "manual_context_selection": {"character_ids": [2]},
            "context_selection": {"organization_ids": [8]},
            "world": {"title": "静潮纪", "rules": "海底存在潮汐现象"},
        }

        processed = skill.pre_process(context, {})
        references = json.loads(processed["_analysis_reference_context"])

        self.assertEqual([item["name"] for item in references["characters"]], ["江澜", "林岚"])
        self.assertEqual(
            [item["name"] for item in references["organizations"]], ["玄鲸商会", "远航局"]
        )
        self.assertEqual([item["title"] for item in references["world_settings"]], ["潮汐定位标"])
        self.assertEqual([item["keyword"] for item in references["foreshadowings"]], ["潮汐定位标"])
        self.assertLess(len(processed["_analysis_reference_context"]), 1200)


if __name__ == "__main__":
    unittest.main()
