"""Gate contract serialization."""

from shared.gate_contracts import (
    GapItem,
    GateResult,
    HonestySlice,
    gap_to_clarification_question,
    gate_result_needs_human,
    gate_result_ok,
)


def test_gap_round_trip() -> None:
    gap = GapItem(
        field="customer",
        question="Which customer?",
        severity="choice",
        candidates=["A", "B"],
        rule_id="ler_test",
    )
    restored = GapItem.from_dict(gap.to_dict())
    assert restored.field == "customer"
    assert restored.candidates == ["A", "B"]


def test_gate_result_round_trip() -> None:
    gr = gate_result_needs_human(
        "resolve",
        [
            GapItem(field="customer", question="Pick one", candidates=["X"]),
        ],
        resolved={"customer": None},
        meta={"brain_version": "1.0.0"},
    )
    data = gr.to_dict()
    back = GateResult.from_dict(data)
    assert back.gate == "resolve"
    assert back.status == "needs_human"
    assert len(back.gaps) == 1
    assert back.meta["brain_version"] == "1.0.0"


def test_gap_to_clarification_question_with_candidates() -> None:
    gap = GapItem(field="supplier", question="", candidates=["S1", "S2"])
    q = gap_to_clarification_question(gap)
    assert "S1" in q
    assert "supplier" in q.casefold() or "Which" in q


def test_gate_result_ok() -> None:
    gr = gate_result_ok("complete", resolved={"items": 1})
    assert gr.status == "ok"
    assert gr.honesty.valid is True
    hs = HonestySlice(valid=False, errors=["e1"])
    assert hs.to_dict()["errors"] == ["e1"]
