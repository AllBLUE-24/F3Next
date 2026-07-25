"""Tests for pre-plan clarifying questions."""

from __future__ import annotations

from pathlib import Path

from containers.discovery.discovery_clarify import (
    OTHER_LABEL,
    OTHER_VALUE,
    append_clarifications_to_transcript,
    build_clarifying_questions,
    format_clarification_answer,
    needs_clarification,
)

FIXTURES = Path(__file__).parent / "fixtures"
YIELD_TRANSCRIPT = (FIXTURES / "cleaning_chemicals_yield.txt").read_text(encoding="utf-8")


def _first_domain_option(questions):
    for q in questions:
        for opt in q.options:
            if opt["value"] != OTHER_VALUE:
                return opt["value"]
    return "yes"


def test_yield_story_asks_strategy_and_quality_not_routing():
    """Fixture already mentions per-step routing — niche + generic ambiguities remain."""
    questions = build_clarifying_questions(
        YIELD_TRANSCRIPT,
        niche_id="manufacturing_project_chemical",
    )
    ids = {q.id for q in questions}
    assert "manufacturing_strategy" in ids or any(i.startswith("f3iche_q_") for i in ids)
    assert "quality_gates" in ids or any(i.startswith("f3iche_q_") for i in ids)
    assert "routing_depth" not in ids


def test_niche_playbook_questions_use_domain_options_not_generic_pain():
    transcript = (
        "Apex Resins manufactures Part A and Part B adhesives for project site installation. "
        "Batch traceability in Excel."
    )
    questions = build_clarifying_questions(
        transcript,
        niche_id="manufacturing_project_chemical",
    )
    ids = {q.id for q in questions}
    assert any(i.startswith("f3iche_q_") for i in ids)
    f3iche_q = next(q for q in questions if q.id.startswith("f3iche_q_"))
    labels = {o["label"] for o in f3iche_q.options}
    assert OTHER_LABEL in labels
    assert not any("problem we need ERP" in label for label in labels)
    assert any("Part A" in label or "kit" in label.lower() or "warehouse" in label.lower() for label in labels)


def test_all_clarify_questions_include_other_option():
    transcript = "We manufacture adhesives in batches and sell to distributors."
    questions = build_clarifying_questions(transcript)
    for q in questions:
        assert any(o["value"] == OTHER_VALUE for o in q.options)
        assert q.to_dict().get("allows_other") is True
        assert "why" not in q.to_dict()


def test_manufacturing_without_strategy_asks_mts_mto():
    transcript = "We manufacture adhesives in batches and sell to distributors."
    questions = build_clarifying_questions(transcript)
    assert any(q.id == "manufacturing_strategy" for q in questions)


def test_answered_questions_are_filtered():
    questions = build_clarifying_questions(
        YIELD_TRANSCRIPT,
        clarification_answers={"routing_depth": "yes"},
    )
    assert all(q.id != "routing_depth" for q in questions)


def test_needs_clarification_false_when_all_answered():
    answers: dict = {}
    while True:
        questions = build_clarifying_questions(YIELD_TRANSCRIPT, clarification_answers=answers)
        if not questions:
            break
        for q in questions:
            if q.question_type == "multi_choice_with_other":
                answers[q.id] = [_first_domain_option([q])]
            else:
                answers[q.id] = _first_domain_option([q])
    assert not needs_clarification(YIELD_TRANSCRIPT, clarification_answers=answers)


def test_append_clarifications_uses_human_labels():
    questions = build_clarifying_questions(
        "We manufacture Part A and Part B adhesives for project site installation.",
        niche_id="manufacturing_project_chemical",
    )
    q = next(q for q in questions if q.id.startswith("f3iche_q_"))
    first_val = _first_domain_option([q])
    out = append_clarifications_to_transcript(
        "We mix chemicals.",
        {q.id: first_val},
        niche_id="manufacturing_project_chemical",
    )
    assert "CLARIFICATION ANSWERS" in out
    assert format_clarification_answer(q, first_val) in out


def test_format_other_answer():
    questions = build_clarifying_questions(
        "We manufacture adhesives in batches and sell to distributors.",
    )
    q = questions[0]
    text = format_clarification_answer(q, f"{OTHER_VALUE}:We run hybrid MTS for export only")
    assert "export" in text
    assert OTHER_VALUE not in text


def test_org_questions_when_structure_unstated():
    transcript = "We manufacture adhesives and track batches in Excel."
    questions = build_clarifying_questions(transcript, niche_id="manufacturing_project_chemical")
    ids = {q.id for q in questions}
    assert any(i.startswith("org_") for i in ids) or len(questions) == 3


def test_max_three_questions():
    transcript = (
        "We manufacture cleaning chemicals in batches with yield variance. "
        "We need traceability for recalls and expiry rotation."
    )
    questions = build_clarifying_questions(transcript)
    assert len(questions) <= 3
