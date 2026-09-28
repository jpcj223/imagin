from __future__ import annotations

import json
import math
import os
import socket
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

from app.db.session import get_core_db
from app.models.core.model_config import ModelConfig


class LLMError(RuntimeError):
    pass


class LLMCancelled(LLMError):
    """用户主动停止当前模型请求。"""


def _interrupt_response(response: Any) -> None:
    """关闭底层 socket，尽可能让阻塞中的 urllib 读取立即返回。"""
    try:
        raw_socket = response.fp.raw._sock
        raw_socket.shutdown(socket.SHUT_RDWR)
    except (AttributeError, OSError, ValueError):
        pass
    try:
        response.close()
    except (AttributeError, OSError, ValueError):
        pass


def _watch_response_cancellation(response: Any, cancel_event: threading.Event | None):
    """监控工作流取消信号，并在模型响应阻塞时关闭连接。"""
    if cancel_event is None:
        return lambda: None
    if cancel_event.is_set():
        _interrupt_response(response)
        return lambda: None

    finished = threading.Event()

    def watch() -> None:
        while not finished.wait(0.05):
            if cancel_event.is_set():
                _interrupt_response(response)
                return

    watcher = threading.Thread(target=watch, name="llm-cancel-watch", daemon=True)
    watcher.start()

    def stop_watching() -> None:
        finished.set()
        watcher.join(timeout=0.2)

    return stop_watching


