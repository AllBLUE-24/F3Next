"""
containers/OS/os_workflow/workflow.py

The ERP-OS Temporal Workflow — the central orchestrator.
One workflow execution = one user NL command, end to end.

FIXES: 
  - Changed terminal states on handled errors from "error" to "done".
  - This forces the frontend to fetch the `/result` endpoint and
    render the translated English error message instead of panicking
    and showing a generic UI fallback string.
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Any, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from shared.models.command import CommandWorkflowInput, CommandWorkflowOutput

logger = logging.getLogger(__name__)

# ─── Retry policies ───────────────────────────────────────────────────────────

_RETRY_2 = RetryPolicy(
    maximum_attempts    = 2,
    initial_interval    = timedelta(seconds=2),
    backoff_coefficient = 2.0,
)

# LLM activities (Clarity, Result Formatter) — Gemini cold starts can exceed 60s
_RETRY_LLM = RetryPolicy(
    maximum_attempts    = 3,
    initial_interval    = timedelta(seconds=3),
    backoff_coefficient = 2.0,
)

_RETRY_3 = RetryPolicy(
    maximum_attempts    = 3,
    initial_interval    = timedelta(seconds=3),
    backoff_coefficient = 2.0,
    non_retryable_error_types = ["ValueError", "PermissionError", "AuthError"],
)

_NO_RETRY = RetryPolicy(maximum_attempts=1)

OS_QUEUE = "os-main-queue"

# ─── Post-clarity gating (prevent bad intents from propagating) ───────────────
_ITEMS_REQUIRED_DOCTYPES = {
    "Sales Order", "Sales Invoice", "Delivery Note",
    "Purchase Order", "Purchase Invoice", "Purchase Receipt",
    "Stock Entry", "Quotation",
}

_SALES_DOCTYPES_REQUIRE_CUSTOMER = {"Sales Order", "Sales Invoice", "Delivery Note", "Quotation"}
_PURCHASE_DOCTYPES_REQUIRE_SUPPLIER = {"Purchase Order", "Purchase Invoice", "Purchase Receipt"}


def _gate_intent_for_minimum_requirements(intent_dict: dict) -> dict:
    """
    Ensure low-confidence / fallback / incomplete intents trigger the ambiguity loop.

    This is deterministic and runs inside the workflow (no I/O).
    """
    doctype = str(intent_dict.get("target_doctype") or "")
    entities = intent_dict.get("entities") or {}
    confidence = float(intent_dict.get("confidence") or 0.0)
    is_fallback = bool(intent_dict.get("_fallback"))

    ambiguities = intent_dict.get("ambiguities")
    if not isinstance(ambiguities, list):
        ambiguities = []
    else:
        # Defensive: ambiguity loop expects dicts with a 'question' key
        ambiguities = [a for a in ambiguities if isinstance(a, dict) and a.get("question")]

    def _add_required(field: str, question: str) -> None:
        ambiguities.append({"field": field, "question": question, "required": True})

    # Required items
    items = entities.get("items") or []
    if doctype in _ITEMS_REQUIRED_DOCTYPES and (not isinstance(items, list) or len(items) == 0):
        _add_required(
            "items",
            f"What item(s) should be included in this {doctype}, and what quantity for each?",
        )

    # Required party
    if doctype in _SALES_DOCTYPES_REQUIRE_CUSTOMER and not entities.get("customer"):
        _add_required("customer", f"Which customer is this {doctype} for?")
    if doctype in _PURCHASE_DOCTYPES_REQUIRE_SUPPLIER and not entities.get("supplier"):
        _add_required("supplier", f"Which supplier is this {doctype} for?")

    # Fallback/low-confidence intents must clarify unless already clarified
    if (is_fallback or confidence < 0.70) and not ambiguities:
        _add_required(
            "clarify",
            "I couldn't reliably parse your command. Please confirm the customer/supplier and the item(s) with quantity.",
        )

    intent_dict["ambiguities"] = ambiguities
    intent_dict["has_ambiguities"] = len(ambiguities) > 0
    return intent_dict


_FIXABLE_VALIDATION_RULE_IDS = {
    "mandatory_fields",
    "child_table_validation",
    "unknown_customer",
    "unknown_supplier",
    "unknown_item",
    "unknown_warehouse",
}

class NotReadyError(Exception):
    """Raised when OS prerequisites (IS/CVS) are not satisfied."""


def _readiness_blocker(intent_dict: dict, context: dict) -> Optional[str]:
    """
    Return a human-friendly blocker message if the system is not ready to execute
    this intent. Pure function (safe in workflow).
    """
    if isinstance(context, dict) and context.get("_readiness_blocker"):
        return str(context.get("_readiness_blocker"))

    profile = context.get("company_profile", {}) if isinstance(context, dict) else {}
    if not isinstance(profile, dict):
        profile = {}

    if profile.get("is_dummy") and not profile.get("dummy_allowed", False):
        return (
            "Your ERP setup is not complete yet (no ERP credentials configured). "
            "Please finish the Implementation System deployment first."
        )

    registry = profile.get("entity_registry", {}) if isinstance(profile.get("entity_registry", {}), dict) else {}
    known_customers = registry.get("known_customers") or []
    known_suppliers = registry.get("known_suppliers") or []
    known_items = registry.get("known_items") or []

    doctype = str(intent_dict.get("target_doctype") or "")

    if doctype in _ITEMS_REQUIRED_DOCTYPES and (not isinstance(known_items, list) or len(known_items) == 0):
        return (
            "Context sync is not ready: no Items found in CVS for this company. "
            "Run CVS force-sync after deployment/import, then try again."
        )

    if doctype in _SALES_DOCTYPES_REQUIRE_CUSTOMER and (not isinstance(known_customers, list) or len(known_customers) == 0):
        return (
            "Context sync is not ready: no Customers found in CVS for this company. "
            "Run CVS force-sync after deployment/import, then try again."
        )

    if doctype in _PURCHASE_DOCTYPES_REQUIRE_SUPPLIER and (not isinstance(known_suppliers, list) or len(known_suppliers) == 0):
        return (
            "Context sync is not ready: no Suppliers found in CVS for this company. "
            "Run CVS force-sync after deployment/import, then try again."
        )

    return None


def _is_fixable_validation(validation: dict) -> bool:
    errs = validation.get("errors", []) if isinstance(validation, dict) else []
    for e in errs if isinstance(errs, list) else []:
        if isinstance(e, dict) and e.get("rule_id") in _FIXABLE_VALIDATION_RULE_IDS:
            return True
    return False


def _build_validation_clarification_question(validation: dict) -> str:
    """
    Convert validation errors into a single high-signal clarification question.
    """
    errs = validation.get("errors", []) if isinstance(validation, dict) else []
    rule_ids = {e.get("rule_id") for e in errs if isinstance(e, dict)}
    fields = {e.get("field") for e in errs if isinstance(e, dict)}

    # Most common blockers
    if "mandatory_fields" in rule_ids or "child_table_validation" in rule_ids:
        if any("items" in str(f or "") for f in fields):
            return "Please provide the item(s) to include and the quantity for each."

    if "unknown_customer" in rule_ids:
        bad = next((e.get("message") for e in errs if isinstance(e, dict) and e.get("rule_id") == "unknown_customer"), "")
        return f"{bad} Please provide an existing customer name."

    if "unknown_supplier" in rule_ids:
        bad = next((e.get("message") for e in errs if isinstance(e, dict) and e.get("rule_id") == "unknown_supplier"), "")
        return f"{bad} Please provide an existing supplier name."

    if "unknown_item" in rule_ids:
        bad = next((e.get("message") for e in errs if isinstance(e, dict) and e.get("rule_id") == "unknown_item"), "")
        return f"{bad} Please provide an existing item code/name and quantity."

    # Fallback: show concise list
    messages = [e.get("message", "") for e in errs if isinstance(e, dict) and e.get("message")]
    messages = [m for m in messages if m]
    joined = "; ".join(messages[:3])
    return f"I need a quick clarification to proceed: {joined}" if joined else "Could you clarify the missing details?"


# ─── Main Workflow ────────────────────────────────────────────────────────────

@workflow.defn
class ERPOSCommandWorkflow:
    """
    The ERP-OS Command Workflow.
    One instance per user command.
    """

    def __init__(self) -> None:
        self._status:               str                    = "starting"
        self._confirmation_request: Optional[dict]         = None
        self._user_confirmation:    Optional[str]          = None
        self._user_answer:          Optional[str]          = None
        self._final_response:       Optional[str]          = None

    # ── Signals ───────────────────────────────────────────────────────────────

    @workflow.signal
    async def user_confirmation(self, decision: str) -> None:
        self._user_confirmation = decision

    @workflow.signal
    async def user_answer(self, answer: str) -> None:
        self._user_answer = answer

    # ── Query ─────────────────────────────────────────────────────────────────

    @workflow.query
    def get_status(self) -> dict[str, Any]:
        """Polled by the frontend every 1.5s."""
        return {
            "status":               self._status,
            "confirmation_request": self._confirmation_request,
            "response":             self._final_response,
        }

    async def _run_ambiguity_loop(
        self,
        original_prompt: str,
        intent_dict: dict,
        clarification_qa: list[dict],
        *,
        max_rounds: int = 3,
    ) -> tuple[dict, list[dict]]:
        """
        Run the shared ambiguity/clarification loop.
        Can be invoked multiple times (e.g., after validation failures).
        """
        for round_num in range(1, max_rounds + 1):
            ambiguities = intent_dict.get("ambiguities", [])
            if not isinstance(ambiguities, list):
                ambiguities = []
            blocking = [a for a in ambiguities if isinstance(a, dict) and a.get("required", True)]
            if not blocking:
                break

            first_q = blocking[0].get("question") or "Could you clarify?"
            self._status = "awaiting_clarification"
            self._confirmation_request = {
                "type":     "ambiguity",
                "question": first_q,
                "round":    round_num,
            }
            self._user_answer = None

            try:
                await workflow.wait_condition(
                    lambda: self._user_answer is not None,
                    timeout=timedelta(minutes=5),
                )
            except TimeoutError:
                workflow.logger.warning("Clarification timeout round %d — proceeding", round_num)
                self._confirmation_request = None
                break

            answer = self._user_answer
            self._user_answer = None
            self._confirmation_request = None
            clarification_qa.append({"question": first_q, "answer": answer})
            self._status = "clarity"

            intent_dict = await workflow.execute_activity(
                "resolve_ambiguity",
                args=[{
                    "original_prompt":  original_prompt,
                    "partial_intent":   intent_dict,
                    "clarification_qa": clarification_qa,
                }],
                task_queue             = OS_QUEUE,
                start_to_close_timeout = timedelta(seconds=90),
                retry_policy           = _RETRY_LLM,
            )

            # Re-apply post-clarity gate after every clarification
            intent_dict = _gate_intent_for_minimum_requirements(intent_dict)

        return intent_dict, clarification_qa

    async def _build_plan_payload_and_validate(
        self,
        inp: CommandWorkflowInput,
        intent_dict: dict,
        *,
        hr: str,
    ) -> tuple[dict, dict, dict, dict]:
        """
        Steps 3-6: retrieve context, build plan, generate payload, validate payload.
        Extracted so the workflow can re-run this block after clarifications.
        """
        # ══════════════════════════════════════════════════════════════════════
        # STEP 3 — CONTEXT RETRIEVAL
        # ══════════════════════════════════════════════════════════════════════
        self._status = "retrieving_context"
        workflow.logger.info("\n%s\n📚  [3] CONTEXT RETRIEVAL — loading company profile & KB\n%s", hr, hr)

        context: dict = await workflow.execute_activity(
            "retrieve_context",
            args=[{
                "intent_dict":    intent_dict,
                # Canonical internal identifier is the project UUID.
                # company_id is treated as company_slug (legacy/human-friendly).
                "company_id":     inp.project_id,
                "erp_type":       inp.erp_type,
                "session_id":     inp.session_id,
                "cached_context": None,
            }],
            task_queue             = OS_QUEUE,
            start_to_close_timeout = timedelta(seconds=30),
            retry_policy           = _RETRY_2,
        )

        workflow.logger.info(
            "\n✅ [3] CONTEXT — company=%s  module=%s  doctype=%s\n",
            context.get("_safe_snapshot", {}).get("company_name", "?"),
            context.get("_safe_snapshot", {}).get("module", "?"),
            context.get("_safe_snapshot", {}).get("target_doctype", "?"),
        )

        blocker = _readiness_blocker(intent_dict, context)
        if blocker:
            raise NotReadyError(blocker)

        # ══════════════════════════════════════════════════════════════════════
        # STEP 4 — COMMAND PLANNER
        # ══════════════════════════════════════════════════════════════════════
        self._status = "planning"
        workflow.logger.info("\n%s\n⚙️   [4] COMMAND PLANNER — building execution plan\n%s", hr, hr)

        plan: dict = await workflow.execute_activity(
            "plan_command",
            args=[{
                "intent_dict": intent_dict,
                "context":     context,
            }],
            task_queue             = OS_QUEUE,
            start_to_close_timeout = timedelta(seconds=20),
            retry_policy           = _RETRY_2,
        )

        workflow.logger.info(
            "\n✅ [4] PLAN — steps=%d  risk=%s  confirm=%s  pattern=%s\n%s\n",
            len(plan.get("steps", [])),
            plan.get("risk_level", "?"),
            plan.get("requires_confirmation", False),
            plan.get("pattern_id") or "single-step",
            json.dumps(plan, indent=2, default=str),
        )

        # ══════════════════════════════════════════════════════════════════════
        # STEP 5 — PAYLOAD GENERATOR
        # ══════════════════════════════════════════════════════════════════════
        self._status = "generating_payload"
        workflow.logger.info("\n%s\n📦  [5] PAYLOAD GENERATOR — building ERP API payload\n%s", hr, hr)

        payload: dict = await workflow.execute_activity(
            "generate_payload",
            args=[{
                "plan":        plan,
                "context":     context,
                "intent_dict": intent_dict,
            }],
            task_queue             = OS_QUEUE,
            start_to_close_timeout = timedelta(seconds=20),
            retry_policy           = _RETRY_2,
        )

        n_steps = len(payload.get("steps", []))
        workflow.logger.info(
            "\n✅ [5] PAYLOAD — %d step(s) built\n%s\n",
            n_steps,
            json.dumps(payload, indent=2, default=str),
        )

        # ══════════════════════════════════════════════════════════════════════
        # STEP 6 — VALIDATION AGENT
        # ══════════════════════════════════════════════════════════════════════
        self._status = "validating"
        workflow.logger.info("\n%s\n🔍  [6] VALIDATION AGENT — checking payload\n%s", hr, hr)

        validation: dict = await workflow.execute_activity(
            "validate_payload",
            args=[payload, context],
            task_queue             = OS_QUEUE,
            start_to_close_timeout = timedelta(seconds=15),
            retry_policy           = _NO_RETRY,
        )

        return context, plan, payload, validation

    # ── Run ───────────────────────────────────────────────────────────────────

    @workflow.run
    async def run(self, inp: CommandWorkflowInput) -> CommandWorkflowOutput:
        try:
            return await self._execute_pipeline(inp)
        except Exception as e:
            workflow.logger.error("Workflow failed: %s", e)
            # 🔴 FIX: Set to "done" so frontend fetches the result JSON
            self._status = "done" 
            self._final_response = f"❌ Command failed: {e}"
            return CommandWorkflowOutput(
                status   = "error",
                response = self._final_response,
                errors   = [{"message": str(e)}],
            )

    async def _execute_pipeline(self, inp: CommandWorkflowInput) -> CommandWorkflowOutput:
        """Full 9-step pipeline — all real activities, no stubs, no fallbacks."""

        _HR = "━" * 64

        # ══════════════════════════════════════════════════════════════════════
        # STEP 1 — CLARITY: extract intent
        # ══════════════════════════════════════════════════════════════════════
        self._status = "clarity"
        workflow.logger.info("\n%s\n🧠  [1] CLARITY AGENT — extracting intent\n%s", _HR, _HR)

        intent_dict: dict = await workflow.execute_activity(
            "extract_intent",
            args=[{
                "prompt":          inp.prompt,
                "session_context": inp.session_context,
                "erp_type":        inp.erp_type,
                "clarifications":  [],
                "project_id":      str(inp.project_id),
            }],
            task_queue             = OS_QUEUE,
            start_to_close_timeout = timedelta(seconds=90),
            retry_policy           = _RETRY_LLM,
        )

        workflow.logger.info(
            "\n✅ [1] CLARITY — intent=%s  doctype=%s  confidence=%.2f  ambiguities=%d\n",
            intent_dict.get("intent_id"),
            intent_dict.get("target_doctype"),
            intent_dict.get("confidence", 0),
            len(intent_dict.get("ambiguities", [])),
        )

        # Post-clarity gate: force ambiguity loop for fallback/low-confidence/incomplete intents
        intent_dict = _gate_intent_for_minimum_requirements(intent_dict)

        # ══════════════════════════════════════════════════════════════════════
        # STEP 2 — AMBIGUITY LOOP (max 3 rounds)
        # ══════════════════════════════════════════════════════════════════════
        clarification_qa: list[dict] = []
        intent_dict, clarification_qa = await self._run_ambiguity_loop(
            original_prompt=inp.prompt,
            intent_dict=intent_dict,
            clarification_qa=clarification_qa,
            max_rounds=3,
        )
        # Steps 3-6: allow a small number of repair rounds if validation is fixable
        context: dict = {}
        plan: dict = {}
        payload: dict = {}
        validation: dict = {}

        max_repairs = 2
        for repair_round in range(0, max_repairs + 1):
            if repair_round > 0:
                workflow.logger.info("\n🔁 Repair round %d/%d — rebuilding plan/payload after clarification\n", repair_round, max_repairs)

            try:
                context, plan, payload, validation = await self._build_plan_payload_and_validate(
                    inp=inp,
                    intent_dict=intent_dict,
                    hr=_HR,
                )
            except NotReadyError as e:
                self._status = "done"
                self._final_response = str(e)
                return CommandWorkflowOutput(
                    status="error",
                    response=self._final_response,
                    errors=[{"rule_id": "not_ready", "field": "system", "message": str(e), "severity": "error", "step": 0}],
                )
            n_warn = len(validation.get("warnings", []))
            n_fix  = len(validation.get("auto_corrections", []))

            if not validation.get("valid", True):
                errors_text = "; ".join(e.get("message", "") for e in validation.get("errors", []))
                workflow.logger.error("\n❌ [6] VALIDATION FAILED: %s\n", errors_text)

                if repair_round < max_repairs and _is_fixable_validation(validation):
                    q = _build_validation_clarification_question(validation)
                    intent_dict["ambiguities"] = [{"field": "validation", "question": q, "required": True}]
                    intent_dict["has_ambiguities"] = True
                    intent_dict, clarification_qa = await self._run_ambiguity_loop(
                        original_prompt=inp.prompt,
                        intent_dict=intent_dict,
                        clarification_qa=clarification_qa,
                        max_rounds=1,
                    )
                    # retry steps 3-6
                    continue

                validation_error_result = {
                    "success":           False,
                    "result":            {},
                    "steps_results":     [],
                    "execution_time_ms": 0,
                    "error":             {"message": f"Validation failed: {errors_text}"},
                }

                try:
                    formatted_error: str = await workflow.execute_activity(
                        "format_result",
                        args=[validation_error_result, intent_dict, inp.prompt],
                        task_queue             = OS_QUEUE,
                        start_to_close_timeout = timedelta(seconds=25),
                        retry_policy           = _NO_RETRY,
                    )
                except Exception:
                    formatted_error = f"❌ Validation failed: {errors_text}"

                # 🔴 FIX: Set to "done" so frontend fetches the result JSON instead of panicking
                self._status         = "done"
                self._final_response = formatted_error
                return CommandWorkflowOutput(
                    status   = "error", # Backend knows it's an error, but workflow is "done"
                    response = self._final_response,
                    errors   = validation.get("errors", []),
                )

            workflow.logger.info(
                "\n✅ [6] VALIDATION — valid=True  errors=0  warnings=%d  corrections=%d\n",
                n_warn, n_fix,
            )
            break

        # ══════════════════════════════════════════════════════════════════════
        # STEP 7 — CONFIRMATION GATE
        # ══════════════════════════════════════════════════════════════════════
        risk_level            = plan.get("risk_level", intent_dict.get("risk_level", "low"))
        requires_confirmation = plan.get("requires_confirmation", False)
        should_confirm        = requires_confirmation or risk_level in ("medium", "high", "critical")

        if should_confirm:
            self._status = "awaiting_confirmation"
            workflow.logger.info(
                "\n⏸️   [7] CONFIRMATION GATE — risk=%s  awaiting user decision\n", risk_level
            )

            self._confirmation_request = {
                "type":       "confirmation",
                "risk_level": risk_level,
                "preview": {
                    "action_summary":   f"{intent_dict.get('action','Create').title()} {intent_dict.get('target_doctype','Document')}",
                    "entities":         _build_entities_preview(intent_dict, validation),
                    "warnings":         validation.get("warnings", []),
                    "auto_corrections": validation.get("auto_corrections", []),
                },
            }

            self._user_confirmation = None
            try:
                await workflow.wait_condition(
                    lambda: self._user_confirmation is not None,
                    timeout=timedelta(minutes=5),
                )
            except TimeoutError:
                # 🔴 FIX: Set to "done"
                self._status = "done"
                self._confirmation_request = None
                self._final_response = "Command timed out waiting for confirmation. No changes were made."
                return CommandWorkflowOutput(
                    status   = "cancelled",
                    response = self._final_response,
                )

            decision = self._user_confirmation
            self._user_confirmation    = None
            self._confirmation_request = None

            if decision == "cancel":
                # 🔴 FIX: Set to "done"
                self._status = "done"
                self._final_response = "Command cancelled. No changes were made."
                return CommandWorkflowOutput(
                    status   = "cancelled",
                    response = self._final_response,
                )

            workflow.logger.info("\n✅ [7] CONFIRMATION — user confirmed, proceeding\n")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 8 — EXECUTION AGENT
        # ══════════════════════════════════════════════════════════════════════
        self._status = "executing"
        workflow.logger.info("\n%s\n🚀  [8] EXECUTION AGENT — calling ERPNext API\n%s", _HR, _HR)

        execution_result: dict = await workflow.execute_activity(
            "execute_command",
            args=[payload, plan, context],
            task_queue             = OS_QUEUE,
            start_to_close_timeout = timedelta(seconds=60),
            retry_policy           = _RETRY_3,
        )

        if not execution_result.get("success", False):
            err_msg = execution_result.get("error", {})
            if isinstance(err_msg, dict):
                err_msg = err_msg.get("message", "Execution failed")
            workflow.logger.info("\n❌ [8] EXECUTION FAILED: %s\n", err_msg)

            try:
                formatted_error: str = await workflow.execute_activity(
                    "format_result",
                    args=[execution_result, intent_dict, inp.prompt],
                    task_queue             = OS_QUEUE,
                    start_to_close_timeout = timedelta(seconds=15),
                    retry_policy           = _NO_RETRY,
                )
            except Exception:
                formatted_error = f"❌ {err_msg}"

            # 🔴 FIX: Set to "done" so frontend fetches the result JSON
            self._status         = "done"
            self._final_response = formatted_error
            return CommandWorkflowOutput(
                status   = "error",
                response = self._final_response,
                errors   = [{"message": str(err_msg)}],
            )

        primary     = execution_result.get("result", {})
        doc_name    = primary.get("name", "") if isinstance(primary, dict) else ""
        exec_ms     = execution_result.get("execution_time_ms", 0)
        erp_url     = context.get("erp_credentials", {}).get("erp_url", "")
        doctype     = intent_dict.get("target_doctype", "")

        erp_link = ""
        if erp_url and doc_name and doctype:
            erp_link = f"{erp_url}/{doctype.replace(' ', '-').lower()}/{doc_name}"

        all_results = execution_result.get("all_results", [])
        steps_summary = "  ".join(
            f"Step {r['step']}: {r['doctype']} → {r['name']}"
            for r in all_results if r.get("name")
        ) or f"{doctype} → {doc_name}"

        workflow.logger.info(
            "\n✅ [8] EXECUTION SUCCESS in %dms\n   %s\n%s\n",
            exec_ms, steps_summary,
            f"   🔗 {erp_link}" if erp_link else "",
        )

        # ══════════════════════════════════════════════════════════════════════
        # STEP 9 — RESULT FORMATTER
        # ══════════════════════════════════════════════════════════════════════
        self._status = "formatting"
        workflow.logger.info("\n%s\n💬  [9] RESULT FORMATTER — composing response\n%s", _HR, _HR)

        formatted: str = await workflow.execute_activity(
            "format_result",
            args=[execution_result, intent_dict, inp.prompt],
            task_queue             = OS_QUEUE,
            start_to_close_timeout = timedelta(seconds=60),
            retry_policy           = _RETRY_LLM,
        )

        self._status         = "done"
        self._final_response = formatted

        workflow.logger.info(
            "\n%s\n🏁  PIPELINE COMPLETE\n   command  : %s\n   result   : %s\n   response : %s\n%s\n%s\n",
            _HR,
            inp.prompt,
            doc_name or "(no doc)",
            formatted[:120],
            f"   link     : {erp_link}" if erp_link else "",
            _HR,
        )

        return CommandWorkflowOutput(
            status   = "success",
            response = formatted,
            result   = execution_result.get("result"),
        )


# ─── Preview helper (pure function — safe in workflow) ────────────────────────

def _build_entities_preview(intent_dict: dict, validation: dict) -> list[str]:
    entities = intent_dict.get("entities", {})
    lines: list[str] = []

    if entities.get("customer"):
        lines.append(f"Customer: {entities['customer']}")
    if entities.get("supplier"):
        lines.append(f"Supplier: {entities['supplier']}")

    items = entities.get("items", [])
    for item in items:
        parts = []
        if item.get("item_code"):
            parts.append(item["item_code"])
        if item.get("qty") is not None:
            parts.append(f"× {item['qty']}")
        if item.get("rate") is not None:
            parts.append(f"@ ₹{item['rate']}")
        if parts:
            lines.append(" ".join(str(p) for p in parts))

    if entities.get("delivery_date"):
        lines.append(f"Delivery: {entities['delivery_date']}")
    if entities.get("po_no"):
        lines.append(f"PO Ref: {entities['po_no']}")
    if entities.get("amount"):
        lines.append(f"Amount: ₹{entities['amount']}")

    return lines