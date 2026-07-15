"""F3iche template seed loading and validation hints for discovery target generation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def canonicalize_template_doctype(name: str) -> str:
    """Strip f3iche parenthetical labels: 'BOM (Formulation)' → 'BOM'."""
    raw = str(name or "").strip()
    if not raw:
        return ""
    return raw.split(" (")[0].strip()


def merge_seed_sources(*sources: List[str]) -> List[str]:
    """Union seed lists preserving first-seen order."""
    seen: Set[str] = set()
    merged: List[str] = []
    for source in sources:
        for dt in source or []:
            name = str(dt or "").strip()
            if name and name not in seen:
                seen.add(name)
                merged.append(name)
    return merged


def load_f3iche_template_seeds(f3iche_path: str) -> Tuple[List[str], Dict[str, Any]]:
    """Load and canonicalize seed doctypes from f3iche JSON."""
    path = Path(f3iche_path)
    if not path.exists():
        return [], {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("required_doctypes") or data.get("mandatory_doctypes") or []
    seeds = [canonicalize_template_doctype(d) for d in raw if d]
    return list(dict.fromkeys(seeds)), data


def validation_rules_from_f3iche(f3iche_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract lightweight validation hints from f3iche template."""
    rules: Dict[str, Any] = {"custom_fields": [], "notes": []}
    masters = f3iche_data.get("erpnext_masters_setup") or {}
    item_struct = masters.get("item_structure") or {}
    custom = item_struct.get("custom_fields_required")
    if custom:
        rules["custom_fields"].append({"doctype": "Item", "fields": custom})
        rules["notes"].append("Item custom fields required per niche template")
    if f3iche_data.get("regulatory_criticality_level"):
        rules["regulatory_criticality"] = f3iche_data["regulatory_criticality_level"]
    return rules


def bottlenecks_from_f3iche(f3iche_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return Research-owned bottlenecks[] block when present on F3iche JSON."""
    raw = f3iche_data.get("bottlenecks")
    if not isinstance(raw, list):
        return []
    return [b for b in raw if isinstance(b, dict)]
