"""Company data mapping to ERPNext doctypes and fields."""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import csv
import io

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "implementation" / "knowledge"
FIELD_MAPPINGS_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / "containers" / "operation_agent" / "knowledge" / "erpnext_field_mappings.json"


class MappingEngine:
    """Maps user-provided data to ERPNext doctype.field."""

    def __init__(self):
        self._field_mappings = {}
        self._doctype_graph = None

    def _load_field_mappings(self) -> Dict:
        if not self._field_mappings and FIELD_MAPPINGS_PATH.exists():
            with open(FIELD_MAPPINGS_PATH, "r", encoding="utf-8") as f:
                self._field_mappings = json.load(f)
        return self._field_mappings

    def _load_doctype_graph(self) -> Dict:
        if self._doctype_graph is None:
            path = KNOWLEDGE_DIR / "doctypes_graph_ERPNext.json"
            with open(path, "r", encoding="utf-8") as f:
                self._doctype_graph = json.load(f)
        return self._doctype_graph

    def infer_doctype_from_columns(self, columns: List[str]) -> Optional[str]:
        """Infer ERPNext doctype from column names."""
        cols_lower = [c.lower() for c in columns]
        mappings = self._load_field_mappings()

        for doctype, config in mappings.items():
            user_to_erp = config.get("user_to_erp", {})
            match_count = sum(1 for k in user_to_erp.keys() if k.lower() in cols_lower or any(k.lower() in c for c in cols_lower))
            if match_count >= 2:
                return doctype

        # Heuristics
        if any("customer" in c or "party" in c for c in cols_lower) and any("item" in c or "product" in c for c in cols_lower):
            return "Sales Invoice"
        if any("supplier" in c or "vendor" in c for c in cols_lower):
            return "Purchase Invoice"
        if any("item" in c or "sku" in c for c in cols_lower) and "qty" not in " ".join(cols_lower):
            return "Item"
        if any("customer" in c for c in cols_lower) and "item" not in " ".join(cols_lower):
            return "Customer"
        if any("supplier" in c or "vendor" in c for c in cols_lower) and "item" not in " ".join(cols_lower):
            return "Supplier"

        return None

    def map_columns_to_doctype(
        self,
        columns: List[str],
        doctype: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Map source columns to ERPNext fields.
        Returns {source_column: erpnext_field}
        """
        if not doctype:
            doctype = self.infer_doctype_from_columns(columns)
        if not doctype:
            return {}

        mappings = self._load_field_mappings()
        config = mappings.get(doctype, {})
        user_to_erp = config.get("user_to_erp", {})
        items_child = config.get("items_child_table", {})

        result = {}
        cols_lower = [c.lower() for c in columns]

        for src, erp in user_to_erp.items():
            for i, col in enumerate(columns):
                if src.lower() in col.lower() or col.lower() in src.lower():
                    result[col] = erp
                    break

        for src, erp in items_child.items():
            for i, col in enumerate(columns):
                if src.lower() in col.lower() or col.lower() in src.lower():
                    result[col] = erp
                    break

        return result

    def parse_csv(self, content: str) -> List[Dict]:
        """Parse CSV content into list of dicts."""
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)

    def map_file_to_erpnext(
        self,
        content: str,
        filename: str,
        doctype_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Map a file's content to ERPNext structure.
        Returns {doctype, field_mapping, rows, inferred_doctype}
        """
        rows = self.parse_csv(content)
        if not rows:
            return {"doctype": None, "field_mapping": {}, "rows": [], "inferred_doctype": None}

        columns = list(rows[0].keys())
        doctype = doctype_hint or self.infer_doctype_from_columns(columns)
        field_mapping = self.map_columns_to_doctype(columns, doctype)

        return {
            "doctype": doctype,
            "field_mapping": field_mapping,
            "rows": rows,
            "inferred_doctype": doctype,
            "source_columns": columns,
        }
