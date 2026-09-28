"""模型单价、缓存 Token 解析和历史价格迁移回归测试。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.core.llm import _attach_pricing, _normalize_token_usage, get_active_model_config
from app.db.migrations.core.v024_model_token_prices import upgrade
from app.models.core.model_config import ModelConfig
from app.schemas.core.models import ModelConfigCreate, ModelConfigUpdate


class ModelTokenPricingTests(unittest.TestCase):
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
