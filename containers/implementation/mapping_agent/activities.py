"""
Mapping Agent — Temporal activities for mapping uploaded files to ERPNext doctypes.
Moved from: backend/app/services/implementation/mapping_engine.py
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from temporalio import activity

FIELD_MAPPINGS_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "containers" / "operation_agent" / "knowledge" / "erpnext_field_mappings.json"
)


# ── Embedded service logic ────────────────────────────────────────────────────

class _MappingEngine:
    def __init__(self):
        self._field_mappings: Dict = {}

    def _load_field_mappings(self) -> Dict:
        if not self._field_mappings and FIELD_MAPPINGS_PATH.exists():
            with open(FIELD_MAPPINGS_PATH, "r", encoding="utf-8") as f:
                self._field_mappings = json.load(f)
        return self._field_mappings

    def infer_doctype(self, columns: List[str]) -> Optional[str]:
        cols_lower = [c.lower() for c in columns]
        mappings = self._load_field_mappings()

        for doctype, config in mappings.items():
            user_to_erp = config.get("user_to_erp", {})
            match_count = sum(
                1 for k in user_to_erp.keys()
                if k.lower() in cols_lower or any(k.lower() in c for c in cols_lower)
            )
            if match_count >= 2:
                return doctype

        # Heuristics fallback
        if any("customer" in c or "party" in c for c in cols_lower) and any("item" in c or "product" in c for c in cols_lower):
            return "Sales Invoice"
        if any("supplier" in c or "vendor" in c for c in cols_lower) and any("item" in c for c in cols_lower):
            return "Purchase Invoice"
        if any("item" in c or "sku" in c for c in cols_lower) and "qty" not in " ".join(cols_lower):
            return "Item"
        if any("customer" in c for c in cols_lower) and "item" not in " ".join(cols_lower):
            return "Customer"
        if any("supplier" in c or "vendor" in c for c in cols_lower) and "item" not in " ".join(cols_lower):
            return "Supplier"
        return None

    def map_columns(self, columns: List[str], doctype: Optional[str] = None) -> Dict[str, str]:
        if not doctype:
            doctype = self.infer_doctype(columns)
        if not doctype:
            return {}
        mappings = self._load_field_mappings()
        config = mappings.get(doctype, {})
        result: Dict[str, str] = {}
        for src, erp in {**config.get("user_to_erp", {}), **config.get("items_child_table", {})}.items():
            for col in columns:
                if src.lower() in col.lower() or col.lower() in src.lower():
                    result[col] = erp
                    break
        return result

    def parse_csv(self, content: str) -> List[Dict]:
        return list(csv.DictReader(io.StringIO(content)))

    def map_file(self, content: str, filename: str, doctype_hint: Optional[str] = None) -> Dict[str, Any]:
        rows = self.parse_csv(content)
        if not rows:
            return {"doctype": None, "field_mapping": {}, "rows": [], "inferred_doctype": None, "source_columns": []}
        columns = list(rows[0].keys())
        doctype = doctype_hint or self.infer_doctype(columns)
        return {
            "doctype": doctype,
            "field_mapping": self.map_columns(columns, doctype),
            "rows": rows,
            "inferred_doctype": doctype,
            "source_columns": columns,
        }


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class MapFileInput:
    content: str           # raw CSV text
    filename: str
    doctype_hint: Optional[str] = None


@dataclass
class MapColumnsInput:
    columns: List[str]
    doctype_hint: Optional[str] = None


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="map_file_to_erpnext")
async def map_file_to_erpnext(inp: MapFileInput) -> Dict[str, Any]:
    """
    Parse a CSV file and map its columns to the matching ERPNext doctype + fields.
    Returns: {doctype, field_mapping, rows, inferred_doctype, source_columns}
    """
    engine = _MappingEngine()
    return engine.map_file(inp.content, inp.filename, inp.doctype_hint)


@activity.defn(name="infer_doctype_from_columns")
async def infer_doctype_from_columns(inp: MapColumnsInput) -> Dict[str, Any]:
    """
    Given a list of column names, infer the best-matching ERPNext doctype
    and return the field mapping without requiring the full CSV.
    """
    engine = _MappingEngine()
    doctype = engine.infer_doctype(inp.columns)
    field_mapping = engine.map_columns(inp.columns, doctype or inp.doctype_hint)
    return {"doctype": doctype, "field_mapping": field_mapping}