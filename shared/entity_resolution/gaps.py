"""
Build GateResult gaps from unresolved LER values.
"""

from __future__ import annotations

from typing import Any, Optional

from shared.entity_resolution.resolve import ResolvedEntities
from shared.gate_contracts import GapItem, GapSeverity


def resolution_gaps_from_unresolved(
    resolved: ResolvedEntities,
    *,
    doctype: str = "",
    link_cache: Optional[dict[str, list[str]]] = None,
) -> list[GapItem]:
    """
    Turn LER misses into CLARIFY gaps (blocking or choice with candidates).
    """
    gaps: list[GapItem] = []
    link_cache = link_cache or {}

    entity_to_doctype = {
        "customer": "Customer",
        "supplier": "Supplier",
        "company": "Company",
        "item_code": "Item",
    }

    for entity_key, values in resolved.unresolved.items():
        if not values:
            continue
        erp_dt = entity_to_doctype.get(entity_key, "Item")
        raw_val = values[0]
        known = link_cache.get(erp_dt) or []
        candidates = _fuzzy_candidates(raw_val, known)

        if candidates:
            gaps.append(
                GapItem(
                    field=entity_key,
                    entity_key=entity_key,
                    doctype=doctype or None,
                    question=(
                        f"I couldn't find an exact match for '{raw_val}' in {erp_dt}. "
                        "Which one did you mean?"
                    ),
                    severity="choice",
                    candidates=candidates[:8],
                    rule_id="ler_unresolved_choice",
                )
            )
        else:
            gaps.append(
                GapItem(
                    field=entity_key,
                    entity_key=entity_key,
                    doctype=doctype or None,
                    question=(
                        f"'{raw_val}' is not in your ERP {erp_dt} list yet. "
                        "Add it in ERPNext or upload it via implementation, then try again."
                    ),
                    severity="blocking",
                    rule_id="ler_unresolved_blocking",
                )
            )

    for entity_key, cands in resolved.ambiguous.items():
        if entity_key in resolved.unresolved:
            continue
        gaps.append(
            GapItem(
                field=entity_key,
                entity_key=entity_key,
                doctype=doctype or None,
                question=f"Multiple matches for {entity_key}. Please confirm.",
                severity="choice",
                candidates=cands[:8],
                rule_id="ler_ambiguous",
            )
        )

    return gaps


def _fuzzy_candidates(raw: str, known: list[str], *, limit: int = 8) -> list[str]:
    """Simple substring / prefix filter for choice gaps."""
    if not raw or not known:
        return []
    q = raw.casefold()
    hits: list[str] = []
    for name in known:
        ncf = name.casefold()
        if q in ncf or ncf.startswith(q) or q.startswith(ncf.split(" - ")[0]):
            hits.append(name)
        if len(hits) >= limit:
            break
    return hits
