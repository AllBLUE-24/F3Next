"""Resolve cascade rules from KB for an ERPNext event."""

from __future__ import annotations

from typing import Any

from temporalio import activity

from containers.cascade.rule_resolver.kb_loader import match_rules
from shared.erp_policies.action_risk import classify_cascade_risk


def _extract_trigger_event(payload: dict[str, Any]) -> str:
    """Infer Frappe webhook event from payload."""
    for key in ("event", "trigger_event", "doc_event"):
        val = payload.get(key)
        if val:
            return str(val)
    status = str(payload.get("status") or "").lower()
    if status == "cancelled":
        return "on_cancel"
    return "on_submit"


def _flatten_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Merge nested document data into a flat dict for template formatting."""
    flat = dict(payload)
    nested = payload.get("data")
    if isinstance(nested, dict):
        flat.update(nested)
    return flat


@activity.defn(name="resolve_cascade_rules")
async def resolve_cascade_rules(data: dict[str, Any]) -> dict[str, Any]:
    """
    Match KB rules and compute risk tier for the event.

    Returns:
        matched_rules: list of rule dicts expanded per department
        risk_tier: overall tier for the event
        template_context: flat dict for message templates
    """
    payload = data.get("event_payload") or {}
    doctype = data.get("doctype") or payload.get("doctype") or ""
    trigger_event = data.get("trigger_event") or _extract_trigger_event(payload)
    template_context = _flatten_payload(payload)
    template_context.setdefault("doctype", doctype)
    template_context.setdefault("name", data.get("doc_name") or payload.get("name") or "")

    raw_rules = match_rules(doctype, trigger_event)
    risk_tier = classify_cascade_risk(
        doctype,
        trigger_event,
        payload=template_context,
    )

    matched: list[dict[str, Any]] = []
    for rule in raw_rules:
        rule_tier = rule.get("risk_tier_override") or risk_tier
        for dept in rule.get("target_departments") or []:
            matched.append({
                "rule_id": rule.get("rule_id"),
                "department": dept,
                "title_template": rule.get("title_template") or f"{doctype} update",
                "message_template": rule.get("message_template") or "{name} updated in ERPNext.",
                "risk_tier": rule_tier,
            })

    try:
        from shared.cascade_metrics import CASCADE_RULES_MATCHED_TOTAL

        if CASCADE_RULES_MATCHED_TOTAL and matched:
            CASCADE_RULES_MATCHED_TOTAL.labels(
                doctype=doctype,
                trigger_event=trigger_event,
            ).inc(len(matched))
    except Exception:
        pass

    activity.logger.info(
        "Cascade rules: doctype=%s event=%s matches=%d tier=%s",
        doctype,
        trigger_event,
        len(matched),
        risk_tier,
    )

    return {
        "matched_rules": matched,
        "matched_rule_ids": [r.get("rule_id") for r in raw_rules],
        "risk_tier": risk_tier,
        "template_context": template_context,
        "doctype": doctype,
        "trigger_event": trigger_event,
    }
