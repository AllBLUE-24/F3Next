"""
containers/OS/command_planner/activities.py

Temporal activity for the Command Planning Agent.
Registered on: os-planner-queue

Activity:
  plan_command — builds an ExecutionPlan from StructuredIntent + context bundle

NO LLM CALL — pure rule-based matching against KB-03.
Timeout: 20 seconds (KB file reads at startup + O(1) dict lookups at runtime).

Design rules applied:
  - Never raises — always returns a valid ExecutionPlan dict
  - Fallback: if plan_builder fails for any reason, returns a safe 1-step plan
  - heartbeat() called before/after KB load and before return
"""

from __future__ import annotations

import logging

from temporalio import activity

from containers.OS.command_planner.kb_plans import plans_kb
from containers.OS.command_planner.plan_builder import build_plan
from shared.models.plan import ExecutionPlan, PlanStep

logger = logging.getLogger(__name__)


def _emergency_fallback(intent_dict: dict) -> dict:
    """
    Last-resort single-step plan when plan_builder fails completely.
    Uses only data from intent_dict — no KB access.
    """
    action  = intent_dict.get("action", "create")
    doctype = intent_dict.get("target_doctype", "")
    risk    = intent_dict.get("risk_level", "low")

    plan = ExecutionPlan(
        pattern_id             = None,
        steps                  = [PlanStep(
            step_number  = 1,
            action       = action,
            doctype      = doctype,
            entities     = intent_dict.get("entities", {}),
            description  = f"{action.title()} {doctype} (fallback plan)",
        )],
        risk_level             = risk,
        requires_confirmation  = risk in ("high", "critical"),
        estimated_api_calls    = 1,
        is_multi_step          = False,
        rollback_strategy      = "none",
    )
    return plan.model_dump()


@activity.defn(name="plan_command")
async def plan_command(data: dict) -> dict:
    """
    Command Planning Agent activity.

    Input dict keys:
      intent_dict:  dict   — StructuredIntent from Clarity Agent
      context:      dict   — context bundle from Context Retrieval Agent

    Returns:
      ExecutionPlan as dict — never raises, fallback on any error.

    Pipeline position: Agent 3 of 8.
    Consumer: Payload Generation Agent (Agent 4) reads steps[].entities
              and steps[].required_fields to build API payloads.
    """
    intent_dict = data.get("intent_dict", {})
    context     = data.get("context", {})

    intent_id  = intent_dict.get("intent_id", "unknown")
    raw_prompt = intent_dict.get("raw_prompt", "")

    activity.heartbeat("Loading plan knowledge base")

    # Warm up singleton on first call (subsequent calls are instant)
    try:
        plans_kb()   # Ensures KB is loaded before we proceed
    except Exception as e:
        logger.exception("KB load failed: %s — will attempt plan anyway", e)

    activity.heartbeat(f"Building plan for intent: {intent_id}")

    try:
        plan = build_plan(intent_dict, context)

        logger.info(
            "plan_command: intent=%s → pattern=%s steps=%d risk=%s confirm=%s",
            intent_id,
            plan.pattern_id or "single-step",
            len(plan.steps),
            plan.risk_level,
            plan.requires_confirmation,
        )

        activity.heartbeat(
            f"Plan ready: {len(plan.steps)} step(s), risk={plan.risk_level}"
        )

        return plan.model_dump()

    except Exception as e:
        logger.exception(
            "plan_command failed for intent='%s' prompt='%s': %s",
            intent_id, raw_prompt[:60], e,
        )
        return _emergency_fallback(intent_dict)