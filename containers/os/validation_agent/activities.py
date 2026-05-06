"""
containers/OS/validation_agent/activities.py

Temporal activity for the Validation Agent.
Registered on: os-main-queue

Activity name: "validate_payload"

FIX: Activity signature accepts (data: dict) — single dict.
     Workflow sends: args=[{"payload_bundle": payload, "context": context}]

Output: ValidationResult dict
  { valid, errors, warnings, auto_corrections }

No LLM. Timeout: 15 seconds.
Fail-open: crashes return valid=True + warning.
"""

from __future__ import annotations

import logging

from temporalio import activity

from containers.os.validation_agent.kb_rules import rules_kb
from containers.os.validation_agent.validator import validate_payload_bundle

logger = logging.getLogger(__name__)

from shared.os_metrics import OS_VALIDATION_ERRORS_TOTAL


@activity.defn(name="validate_payload")
async def validate_payload(payload_bundle: dict, context: dict) -> dict:
    """
    Validation Agent activity.

    Workflow passes: payload_bundle and context
    """
    steps   = payload_bundle.get("steps", [])
    n_steps = len(steps)
    doctype = steps[0].get("doctype", "?") if steps else "?"
    action  = steps[0].get("action",  "?") if steps else "?"

    activity.heartbeat("Loading validation KB")
    try:
        rules_kb()
    except Exception as e:
        logger.warning("KB-06 warm-up warning: %s", e)

    activity.heartbeat(f"Validating {n_steps} step(s) for {doctype}")

    try:
        result = validate_payload_bundle(payload_bundle, context)

        n_err  = len(result["errors"])
        n_warn = len(result["warnings"])
        n_corr = len(result["auto_corrections"])

        activity.logger.info(
            "validate_payload: doctype=%s action=%s steps=%d  "
            "valid=%s  errors=%d  warnings=%d  corrections=%d",
            doctype, action, n_steps,
            result["valid"], n_err, n_warn, n_corr,
        )

        for e in result.get("errors", []):
            activity.logger.warning("  ❌ [%s] %s — %s", e["rule_id"], e["field"], e["message"])
            try:
                if OS_VALIDATION_ERRORS_TOTAL is not None:
                    OS_VALIDATION_ERRORS_TOTAL.labels(rule_id=str(e.get("rule_id", "unknown"))).inc()
            except Exception:
                pass
        for w in result.get("warnings", []):
            activity.logger.info("  ⚠️  [%s] %s — %s", w["rule_id"], w["field"], w["message"])
        for c in result.get("auto_corrections", []):
            activity.logger.info("  🔧 %s: %r → %r", c["field"], c["original_value"], c["corrected_value"])

        return result

    except Exception as e:
        logger.exception("validate_payload crashed for doctype=%s: %s", doctype, e)
        return {
            "valid":   True,
            "errors":  [],
            "warnings": [{
                "rule_id":  "validator_error",
                "field":    "system",
                "message":  f"Validator crashed ({e}) — proceeding to execution.",
                "severity": "warning",
                "step":     0,
            }],
            "auto_corrections": [],
        }