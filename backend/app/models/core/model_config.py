"""模型配置表 ORM 模型（核心库）。"""
from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, func

from app.db.session import Base


class ModelConfig(Base):
    """OpenAI-compatible 模型连接配置。"""

    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, default="")
    base_url = Column(String(512), nullable=False, default="")
    api_key = Column(String(512), nullable=False, default="")
    model = Column(String(255), nullable=False, default="")
    is_active = Column(Integer, default=0)
    # 采样参数
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, nullable=True)
    top_p = Column(Float, default=0.9)
    frequency_penalty = Column(Float, default=0)
    presence_penalty = Column(Float, default=0)
    proxy_url = Column(String(512), default="")
    # 单价统一按人民币/百万 Token 录入；缓存输入价格可留空并回退到普通输入单价估算。
    input_price_per_million = Column(Float, nullable=True)
    output_price_per_million = Column(Float, nullable=True)
    cached_input_price_per_million = Column(Float, nullable=True)
    # 时间戳
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
