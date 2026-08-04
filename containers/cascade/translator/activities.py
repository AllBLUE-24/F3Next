"""Translate cascade rules into human-readable notification messages."""

from __future__ import annotations

from typing import Any

from temporalio import activity


def _safe_format(template: str, context: dict[str, Any]) -> str:
    """Format template with context; leave unknown placeholders as-is."""
    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    try:
        return template.format_map(_SafeDict(context))
    except Exception:
        return template


@activity.defn(name="translate_event_to_messages")
async def translate_event_to_messages(data: dict[str, Any]) -> dict[str, Any]:
    """
    Build notification title/body per matched rule using KB templates.
    """
    matched_rules = data.get("matched_rules") or []
    context = data.get("template_context") or {}

    messages: list[dict[str, Any]] = []
    for rule in matched_rules:
        title = _safe_format(str(rule.get("title_template") or ""), context)
        body = _safe_format(str(rule.get("message_template") or ""), context)
        messages.append({
            "rule_id": rule.get("rule_id"),
            "department": rule.get("department"),
            "title": title.strip() or "ERPNext update",
            "body": body.strip() or "An ERPNext document was updated.",
            "risk_tier": rule.get("risk_tier") or data.get("risk_tier") or "low",
        })

    return {"messages": messages, "count": len(messages)}
