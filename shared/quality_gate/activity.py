"""
Quality gate Temporal activity — deterministic rules + optional LLM review.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from temporalio import activity

from shared.models.quality_gate import QualityGateInput, QualityGateResult, StepContract
from shared.quality_gate.evaluate import evaluate_quality_gate


class QualityGateLLMOutput(BaseModel):
    verdict: str = Field(description="ok | retry | user_gap | hard_block")
    analysis: str = ""
    retry_feedback: str = ""
    user_gap_description: str = ""


QUALITY_GATE_LLM_PROMPT = """You are a pipeline quality gate for an ERP import system.

STEP: {step_name} ({pipeline})
EXPECTED:
{expected}

AUTO-FIXABLE (supervisor/KB can resolve):
{auto_fixable}

USER-REQUIRED ONLY:
{user_required}

ACTUAL OUTPUT:
{actual_json}

NODE STATUS (errors/warnings):
{status_json}

RETRY COUNT: {retry_count}

Classify the outcome. Prefer "ok" when expectations are met or only benign warnings exist.
Use "retry" only for fixable pipeline issues (not missing user data).
Use "user_gap" when the user must upload data or confirm values.
Use "hard_block" for unrecoverable internal failures.

Return JSON matching the schema.
"""


async def _log_gate_audit(inp: QualityGateInput, result: QualityGateResult) -> None:
    details = {
        "pipeline": inp.pipeline,
        "step": inp.step_name,
        "verdict": result.verdict,
        "analysis": result.analysis,
        "retry_count": inp.retry_count,
    }
    if inp.pipeline == "IS" and inp.session_id:
        try:
            from containers.implementation.file_io.persist_audit import log_audit

            await log_audit(
                session_id=inp.session_id,
                action="quality_gate_verdict",
                actor="quality_gate",
                details=details,
                result=result.verdict,
            )
        except Exception as e:
            activity.logger.warning("quality_gate audit log failed: %s", e)


async def _persist_gate_chat(inp: QualityGateInput, result: QualityGateResult) -> None:
    if inp.pipeline != "IS" or not inp.session_id:
        return
    try:
        from containers.implementation.file_io.persist_chat_message import save_chat_message
        from shared.quality_gate.chat_bridge import step_to_chat_step

        step = step_to_chat_step(inp.step_name, inp.pipeline)
        if result.verdict == "user_gap" and result.user_gap_description:
            content = (
                "I need your help before we can continue:\n"
                f"{result.user_gap_description}"
            )
            await save_chat_message(
                inp.session_id,
                step,
                "system",
                content,
                message_type="supervisor_question",
                message_metadata={"quality_gate": True, "verdict": result.verdict},
            )
        elif result.verdict == "retry" and result.retry_feedback:
            content = (
                "I detected a fixable issue and will retry automatically:\n"
                f"{result.retry_feedback}"
            )
            await save_chat_message(
                inp.session_id,
                step,
                "system",
                content,
                message_type="auto_fix_applied",
                message_metadata={"quality_gate": True, "verdict": result.verdict},
            )
        elif result.verdict == "hard_block":
            content = f"Import blocked at **{inp.step_name}**: {result.analysis}"
            await save_chat_message(
                inp.session_id,
                step,
                "system",
                content,
                message_type="supervisor_question",
                message_metadata={"quality_gate": True, "verdict": result.verdict, "step": inp.step_name},
            )
        elif result.verdict == "ok" and result.analysis and "successfully" not in result.analysis.lower():
            await save_chat_message(
                inp.session_id,
                step,
                "system",
                result.analysis,
                message_type="default_assumed",
                message_metadata={"quality_gate": True, "verdict": "ok", "step": inp.step_name},
            )
    except Exception as e:
        activity.logger.warning("quality_gate chat message failed: %s", e)


async def _llm_evaluate(
    contract: StepContract,
    node_report: Dict[str, Any],
    retry_count: int,
) -> QualityGateResult:
    from shared.structured_llm import generate_typed

    prompt = QUALITY_GATE_LLM_PROMPT.format(
        step_name=contract.step_name,
        pipeline=contract.pipeline,
        expected="\n".join(f"- {c}" for c in contract.expected_conditions),
        auto_fixable="\n".join(f"- {c}" for c in contract.auto_fixable_issues),
        user_required="\n".join(f"- {c}" for c in contract.user_required_issues),
        actual_json=json.dumps(node_report.get("actual_outputs") or {}, default=str)[:6000],
        status_json=json.dumps(node_report.get("node_status") or {}, default=str)[:6000],
        retry_count=retry_count,
    )
    out = await generate_typed(
        prompt=prompt,
        schema=QualityGateLLMOutput,
        temperature=0.0,
        max_output_tokens=800,
    )
    verdict = str(out.get("verdict") or "ok")
    if verdict not in ("ok", "retry", "user_gap", "hard_block"):
        verdict = "ok"
    return QualityGateResult(
        verdict=verdict,  # type: ignore[arg-type]
        analysis=str(out.get("analysis") or ""),
        retry_feedback=str(out.get("retry_feedback") or "") or None,
        user_gap_description=str(out.get("user_gap_description") or "") or None,
    )


@activity.defn(name="quality_gate")
async def quality_gate(inp: QualityGateInput) -> Dict[str, Any]:
    if inp.pipeline == "IS" and os.getenv("IS_QUALITY_GATE_ENABLED", "0") != "1":
        activity.logger.info(
            "▶ quality_gate | pipeline=%s step=%s — disabled (IS_QUALITY_GATE_ENABLED=0)",
            inp.pipeline,
            inp.step_name,
        )
        return QualityGateResult(
            verdict="ok",
            analysis="quality gate disabled",
        ).to_dict()

    activity.logger.info(
        "▶ quality_gate | pipeline=%s step=%s retry=%d",
        inp.pipeline,
        inp.step_name,
        inp.retry_count,
    )

    contract = StepContract(
        step_name=str(inp.contract.get("step_name") or inp.step_name),
        pipeline=str(inp.contract.get("pipeline") or inp.pipeline),
        expected_conditions=list(inp.contract.get("expected_conditions") or []),
        auto_fixable_issues=list(inp.contract.get("auto_fixable_issues") or []),
        user_required_issues=list(inp.contract.get("user_required_issues") or []),
        max_retries=int(inp.contract.get("max_retries") or 2),
    )

    node_report = dict(inp.node_report or {})

    result = evaluate_quality_gate(contract, node_report, retry_count=inp.retry_count)

    use_llm = os.getenv("QUALITY_GATE_LLM", "0") == "1"
    if result is None and use_llm:
        try:
            result = await _llm_evaluate(contract, node_report, inp.retry_count)
        except Exception as e:
            activity.logger.warning("quality_gate LLM fallback failed: %s", e)
            result = QualityGateResult(
                verdict="ok",
                analysis="Ambiguous outcome; proceeding (LLM gate unavailable).",
            )

    if result is None:
        result = QualityGateResult(
            verdict="ok",
            analysis="No blocking issues detected by deterministic gate.",
        )

    await _log_gate_audit(inp, result)
    await _persist_gate_chat(inp, result)

    activity.logger.info(
        "✅ quality_gate | verdict=%s analysis=%s",
        result.verdict,
        result.analysis[:120],
    )
    return result.to_dict()
