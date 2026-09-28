"""模型单价、缓存 Token 解析和历史价格迁移回归测试。"""
from __future__ import annotations

import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.core.llm import (
    LLMCancelled,
    _attach_pricing,
    _build_payload,
    _normalize_token_usage,
    chat_completion_with_usage,
    chat_completion_stream_with_usage,
    get_active_model_config,
)
from app.db.migrations.core.v024_model_token_prices import upgrade
from app.models.core.model_config import ModelConfig
from app.schemas.core.models import ModelConfigCreate, ModelConfigUpdate


class ModelTokenPricingTests(unittest.TestCase):
    def test_stream_requests_provider_usage_for_cost_estimation(self):
        payload = _build_payload({"model": "qwen-test"}, [], stream=True)

        self.assertTrue(payload["stream"])
        self.assertEqual(payload["stream_options"], {"include_usage": True})

    def test_stream_usage_chunk_is_counted_even_when_it_has_no_choices(self):
        class StreamResponse:
            def __init__(self):
                self.lines = [
                    b'data: {"choices":[{"delta":{"content":"hello"}}]}\n',
                    b'data: {"choices":[],"usage":{"prompt_tokens":1000,"completion_tokens":100}}\n',
                    b"data: [DONE]\n",
                ]

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def __iter__(self):
                return iter(self.lines)

        config = {
            "model": "qwen-test",
            "base_url": "https://example.invalid/v1",
            "api_key": "test-key",
            "input_price_per_million": 0.5,
            "output_price_per_million": 4,
        }
        with patch("app.core.llm.get_active_model_config", return_value=config), patch(
            "app.core.llm._make_urlopen", return_value=StreamResponse()
        ):
            events = list(chat_completion_stream_with_usage([{"role": "user", "content": "test"}]))

        self.assertEqual(events[0], {"type": "delta", "content": "hello"})
        self.assertEqual(events[1]["type"], "usage")
        self.assertEqual(events[1]["usage"]["cost_cny"], 0.0009)

    def test_cancellation_closes_a_blocked_non_streaming_response(self):
        class BlockingResponse:
            def __init__(self):
                self.read_started = threading.Event()
                self.closed = threading.Event()

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

            def read(self):
                self.read_started.set()
                self.closed.wait(timeout=3)
                raise OSError("response closed")

            def close(self):
                self.closed.set()

        response = BlockingResponse()
        cancel_event = threading.Event()
        config = {
            "model": "qwen-test",
            "base_url": "https://example.invalid/v1",
            "api_key": "test-key",
        }
        with patch("app.core.llm.get_active_model_config", return_value=config), patch(
            "app.core.llm._make_urlopen", return_value=response
        ), ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                chat_completion_with_usage,
                [{"role": "user", "content": "test"}],
                cancel_event=cancel_event,
            )
            self.assertTrue(response.read_started.wait(timeout=1))
            cancel_event.set()
            with self.assertRaises(LLMCancelled):
                future.result(timeout=1)

    def test_normalizes_cached_input_token_aliases(self):
        usage = _normalize_token_usage({
            "prompt_tokens": 1200,
            "completion_tokens": 300,
            "prompt_tokens_details": {"cached_tokens": 450},
        })

        self.assertEqual(usage, {
            "input_tokens": 1200,
            "output_tokens": 300,
            "total_tokens": 1500,
            "cached_input_tokens": 450,
        })

    def test_estimates_cost_from_call_time_rates_and_cached_rate(self):
        usage = _attach_pricing(
            {"input_tokens": 1000, "output_tokens": 100, "cached_input_tokens": 400},
            {
                "id": 3,
                "name": "当前配置",
                "model": "model-x",
                "input_price_per_million": 2.0,
                "output_price_per_million": 6.0,
                "cached_input_price_per_million": 0.5,
            },
        )

        self.assertEqual(usage["cost_cny"], 0.002)
        self.assertEqual(usage["pricing_snapshot"]["model"], "model-x")
        self.assertEqual(usage["pricing_snapshot"]["cached_input_price_per_million"], 0.5)
        self.assertFalse(usage["pricing_snapshot"]["cached_input_uses_input_price"])

    def test_missing_cached_rate_falls_back_to_input_rate(self):
        usage = _attach_pricing(
            {"input_tokens": 1000, "output_tokens": 100, "cached_input_tokens": 400},
            {"input_price_per_million": 2, "output_price_per_million": 6},
        )

        self.assertEqual(usage["cost_cny"], 0.0026)
        self.assertTrue(usage["pricing_snapshot"]["cached_input_uses_input_price"])

    def test_missing_base_rate_does_not_invent_a_cost(self):
        usage = _attach_pricing(
            {"input_tokens": 1000, "output_tokens": 100},
            {"input_price_per_million": 2},
        )

        self.assertIsNone(usage["cost_cny"])
        self.assertEqual(usage["pricing_snapshot"]["output_price_per_million"], None)

    def test_price_migration_is_idempotent_for_existing_config_table(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE model_configs (id INTEGER PRIMARY KEY, model TEXT)"))
        with Session(engine) as db:
            upgrade(db)
            upgrade(db)
            db.commit()

        columns = {column["name"] for column in inspect(engine).get_columns("model_configs")}
        self.assertTrue({
            "input_price_per_million",
            "output_price_per_million",
            "cached_input_price_per_million",
        }.issubset(columns))
        engine.dispose()

    def test_active_model_lookup_reads_the_configured_core_database(self):
        active = ModelConfig(
            id=8,
            name="核心库模型",
            base_url="https://example.invalid/v1",
            api_key="secret",
            model="model-y",
            is_active=1,
            input_price_per_million=1.25,
            output_price_per_million=3.5,
        )
        session = MagicMock()
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = active
        context_manager = MagicMock()
        context_manager.__enter__.return_value = session
        with patch("app.core.llm.get_core_db", return_value=context_manager):
            config = get_active_model_config()

        self.assertEqual(config["id"], 8)
        self.assertEqual(config["input_price_per_million"], 1.25)
        self.assertEqual(config["model"], "model-y")

    def test_price_schema_accepts_zero_and_optional_cache_rate(self):
        config = ModelConfigCreate(
            base_url="https://example.invalid/v1",
            api_key="secret",
            model="model-z",
            input_price_per_million=0,
            output_price_per_million=2.2,
            cached_input_price_per_million=None,
        )
        update = ModelConfigUpdate(cached_input_price_per_million=0)
        self.assertEqual(config.input_price_per_million, 0)
        self.assertIsNone(config.cached_input_price_per_million)
        self.assertEqual(update.cached_input_price_per_million, 0)


if __name__ == "__main__":
    unittest.main()
