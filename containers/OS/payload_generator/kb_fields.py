"""
containers/OS/payload_generator/kb_fields.py

Loads KB-04 (Field Mapping Rules) at worker startup.
Provides fast in-memory lookups for the payload_builder.

Index built:
  doctype → {
    field_mappings:    {entity_key → full field spec}
    mandatory_fields:  [fieldname, ...]
    child_tables:      {fieldname → {child_fields: {...}}}
  }

Also indexes parsing rules (date, currency, quantity) so
payload_builder can resolve natural language values.
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_KB_ROOT = Path(__file__).parent.parent.parent / "knowledge_base"
_ERPNEXT = _KB_ROOT / "erpnext"


def _load(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("KB-04 not found at %s — using empty mapping", path)
        return {}
    except json.JSONDecodeError as e:
        logger.error("KB-04 invalid JSON: %s — %s", path, e)
        return {}


class FieldKnowledgeBase:
    """
    KB-04 singleton. Loaded once at worker startup.
    Provides per-doctype field metadata + value parsing rules.
    """

    def __init__(self) -> None:
        raw = _load(_ERPNEXT / "schema" / "field_mappings.json")

        # doctype → field mapping dict
        self._doctypes: dict[str, dict] = raw.get("doctypes", {})

        # Parsing rules
        self._date_rules:     dict = raw.get("date_parsing_rules", {})
        self._currency_rules: dict = raw.get("currency_parsing_rules", {})
        self._qty_rules:      dict = raw.get("quantity_parsing_rules", {})
        self._default_rules:  dict = raw.get("default_value_rules", {})

        logger.info(
            "Field KB loaded: %d doctypes in KB-04", len(self._doctypes)
        )

    # ── Field lookups ─────────────────────────────────────────────────────────

    def field_mappings(self, doctype: str) -> dict:
        """entity_key → field spec dict for a doctype. {} if unknown."""
        return self._doctypes.get(doctype, {}).get("field_mappings", {})

    def mandatory_fields(self, doctype: str) -> list[str]:
        """List of mandatory entity keys for a doctype."""
        return [
            fname
            for fname, fdata in self.field_mappings(doctype).items()
            if fdata.get("mandatory")
        ]

    def child_fields(self, doctype: str, table_field: str) -> dict:
        """
        child_fields for a child-table field.
        e.g. field_kb.child_fields("Sales Order", "items")
        → {"item_code": {...}, "qty": {...}, ...}
        """
        fm = self.field_mappings(doctype)
        return fm.get(table_field, {}).get("child_fields", {})

    def fieldname(self, doctype: str, entity_key: str) -> str:
        """
        ERPNext API fieldname for an entity key.
        e.g. fieldname("Sales Order", "customer") → "customer"
        Most are identical, but this makes field renames transparent.
        """
        fm = self.field_mappings(doctype)
        return fm.get(entity_key, {}).get("fieldname", entity_key)

    def field_type(self, doctype: str, entity_key: str) -> str:
        fm = self.field_mappings(doctype)
        return fm.get(entity_key, {}).get("fieldtype", "Data")

    def default_value(self, doctype: str, entity_key: str) -> Optional[str]:
        fm = self.field_mappings(doctype)
        return fm.get(entity_key, {}).get("default_value")

    # ── Date parsing ──────────────────────────────────────────────────────────

    def resolve_date(self, value: str) -> str:
        """
        Convert natural language / formatted date string → ISO date (YYYY-MM-DD).
        Falls back to value as-is if not recognised.
        """
        if not value:
            return date.today().isoformat()

        v = str(value).strip().lower()

        nl_map = self._date_rules.get("natural_language", {})

        # Direct natural language
        if v in ("today", ""):
            return date.today().isoformat()
        if v == "tomorrow":
            return (date.today() + timedelta(days=1)).isoformat()
        if v == "yesterday":
            return (date.today() - timedelta(days=1)).isoformat()
        if v in ("next week", "next_week"):
            return (date.today() + timedelta(days=7)).isoformat()
        if v in ("end of month", "end of this month"):
            today = date.today()
            # Last day of current month
            if today.month == 12:
                last = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                last = date(today.year, today.month + 1, 1) - timedelta(days=1)
            return last.isoformat()

        # Already ISO format
        if len(v) == 10 and v[4] == "-" and v[7] == "-":
            return v   # YYYY-MM-DD

        # DD-MM-YYYY or DD/MM/YYYY
        for sep in ("-", "/"):
            parts = v.split(sep)
            if len(parts) == 3 and len(parts[2]) == 4:
                try:
                    return date(int(parts[2]), int(parts[1]), int(parts[0])).isoformat()
                except ValueError:
                    pass

        # Return as-is (let ERPNext validate)
        return str(value)

    def today_plus_days(self, days: int) -> str:
        return (date.today() + timedelta(days=days)).isoformat()

    # ── Currency parsing ──────────────────────────────────────────────────────

    def resolve_amount(self, value) -> float:
        """
        Parse '50K', '5 lakh', '₹50,000' → float.
        Returns float(value) as-is if already numeric.
        """
        if isinstance(value, (int, float)):
            return float(value)

        v = str(value).strip()

        # Strip currency symbols
        for sym in self._currency_rules.get("symbols", {}).keys():
            v = v.replace(sym, "")

        # Strip commas
        v = v.replace(",", "").strip()

        # Word multipliers (order: largest first)
        # Only process entries whose value is numeric (e.g. "*100000")
        # Skip currency-code entries like "rupees": "INR"
        words = self._currency_rules.get("words", {})
        multiplier = 1.0
        numeric_words = {
            w: m for w, m in words.items()
            if m.replace("*", "").replace(".", "").lstrip("-").isdigit()
        }
        for word, mult_str in sorted(
            numeric_words.items(),
            key=lambda x: -abs(float(x[1].replace("*", "") or "1")),
        ):
            if word in v.lower():
                try:
                    multiplier = float(mult_str.replace("*", ""))
                    v = v.lower().replace(word, "").strip()
                except ValueError:
                    pass
                break

        try:
            return float(v) * multiplier
        except ValueError:
            logger.warning("Cannot parse amount: %s — returning 0", value)
            return 0.0

    # ── UOM normalisation ─────────────────────────────────────────────────────

    def resolve_uom(self, value: str) -> str:
        """Normalise user-entered UOM to ERPNext UOM name."""
        if not value:
            return "Nos"
        units = self._qty_rules.get("units", {})
        return units.get(str(value).lower().strip(), str(value))


# ── Module-level singleton ─────────────────────────────────────────────────────

_fkb_instance: Optional[FieldKnowledgeBase] = None


def field_kb() -> FieldKnowledgeBase:
    global _fkb_instance
    if _fkb_instance is None:
        _fkb_instance = FieldKnowledgeBase()
    return _fkb_instance