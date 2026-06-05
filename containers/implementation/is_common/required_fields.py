"""Single source of truth for per-doctype required import fields (IS pipeline)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from shared.kb.policy_loaders import get_is_import_rules

_KB_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "erpnext"
_GRAPH_PATH = _KB_DIR / "erpnext_doctype_graph.json"

# Last-resort fallback (mirrors validation_agent)
_FALLBACK: Dict[str, List[str]] = {
    "Item": ["item_code", "item_name", "item_group", "stock_uom"],
    "Customer": ["customer_name", "customer_group", "territory"],
    "Supplier": ["supplier_name", "supplier_group"],
    "Employee": ["employee_name", "date_of_joining"],
    "Sales Order": ["customer", "transaction_date", "delivery_date", "items"],
    "Sales Invoice": ["customer", "posting_date"],
    "Purchase Order": ["supplier", "transaction_date", "items"],
    "Purchase Invoice": ["supplier", "bill_no", "bill_date"],
    "Payment Entry": ["payment_type", "party_type", "party", "paid_amount"],
    "Journal Entry": ["posting_date", "accounts"],
    "Stock Entry": ["stock_entry_type", "items"],
    "Project": ["project_name"],
}


def normalize_required_fieldnames(fields: List[str]) -> List[str]:
    """'items (item_code, qty)' → 'items'; 'paid_to/paid_from' → split."""
    out: List[str] = []
    seen: set = set()
    for raw in fields or []:
        s = str(raw or "").strip()
        if not s:
            continue
        if "(" in s:
            s = s.split("(", 1)[0].strip()
        parts = [p.strip() for p in s.split("/") if p.strip()]
        for p in parts or [s]:
            p2 = p.split(" ", 1)[0].strip()
            if p2 and p2 not in seen:
                seen.add(p2)
                out.append(p2)
    return out


@lru_cache(maxsize=1)
def _load_graph() -> Dict:
    try:
        import json

        with open(_GRAPH_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_required_fields(doctype: str) -> List[str]:
    """
    Required fields for import validation and readiness (graph → KB rules → fallback).
    Matches validation_agent._get_required_fields precedence.
    """
    graph_fields = (
        (_load_graph().get("doctypes") or {})
        .get(doctype, {})
        .get("required_fields", [])
    )
    kb_fields = (get_is_import_rules().get("required_fields_by_doctype") or {}).get(doctype, [])
    raw = graph_fields if graph_fields else (kb_fields if kb_fields else _FALLBACK.get(doctype, []))
    return normalize_required_fieldnames(raw or [])
