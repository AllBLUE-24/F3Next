"""Shared discovery helpers (chat history shape, transcript formatting)."""
from __future__ import annotations

from typing import Any


def normalize_messages(chat_history: Any) -> list[dict]:
    """Accept legacy shapes; always return [{role, content, ts?}, ...]."""
    if not chat_history:
        return []
    if isinstance(chat_history, list):
        return [
            m
            for m in chat_history
            if isinstance(m, dict) and m.get("role") and m.get("content")
        ]
    if isinstance(chat_history, dict):
        msgs = chat_history.get("messages")
        if isinstance(msgs, list):
            return normalize_messages(msgs)
    return []


def transcript_text(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        role = m.get("role", "unknown").capitalize()
        content = (m.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)
