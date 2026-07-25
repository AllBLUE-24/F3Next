"""
Discovery Step 1 — org-structure assumptions not yet confirmed in chat.

These facts change Day-1 target structure (warehouses per branch, opening stock,
fiscal year). Step 1 surfaces them as open items when not stated in the transcript.
"""

from __future__ import annotations

import re
from typing import Any

ORG_ASSUMPTION_SPECS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "locations",
        "Number of operating locations / branches / warehouses",
        (r"\b\d+\s+(branch|branches|location|locations|warehouse|warehouses|plant|plants)\b", r"multi[\s-]?branch", r"single site", r"one factory"),
    ),
    (
        "fiscal_year",
        "Fiscal year start (e.g. April–March India)",
        (r"fiscal year", r"april.*march", r"financial year", r"year start"),
    ),
    (
        "opening_balance",
        "Opening balance / cutover date for go-live stock and balances",
        (r"opening balance", r"cutover", r"go[\s-]?live date", r"migration date", r"as on date"),
    ),
    (
        "multi_company",
        "Single company vs multi-company / multi-currency setup",
        (r"multi[\s-]?company", r"multiple compan", r"subsidiar", r"multi[\s-]?currency", r"export.*currency"),
    ),
)


def _text(transcript: str) -> str:
    return (transcript or "").lower()


def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def open_org_assumptions(transcript: str) -> list[dict[str, str]]:
    """Return org facts not yet mentioned in the discovery transcript."""
    text = _text(transcript)
    open_items: list[dict[str, str]] = []
    for key, label, patterns in ORG_ASSUMPTION_SPECS:
        if not _has_any(text, patterns):
            open_items.append({"id": key, "label": label})
    return open_items


def org_assumption_summary(transcript: str) -> dict[str, Any]:
    open_items = open_org_assumptions(transcript)
    return {
        "open_assumptions": open_items,
        "assumptions_complete": len(open_items) == 0,
    }


__all__ = ["open_org_assumptions", "org_assumption_summary"]
