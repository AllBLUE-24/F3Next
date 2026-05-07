from __future__ import annotations

import re
from typing import Any, Optional

from containers.os.clarity_agent.kb_loader import kb


def guess_intent_meta(prompt: str) -> tuple[Optional[str], Optional[str]]:
    """
    Best-effort guess for (intent_id, target_doctype) using KB-01 intents/synonyms.
    This is used only to shape tool enums / hints — not as a source of truth.
    """
    text = (prompt or "").strip()
    if not text:
        return None, None

    _kb = kb()

    # Abbreviation expansion (SO/PO/etc) — apply to the raw text for better synonym hits.
    def _expand_abbrs(s: str) -> str:
        out = s
        for abbr, full in _kb.abbreviations().items():
            out = re.sub(rf"\b{re.escape(abbr)}\b", full, out, flags=re.IGNORECASE)
        return out

    expanded = _expand_abbrs(text)

    # Direct synonym hit (fast path)
    # Try longer phrases first (e.g. "sales order" before "order")
    candidates = sorted(_kb.abbreviations().values(), key=len, reverse=True)
    for phrase in candidates:
        if phrase and phrase.lower() in expanded.lower():
            # This is a doctype name, not an intent id — still useful as a hint.
            return None, phrase

    # Intent synonym hit
    # Scan the KB synonym index via get_intent_by_synonym on common ngrams.
    words = re.findall(r"[A-Za-z0-9]+", expanded.lower())
    for n in (4, 3, 2, 1):
        for i in range(0, max(0, len(words) - n + 1)):
            frag = " ".join(words[i : i + n])
            hit = _kb.get_intent_by_synonym(frag)
            if hit:
                return hit.get("intent_id"), hit.get("target_doctype")

    return None, None


def build_allowed_entity_types(target_doctype_hint: Optional[str]) -> list[str]:
    """
    Build the allowed `entity_type` enum for the CVS search tool.

    NOTE: This does NOT guarantee CVS contains these entity lists; it only
    constrains LLM tool calls to a sane set of master types.
    """
    base = {"Item", "Customer", "Supplier", "Warehouse", "Cost Center"}

    if not target_doctype_hint:
        return sorted(base)

    _kb = kb()
    fm = _kb.field_mappings_for(target_doctype_hint) or {}
    mappings = fm.get("field_mappings") or {}
    for _field, spec in mappings.items():
        if isinstance(spec, dict) and spec.get("fieldtype") == "Link":
            opt = spec.get("options")
            if isinstance(opt, str) and opt.strip():
                base.add(opt.strip())

    return sorted(base)


def normalise_intent_dict(result: dict, *, prompt: str, erp_type: str, session_context: list) -> dict:
    """
    Make Clarity output shape consistent (esp. ambiguities).
    This keeps downstream workflow gates deterministic.
    """
    if not isinstance(result, dict):
        result = {}

    result.setdefault("erp_type", erp_type)
    result.setdefault("raw_prompt", prompt)
    result.setdefault("session_context", session_context)

    # Ambiguities MUST be a list[dict] (workflow relies on dict shape).
    ambiguities = result.get("ambiguities")
    if not isinstance(ambiguities, list):
        ambiguities = []
    norm_amb: list[dict[str, Any]] = []
    for a in ambiguities:
        if isinstance(a, dict):
            q = a.get("question")
            if isinstance(q, str) and q.strip():
                norm_amb.append(
                    {
                        "field": str(a.get("field") or "unknown"),
                        "question": q.strip(),
                        "required": bool(a.get("required", True)),
                    }
                )
        elif isinstance(a, str) and a.strip():
            # Legacy format (List[str]) — convert to dict
            norm_amb.append({"field": "unknown", "question": a.strip(), "required": True})
    result["ambiguities"] = norm_amb
    result["has_ambiguities"] = bool(norm_amb)

    # Entities defaults (keep permissive; allow extra keys)
    ent = result.setdefault("entities", {})
    if not isinstance(ent, dict):
        ent = {}
        result["entities"] = ent

    ent.setdefault("items", [])
    if not isinstance(ent.get("items"), list):
        ent["items"] = []

    ent.setdefault("extra", {})
    if not isinstance(ent.get("extra"), dict):
        ent["extra"] = {}

    return result

