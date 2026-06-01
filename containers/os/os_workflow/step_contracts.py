"""OS pipeline step contracts for quality gate evaluation."""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from shared.models.quality_gate import StepContract

OS_STEP_CONTRACTS: Dict[str, StepContract] = {
    "extract_intent": StepContract(
        step_name="extract_intent",
        pipeline="OS",
        expected_conditions=[
            "Target doctype identified with confidence >= 0.7",
            "Action type (create/update/submit) is clear",
            "Required entities present for the doctype",
        ],
        auto_fixable_issues=[
            "Ambiguous intent rephrased with session context",
            "Low confidence triggers clarification loop",
        ],
        user_required_issues=[
            "Command too vague to determine doctype or action",
        ],
    ),
    "resolve_entities": StepContract(
        step_name="resolve_entities",
        pipeline="OS",
        expected_conditions=[
            "All referenced entity names resolved against live ERP",
            "No unresolved link fields in payload plan",
        ],
        auto_fixable_issues=[
            "Fuzzy entity match with confidence above 0.7",
        ],
        user_required_issues=[
            "Entity does not exist in ERP and must be created or renamed by user",
        ],
    ),
    "plan_command": StepContract(
        step_name="plan_command",
        pipeline="OS",
        expected_conditions=[
            "Plan references valid Frappe doctype and field names",
            "Mandatory fields included or defaulted",
        ],
        auto_fixable_issues=[
            "Field name corrected via live schema lookup",
        ],
        user_required_issues=[
            "Mandatory field missing with no safe default",
        ],
    ),
    "validate_payload": StepContract(
        step_name="validate_payload",
        pipeline="OS",
        expected_conditions=[
            "valid=True with no hard rule violations",
            "Auto-corrections applied where safe",
        ],
        auto_fixable_issues=[
            "Date/format normalization",
            "Safe default value injection",
        ],
        user_required_issues=[
            "Business rule violation requiring user decision",
            "Missing party or line items",
        ],
    ),
    "execute_command": StepContract(
        step_name="execute_command",
        pipeline="OS",
        expected_conditions=[
            "Frappe API returns success for the command",
        ],
        auto_fixable_issues=[
            "Transient network/API error worth one retry",
        ],
        user_required_issues=[
            "ERP permission or data constraint from live site",
        ],
    ),
}


def contract_as_dict(step_name: str) -> dict:
    c = OS_STEP_CONTRACTS[step_name]
    return asdict(c)
