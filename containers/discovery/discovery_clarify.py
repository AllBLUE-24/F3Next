"""
Discovery Step 1 — pre-plan clarifying questions.

Detects ambiguities in the transcript before MVP planning so the system
does not guess MTS/MTO, trace direction, or routing depth silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from containers.discovery.workflow_closure import detect_workflow_signals

_F3ICHE_RELEVANCE = (
    r"part a",
    r"part b",
    r"hardener",
    r"project site",
    r"installation",
    r"formulat",
    r"batch",
    r"recall",
    r"shelf life",
    r"resin",
    r"adhesive",
    r"yield",
    r"wip",
    r"work order",
    r"factory",
    r"\bmix",
)


def _f3iche_question_relevant(question: str, transcript: str) -> bool:
    """Skip niche questions clearly unrelated to this transcript."""
    text = _text(transcript)
    q = question.lower()
    if "part a" in q or "part b" in q:
        return _has_any(text, (r"part a", r"part b", r"hardener", r"two[\s-]?part", r"resin"))
    if "project site" in q or "field crew" in q:
        return _has_any(text, (r"project", r"site", r"installation", r"field"))
    if "viscosity" in q or "recipe" in q:
        return _has_any(text, (r"formulat", r"recipe", r"batch", r"mix", r"viscosity"))
    return _has_any(text, _F3ICHE_RELEVANCE)


def _niche_clarifying_questions(
    niche_id: str | None,
    transcript: str,
    clarification_answers: dict[str, Any] | None,
) -> list[ClarifyingQuestion]:
    if not niche_id:
        return []
    from containers.discovery.target.f3iche_seeds import load_f3iche_playbook

    playbook = load_f3iche_playbook(niche_id)
    out: list[ClarifyingQuestion] = []
    for entry in playbook.get("questions") or []:
        qid = entry["id"]
        if _answered(clarification_answers, qid):
            continue
        prompt = entry["question"]
        if not _f3iche_question_relevant(prompt, transcript):
            continue
        out.append(
            ClarifyingQuestion(
                id=qid,
                prompt=prompt,
                question_type="single_choice",
                options=[
                    {"value": "pain", "label": "Yes — this is a problem we need ERP to solve"},
                    {"value": "handled", "label": "No — we handle this adequately today"},
                    {"value": "partial", "label": "Partially / sometimes an issue"},
                ],
                why=entry.get("purpose") or "Niche-specific discovery question from implementation playbook.",
            )
        )
    return out

QuestionType = Literal[
    "single_choice",
    "multi_choice",
    "yes_no",
]


@dataclass
class ClarifyingQuestion:
    id: str
    prompt: str
    question_type: QuestionType
    options: list[dict[str, str]] = field(default_factory=list)
    why: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "question_type": self.question_type,
            "options": self.options,
            "why": self.why,
        }


def _text(transcript: str) -> str:
    return (transcript or "").lower()


def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def _answered(clarification_answers: dict[str, Any] | None, qid: str) -> bool:
    if not clarification_answers:
        return False
    val = clarification_answers.get(qid)
    if val is None:
        return False
    if isinstance(val, str):
        return bool(val.strip())
    if isinstance(val, list):
        return len(val) > 0
    return True


def build_clarifying_questions(
    transcript: str,
    *,
    coverage: dict[str, Any] | None = None,
    clarification_answers: dict[str, Any] | None = None,
    niche_id: str | None = None,
) -> list[ClarifyingQuestion]:
    """
    Return unanswered clarifying questions for this transcript (max 3).

    Niche-specific F3iche playbook questions take priority; generic manufacturing
    ambiguities fill remaining slots.
    """
    text = _text(transcript)
    signals = detect_workflow_signals(transcript)
    questions: list[ClarifyingQuestion] = list(
        _niche_clarifying_questions(niche_id, transcript, clarification_answers)
    )
    seen_ids = {q.id for q in questions}

    # Manufacturing strategy: make-to-stock vs make-to-order
    if len(questions) < 3 and "manufacturing_strategy" not in seen_ids and _has_any(
        text,
        (r"\bmanufactur", r"factory", r"production batch", r"\bmix", r"batch ticket"),
    ) and not _has_any(
        text,
        (
            r"make[\s-]?to[\s-]?stock",
            r"make[\s-]?to[\s-]?order",
            r"against order",
            r"from stock",
            r"order[\s-]?driven",
        ),
    ):
        questions.append(
            ClarifyingQuestion(
                id="manufacturing_strategy",
                prompt="How does production get triggered today?",
                question_type="single_choice",
                options=[
                    {"value": "mts", "label": "Make-to-stock — we produce to inventory, then sell from stock"},
                    {"value": "mto", "label": "Make-to-order — we produce after a customer order is confirmed"},
                    {"value": "both", "label": "Both — some SKUs are stocked, others are made to order"},
                ],
                why="This decides whether Sales Order is Day-1 or deferred without hurting traceability.",
            )
        )
        seen_ids.add("manufacturing_strategy")

    # Trace direction: upstream raw vs downstream customer recall
    if len(questions) < 3 and "trace_direction" not in seen_ids and _has_any(
        text,
        (
            r"trace",
            r"batch",
            r"recall",
            r"defect",
            r"compliance",
            r"expiry",
            r"shelf life",
        ),
    ) and not _has_any(
        text,
        (
            r"which other customers",
            r"raw material batch",
            r"upstream",
            r"downstream",
            r"both.*customer.*raw",
        ),
    ):
        questions.append(
            ClarifyingQuestion(
                id="trace_direction",
                prompt="When something goes wrong with a batch, what must you trace?",
                question_type="multi_choice",
                options=[
                    {"value": "upstream", "label": "Which raw material / supplier batch went into the product"},
                    {"value": "downstream", "label": "Which customers received the same finished batch"},
                    {"value": "expiry", "label": "Expiry / shelf-life rotation (FEFO)"},
                ],
                why="Sets whether Purchase Receipt, Stock Entry, Customer, and Delivery Note are all Day-1.",
            )
        )
        seen_ids.add("trace_direction")

    # Routing / yield depth
    if len(questions) < 3 and "routing_depth" not in seen_ids and signals & {"yield_routing", "material_consumption", "wip_visibility"} and not _has_any(
        text,
        (r"machine time", r"each step", r"each stage", r"workstation", r"routing"),
    ):
        questions.append(
            ClarifyingQuestion(
                id="routing_depth",
                prompt="Do you need time and material consumption recorded at each production step (vat, cure, bottle)?",
                question_type="yes_no",
                options=[
                    {"value": "yes", "label": "Yes — per-step yield and machine time"},
                    {"value": "no", "label": "No — only total batch input/output is enough"},
                ],
                why="Per-step tracking requires Job Card + Stock Entry, not just Work Order shells.",
            )
        )
        seen_ids.add("routing_depth")

    # Quality gates vs costing-only
    if len(questions) < 3 and "quality_gates" not in seen_ids and _has_any(text, (r"chemic", r"formulat", r"mix", r"batch")) and not _has_any(
        text,
        (
            r"quality inspection",
            r"\biso\b",
            r"incoming qc",
            r"quality gate",
            r"certificate of analysis",
            r"\bcoa\b",
            r"quality control",
        ),
    ) and signals & {"yield_routing", "wip_visibility", "material_consumption"}:
        questions.append(
            ClarifyingQuestion(
                id="quality_gates",
                prompt="Do you need formal quality inspections (hold/release) at any stage, or is this mainly a costing/yield problem?",
                question_type="single_choice",
                options=[
                    {"value": "costing_only", "label": "Mainly costing / yield visibility — no QC holds for now"},
                    {"value": "incoming_qc", "label": "Incoming raw material QC before use"},
                    {"value": "stage_qc", "label": "QC gates during production (mix, cure, bottle)"},
                ],
                why="Avoids pushing Quality Inspection into Day-1 when the pain is shop-floor costing.",
            )
        )

    unanswered = [
        q for q in questions[:3]
        if not _answered(clarification_answers, q.id)
    ]
    return unanswered


def needs_clarification(
    transcript: str,
    *,
    coverage: dict[str, Any] | None = None,
    clarification_answers: dict[str, Any] | None = None,
    niche_id: str | None = None,
) -> bool:
    return bool(
        build_clarifying_questions(
            transcript,
            coverage=coverage,
            clarification_answers=clarification_answers,
            niche_id=niche_id,
        )
    )


def append_clarifications_to_transcript(
    transcript: str,
    clarification_answers: dict[str, Any],
) -> str:
    """Append structured clarification answers for planner context."""
    if not clarification_answers:
        return transcript
    lines = [transcript.strip(), "", "CLARIFICATION ANSWERS (user confirmed):"]
    for qid, answer in clarification_answers.items():
        if isinstance(answer, list):
            val = ", ".join(str(a) for a in answer)
        else:
            val = str(answer)
        lines.append(f"- {qid}: {val}")
    return "\n".join(lines)


__all__ = [
    "ClarifyingQuestion",
    "append_clarifications_to_transcript",
    "build_clarifying_questions",
    "needs_clarification",
]
