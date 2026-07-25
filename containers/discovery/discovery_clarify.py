"""
Discovery Step 1 — pre-plan clarifying questions.

Detects ambiguities in the transcript before MVP planning so the system
does not guess MTS/MTO, trace direction, or routing depth silently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from containers.discovery.discovery_org_assumptions import open_org_assumptions
from containers.discovery.workflow_closure import detect_workflow_signals

OTHER_VALUE = "other"
OTHER_LABEL = "Something else — I'll describe below"

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
    r"dispatch",
    r"technician",
    r"distribut",
    r"van ",
    r"route",
    r"expiry",
    r"warehouse",
    r"service",
    r"amc",
    r"warranty",
)

_ORG_QUESTIONS: tuple[tuple[str, str, list[str]], ...] = (
    (
        "org_locations",
        "How many operating sites hold inventory or run production?",
        [
            "Single site or one factory",
            "2–5 branches, godowns, or warehouses",
            "More than 5 locations",
        ],
    ),
    (
        "org_fiscal_year",
        "When does your financial year start?",
        [
            "April–March (common in India)",
            "January–December",
            "Other month — I'll specify",
        ],
    ),
    (
        "org_opening_balance",
        "Do you have a planned go-live / cutover date for opening stock and balances?",
        [
            "Yes — we have a target cutover date",
            "Not yet — still deciding",
            "We will run parallel for a while first",
        ],
    ),
    (
        "org_multi_company",
        "Is this a single legal entity, or multiple companies / currencies?",
        [
            "Single company, one currency",
            "Single company with export / foreign currency",
            "Multiple companies or subsidiaries",
        ],
    ),
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
    if any(k in q for k in ("technician", "dispatch", "amc", "warranty", "visit")):
        return _has_any(text, (r"technician", r"dispatch", r"service", r"repair", r"amc", r"field"))
    if any(k in q for k in ("distribut", "van", "route", "expiry", "godown", "beat")):
        return _has_any(text, (r"distribut", r"van", r"route", r"expiry", r"wholesale", r"fmcg"))
    return _has_any(text, _F3ICHE_RELEVANCE)


def _slug_option(label: str, idx: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:48]
    return slug or f"opt_{idx}"


def _options_from_labels(labels: list[str]) -> list[dict[str, str]]:
    opts: list[dict[str, str]] = []
    seen: set[str] = set()
    for idx, label in enumerate(labels):
        value = _slug_option(label, idx)
        while value in seen:
            value = f"{value}_{idx}"
        seen.add(value)
        opts.append({"value": value, "label": label})
    if not any(o["value"] == OTHER_VALUE for o in opts):
        opts.append({"value": OTHER_VALUE, "label": OTHER_LABEL})
    return opts


def _finalize_options(options: list[dict[str, str]]) -> list[dict[str, str]]:
    """Ensure domain options exist and 'other' is always last."""
    without_other = [o for o in options if o.get("value") != OTHER_VALUE]
    return _options_from_labels([o["label"] for o in without_other]) if without_other else [
        {"value": OTHER_VALUE, "label": OTHER_LABEL},
    ]


def _niche_clarifying_questions(
    niche_id: str | None,
    transcript: str,
    clarification_answers: dict[str, Any] | None,
) -> list["ClarifyingQuestion"]:
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
        raw_labels = entry.get("options") or []
        if not raw_labels:
            continue
        options = _options_from_labels([str(x) for x in raw_labels])
        out.append(
            ClarifyingQuestion(
                id=qid,
                prompt=prompt,
                question_type="single_choice_with_other",
                options=options,
            )
        )
    return out


def _org_clarifying_questions(
    transcript: str,
    clarification_answers: dict[str, Any] | None,
    open_ids: set[str],
) -> list["ClarifyingQuestion"]:
    org_key_by_qid = {
        "org_locations": "locations",
        "org_fiscal_year": "fiscal_year",
        "org_opening_balance": "opening_balance",
        "org_multi_company": "multi_company",
    }
    out: list[ClarifyingQuestion] = []
    for qid, prompt, labels in _ORG_QUESTIONS:
        if org_key_by_qid.get(qid) not in open_ids:
            continue
        if _answered(clarification_answers, qid):
            continue
        out.append(
            ClarifyingQuestion(
                id=qid,
                prompt=prompt,
                question_type="single_choice_with_other",
                options=_options_from_labels(labels),
            )
        )
    return out


QuestionType = Literal[
    "single_choice",
    "single_choice_with_other",
    "multi_choice",
    "multi_choice_with_other",
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
            "allows_other": True,
        }

    def label_for_value(self, value: str) -> str:
        for opt in self.options:
            if opt["value"] == value:
                return opt["label"]
        return value


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
        s = val.strip()
        if not s:
            return False
        if s == OTHER_VALUE:
            return False
        if s.startswith(f"{OTHER_VALUE}:"):
            return bool(s[len(OTHER_VALUE) + 1 :].strip())
        return True
    if isinstance(val, list):
        if not val:
            return False
        for item in val:
            s = str(item).strip()
            if s == OTHER_VALUE:
                return False
            if s.startswith(f"{OTHER_VALUE}:") and not s[len(OTHER_VALUE) + 1 :].strip():
                return False
        return True
    return True


def _with_other_options(options: list[dict[str, str]]) -> list[dict[str, str]]:
    return _finalize_options(options)


def _collect_clarifying_questions(
    transcript: str,
    *,
    coverage: dict[str, Any] | None = None,
    clarification_answers: dict[str, Any] | None = None,
    niche_id: str | None = None,
    limit: int | None = 3,
) -> list[ClarifyingQuestion]:
    """
    Return unanswered clarifying questions for this transcript (max 3).

    Niche-specific F3iche playbook questions take priority; generic manufacturing
    ambiguities and org-structure gaps fill remaining slots.
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
                question_type="single_choice_with_other",
                options=_with_other_options([
                    {"value": "mts", "label": "Make-to-stock — we produce to inventory, then sell from stock"},
                    {"value": "mto", "label": "Make-to-order — we produce after a customer order is confirmed"},
                    {"value": "both", "label": "Both — some SKUs are stocked, others are made to order"},
                ]),
            )
        )
        seen_ids.add("manufacturing_strategy")

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
                question_type="multi_choice_with_other",
                options=_with_other_options([
                    {"value": "upstream", "label": "Which raw material / supplier batch went into the product"},
                    {"value": "downstream", "label": "Which customers received the same finished batch"},
                    {"value": "expiry", "label": "Expiry / shelf-life rotation (FEFO)"},
                ]),
            )
        )
        seen_ids.add("trace_direction")

    if len(questions) < 3 and "routing_depth" not in seen_ids and signals & {"yield_routing", "material_consumption", "wip_visibility"} and not _has_any(
        text,
        (r"machine time", r"each step", r"each stage", r"workstation", r"routing"),
    ):
        questions.append(
            ClarifyingQuestion(
                id="routing_depth",
                prompt="Do you need time and material consumption recorded at each production step (vat, cure, bottle)?",
                question_type="single_choice_with_other",
                options=_with_other_options([
                    {"value": "yes", "label": "Yes — per-step yield and machine time"},
                    {"value": "no", "label": "No — only total batch input/output is enough"},
                ]),
            )
        )
        seen_ids.add("routing_depth")

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
                question_type="single_choice_with_other",
                options=_with_other_options([
                    {"value": "costing_only", "label": "Mainly costing / yield visibility — no QC holds for now"},
                    {"value": "incoming_qc", "label": "Incoming raw material QC before use"},
                    {"value": "stage_qc", "label": "QC gates during production (mix, cure, bottle)"},
                ]),
            )
        )

    open_org = open_org_assumptions(transcript)
    open_org_ids = {item["id"] for item in open_org}
    for org_q in _org_clarifying_questions(transcript, clarification_answers, open_org_ids):
        if len(questions) >= 3:
            break
        if org_q.id not in seen_ids:
            questions.append(org_q)
            seen_ids.add(org_q.id)

    unanswered = [
        q for q in (questions[:limit] if limit is not None else questions)
        if not _answered(clarification_answers, q.id)
    ]
    return unanswered