def _api_timeout_seconds() -> int:
    """读取模型请求超时时间。

    用户常用毫秒环境变量 API_TIMEOUT_MS 配置外部模型等待时间；没有配置时默认 300 秒，
    避免长章节生成被 60 秒硬超时打断。
    """
    raw = os.getenv("API_TIMEOUT_MS", "300000")
    try:
        return max(10, int(raw) // 1000)
    except ValueError:
        return 300


def _max_tokens_default() -> int:
    """限制单次生成长度的全局默认值，避免短目标触发模型自由扩写后长时间不返回。"""
    raw = os.getenv("LLM_MAX_TOKENS", "2048")
    try:
        return max(256, int(raw))
    except ValueError:
        return 2048


def get_active_model_config() -> dict[str, Any] | None:
    """读取配置页使用的核心库，确保模型调用与费用设置来自同一条配置。"""
    with get_core_db() as db:
        config = (
            db.query(ModelConfig)
            .filter(ModelConfig.is_active == 1)
            .order_by(ModelConfig.id.desc())
            .first()
        )
        if config is None:
            return None
        return {
            column.key: getattr(config, column.key)
            for column in ModelConfig.__mapper__.column_attrs
        }


def _pricing_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    """生成不含凭据的模型与单价快照，随每次调用记录。"""
    def read_price(field: str) -> float | None:
        value = config.get(field)
        if value is None or isinstance(value, bool):
            return None
        try:
            price = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return price if math.isfinite(price) and price >= 0 else None

    cached_price = read_price("cached_input_price_per_million")
    input_price = read_price("input_price_per_million")
    return {
        "config_id": config.get("id"),
        "config_name": config.get("name") or "",
        "model": config.get("model") or "",
        "currency": "CNY",
        "unit": "per_million_tokens",
        "input_price_per_million": input_price,
        "output_price_per_million": read_price("output_price_per_million"),
        "cached_input_price_per_million": cached_price,
        "cached_input_uses_input_price": cached_price is None and input_price is not None,
    }


def _attach_pricing(token_usage: dict[str, int] | None, config: dict[str, Any]) -> dict[str, Any] | None:
    """把供应商实报 Token 用量与调用时价格组合为可追溯估算。"""
    if not token_usage:
        return None

    result: dict[str, Any] = dict(token_usage)
    pricing = _pricing_snapshot(config)
    result["pricing_snapshot"] = pricing
    input_tokens = token_usage.get("input_tokens")
    output_tokens = token_usage.get("output_tokens")
    input_price = pricing["input_price_per_million"]
    output_price = pricing["output_price_per_million"]
    if input_tokens is None or output_tokens is None or input_price is None or output_price is None:
        result["cost_cny"] = None
        return result

    cached_tokens = min(max(token_usage.get("cached_input_tokens", 0), 0), input_tokens)
    uncached_tokens = max(input_tokens - cached_tokens, 0)
    cached_price = pricing["cached_input_price_per_million"]
    if cached_price is None:
        cached_price = input_price
    cost = (
        uncached_tokens * input_price
        + cached_tokens * cached_price
        + output_tokens * output_price
    ) / 1_000_000
    result["cost_cny"] = round(cost, 8)
    return result


def get_effective_llm_settings(
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """返回本次模型调用的有效参数，不包含密钥、地址或代理信息。"""
    config = get_active_model_config()
    if not config:
        return {"configured": False}

    # 模型请求只允许调用参数覆盖温度和最大 Token；采样惩罚来自当前模型配置。
    params = _build_payload(config, [], **(overrides or {}))
    return {
        "configured": True,
        "config_name": config.get("name") or "",
        "model": config.get("model") or "",
        "pricing": _pricing_snapshot(config),
        "temperature": params.get("temperature"),
        "max_tokens": params.get("max_tokens"),
        "top_p": params.get("top_p"),
        "frequency_penalty": params.get("frequency_penalty"),
        "presence_penalty": params.get("presence_penalty"),
    }


def _build_payload(config: dict[str, Any], messages: list[dict[str, str]],
                   temperature: float | None = None,
                   max_tokens: int | None = None,
                   stream: bool = False) -> dict[str, Any]:
    """根据配置 + 调用方覆盖参数构造请求 payload。

    优先级：调用方传入参数 > 配置中保存的参数 > 硬编码默认值。
    """
    payload: dict[str, Any] = {
        "model": config["model"],
        "messages": messages,
    }

    # 温度：调用方优先，其次配置值，最后默认 0.7
    if temperature is not None:
        payload["temperature"] = temperature
    elif config.get("temperature") is not None:
        payload["temperature"] = config["temperature"]
    else:
        payload["temperature"] = 0.7

    # max_tokens：调用方优先，其次配置值，最后环境变量默认
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    elif config.get("max_tokens"):
        payload["max_tokens"] = config["max_tokens"]
    else:
        payload["max_tokens"] = _max_tokens_default()

    # top_p：配置中有就传
    if config.get("top_p") is not None:
        payload["top_p"] = config["top_p"]

    # frequency_penalty：配置中有就传
    if config.get("frequency_penalty") is not None:
        payload["frequency_penalty"] = config["frequency_penalty"]

    # presence_penalty：配置中有就传
    if config.get("presence_penalty") is not None:
        payload["presence_penalty"] = config["presence_penalty"]

    if stream:
        payload["stream"] = True
        # OpenAI-compatible 流式接口默认可能不回传用量；请求最后一个 chunk 附带 Token 统计。
        payload["stream_options"] = {"include_usage": True}

    return payload


def _make_urlopen(config: dict[str, Any], payload: dict[str, Any]):
    """构造并发送请求，返回 response 对象（供 with 使用）。

    支持 proxy_url 配置；没有代理时走默认直连。
    """
    base_url = config["base_url"].rstrip("/")
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=data,
        headers=headers,
        method="POST",
    )

    proxy_url = config.get("proxy_url") or ""
    if proxy_url:
        proxy_handler = urllib.request.ProxyHandler({
            "http": proxy_url,
            "https": proxy_url,
        })
        opener = urllib.request.build_opener(proxy_handler)
        return opener.open(request, timeout=_api_timeout_seconds())
    else:
        return urllib.request.urlopen(request, timeout=_api_timeout_seconds())


def chat_completion(messages: list[dict[str, str]], temperature: float | None = None,
                    max_tokens: int | None = None) -> str:
    """调用 OpenAI-compatible 聊天接口。

    步骤 1：调用统一的用量接口；步骤 2：沿用旧签名只返回文本，兼容现有 Agent。
    这里刻意保持轻量，不把业务流程绑死到 LangChain；后续可以替换为更完整的模型适配层。
    """
    content, _ = chat_completion_with_usage(
        messages, temperature=temperature, max_tokens=max_tokens
    )
    return content


def chat_completion_with_usage(
    messages: list[dict[str, str]],
    temperature: float | None = None,
    max_tokens: int | None = None,
    cancel_event: threading.Event | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """调用兼容接口并同时返回供应商报告的 Token 用量。

    步骤 1：按现有配置发送聊天请求；步骤 2：读取文本和可用用量字段；
    步骤 3：不估算缺失用量，避免把猜测值当成真实消耗。
    """
    config = get_active_model_config()
    if not config:
        raise LLMError("尚未配置可用模型")
    if cancel_event is not None and cancel_event.is_set():
        raise LLMCancelled("用户中断模型请求")

    base_url = config["base_url"].rstrip("/")
    if "/anthropic" in base_url.lower():
        # 当前应用内 Agent 使用 OpenAI-compatible /chat/completions 协议；
        # Anthropic 地址通常给 Claude Code 等工具使用，直接拼接会得到 404。
        raise LLMError("当前模型通道使用 OpenAI-compatible 协议，请填写以 /v1 结尾的兼容地址，例如 https://api.siliconflow.cn/v1")

    payload = _build_payload(config, messages, temperature=temperature,
                             max_tokens=max_tokens, stream=False)

    try:
        with _make_urlopen(config, payload) as response:
            stop_watching = _watch_response_cancellation(response, cancel_event)
            try:
                body = json.loads(response.read().decode("utf-8"))
            finally:
                stop_watching()
    except urllib.error.HTTPError as exc:
        if cancel_event is not None and cancel_event.is_set():
            raise LLMCancelled("用户中断模型请求") from exc
        detail = exc.read().decode("utf-8", errors="ignore")
        raise LLMError(f"模型接口返回错误：{exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        if cancel_event is not None and cancel_event.is_set():
            raise LLMCancelled("用户中断模型请求") from exc
        raise LLMError(f"无法连接模型接口：{exc.reason}") from exc
    except (TimeoutError, socket.timeout) as exc:
        if cancel_event is not None and cancel_event.is_set():
            raise LLMCancelled("用户中断模型请求") from exc
        raise LLMError(f"模型接口读取超时：{_api_timeout_seconds()} 秒内未返回完整响应") from exc
    except Exception as exc:
        if cancel_event is not None and cancel_event.is_set():
            raise LLMCancelled("用户中断模型请求") from exc
        raise

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError("模型返回格式不符合 OpenAI-compatible 规范") from exc

    return content, _attach_pricing(_normalize_token_usage(body.get("usage")), config)


def _normalize_token_usage(raw_usage: Any) -> dict[str, int] | None:
    """规范化供应商用量字段；缺少时保持为空，不推算模型消耗。"""
    if not isinstance(raw_usage, dict):
        return None

    # 步骤 1：兼容常用 input/output 字段别名；步骤 2：只接受非负整数值。
    def read_count_from(source: dict[str, Any], *keys: str) -> int | None:
        # 步骤 1：依次读取供应商别名；步骤 2：忽略缺失、布尔值和无效数字。
        for key in keys:
            value = source.get(key)
            if value is None or isinstance(value, bool):
                continue
            try:
                count = int(value)
            except (TypeError, ValueError, OverflowError):
                continue
            if count >= 0:
                return count
        return None

    def read_count(*keys: str) -> int | None:
        return read_count_from(raw_usage, *keys)

    input_tokens = read_count("prompt_tokens", "input_tokens")
    output_tokens = read_count("completion_tokens", "output_tokens")
    total_tokens = read_count("total_tokens")
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    cached_input_tokens = read_count("cached_input_tokens", "cache_read_input_tokens")
    if cached_input_tokens is None:
        for details_key in ("prompt_tokens_details", "input_tokens_details", "prompt_token_details"):
            details = raw_usage.get(details_key)
            if isinstance(details, dict):
                cached_input_tokens = read_count_from(details, "cached_tokens", "cache_read_input_tokens")
                if cached_input_tokens is not None:
                    break

    usage = {
        key: value
        for key, value in (
            ("input_tokens", input_tokens),
            ("output_tokens", output_tokens),
            ("total_tokens", total_tokens),
            ("cached_input_tokens", cached_input_tokens),
        )
        if value is not None
    }
    return usage or None


def chat_completion_stream_with_usage(
    messages: list[dict[str, str]],
    temperature: float | None = None,
    max_tokens: int | None = None,
    cancel_event: threading.Event | None = None,
) -> Iterator[dict[str, Any]]:
    """流式请求并保留供应商主动返回的 Token 用量事件。"""
    # 步骤 1：按当前 OpenAI-compatible 配置建立流；步骤 2：逐条解析文本和可选用量事件。
    config = get_active_model_config()
    if not config:
        raise LLMError("尚未配置可用模型")
    if cancel_event is not None and cancel_event.is_set():
        raise LLMCancelled("用户中断模型请求")

    base_url = config["base_url"].rstrip("/")
    if "/anthropic" in base_url.lower():
        raise LLMError("当前模型通道使用 OpenAI-compatible 协议，请填写以 /v1 结尾的兼容地址，例如 https://api.siliconflow.cn/v1")

    payload = _build_payload(config, messages, temperature=temperature, max_tokens=max_tokens, stream=True)
    try:
        with _make_urlopen(config, payload) as response:
            stop_watching = _watch_response_cancellation(response, cancel_event)
            try:
                for raw_line in response:
                    if cancel_event is not None and cancel_event.is_set():
                        raise LLMCancelled("用户中断模型请求")
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        break
                    try:
                        body = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(body, dict):
                        continue

                    # 用量 chunk 通常 choices 为空；先处理用量，再读取可能不存在的文本增量。
                    usage = _attach_pricing(_normalize_token_usage(body.get("usage")), config)
                    if usage:
                        yield {"type": "usage", "usage": usage}
                    try:
                        content = body["choices"][0].get("delta", {}).get("content") or ""
                    except (KeyError, IndexError, TypeError):
                        continue
                    if content:
                        yield {"type": "delta", "content": content}
            finally:
                stop_watching()
    except urllib.error.HTTPError as exc:
        if cancel_event is not None and cancel_event.is_set():
            raise LLMCancelled("用户中断模型请求") from exc
        detail = exc.read().decode("utf-8", errors="ignore")
        raise LLMError(f"模型接口返回错误：{exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        if cancel_event is not None and cancel_event.is_set():
            raise LLMCancelled("用户中断模型请求") from exc
        raise LLMError(f"无法连接模型接口：{exc.reason}") from exc
    except (TimeoutError, socket.timeout) as exc:
        if cancel_event is not None and cancel_event.is_set():
            raise LLMCancelled("用户中断模型请求") from exc
        raise LLMError(f"模型接口读取超时：{_api_timeout_seconds()} 秒内未返回完整响应") from exc
    except Exception as exc:
        if cancel_event is not None and cancel_event.is_set():
            raise LLMCancelled("用户中断模型请求") from exc
        raise


def chat_completion_stream(messages: list[dict[str, str]],
                           temperature: float | None = None,
                           max_tokens: int | None = None) -> Iterator[str]:
    """流式调用 OpenAI-compatible 聊天接口。

    后端只向业务层暴露纯文本增量，SSE/JSON 解析细节封装在这里，方便以后替换模型供应商。
    """
    # 步骤 1：复用带用量解析的流式实现；步骤 2：维持旧调用方只接收文本片段的接口。
    for event in chat_completion_stream_with_usage(messages, temperature, max_tokens):
        if event.get("type") == "delta":
            yield event["content"]
