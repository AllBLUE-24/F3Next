"""
Evaluate execution_preflight_rules.json against a create payload (OS COMMIT).
"""

from __future__ import annotations

from typing import Any

from shared.kb.policy_loaders import get_execution_preflight_rules


def _format_message(template: str, ctx: dict[str, Any]) -> str:
    out = template
    for key, val in ctx.items():
        out = out.replace("{" + key + "}", str(val or ""))
    return out


def _truthy(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if val in (1, "1", "yes", "true", "True"):
        return True
    return bool(val)


def _when_matches(when: dict[str, Any], ctx: dict[str, Any]) -> bool:
    if not when:
        return True
    field_present = when.get("field")
    if field_present and when.get("present"):
        return bool(str(ctx.get(field_present) or "").strip())
    for key, expected in when.items():
        if key in ("field", "present"):
            continue
        actual = ctx.get(key)
        if isinstance(expected, bool):
            if _truthy(actual) != expected:
                return False
        elif actual != expected:
            return False
    return True


def _check_passes(check: dict[str, Any], ctx: dict[str, Any]) -> bool:
    if not check:
        return True
    for key, expected in check.items():
        if key == "live_doctype" or key == "field" or key == "exists":
            continue
        actual = ctx.get(key)
        if isinstance(expected, bool):
            if _truthy(actual) != expected:
                return False
        elif actual != expected:
            return False
    return True


async def evaluate_execution_preflight(
    adapter,
    doctype: str,
    payload: dict[str, Any],
) -> list[str]:
    """Return blocking error messages for this create step (empty if ok)."""
    from shared.erp_tools import get_item_flags, get_supplier_flags

    errors: list[str] = []
    rules = get_execution_preflight_rules()
    base_ctx = dict(payload)
    base_ctx["doctype"] = doctype

    for rule in rules:
        rule_dt = rule.get("doctype")
        if rule_dt and rule_dt != doctype and rule_dt != "*":
            continue

        scope = rule.get("scope")
        check = rule.get("check") or {}
        when = rule.get("when") or {}

        supplier = str(payload.get("supplier") or "")
        sup_flags: dict[str, Any] = {}
        if supplier:
            sup_flags = await get_supplier_flags(adapter, supplier)
            base_ctx["supplier"] = supplier
            for k, v in sup_flags.items():
                base_ctx[f"supplier.{k}"] = v

        if scope == "items":
            if not _when_matches(when, base_ctx):
                continue
            items = payload.get("items") or []
            if not isinstance(items, list):
                continue
            for row in items:
                if not isinstance(row, dict):
                    continue
                code = row.get("item_code")
                if not code:
                    continue
                flags = await get_item_flags(adapter, str(code))
                row_ctx = {
                    **base_ctx,
                    "item_code": code,
                    **{f"item.{k}": v for k, v in flags.items()},
                }
                if flags.get("_missing"):
                    errors.append(
                        _format_message(
                            "Item '{item_code}' was not found on your ERP site.",
                            row_ctx,
                        )
                    )
                    continue
                if not _check_passes(check, row_ctx):
                    errors.append(_format_message(rule.get("message", "Preflight failed"), row_ctx))
            continue

        ctx = dict(base_ctx)
        if not _when_matches(when, ctx):
            continue

        if check.get("live_doctype") and check.get("exists"):
            field = check.get("field") or "company"
            value = str(payload.get(field) or "").strip()
            if not value:
                continue
            live_dt = check["live_doctype"]
            if live_dt == "Supplier":
                flags = sup_flags or await get_supplier_flags(adapter, value)
                if flags.get("_missing"):
                    errors.append(_format_message(rule.get("message", "Invalid link"), {**ctx, field: value}))
            else:
                try:
                    rows = await adapter.list_records(live_dt, ["name"], limit=200)
                    names = {str(r.get("name", "")).casefold() for r in rows if r.get("name")}
                    if names and value.casefold() not in names:
                        errors.append(_format_message(rule.get("message", "Invalid link"), {**ctx, field: value}))
                except Exception:
                    continue
            continue

        if not _check_passes(check, ctx):
            errors.append(_format_message(rule.get("message", "Preflight failed"), ctx))

    return errors
