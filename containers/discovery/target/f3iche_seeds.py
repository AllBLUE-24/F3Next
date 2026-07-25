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


def org_skeleton_from_f3iche(f3iche_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract warehouse and default seeding skeleton from niche template."""
    if not f3iche_data:
        return {}
    masters = f3iche_data.get("erpnext_masters_setup") or {}
    warehouse = masters.get("warehouse_setup") or {}
    defaults = f3iche_data.get("default_settings") or {}
    seeding = defaults.get("seeding_strategies") or {}
    stock = defaults.get("stock_settings") or {}
    manufacturing = defaults.get("manufacturing_settings") or {}
    skeleton: Dict[str, Any] = {}
    if warehouse.get("required_warehouses"):
        skeleton["required_warehouses"] = warehouse["required_warehouses"]
    if warehouse.get("warehouse_logic"):
        skeleton["warehouse_logic"] = warehouse["warehouse_logic"]
    if seeding:
        skeleton["seeding_strategies"] = seeding
    if stock.get("valuation_method"):
        skeleton["valuation_method"] = stock["valuation_method"]
    if manufacturing.get("material_consumption"):
        skeleton["material_consumption"] = manufacturing["material_consumption"]
    bom = masters.get("bom_structure") or {}
    if bom.get("operations"):
        skeleton["bom_operations"] = bom["operations"]
    return skeleton


def clarifying_questions_from_f3iche(f3iche_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return Research-authored questions_to_ask from niche JSON."""
    raw = f3iche_data.get("questions_to_ask") or []
    out: List[Dict[str, str]] = []
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            continue
        question = str(entry.get("question") or "").strip()
        if not question:
            continue
        out.append({
            "id": f"f3iche_q_{idx}",
            "question": question,
            "purpose": str(entry.get("purpose") or "").strip(),
        })
    return out


def load_f3iche_playbook(f3iche_id: str) -> Dict[str, Any]:
    """Load niche JSON playbook blocks used by clarify and target structure."""
    from containers.discovery.niche_resolver import f3iche_template_path

    path = f3iche_template_path(f3iche_id)
    if not path.is_file():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "data": data,
        "questions": clarifying_questions_from_f3iche(data),
        "data_gaps": [str(g) for g in (data.get("common_data_gaps") or []) if g],
        "failures": [f for f in (data.get("common_failures") or []) if isinstance(f, dict)],
    }


def bottlenecks_from_f3iche(f3iche_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return Research-owned bottlenecks[] block when present on F3iche JSON."""
    raw = f3iche_data.get("bottlenecks")
    if not isinstance(raw, list):
        return []
    return [b for b in raw if isinstance(b, dict)]
