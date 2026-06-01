"""IS pipeline step contracts for quality gate evaluation."""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from shared.models.quality_gate import StepContract

IS_STEP_CONTRACTS: Dict[str, StepContract] = {
    "assign_corpus_doctypes": StepContract(
        step_name="assign_corpus_doctypes",
        pipeline="IS",
        expected_conditions=[
            "Every uploaded file has an assigned ERPNext doctype",
            "Classification confidence is above 0.5 for mapped files",
        ],
        auto_fixable_issues=[
            "Low-confidence classification recoverable via synonym or filename prior",
            "Wrong doctype from weak column overlap",
        ],
        user_required_issues=[
            "File format completely unrecognized",
            "User must confirm doctype for ambiguous multi-match file",
        ],
    ),
    "map_file_to_erpnext": StepContract(
        step_name="map_file_to_erpnext",
        pipeline="IS",
        expected_conditions=[
            "All mandatory identity fields mapped for each doctype",
            "No empty mandatory identity values after KB defaults",
        ],
        auto_fixable_issues=[
            "Missing naming_series or stock_uom filled from KB defaults",
            "Enum values normalized to ERP allowed options",
            "Units stripped from numeric fields",
        ],
        user_required_issues=[
            "No source column maps to a mandatory ERP field",
            "User must supply missing master data file",
        ],
    ),
    "validate_mapped_data": StepContract(
        step_name="validate_mapped_data",
        pipeline="IS",
        expected_conditions=[
            "Overall status is pass, or partial only due to data warnings",
            "No pipeline/KB failures masquerading as pass",
            "Row-level identity fields populated where required",
        ],
        auto_fixable_issues=[
            "Enum normalization and KB default injection",
            "naming_series defaults",
            "Format warnings fixable without user data",
        ],
        user_required_issues=[
            "Empty supplier/customer/item identity values in source data",
            "Cross-entity row leakage requiring user to fix source files",
            "Genuinely missing rows the user must upload",
        ],
    ),
    "finalize_import_plan": StepContract(
        step_name="finalize_import_plan",
        pipeline="IS",
        expected_conditions=[
            "Import plan includes all doctypes present in mapped corpus",
            "No phases blocked solely due to KB graph gaps",
        ],
        auto_fixable_issues=[
            "Phase ordering corrected per dependency graph",
            "Missing prerequisite doctype injected into plan",
        ],
        user_required_issues=[
            "Customer explicitly excluded a doctype from scope",
        ],
    ),
    "execute_import_phase": StepContract(
        step_name="execute_import_phase",
        pipeline="IS",
        expected_conditions=[
            "Import steps succeed or fail only due to source data issues",
            "No schema mismatch from stale KB",
        ],
        auto_fixable_issues=[
            "Duplicate record skip via idempotency",
            "Transient link resolution retry",
        ],
        user_required_issues=[
            "Data integrity violation in source rows",
            "Permission or business rule rejection from ERP",
        ],
    ),
}


def contract_as_dict(step_name: str) -> dict:
    c = IS_STEP_CONTRACTS[step_name]
    return asdict(c)
