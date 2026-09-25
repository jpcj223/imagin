from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

from app.db.database import get_connection


class LLMError(RuntimeError):
    pass


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
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM model_configs WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None


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
) -> tuple[str, dict[str, int] | None]:
    """调用兼容接口并同时返回供应商报告的 Token 用量。

    步骤 1：按现有配置发送聊天请求；步骤 2：读取文本和可用用量字段；
    步骤 3：不估算缺失用量，避免把猜测值当成真实消耗。
    """
    config = get_active_model_config()
    if not config:
        raise LLMError("尚未配置可用模型")

    base_url = config["base_url"].rstrip("/")
    if "/anthropic" in base_url.lower():
        # 当前应用内 Agent 使用 OpenAI-compatible /chat/completions 协议；
        # Anthropic 地址通常给 Claude Code 等工具使用，直接拼接会得到 404。
        raise LLMError("当前模型通道使用 OpenAI-compatible 协议，请填写以 /v1 结尾的兼容地址，例如 https://api.siliconflow.cn/v1")

    payload = _build_payload(config, messages, temperature=temperature,
                             max_tokens=max_tokens, stream=False)

    try:
        with _make_urlopen(config, payload) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise LLMError(f"模型接口返回错误：{exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"无法连接模型接口：{exc.reason}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise LLMError(f"模型接口读取超时：{_api_timeout_seconds()} 秒内未返回完整响应") from exc

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError("模型返回格式不符合 OpenAI-compatible 规范") from exc

    return content, _normalize_token_usage(body.get("usage"))


def _normalize_token_usage(raw_usage: Any) -> dict[str, int] | None:
    """规范化供应商用量字段；缺少时保持为空，不推算模型消耗。"""
    if not isinstance(raw_usage, dict):
        return None

    # 步骤 1：兼容常用 input/output 字段别名；步骤 2：只接受非负整数值。
    def read_count(*keys: str) -> int | None:
        # 步骤 1：依次读取供应商别名；步骤 2：忽略缺失、布尔值和无效数字。
        for key in keys:
            value = raw_usage.get(key)
            if value is None or isinstance(value, bool):
                continue
            try:
                count = int(value)
            except (TypeError, ValueError, OverflowError):
                continue
            if count >= 0:
                return count
        return None

    input_tokens = read_count("prompt_tokens", "input_tokens")
    output_tokens = read_count("completion_tokens", "output_tokens")
    total_tokens = read_count("total_tokens")
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    usage = {
        key: value
        for key, value in (
            ("input_tokens", input_tokens),
            ("output_tokens", output_tokens),
            ("total_tokens", total_tokens),
        )
        if value is not None
    }
    return usage or None


def chat_completion_stream_with_usage(
    messages: list[dict[str, str]],
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Iterator[dict[str, Any]]:
    """流式请求并保留供应商主动返回的 Token 用量事件。"""
    # 步骤 1：按当前 OpenAI-compatible 配置建立流；步骤 2：逐条解析文本和可选用量事件。
    config = get_active_model_config()
    if not config:
        raise LLMError("尚未配置可用模型")

    base_url = config["base_url"].rstrip("/")
    if "/anthropic" in base_url.lower():
        raise LLMError("当前模型通道使用 OpenAI-compatible 协议，请填写以 /v1 结尾的兼容地址，例如 https://api.siliconflow.cn/v1")

    payload = _build_payload(config, messages, temperature=temperature, max_tokens=max_tokens, stream=True)
    try:
        with _make_urlopen(config, payload) as response:
            for raw_line in response:
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

                # 步骤 3：部分供应商会在流末尾返回用量；没有时不估算。
                usage = _normalize_token_usage(body.get("usage"))
                if usage:
                    yield {"type": "usage", "usage": usage}
                try:
                    content = body["choices"][0].get("delta", {}).get("content") or ""
                except (KeyError, IndexError, TypeError):
                    continue
                if content:
                    yield {"type": "delta", "content": content}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise LLMError(f"模型接口返回错误：{exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"无法连接模型接口：{exc.reason}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise LLMError(f"模型接口读取超时：{_api_timeout_seconds()} 秒内未返回完整响应") from exc


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
