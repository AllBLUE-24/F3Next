"""readiness_ui payload tests."""
from __future__ import annotations

from containers.implementation.readiness.readiness_ui import build_readiness_ui_payload


def test_ui_payload_hides_internal_jargon():
    report = {
        "executive_summary": "Step 8c dry_run blocked",
        "minimum_viable_possible": False,
        "import_readiness_score": 0.4,
        "ready_doctypes": [],
        "missing_doctypes": [{"doctype": "Stock Entry"}],
        "gap_report": {"gap_items": []},
    }
    ui = build_readiness_ui_payload(report)
    assert "8c" not in ui["executive_summary"].lower()
    assert ui["readiness_level"] == "red"
    assert ui["requires_acknowledgment"] is False


def test_ui_matrix_from_gap_report():
    report = {
        "minimum_viable_possible": True,
        "import_readiness_score": 0.8,
        "user_action_required": True,
        "gap_report": {
            "matrix": {
                "rows": [{
                    "filename": "a.csv",
                    "doctype": "Item",
                    "status": "ready",
                    "required_fields": ["item_code"],
                    "present_fields": ["item_code"],
                    "missing_fields": [],
                }],
            },
            "gap_items": [],
        },
    }
    ui = build_readiness_ui_payload(report)
    assert len(ui["matrix"]["rows"]) == 1
    assert ui["readiness_level"] == "yellow"