def build_clarifying_questions(
    transcript: str,
    *,
    coverage: dict[str, Any] | None = None,
    clarification_answers: dict[str, Any] | None = None,
    niche_id: str | None = None,
) -> list[ClarifyingQuestion]:
    return _collect_clarifying_questions(
        transcript,
        coverage=coverage,
        clarification_answers=clarification_answers,
        niche_id=niche_id,
        limit=3,
    )


def clarifying_question_catalog(
    transcript: str,
    *,
    coverage: dict[str, Any] | None = None,
    niche_id: str | None = None,
) -> dict[str, ClarifyingQuestion]:
    """All possible questions (for answer label lookup after submit)."""
    catalog: dict[str, ClarifyingQuestion] = {}

    if niche_id:
        from containers.discovery.target.f3iche_seeds import load_f3iche_playbook

        playbook = load_f3iche_playbook(niche_id)
        for entry in playbook.get("questions") or []:
            raw_labels = entry.get("options") or []
            if not raw_labels:
                continue
            catalog[entry["id"]] = ClarifyingQuestion(
                id=entry["id"],
                prompt=entry["question"],
                question_type="single_choice_with_other",
                options=_options_from_labels([str(x) for x in raw_labels]),
            )

    open_org_ids = {item["id"] for item in open_org_assumptions(transcript)}
    for org_q in _org_clarifying_questions(transcript, {}, open_org_ids):
        catalog[org_q.id] = org_q

    for q in _collect_clarifying_questions(
        transcript,
        coverage=coverage,
        clarification_answers={},
        niche_id=niche_id,
        limit=None,
    ):
        catalog[q.id] = q

    return catalog


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


