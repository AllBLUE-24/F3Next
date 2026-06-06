"""Shared party-split rules from corpus KB (single source for 8c + Step 9)."""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict, FrozenSet, List, Optional

from containers.knowledge_base.erpnext.schema.compose import corpus_rules


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _norm_col(s: str) -> str:
    return _norm(str(s or "").replace("_", " "))


@lru_cache(maxsize=1)
def split_column_synonyms() -> FrozenSet[str]:
    rules = corpus_rules()
    syns = rules.get("split_column_synonyms") or []
    return frozenset(_norm_col(s) for s in syns if s)


@lru_cache(maxsize=1)
def _party_synonym_index() -> Dict[str, List[str]]:
    """Canonical doctype → lowercase alias values."""
    rules = corpus_rules()
    raw = rules.get("party_type_synonyms") or {}
    normalized: Dict[str, List[str]] = {}
    if not isinstance(raw, dict):
        return normalized
    if raw and all(isinstance(v, str) for v in raw.values()):
        for alias, canonical in raw.items():
            canon = str(canonical).strip()
            alias_l = str(alias).strip().lower()
            if not canon or not alias_l:
                continue
            normalized.setdefault(canon, [])
            if alias_l not in normalized[canon]:
                normalized[canon].append(alias_l)
    else:
        for canonical, aliases in raw.items():
            canon = str(canonical).strip()
            if not canon:
                continue
            normalized.setdefault(canon, [])
            for alias in aliases or []:
                alias_l = str(alias).strip().lower()
                if alias_l and alias_l not in normalized[canon]:
                    normalized[canon].append(alias_l)
    for canon, aliases in normalized.items():
        canon_l = canon.lower()
        if canon_l not in aliases:
            aliases.append(canon_l)
    return normalized


def customer_role_values() -> FrozenSet[str]:
    syns = _party_synonym_index()
    values = set(syns.get("Customer", []))
    values.update({"customer", "client", "buyer"})
    return frozenset(values)


def supplier_role_values() -> FrozenSet[str]:
    syns = _party_synonym_index()
    values = set(syns.get("Supplier", []))
    values.update({"supplier", "vendor", "seller"})
    return frozenset(values)


def find_split_column(columns: List[str]) -> Optional[str]:
    syns = split_column_synonyms()
    for col in columns:
        if _norm_col(col) in syns:
            return col
    return None


def is_customer_role(value: str) -> bool:
    return _norm(value) in customer_role_values()


def is_supplier_role(value: str) -> bool:
    return _norm(value) in supplier_role_values()


def alias_to_canonical_party() -> Dict[str, str]:
    syns = _party_synonym_index()
    return {
        alias: canonical
        for canonical, aliases in syns.items()
        for alias in aliases
    }
