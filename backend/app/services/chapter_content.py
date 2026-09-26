"""章节正文指纹工具，用于识别分析结果和提案是否已过期。"""
from __future__ import annotations

import hashlib


def content_fingerprint(content: str | None) -> str:
    """计算正文稳定指纹，不保存或回传正文副本。"""
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()


def content_has_changed(source_fingerprint: str | None, current_content: str | None) -> bool | None:
    """返回正文是否变化；旧数据没有指纹时返回 None，避免误报为新鲜。"""
    if not source_fingerprint:
        return None
    return source_fingerprint != content_fingerprint(current_content)
