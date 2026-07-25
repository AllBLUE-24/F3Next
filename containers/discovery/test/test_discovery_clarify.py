"""Tests for pre-plan clarifying questions."""

from __future__ import annotations

from pathlib import Path

from containers.discovery.discovery_clarify import (
    append_clarifications_to_transcript,
    build_clarifying_questions,
    needs_clarification,
)

FIXTURES = Path(__file__).parent / "fixtures"
YIELD_TRANSCRIPT = (FIXTURES / "cleaning_chemicals_yield.txt").read_text(encoding="utf-8")


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


def test_niche_playbook_questions_for_chemical():
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
    assert any("Part A" in q.prompt or "batch" in q.prompt.lower() for q in questions)


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
    questions = build_clarifying_questions(YIELD_TRANSCRIPT)
    answers = {q.id: "yes" if q.question_type == "yes_no" else q.options[0]["value"] for q in questions}
    assert not needs_clarification(YIELD_TRANSCRIPT, clarification_answers=answers)


def test_append_clarifications_to_transcript():
    out = append_clarifications_to_transcript(
        "We mix chemicals.",
        {"routing_depth": "yes", "trace_direction": ["upstream", "downstream"]},
    )
    assert "CLARIFICATION ANSWERS" in out
    assert "routing_depth: yes" in out
    assert "upstream, downstream" in out


def test_max_three_questions():
    transcript = (
        "We manufacture cleaning chemicals in batches with yield variance. "
        "We need traceability for recalls and expiry rotation."
    )
    questions = build_clarifying_questions(transcript)
    assert len(questions) <= 3
