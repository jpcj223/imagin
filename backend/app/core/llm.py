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


def _max_tokens() -> int:
    """限制单次生成长度，避免短目标触发模型自由扩写后长时间不返回。"""
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


def chat_completion(messages: list[dict[str, str]], temperature: float = 0.7) -> str:
    """调用 OpenAI-compatible 聊天接口。

    这里刻意保持轻量，不把业务流程绑死到 LangChain；后续可以替换为更完整的模型适配层。
    """
    config = get_active_model_config()
    if not config:
        raise LLMError("尚未配置可用模型")

    base_url = config["base_url"].rstrip("/")
    if "/anthropic" in base_url.lower():
        # 当前应用内 Agent 使用 OpenAI-compatible /chat/completions 协议；
        # Anthropic 地址通常给 Claude Code 等工具使用，直接拼接会得到 404。
        raise LLMError("当前模型通道使用 OpenAI-compatible 协议，请填写以 /v1 结尾的兼容地址，例如 https://api.siliconflow.cn/v1")
    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": _max_tokens(),
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=_api_timeout_seconds()) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise LLMError(f"模型接口返回错误：{exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"无法连接模型接口：{exc.reason}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise LLMError(f"模型接口读取超时：{_api_timeout_seconds()} 秒内未返回完整响应") from exc

    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError("模型返回格式不符合 OpenAI-compatible 规范") from exc


def chat_completion_stream(messages: list[dict[str, str]], temperature: float = 0.7) -> Iterator[str]:
    """流式调用 OpenAI-compatible 聊天接口。

    后端只向业务层暴露纯文本增量，SSE/JSON 解析细节封装在这里，方便以后替换模型供应商。
    """
    config = get_active_model_config()
    if not config:
        raise LLMError("尚未配置可用模型")

    base_url = config["base_url"].rstrip("/")
    if "/anthropic" in base_url.lower():
        # 当前应用内 Agent 使用 OpenAI-compatible /chat/completions 协议。
        raise LLMError("当前模型通道使用 OpenAI-compatible 协议，请填写以 /v1 结尾的兼容地址，例如 https://api.siliconflow.cn/v1")

    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
        "stream": True,
        "max_tokens": _max_tokens(),
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=_api_timeout_seconds()) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="ignore").strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    break
                try:
                    body = json.loads(data)
                    delta = body["choices"][0].get("delta", {})
                    content = delta.get("content") or ""
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    continue
                if content:
                    yield content
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise LLMError(f"模型接口返回错误：{exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"无法连接模型接口：{exc.reason}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise LLMError(f"模型接口读取超时：{_api_timeout_seconds()} 秒内未返回完整响应") from exc
