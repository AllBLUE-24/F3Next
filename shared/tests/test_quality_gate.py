"""Tests for deterministic quality gate evaluation."""

from dataclasses import asdict

from shared.models.quality_gate import StepContract, build_node_report
from shared.quality_gate.evaluate import evaluate_quality_gate


def _contract(step: str) -> StepContract:
    return StepContract(
        step_name=step,
        pipeline="IS",
        expected_conditions=["pass or partial from data only"],
        auto_fixable_issues=["enum", "defaults"],
        user_required_issues=["missing data"],
        max_retries=2,
    )


def test_validate_success_ok():
    report = asdict(
        build_node_report(
            "validate_mapped_data",
            "IS",
            {"status": "success", "errors": [], "warnings": []},
            actual_outputs={"overall": "pass"},
        )
    )
    result = evaluate_quality_gate(_contract("validate_mapped_data"), report)
    assert result is not None
    assert result.verdict == "ok"


def test_validate_partial_warnings_ok():
    report = asdict(
        build_node_report(
            "validate_mapped_data",
            "IS",
            {"status": "partial", "errors": [], "warnings": [{"message": "sparse row"}]},
        )
    )
    result = evaluate_quality_gate(_contract("validate_mapped_data"), report)
    assert result.verdict == "ok"


def test_validate_missing_info_user_gap():
    report = asdict(
        build_node_report(
            "validate_mapped_data",
            "IS",
            {
                "status": "failed",
                "errors": [],
                "missing_information": ["Supplier name empty on rows 3-4"],
            },
        )
    )
    result = evaluate_quality_gate(_contract("validate_mapped_data"), report)
    assert result.verdict == "user_gap"


def test_finalize_blocked():
    report = {
        "node_status": {"status": "failed"},
        "actual_outputs": {"plan_status": "blocked"},
    }
    contract = StepContract(step_name="finalize_import_plan", pipeline="IS")
    result = evaluate_quality_gate(contract, report)
    assert result.verdict == "user_gap"


def test_map_zero_user_gap():
    report = {
        "node_status": {"status": "failed"},
        "actual_outputs": {"mapped_count": 0, "total_files": 3},
    }
    contract = StepContract(step_name="map_file_to_erpnext", pipeline="IS")
    result = evaluate_quality_gate(contract, report)
    assert result.verdict == "user_gap"


def test_os_validate_invalid_user_gap():
    report = asdict(
        build_node_report(
            "validate_payload",
            "OS",
            {},
            actual_outputs={
                "valid": False,
                "errors": [{"message": "Customer is required for Sales Order"}],
            },
        )
    )
    contract = StepContract(step_name="validate_payload", pipeline="OS", max_retries=2)
    result = evaluate_quality_gate(contract, report)
    assert result.verdict == "user_gap"


def test_validate_source_file_conflict_user_gap():
    report = {
        "node_status": {"status": "partial"},
        "actual_outputs": {
            "overall": "partial",
            "source_file_conflicts": [
                {
                    "file": "active_projects.csv",
                    "assigned_doctype": "Purchase Receipt",
                    "implied_doctype": "Project",
                }
            ],
        },
    }
    result = evaluate_quality_gate(_contract("validate_mapped_data"), report)
    assert result is not None
    assert result.verdict == "user_gap"


def test_quality_gate_activity_skips_when_is_gate_disabled(monkeypatch):
    import asyncio

    from shared.models.quality_gate import QualityGateInput
    from shared.quality_gate.activity import quality_gate

    monkeypatch.delenv("IS_QUALITY_GATE_ENABLED", raising=False)

    result = asyncio.run(
        quality_gate(
            QualityGateInput(
                pipeline="IS",
                step_name="persist_session",
                contract={"step_name": "persist_session", "pipeline": "IS"},
                node_report={"node_status": {"status": "success"}},
            )
        )
    )
    assert result["verdict"] == "ok"
    assert result["analysis"] == "quality gate disabled"