def format_clarification_answer(question: ClarifyingQuestion, answer: Any) -> str:
    """Human-readable answer for transcript append and explainer context."""
    label_by_value = {o["value"]: o["label"] for o in question.options}

    def _one(raw: str) -> str:
        if raw.startswith(f"{OTHER_VALUE}:"):
            detail = raw[len(OTHER_VALUE) + 1 :].strip()
            return detail or "Other (not specified)"
        return label_by_value.get(raw, raw)

    if isinstance(answer, list):
        return ", ".join(_one(str(v)) for v in answer if str(v).strip())
    return _one(str(answer))


def append_clarifications_to_transcript(
    transcript: str,
    clarification_answers: dict[str, Any],
    *,
    niche_id: str | None = None,
    coverage: dict[str, Any] | None = None,
) -> str:
    """Append structured clarification answers for planner context."""
    if not clarification_answers:
        return transcript
    question_index = clarifying_question_catalog(
        transcript,
        coverage=coverage,
        niche_id=niche_id,
    )
    lines = [transcript.strip(), "", "CLARIFICATION ANSWERS (user confirmed):"]
    for qid, answer in clarification_answers.items():
        q = question_index.get(qid)
        if q:
            val = format_clarification_answer(q, answer)
        elif isinstance(answer, list):
            val = ", ".join(str(a) for a in answer)
        else:
            val = str(answer)
        lines.append(f"- {qid}: {val}")
    return "\n".join(lines)


__all__ = [
    "OTHER_VALUE",
    "OTHER_LABEL",
    "ClarifyingQuestion",
    "append_clarifications_to_transcript",
    "build_clarifying_questions",
    "clarifying_question_catalog",
    "format_clarification_answer",
    "needs_clarification",
]
