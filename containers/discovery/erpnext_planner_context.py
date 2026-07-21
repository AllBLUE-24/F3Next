"""
Rich ERPNext context for the Discovery Step 1 MVP planner prompt.

Surfaces graph unlock chains and consultant-grade doctype semantics — not just depends_on.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_GRAPH_PATH = (
    Path(__file__).parent.parent / "knowledge_base" / "erpnext" / "erpnext_doctype_graph.json"
)

# Doctypes whose unlock chains and notes the planner must see for manufacturing MVP
_PLANNER_GRAPH_DOCTYPES = (
    "Item",
    "BOM",
    "Batch",
    "Warehouse",
    "Work Order",
    "Job Card",
    "Workstation",
    "Operation",
    "Stock Entry",
    "Purchase Receipt",
    "Supplier",
    "Delivery Note",
    "Customer",
)

ERP_NEXT_OPERATING_SEMANTICS = """
ERPNext OPERATING SEMANTICS (consultant rules — respect these when scoping Day-1):

Manufacturing loop:
- BOM defines recipe + optional routing operations (mix, cure, bottle, etc.).
- Work Order is the production batch ticket — it does NOT by itself record machine time or actual consumption.
- Job Card records time and quantity completed at each Operation/Workstation on a Work Order.
- Stock Entry records material issue, WIP transfer between warehouses, scrap, and manufacture (FG receipt).
- Warehouse (especially WIP warehouses per stage) makes "factory black box" visible between operations.

Traceability loop:
- Purchase Receipt links incoming raw material to Supplier (and Batch when batch-managed).
- Stock Entry links raw batch consumption to finished batch on manufacture.
- Delivery Note links finished batch to Customer dispatch.
- Customer master is operational (not financial) when recall/trace requires knowing who received stock.

Dual-system (Tally/Busy):
- Defer Sales Invoice and Payment Entry — keep operational masters (Customer, Supplier) when trace requires them.

Closure test (mandatory before you finalize):
Ask: "After Day-1 import, can we answer the client's bottleneck sentence using ONLY the Day-1 doctypes?"
If NO — add the missing doctype that records the missing event. Do NOT defer execution doctypes
(Job Card, Stock Entry) while keeping planning shells (Work Order, BOM) unless you can prove
the pain does not require shop-floor or stock-movement data.
""".strip()


def _load_graph() -> dict[str, Any]:
    with open(_GRAPH_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_rich_graph_summary() -> str:
    """Format doctype graph with depends_on, unlocks, and consultant notes."""
    graph = _load_graph()
    doctypes = graph.get("doctypes") or {}
    lines: list[str] = []

    for dt in _PLANNER_GRAPH_DOCTYPES:
        info = doctypes.get(dt)
        if not info:
            continue
        deps = info.get("depends_on") or []
        unlocks = info.get("unlocks") or []
        note = str(info.get("notes") or "").strip()
        signals = info.get("signal_in_files") or []
        parts = [f"- {dt}:"]
        if deps:
            parts.append(f"depends_on={deps}")
        if unlocks:
            parts.append(f"unlocks={unlocks}")
        if signals:
            parts.append(f"file_signals={signals[:3]}")
        if note:
            parts.append(f"note={note[:200]}")
        lines.append(" ".join(parts))

    return "\n".join(lines)


__all__ = [
    "ERP_NEXT_OPERATING_SEMANTICS",
    "build_rich_graph_summary",
]
