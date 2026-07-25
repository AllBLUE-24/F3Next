"""Tests for user-facing discovery UI copy."""

from __future__ import annotations

from containers.discovery.discovery_assurance import AssuranceResult, compute_assurance
from containers.discovery.discovery_ui import (
    build_workflow_preview_ui_payload,
    humanize_assurance,
    humanize_promotion_labels,
)


def test_humanize_assurance_hides_internal_jargon():
    result = AssuranceResult(
        level="yellow",
        reasons=[
            "Weak archetype signal match — plan based on general manufacturing patterns.",
            "Day-1 plan used deterministic offline fallback — LLM reasoning did not run.",
        ],
    )
    ui = humanize_assurance(result)
    assert ui["requires_acknowledgment"] is True
    joined = " ".join(ui["reasons"]).lower()
    assert "archetype" not in joined
    assert "offline fallback" not in joined
    assert "llm" not in joined


def test_humanize_promotion_labels():
    labels = humanize_promotion_labels(
        ["Batch", "Customer"],
        {
            "Batch": "Promoted for expiry FEFO trace",
            "Customer": "Validator promoted for downstream trace",
        },
    )
    assert "traceability" in labels["Batch"].lower() or "trace" in labels["Batch"].lower()
    assert "dispatch" in labels["Customer"].lower() or "trace" in labels["Customer"].lower()


def test_workflow_preview_ui_payload_omits_internal_fields():
    payload = build_workflow_preview_ui_payload(
        metadata={
            "closure_test": "After Day-1 we can trace batches.",
            "plan_reasoning": "INTERNAL ONLY",
            "promotion_reasons": {"Batch": "trace batch recall"},
            "assurance": {
                "level": "green",
                "reasons": ["Structural closure passed with strong signal match and explicit closure test."],
            },
            "validator_warnings": [],
        },
        workflow_explanation={"workflow_summary": "Summary", "expected_data": []},
        seed_doctypes=["Item", "Batch"],
        promoted_doctypes=["Batch"],
    )
    assert "plan_reasoning" not in payload
    assert "promotion_reasons" not in payload
    assert payload["promotion_labels"]["Batch"]
    assert payload["assurance"]["reasons"]
