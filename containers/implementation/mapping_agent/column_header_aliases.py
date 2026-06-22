"""Tier-0 header aliases — canonical source→ERP field before KB/LLM column mapping."""
from __future__ import annotations

import re
from typing import Dict, List, Optional


def _norm_col(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower().replace("_", " "))


# Normalized header token → ERP fieldname (per doctype).
# Promote proven aliases to schema/mapping/*.json user_input_synonyms over time.
_HEADER_ALIASES_BY_DOCTYPE: Dict[str, Dict[str, str]] = {
    "Item": {
        "name of item": "item_code",
        "under group": "item_group",
        "base units": "stock_uom",
    },
    "Customer": {
        "ledger name": "customer_name",
    },
    "Supplier": {
        "ledger name": "supplier_name",
    },
}


def apply_header_aliases(
    columns: List[str],
    doctype: str,
    *,
    already_mapped: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Map known export headers (e.g. Tally) before strict KB synonym matching."""
    aliases = _HEADER_ALIASES_BY_DOCTYPE.get(doctype) or {}
    if not aliases:
        return dict(already_mapped or {})

    result = dict(already_mapped or {})
    mapped_targets = set(result.values())

    for col in columns:
        if col in result:
            continue
        target = aliases.get(_norm_col(col))
        if not target or target in mapped_targets:
            continue
        result[col] = target
        mapped_targets.add(target)

    return result
