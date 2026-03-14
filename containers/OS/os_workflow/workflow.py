"""
containers/OS/os_workflow/workflow.py

ERP-OS Temporal Workflow — the central orchestrator.

CORRECT ARGS FOR EACH ACTIVITY (locked from actual signatures):
  validate_payload: args=[{"payload_bundle": payload, "context": context}]
  execute_command:  args=[payload_bundle, plan, context]  (3 positional)
  format_result:    args=[execution_result, intent_dict, prompt]  (3 positional)
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import Any, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from shared.models.command import CommandWorkflowInput, CommandWorkflowOutput

logger = logging.getLogger(__name__)

# ── Retry policies ────────────────────────────────────────────────────────────
_RETRY_2 = RetryPolicy(maximum_attempts=2, initial_interval=timedelta(seconds=1),
                       backoff_coefficient=2.0)
_RETRY_3 = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=2),
                       backoff_coefficient=2.0,
                       non_retryable_error_types=["ValueError", "PermissionError"])
_NO_RETRY = RetryPolicy(maximum_attempts=1)
OS_QUEUE  = "os-main-queue"

# ── Clean logging helper ──────────────────────────────────────────────────────
# workflow.logger appends Temporal metadata to every line — unreadable.
# Use workflow.logger.info which logs cleanly with just our message.

def _log(msg: str) -> None:
    workflow.logger.info(msg)

# ── Main Workflow ─────────────────────────────────────────────────────────────

@workflow.defn
class ERPOSCommandWorkflow:

    def __init__(self) -> None:
        self._status:               str           = "starting"
        self._confirmation_request: Optional[dict] = None
        self._user_confirmation:    Optional[str]  = None
        self._user_answer:          Optional[str]  = None
        self._final_response:       Optional[str]  = None

    @workflow.signal
    async def user_confirmation(self, decision: str) -> None:
        self._user_confirmation = decision

    @workflow.signal
    async def user_answer(self, answer: str) -> None:
        self._user_answer = answer

    @workflow.query
    def get_status(self) -> dict[str, Any]:
        return {
            "status":               self._status,
            "confirmation_request": self._confirmation_request,
            "response":             self._final_response,
        }

    @workflow.run
    async def run(self, inp: CommandWorkflowInput) -> CommandWorkflowOutput:
        try:
            return await self._pipeline(inp)
        except Exception as e:
            err_str = str(e)
            # Strip Temporal boilerplate from user-facing message
            if "Activity task failed" in err_str:
                err_str = "An agent failed unexpectedly. Check the terminal for details."
            elif "timeout" in err_str.lower():
                err_str = "A step timed out. Check your Gemini API key and quota."
            self._status         = "error"
            self._final_response = f"❌ {err_str}"
            workflow.logger.error("Workflow crashed: %s", e)
            return CommandWorkflowOutput(
                status="error", response=self._final_response,
                errors=[{"message": str(e)}],
            )

    async def _pipeline(self, inp: CommandWorkflowInput) -> CommandWorkflowOutput:
        HR = "━" * 64

        # ══════════════════════════════════════════════════════════════════════
        # [1] CLARITY — extract intent
        # ══════════════════════════════════════════════════════════════════════
        self._status = "clarity"
        _log(f"\n{HR}\n🧠  [1] CLARITY — parsing: {inp.prompt[:60]}\n{HR}")

        intent_dict: dict = await workflow.execute_activity(
            "extract_intent",
            args=[{
                "prompt":          inp.prompt,
                "session_context": inp.session_context,
                "erp_type":        inp.erp_type,
                "clarifications":  [],
            }],
            task_queue=OS_QUEUE,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=_RETRY_2,
        )

        conf  = intent_dict.get("confidence", 0)
        doctype = intent_dict.get("target_doctype", "?")
        _log(f"\n✅ [1] CLARITY  intent={intent_dict.get('intent_id')}  "
             f"doctype={doctype}  confidence={conf:.0%}  "
             f"{'⚠️ LLM fallback' if intent_dict.get('_fallback') else '🤖 LLM'}\n")

        # ══════════════════════════════════════════════════════════════════════
        # [2] AMBIGUITY LOOP — only if genuinely ambiguous
        # ══════════════════════════════════════════════════════════════════════
        clarification_qa: list[dict] = []

        for round_num in range(1, 4):
            blocking = [a for a in intent_dict.get("ambiguities", []) if a.get("required", True)]
            if not blocking:
                break

            first_q = blocking[0]["question"]
            self._status = "awaiting_clarification"
            self._confirmation_request = {"type": "ambiguity", "question": first_q, "round": round_num}
            self._user_answer = None

            _log(f"\n⏸️  [2] AMBIGUITY — asking: {first_q[:80]}\n")

            try:
                await workflow.wait_condition(
                    lambda: self._user_answer is not None,
                    timeout=timedelta(minutes=5),
                )
            except TimeoutError:
                self._confirmation_request = None
                break

            answer = self._user_answer
            self._user_answer          = None
            self._confirmation_request = None
            clarification_qa.append({"question": first_q, "answer": answer})
            self._status = "clarity"

            intent_dict = await workflow.execute_activity(
                "resolve_ambiguity",
                args=[{
                    "original_prompt":  inp.prompt,
                    "partial_intent":   intent_dict,
                    "clarification_qa": clarification_qa,
                }],
                task_queue=OS_QUEUE,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=_RETRY_2,
            )

        # ══════════════════════════════════════════════════════════════════════
        # [3] CONTEXT RETRIEVAL
        # ══════════════════════════════════════════════════════════════════════
        self._status = "retrieving_context"
        _log(f"\n{HR}\n📚  [3] CONTEXT — company={inp.company_id}  doctype={doctype}\n{HR}")

        context: dict = await workflow.execute_activity(
            "retrieve_context",
            args=[{
                "intent_dict":    intent_dict,
                "company_id":     inp.company_id,
                "erp_type":       inp.erp_type,
                "session_id":     inp.session_id,
                "cached_context": None,
            }],
            task_queue=OS_QUEUE,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_RETRY_2,
        )

        snap    = context.get("_safe_snapshot", {})
        company = snap.get("company_name", "?")
        module  = snap.get("module", "?")
        is_dummy = context.get("company_profile", {}).get("is_dummy", False)
        _log(f"\n✅ [3] CONTEXT  company={company}  module={module}  "
             f"{'⚠️ DUMMY PROFILE — IS not connected' if is_dummy else '🏢 REAL PROFILE'}\n")

        # ══════════════════════════════════════════════════════════════════════
        # [4] COMMAND PLANNER
        # ══════════════════════════════════════════════════════════════════════
        self._status = "planning"
        _log(f"\n{HR}\n⚙️   [4] PLANNER — {intent_dict.get('intent_id')}\n{HR}")

        plan: dict = await workflow.execute_activity(
            "plan_command",
            args=[{"intent_dict": intent_dict, "context": context}],
            task_queue=OS_QUEUE,
            start_to_close_timeout=timedelta(seconds=20),
            retry_policy=_RETRY_2,
        )

        _log(f"\n✅ [4] PLAN  steps={len(plan.get('steps',[]))}  "
             f"risk={plan.get('risk_level')}  confirm={plan.get('requires_confirmation')}\n")

        # ══════════════════════════════════════════════════════════════════════
        # [5] PAYLOAD GENERATOR
        # ══════════════════════════════════════════════════════════════════════
        self._status = "generating_payload"
        _log(f"\n{HR}\n📦  [5] PAYLOAD — building for {intent_dict.get('target_doctype')}\n{HR}")

        payload: dict = await workflow.execute_activity(
            "generate_payload",
            args=[{"plan": plan, "context": context, "intent_dict": intent_dict}],
            task_queue=OS_QUEUE,
            start_to_close_timeout=timedelta(seconds=20),
            retry_policy=_RETRY_2,
        )

        steps = payload.get("steps", [])
        _log(f"\n✅ [5] PAYLOAD  steps={len(steps)}  "
             f"endpoint={steps[0].get('endpoint','?') if steps else '?'}\n")

        # ══════════════════════════════════════════════════════════════════════
        # [6] VALIDATION
        # ══════════════════════════════════════════════════════════════════════
        self._status = "validating"
        _log(f"\n{HR}\n🔍  [6] VALIDATION — checking {doctype} payload\n{HR}")

        # validate_payload(data: dict) — single dict arg
        validation: dict = await workflow.execute_activity(
            "validate_payload",
            args=[{"payload_bundle": payload, "context": context}],
            task_queue=OS_QUEUE,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=_NO_RETRY,
        )

        n_err  = len(validation.get("errors", []))
        n_warn = len(validation.get("warnings", []))
        n_fix  = len(validation.get("auto_corrections", []))
        _log(f"\n✅ [6] VALIDATION  valid={validation.get('valid')}  "
             f"errors={n_err}  warnings={n_warn}  corrections={n_fix}\n")

        if not validation.get("valid", True):
            errors_text = "; ".join(e.get("message","") for e in validation.get("errors",[]))
            self._status         = "validation_failed"
            self._final_response = f"❌ Validation failed: {errors_text}"
            _log(f"\n❌ [6] VALIDATION FAILED: {errors_text}\n")
            return CommandWorkflowOutput(
                status="error", response=self._final_response,
                errors=validation.get("errors", []),
            )

        # ══════════════════════════════════════════════════════════════════════
        # [7] CONFIRMATION GATE
        # ══════════════════════════════════════════════════════════════════════
        risk_level = plan.get("risk_level", "low")
        should_confirm = plan.get("requires_confirmation", False) or risk_level in ("medium","high","critical")

        if should_confirm:
            self._status = "awaiting_confirmation"
            _log(f"\n⏸️  [7] CONFIRMATION GATE  risk={risk_level}\n")

            self._confirmation_request = {
                "type":       "confirmation",
                "risk_level": risk_level,
                "preview": {
                    "action_summary":   f"{intent_dict.get('action','Create').title()} {doctype}",
                    "entities":         _entities_preview(intent_dict),
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
                self._status         = "cancelled"
                self._final_response = "Command timed out waiting for confirmation."
                return CommandWorkflowOutput(status="cancelled", response=self._final_response)

            decision = self._user_confirmation
            self._user_confirmation    = None
            self._confirmation_request = None

            if decision == "cancel":
                self._status         = "cancelled"
                self._final_response = "Command cancelled. No changes made."
                return CommandWorkflowOutput(status="cancelled", response=self._final_response)

            _log("\n✅ [7] CONFIRMED — proceeding to execution\n")

        # ══════════════════════════════════════════════════════════════════════
        # [8] EXECUTION
        # ══════════════════════════════════════════════════════════════════════
        self._status = "executing"
        erp_url = context.get("erp_credentials", {}).get("erp_url", "")
        _log(f"\n{HR}\n🚀  [8] EXECUTION — {doctype} → {erp_url}\n{HR}")

        # execute_command(payload_bundle, plan, context) — 3 positional args
        execution_result: dict = await workflow.execute_activity(
            "execute_command",
            args=[payload, plan, context],
            task_queue=OS_QUEUE,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=_RETRY_3,
        )

        exec_ms  = execution_result.get("execution_time_ms", 0)
        primary  = execution_result.get("result", {})
        doc_name = primary.get("name", "") if isinstance(primary, dict) else ""
        is_stub  = isinstance(primary, dict) and primary.get("_stub", False)

        # Build ERP link
        erp_link = ""
        if erp_url and doc_name and doctype and not is_stub:
            slug     = doctype.lower().replace(" ", "-")
            erp_link = f"{erp_url}/{slug}/{doc_name}"

        if not execution_result.get("success", False):
            err = execution_result.get("error", {})
            err_msg = err.get("message", "Execution failed") if isinstance(err, dict) else str(err)
            self._status         = "error"
            self._final_response = f"❌ {err_msg}"
            _log(f"\n❌ [8] EXECUTION FAILED: {err_msg}\n")
            return CommandWorkflowOutput(
                status="error", response=self._final_response,
                errors=[{"message": err_msg}],
            )

        all_results = execution_result.get("steps_results", [])
        _log(
            f"\n✅ [8] EXECUTION  doc={doc_name}  time={exec_ms}ms  "
            f"{'⚠️ STUB (dummy ERP)' if is_stub else '✅ REAL'}\n"
            + (f"   🔗 {erp_link}\n" if erp_link else "   (no link — complete IS onboarding for real ERP)\n")
        )

        # ══════════════════════════════════════════════════════════════════════
        # [9] RESULT FORMATTER
        # ══════════════════════════════════════════════════════════════════════
        self._status = "formatting"
        _log(f"\n{HR}\n💬  [9] FORMATTER — composing response\n{HR}")

        # format_result(execution_result, intent_dict, original_prompt) — 3 positional args
        formatted: str = await workflow.execute_activity(
            "format_result",
            args=[execution_result, intent_dict, inp.prompt],
            task_queue=OS_QUEUE,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=_RETRY_2,
        )

        # Append ERP link to user response if we have one
        if erp_link:
            formatted = formatted.rstrip() + f"\n\n🔗 [{doc_name}]({erp_link})"

        self._status         = "done"
        self._final_response = formatted

        _log(
            f"\n{HR}\n"
            f"🏁  PIPELINE COMPLETE\n"
            f"    Command  : {inp.prompt[:80]}\n"
            f"    Document : {doc_name or '(none)'}\n"
            f"    Response : {formatted[:100]}\n"
            + (f"    Link     : {erp_link}\n" if erp_link else "")
            + f"{HR}\n"
        )

        return CommandWorkflowOutput(
            status="success",
            response=formatted,
            result=execution_result.get("result"),
        )


# ── Preview helper ────────────────────────────────────────────────────────────

def _entities_preview(intent_dict: dict) -> list[str]:
    entities = intent_dict.get("entities", {})
    lines: list[str] = []
    if entities.get("customer"):
        lines.append(f"Customer: {entities['customer']}")
    if entities.get("supplier"):
        lines.append(f"Supplier: {entities['supplier']}")
    for item in entities.get("items", []):
        parts = [item.get("item_code","")]
        if item.get("qty") is not None:
            parts.append(f"× {item['qty']}")
        if item.get("rate") is not None:
            parts.append(f"@ ₹{item['rate']}")
        if parts:
            lines.append(" ".join(str(p) for p in parts))
    if entities.get("delivery_date"):
        lines.append(f"Delivery: {entities['delivery_date']}")
    return lines