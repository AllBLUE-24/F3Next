"""
containers/OS/validation_agent/kb_rules.py

Loads KB-06 (Validation Rules) at worker startup.
Provides structured access to every rule category:

  schema_rules()          → list of schema-level rules (mandatory, type, child-table)
  business_rules(doctype) → list of business rules for a specific doctype
  data_quality_warnings() → list of non-blocking warning rules
  india_rules()           → GST / compliance rules

Also provides the KB-04 mandatory field index (shared from payload_generator)
so the validator can check mandatory fields without loading KB-04 separately.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_KB_ROOT = Path(__file__).parent.parent.parent / "knowledge_base"
_ERPNEXT = _KB_ROOT / "erpnext"
_COMMON  = _KB_ROOT / "common"


def _load(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("KB file not found: %s — using empty dict", path)
        return {}
    except json.JSONDecodeError as e:
        logger.error("KB file invalid JSON: %s — %s", path, e)
        return {}


class ValidationKnowledgeBase:
    """
    KB-06 singleton — loaded once per worker process.
    Also caches the mandatory field index from KB-04 to avoid
    cross-importing from payload_generator.
    """

    def __init__(self) -> None:
        raw_kb06 = _load(_ERPNEXT / "docs" / "validation_rules.json")
        if not raw_kb06:
            # Try alternate location
            raw_kb06 = _load(_KB_ROOT / "common" / "validation_rules.json")

        raw_kb04 = _load(_ERPNEXT / "schema" / "field_mappings.json")

        # ── Schema validation rules ─────────────────────────────────────────
        self._schema_rules: list[dict] = (
            raw_kb06.get("schema_validations", {}).get("rules", [])
        )

        # ── Business rules indexed by lowercase doctype key ─────────────────
        brvs = raw_kb06.get("business_rule_validations", {})
        self._business_rules: dict[str, list[dict]] = {
            k.lower().replace(" ", "_"): v
            for k, v in brvs.items()
        }
        # Also index by original camelCase doctype name for easy lookup
        self._business_rules_by_doctype: dict[str, list[dict]] = {}
        _doctype_key_map = {
            "Sales Order":     "sales_order",
            "Sales Invoice":   "sales_invoice",
            "Purchase Order":  "purchase_order",
            "Payment Entry":   "payment_entry",
            "Stock Entry":     "stock_entry",
            "Item":            "item",
            "Customer":        "customer",
            "Supplier":        "supplier",
        }
        for doctype, key in _doctype_key_map.items():
            self._business_rules_by_doctype[doctype] = brvs.get(key, [])

        # ── Data quality warnings ───────────────────────────────────────────
        self._dq_warnings: list[dict] = (
            raw_kb06.get("data_quality_validations", {}).get("warnings", [])
        )

        # ── India compliance (GST etc.) ─────────────────────────────────────
        india = raw_kb06.get("india_compliance_validations", {})
        self._gst_rules: list[dict] = india.get("gst_validations", [])

        # ── Validation sequence ─────────────────────────────────────────────
        self._validation_sequence: list[str] = (
            raw_kb06.get("validation_order", {}).get("sequence", [])
        )

        # ── Mandatory fields from KB-04 ─────────────────────────────────────
        # {doctype: [mandatory_field_key, ...]}
        self._mandatory_fields: dict[str, list[str]] = {}
        self._all_field_specs: dict[str, dict] = {}  # doctype → {field_key → spec}

        for doctype, data in raw_kb04.get("doctypes", {}).items():
            fm = data.get("field_mappings", {})
            self._mandatory_fields[doctype] = [
                fname for fname, fdata in fm.items()
                if fdata.get("mandatory")
            ]
            self._all_field_specs[doctype] = fm

        # ── GSTIN regex ─────────────────────────────────────────────────────
        gstin_rule = next(
            (r for r in self._gst_rules if r.get("rule_id") == "gstin_format"),
            {}
        )
        gstin_pattern = gstin_rule.get(
            "pattern",
            r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
        )
        self._gstin_re = re.compile(gstin_pattern)

        logger.info(
            "Validation KB loaded: %d schema rules, %d business-rule doctypes, "
            "%d DQ warnings, %d GST rules, %d KB-04 doctypes",
            len(self._schema_rules),
            len(self._business_rules_by_doctype),
            len(self._dq_warnings),
            len(self._gst_rules),
            len(self._mandatory_fields),
        )

    # ── Public accessors ──────────────────────────────────────────────────────

    def mandatory_fields(self, doctype: str) -> list[str]:
        """Return list of mandatory field keys for doctype from KB-04."""
        return self._mandatory_fields.get(doctype, [])

    def field_spec(self, doctype: str, field_key: str) -> dict:
        """Full field spec from KB-04 for a given doctype + field key."""
        return self._all_field_specs.get(doctype, {}).get(field_key, {})

    def child_fields(self, doctype: str, table_field: str) -> dict:
        """Child table field specs (e.g. items sub-fields)."""
        spec = self.field_spec(doctype, table_field)
        return spec.get("child_fields", {})

    def business_rules(self, doctype: str) -> list[dict]:
        """Business rules for a doctype. Returns [] if none defined."""
        return self._business_rules_by_doctype.get(doctype, [])

    def validate_gstin(self, gstin: str) -> bool:
        """True if GSTIN matches the standard 15-char pattern."""
        return bool(self._gstin_re.match(str(gstin).upper().strip()))


# ── Module-level singleton ─────────────────────────────────────────────────────

_vkb_instance: Optional[ValidationKnowledgeBase] = None


def validation_kb() -> ValidationKnowledgeBase:
    global _vkb_instance
    if _vkb_instance is None:
        _vkb_instance = ValidationKnowledgeBase()
    return _vkb_instance

# Alias — Sujay's validator.py imports this name
rules_kb = validation_kb