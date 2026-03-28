"""
containers/OS/command_planner/plan_builder.py

Pure, deterministic plan construction logic.
No I/O, no LLM, no DB calls — only dicts in, ExecutionPlan out.
Fully unit-testable.

Two entry points:
  build_plan(intent_dict, context) → ExecutionPlan
    Main function called by the activity.

  _build_single_step_plan(intent_dict, meta)
    For simple CRUD intents: 1-2 steps (create + auto-submit if needed).

  _build_multi_step_plan(intent_dict, pattern, meta)
    For complex intents: expand KB-03 pattern steps with intent entities.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from shared.models.plan import ExecutionPlan, PlanStep
from containers.os.command_planner.kb_plans import plans_kb

logger = logging.getLogger(__name__)


# ─── Risk escalation rules ────────────────────────────────────────────────────

# These action types always escalate risk regardless of KB-01 base risk
_ALWAYS_HIGH_RISK = {"cancel", "delete"}
_ALWAYS_MEDIUM_RISK_MIN = {"submit", "bulk_create", "update"}

# If intent risk_level is "none" (read-only ops) → stays none, no confirmation
_NO_RISK_CATEGORIES = {"read", "search", "report"}


def _effective_risk(intent_risk: str, category: str, action: str, pattern_risk: str = "") -> str:
    """
    Determine effective risk level, considering:
    - Category (read/report = always low/none)
    - Action (cancel/delete always high)
    - KB-03 pattern risk (may escalate KB-01 intent risk)
    - KB-01 intent base risk
    """
    # Read-only operations are never risky
    if category in _NO_RISK_CATEGORIES:
        return "none"

    # Cancel/delete are always high regardless of what KB says
    if action in _ALWAYS_HIGH_RISK:
        return "high"

    # Take the maximum of intent risk and pattern risk
    risk_order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    intent_val  = risk_order.get(intent_risk, 1)
    pattern_val = risk_order.get(pattern_risk, 0)
    effective_val = max(intent_val, pattern_val)

    # Submit/update are minimum medium
    if action in _ALWAYS_MEDIUM_RISK_MIN:
        effective_val = max(effective_val, risk_order["medium"])

    return [k for k, v in risk_order.items() if v == effective_val][0]


# ─── Entity extraction helpers ────────────────────────────────────────────────

def _extract_entities_for_step(
    intent_entities: dict,
    required_fields: list[str],
    optional_fields: list[str],
) -> dict[str, Any]:
    """
    Filter intent entities down to the fields relevant to a specific step.
    Keeps all items (list) always — they're needed by most steps.
    """
    relevant_keys = set(required_fields) | set(optional_fields)

    # Always include items and party fields — needed by most ERP docs
    always_include = {"customer", "supplier", "items", "company"}

    result: dict[str, Any] = {}
    for key in (relevant_keys | always_include):
        val = intent_entities.get(key)
        if val is not None:
            result[key] = val

    # Include extras that might be relevant (dates, references etc.)
    for key in ("delivery_date", "transaction_date", "posting_date", "due_date",
                "po_no", "so_no", "dn_no", "invoice_no", "payment_reference",
                "amount", "currency", "payment_type", "mode_of_payment", "party_type",
                "from_warehouse", "to_warehouse", "stock_entry_type", "project"):
        val = intent_entities.get(key)
        if val is not None and key not in result:
            result[key] = val

    return result


# ─── Single-step plan builder ─────────────────────────────────────────────────

def _build_single_step_plan(intent_dict: dict, meta: dict) -> ExecutionPlan:
    """
    Build a 1-step (or 2-step with auto-submit) plan for simple CRUD intents.

    Auto-submit logic:
    - Read/Search/Report/Report intents → 1 step, no submit
    - Create intents → 1 step (create only — user submits separately if needed)
    - Submit/Cancel/Delete intents from KB-01 → 1 step of that action type
    - Update intents → 1 step update
    """
    kb          = plans_kb()
    intent_id   = intent_dict.get("intent_id", "unknown")
    action      = meta.get("action", "create")
    doctype     = meta.get("target_doctype", intent_dict.get("target_doctype", ""))
    category    = meta.get("category", "create")
    intent_risk = meta.get("risk_level", "low")
    entities    = intent_dict.get("entities", {})

    effective_risk = _effective_risk(intent_risk, category, action)
    req_fields     = meta.get("required_entities", [])
    opt_fields     = meta.get("optional_entities", [])

    step_entities = _extract_entities_for_step(entities, req_fields, opt_fields)

    step = PlanStep(
        step_number        = 1,
        action             = action,
        doctype            = doctype,
        depends_on         = None,
        rollback_if_failed = (action == "create"),
        required_fields    = req_fields,
        optional_fields    = opt_fields,
        entities           = step_entities,
        description        = f"{action.title()} {doctype}",
    )

    rollback_strat = kb.rollback_strategy_for_single(action, category)
    req_confirm    = kb.risk_requires_confirmation(effective_risk)

    logger.debug(
        "Single-step plan: intent=%s action=%s doctype=%s risk=%s",
        intent_id, action, doctype, effective_risk,
    )

    return ExecutionPlan(
        pattern_id             = None,
        pattern_name           = None,
        steps                  = [step],
        risk_level             = effective_risk,
        requires_confirmation  = req_confirm,
        confirmation_message   = (
            f"This will {action} a {doctype}. Proceed?" if req_confirm else None
        ),
        estimated_api_calls    = 1,
        is_multi_step          = False,
        is_async               = False,
        rollback_strategy      = rollback_strat,
    )


# ─── Multi-step plan builder ──────────────────────────────────────────────────

def _build_multi_step_plan(
    intent_dict: dict,
    pattern:     dict,
    meta:        dict,
) -> ExecutionPlan:
    """
    Expand a KB-03 pattern into an ExecutionPlan, enriching each step
    with the entities extracted by Clarity Agent.

    Key enrichment:
    - step.entities populated from intent_dict.entities filtered to step's fields
    - source_step resolved from "result_from_step_N" strings in KB-03 pattern
    - is_async set from kb.is_async_pattern()
    """
    kb          = plans_kb()
    entities    = intent_dict.get("entities", {})
    pattern_id  = pattern["pattern_id"]

    intent_risk  = meta.get("risk_level", "low")
    pattern_risk = pattern.get("risk_level", "low")
    category     = meta.get("category", "create")
    action       = meta.get("action", "create")

    effective_risk = _effective_risk(intent_risk, category, action, pattern_risk)

    steps: list[PlanStep] = []

    for raw_step in pattern.get("steps", []):
        step_num   = raw_step.get("step_number", len(steps) + 1)
        step_action = raw_step.get("action", "create")
        doctype    = raw_step.get("doctype", "")

        # Resolve source_step from "result_from_step_N" reference
        source_ref  = raw_step.get("source", "")
        source_step: Optional[int] = None
        if source_ref and "step_" in source_ref:
            try:
                # "result_from_step_2" → 2
                source_step = int(source_ref.split("step_")[-1])
            except ValueError:
                pass

        # Required/optional fields from pattern step
        req_fields = raw_step.get("required_fields", [])
        opt_fields = raw_step.get("optional_fields", [])
        fetch_fields = raw_step.get("fetch_fields", [])

        # For step 1 (originating step), enrich with all intent entities
        # For downstream steps (create_from), entities come from the source doc at runtime
        if step_action in ("create", "update") and source_step is None:
            step_entities = _extract_entities_for_step(entities, req_fields, opt_fields)
        elif step_action == "create_from":
            # Payload Generator will fetch these from the source doc at runtime
            # Still pass intent entities for override fields
            step_entities = _extract_entities_for_step(entities, [], [])
        else:
            # submit, cancel, validate_data — no entity injection needed
            step_entities = {}

        depends_on = raw_step.get("depends_on")
        if depends_on and not depends_on.startswith("step_"):
            # Normalise "step_N" format if KB has variations
            depends_on = f"step_{depends_on}" if depends_on else None

        steps.append(PlanStep(
            step_number        = step_num,
            action             = step_action,
            doctype            = doctype,
            depends_on         = depends_on,
            rollback_if_failed = raw_step.get("rollback_if_failed", False),
            source_doctype     = raw_step.get("source_doctype"),
            source_step        = source_step,
            fetch_fields       = fetch_fields,
            required_fields    = req_fields,
            optional_fields    = opt_fields,
            entities           = step_entities,
            description        = (
                f"{step_action.replace('_', ' ').title()} {doctype}"
                + (f" (from {raw_step.get('source_doctype', '')})" if source_step else "")
            ),
            rollback_note      = raw_step.get("rollback_note", ""),
        ))

    rollback_strat  = kb.rollback_strategy_for_pattern(pattern)
    is_async        = kb.is_async_pattern(pattern_id)
    req_confirm     = pattern.get("confirmation_required", False) or kb.risk_requires_confirmation(effective_risk)

    logger.debug(
        "Multi-step plan: pattern=%s steps=%d risk=%s confirm=%s",
        pattern_id, len(steps), effective_risk, req_confirm,
    )

    return ExecutionPlan(
        pattern_id             = pattern_id,
        pattern_name           = pattern.get("pattern_name"),
        steps                  = steps,
        risk_level             = effective_risk,
        requires_confirmation  = req_confirm,
        confirmation_message   = pattern.get("confirmation_message"),
        estimated_api_calls    = len(steps),
        is_multi_step          = True,
        is_async               = is_async,
        rollback_strategy      = rollback_strat,
        success_message_template   = pattern.get("success_message"),
        partial_failure_template   = pattern.get("partial_failure_handling"),
    )


# ─── Main entry point ─────────────────────────────────────────────────────────

def build_plan(intent_dict: dict, context: dict) -> ExecutionPlan:
    """
    Build an ExecutionPlan from a StructuredIntent dict and context bundle.

    Decision tree:
      1. Is intent_id a known multi-step intent? → multi-step plan from KB-03
      2. Does raw_prompt contain any KB-03 trigger keywords? → multi-step plan
      3. Does context contain module-level workflow hints? → check for implicit multi-step
      4. Default → single-step plan

    Pure function — no I/O, fully deterministic.
    """
    kb = plans_kb()

    intent_id   = intent_dict.get("intent_id", "unknown")
    raw_prompt  = intent_dict.get("raw_prompt", "")
    meta        = kb.intent_meta(intent_id)

    # ── Route 1: Known multi-step intent_id (e.g. complex_sales_cycle) ────────
    pattern = kb.find_pattern_by_intent(intent_id)
    if pattern:
        logger.info("Planner: matched intent '%s' → pattern '%s'", intent_id, pattern["pattern_id"])
        return _build_multi_step_plan(intent_dict, pattern, meta)

    # ── Route 2: Trigger keyword in raw prompt ─────────────────────────────────
    if raw_prompt:
        pattern = kb.find_pattern_by_keywords(raw_prompt)
        if pattern:
            logger.info(
                "Planner: keyword match in prompt → pattern '%s'", pattern["pattern_id"]
            )
            return _build_multi_step_plan(intent_dict, pattern, meta)

    # ── Route 3: Single-step plan (standard CRUD) ──────────────────────────────
    logger.info("Planner: single-step plan for intent '%s'", intent_id)
    return _build_single_step_plan(intent_dict, meta)