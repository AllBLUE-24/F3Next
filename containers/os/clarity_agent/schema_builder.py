from __future__ import annotations

import copy
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


def _empty_scalar(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    return False


def fill_intent_gaps_from_partial(resolved: dict, partial: dict) -> dict:
    """
    After resolve_ambiguity, restore fields the LLM dropped while merging Q&A.
    Without this, an incomplete JSON response can clear intent_id / doctype / items
    and break planning (intent=unknown, empty ERP POST).
    """
    if not isinstance(resolved, dict):
        resolved = {}
    out = copy.deepcopy(resolved)
    if not isinstance(partial, dict):
        return out

    _kb = kb()
    valid_intents = set(_kb.intent_ids())

    def _valid_intent_id(v: Any) -> bool:
        return isinstance(v, str) and v in valid_intents

    # If resolve_ambiguity invented or cleared intent_id, restore the last
    # known-good value from the partial intent and align target_doctype.
    cur_intent_id = out.get("intent_id")
    partial_intent_id = partial.get("intent_id")
    if not _valid_intent_id(cur_intent_id) and _valid_intent_id(partial_intent_id):
        out["intent_id"] = copy.deepcopy(partial_intent_id)
        cur_intent_id = out["intent_id"]

    intent_def = _kb.get_intent(cur_intent_id) if _valid_intent_id(cur_intent_id) else None
    kb_doctype = (intent_def or {}).get("target_doctype") or None
    if kb_doctype:
        out["target_doctype"] = kb_doctype
    elif _empty_scalar(out.get("target_doctype")) and not _empty_scalar(partial.get("target_doctype")):
        out["target_doctype"] = copy.deepcopy(partial.get("target_doctype"))

    # Action still falls back to the partial intent when missing.
    for key in ("action",):
        if _empty_scalar(out.get(key)):
            pv = partial.get(key)
            if not _empty_scalar(pv):
                out[key] = copy.deepcopy(pv)

    p_ent = partial.get("entities") if isinstance(partial.get("entities"), dict) else {}
    r_ent = out.get("entities") if isinstance(out.get("entities"), dict) else {}
    merged: dict[str, Any] = copy.deepcopy(p_ent)
    for k, v in r_ent.items():
        if k in ("items", "extra"):
            continue
        merged[k] = copy.deepcopy(v)

    r_items = r_ent.get("items") if isinstance(r_ent.get("items"), list) else []
    p_items = p_ent.get("items") if isinstance(p_ent.get("items"), list) else []
    merged["items"] = copy.deepcopy(r_items) if len(r_items) > 0 else copy.deepcopy(p_items)

    for party in ("customer", "supplier"):
        if _empty_scalar(merged.get(party)) and not _empty_scalar(p_ent.get(party)):
            merged[party] = copy.deepcopy(p_ent[party])

    p_ex = p_ent.get("extra") if isinstance(p_ent.get("extra"), dict) else {}
    r_ex = r_ent.get("extra") if isinstance(r_ent.get("extra"), dict) else {}
    merged["extra"] = {**copy.deepcopy(p_ex), **copy.deepcopy(r_ex)}

    out["entities"] = merged

    try:
        cnum = float(out.get("confidence", 0) or 0)
    except (TypeError, ValueError):
        cnum = 0.0
    if cnum <= 0:
        try:
            pcf = float(partial.get("confidence", 0) or 0)
        except (TypeError, ValueError):
            pcf = 0.0
        if pcf > 0:
            out["confidence"] = pcf

    return out

