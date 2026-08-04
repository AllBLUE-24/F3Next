"""Tests for notification reply → OS seed_context wiring."""

from shared.models.command import CommandRequest, CommandWorkflowInput


def test_command_request_accepts_seed_context():
    req = CommandRequest(
        prompt="Approve and increase qty to 200kg",
        project_id="00000000-0000-0000-0000-000000000001",
        company_id="green-surface",
        user_id="user-1",
        seed_context={"doctype": "Sales Order", "doc_name": "SO-001", "trigger_event": "on_submit"},
        origin_notification_id="notif-abc",
    )
    assert req.seed_context["doc_name"] == "SO-001"
    assert req.origin_notification_id == "notif-abc"


def test_workflow_input_carries_seed_context():
    inp = CommandWorkflowInput(
        prompt="test",
        project_id="pid",
        company_id="slug",
        user_id="u1",
        erp_type="erpnext",
        session_id="sess-1",
        session_context=[],
        seed_context={"doctype": "Purchase Order", "doc_name": "PO-9"},
    )
    assert inp.seed_context["doctype"] == "Purchase Order"
