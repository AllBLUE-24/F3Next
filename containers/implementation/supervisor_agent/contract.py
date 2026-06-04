"""
Supervisor gap classification — align with quality_gate evaluate patterns.

ask_user only for user-resolvable data gaps; pipeline/KB bugs → auto_fix or hard_block.
"""

from __future__ import annotations

import re
from typing import Literal

GapClass = Literal["user_gap", "auto_fix", "pipeline_fail"]

_PIPELINE_BUG_PATTERNS = re.compile(
    r"(internal|traceback|graph|corpus_merge|ler|schema resolver|kb miss|pipeline|"
    r"not implemented|attributeerror|keyerror)",
    re.I,
)
_USER_DATA_PATTERNS = re.compile(
    r"(empty|missing|required|no source column|identity|user must|upload|row \d+)",
    re.I,
)
_AUTO_FIX_PATTERNS = re.compile(
    r"(enum|naming_series|default|strip unit|normaliz|kb default|format)",
    re.I,
)


def classify_gap(message: str) -> GapClass:
    """Classify a single error/warning message for supervisor action selection."""
    text = str(message or "").strip()
    if not text:
        return "user_gap"

    if _PIPELINE_BUG_PATTERNS.search(text) and not _USER_DATA_PATTERNS.search(text):
        return "pipeline_fail"

    if _AUTO_FIX_PATTERNS.search(text):
        return "auto_fix"

    if _USER_DATA_PATTERNS.search(text):
        return "user_gap"

    return "user_gap"


def should_ask_user(messages: list[str]) -> bool:
    """True only when at least one message is a user gap and none are pure pipeline failures."""
    if not messages:
        return False
    classes = [classify_gap(m) for m in messages]
    if any(c == "pipeline_fail" for c in classes) and not any(c == "user_gap" for c in classes):
        return False
    return any(c == "user_gap" for c in classes)


def filter_user_gap_messages(messages: list[str]) -> list[str]:
    """Messages safe to show in ask_user prompts."""
    out: list[str] = []
    for m in messages:
        if classify_gap(m) == "user_gap":
            out.append(m)
    return out
