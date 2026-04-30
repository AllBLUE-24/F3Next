"""
containers/OS/payload_generator/activities.py

Temporal activity for the Payload Generation Agent.
Registered on: os-main-queue (via os_worker.py)

Activity:
  generate_payload — builds a PayloadBundle from ExecutionPlan + context + intent

NO LLM CALL — pure KB-04 lookup + deterministic field mapping.
Timeout: 20 seconds.

Input dict keys:
  plan:        dict  — ExecutionPlan (from Command Planner)
  context:     dict  — context bundle (from Context Retrieval)
  intent_dict: dict  — StructuredIntent (from Clarity Agent)

Output: PayloadBundle dict
  {"steps": [{step_number, action, doctype, payload, endpoint, http_method, notes}, ...]}
"""

from __future__ import annotations

import logging

from temporalio import activity

from containers.os.payload_generator.kb_fields import field_kb
from containers.os.payload_generator.payload_builder import build_payload_bundle

logger = logging.getLogger(__name__)


def _emergency_fallback(intent_dict: dict, plan: dict) -> dict:
    """
    Last-resort empty payload bundle when builder fails completely.
    Execution Agent will fail gracefully on empty payloads.
    """
    steps = plan.get("steps", [])
    return {
        "steps": [
            {
                "step_number": s.get("step_number", i + 1),
                "action":      s.get("action", "create"),
                "doctype":     s.get("doctype", ""),
                "payload":     {},
                "endpoint":    f"/api/resource/{s.get('doctype','').replace(' ','%20')}",
                "http_method": "POST",
                "notes":       "⚠️ fallback — payload builder failed",
            }
            for i, s in enumerate(steps)
        ]
    }


@activity.defn(name="generate_payload")
async def generate_payload(data: dict) -> dict:
    """
    Payload Generation Agent activity.

    Converts the ExecutionPlan + StructuredIntent entities into
    ERPNext API-ready payloads for every step in the plan.

    Pipeline position: Agent 5 of 9.
    Consumer: Execution Agent reads payload_bundle.steps[N].payload
              and payload_bundle.steps[N].endpoint to make API calls.
    """
    plan        = data.get("plan", {})
    context     = data.get("context", {})
    intent_dict = data.get("intent_dict", {})

    intent_id  = intent_dict.get("intent_id", "unknown")
    doctype    = intent_dict.get("target_doctype", "")
    n_steps    = len(plan.get("steps", []))

    activity.heartbeat("Loading field KB")
    try:
        field_kb()   # Warm up singleton if first call
    except Exception as e:
        logger.warning("KB-04 load warning: %s — will attempt build anyway", e)

    activity.heartbeat(f"Building payloads for {n_steps} step(s)")

    try:
        bundle = build_payload_bundle(plan, context, intent_dict)

        # --- Date Sanitization (Bug 2 Fix) ---
        # Ensures dates like "2026-4-3" become "2026-04-03" so ERPNext/Validation doesn't crash
        import re
        def _sanitize_dates(obj):
            if isinstance(obj, dict):
                return {k: _sanitize_dates(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_sanitize_dates(i) for i in obj]
            elif isinstance(obj, str):
                match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", obj.strip())
                if match:
                    y, m, d = match.groups()
                    return f"{y}-{int(m):02d}-{int(d):02d}"
            return obj

        for s in bundle.get("steps", []):
            if "payload" in s and isinstance(s["payload"], dict):
                s["payload"] = _sanitize_dates(s["payload"])
        # -------------------------------------

        activity.logger.info(
            "generate_payload: intent=%s doctype=%s steps=%d",
            intent_id, doctype, len(bundle.get("steps", [])),
        )

        # Log each step summary
        for s in bundle.get("steps", []):
            activity.logger.info(
                "  step %d [%s]: %s %s → %s %s  (%d payload keys)",
                s["step_number"],
                s.get("step_role", "main"),
                s["action"],
                s["doctype"],
                s["http_method"],
                s["endpoint"],
                len(s.get("payload", {})),
            )

        return bundle

    except Exception as e:
        logger.exception(
            "generate_payload failed for intent='%s' doctype='%s': %s",
            intent_id, doctype, e,
        )
        return _emergency_fallback(intent_dict, plan)