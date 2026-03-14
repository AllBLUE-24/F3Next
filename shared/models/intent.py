"""
shared/models/intent.py

Pydantic models representing the output of the Clarity Agent.
Used by every downstream agent (Context Retrieval, Planner, Payload Generator, etc.)
Mounted into all containers via the shared/ package.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ─── Ambiguity ────────────────────────────────────────────────────────────────

class Ambiguity(BaseModel):
    """A single piece of missing or unclear information."""

    field:     str             # e.g. "customer", "items[0].qty"
    question:  str             # Human-readable question to ask user
    required:  bool = True     # If True, we cannot proceed without this answer
    options:   Optional[list[str]] = None  # Suggested choices if applicable


# ─── Extracted entities ───────────────────────────────────────────────────────

class ItemEntity(BaseModel):
    """One line item extracted from the prompt."""

    item_code: Optional[str] = None    # User-provided name / code
    qty:       Optional[float] = None
    rate:      Optional[float] = None
    warehouse: Optional[str] = None
    uom:       Optional[str] = None    # e.g. "kg", "Nos", "pcs"


class EntityMap(BaseModel):
    """
    All entities extracted from the user prompt.
    Fields are None when not mentioned — downstream agents fill defaults.
    """

    # Party
    customer:  Optional[str] = None
    supplier:  Optional[str] = None

    # Items — always a list (even for single-item prompts)
    items:     list[ItemEntity] = Field(default_factory=list)

    # Dates
    transaction_date:  Optional[str] = None   # ISO: yyyy-mm-dd
    delivery_date:     Optional[str] = None
    due_date:          Optional[str] = None
    posting_date:      Optional[str] = None

    # References
    po_no:             Optional[str] = None
    so_no:             Optional[str] = None
    dn_no:             Optional[str] = None
    invoice_no:        Optional[str] = None
    payment_reference: Optional[str] = None

    # Finance
    amount:            Optional[float] = None
    currency:          Optional[str] = None
    payment_type:      Optional[str] = None   # "Receive" / "Pay" / "Internal Transfer"
    mode_of_payment:   Optional[str] = None   # "Cash" / "Bank Transfer - NEFT" / etc.
    party_type:        Optional[str] = None   # "Customer" / "Supplier"

    # Stock
    from_warehouse:    Optional[str] = None
    to_warehouse:      Optional[str] = None
    stock_entry_type:  Optional[str] = None   # "Material Transfer" / "Material Issue" / etc.

    # Misc
    project:           Optional[str] = None
    price_list:        Optional[str] = None
    company:           Optional[str] = None

    # Catch-all for ERP-specific fields not covered above
    extra:             dict[str, Any] = Field(default_factory=dict)


# ─── StructuredIntent ─────────────────────────────────────────────────────────

class StructuredIntent(BaseModel):
    """
    The canonical output of the Clarity Agent.
    This is what every downstream agent receives as input.
    """

    # Intent classification
    intent_id:        str                  # e.g. "create_sales_order"
    category:         str                  # "create" / "read" / "update" / "delete" / ...
    target_doctype:   str                  # e.g. "Sales Order"
    action:           str                  # "create" / "get" / "update" / "submit" / ...
    erp_type:         str = "erpnext"      # "erpnext" / "odoo" — passed through unchanged

    # Extracted data
    entities:         EntityMap = Field(default_factory=EntityMap)

    # Confidence + ambiguity
    confidence:       float = 0.0          # 0.0 – 1.0
    ambiguities:      list[Ambiguity] = Field(default_factory=list)
    has_ambiguities:  bool = False

    # Risk + confirmation
    risk_level:       str = "low"          # "low" / "medium" / "high" / "critical"
    requires_confirmation: bool = False

    # Debug / audit
    raw_prompt:       Optional[str] = None
    session_context:  list[dict[str, str]] = Field(default_factory=list)

    def is_executable(self) -> bool:
        """True if confidence is high enough and no blocking ambiguities."""
        blocking = [a for a in self.ambiguities if a.required]
        return self.confidence >= 0.65 and len(blocking) == 0


# ─── Fallback ─────────────────────────────────────────────────────────────────

FALLBACK_INTENT = StructuredIntent(
    intent_id="unknown",
    category="unknown",
    target_doctype="",
    action="unknown",
    confidence=0.0,
    ambiguities=[
        Ambiguity(
            field="intent",
            question="I couldn't understand your command. Could you rephrase it?",
            required=True,
        )
    ],
    has_ambiguities=True,
)