"""Generate plain-language workflow explanation for Discovery Assistant Step 1."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from containers.discovery.prompts import WORKFLOW_EXPLANATION_PROMPT

logger = logging.getLogger(__name__)

EXTRACT_MODEL = "gpt-4o-mini"
EXTRACT_TEMPERATURE = 0.1

# Fallback labels when LLM omits a seed doctype
_DOCTYPE_LABELS: dict[str, tuple[str, str, list[str]]] = {
    "Item": (
        "Product & raw material master",
        "Resins, hardeners, Part A/B SKUs you manufacture or buy",
        ["product_master.xlsx", "item_list.xls"],
    ),
    "BOM": (
        "Your formulation / recipe sheets",
        "Excel BOMs defining chemical mix ratios and batch recipes",
        ["formulation_master.xlsx", "recipe_sheet.xls"],
    ),
    "Work Order": (
        "Factory batch tickets",
        "Production runs and batch tickets from the shop floor",
        ["batch_tickets.xlsx", "production_log.xls"],
    ),
    "Sales Order": (
        "Sales bookings driving production",
        "Confirmed orders from Tally or Excel that the factory must fulfill",
        ["sales_orders.xlsx", "order_book.xls"],
    ),
    "Stock Entry": (
        "Stock & WIP movement records",
        "Material issues, WIP transfers, and finished goods receipts",
        ["stock_movement.xlsx", "wip_log.xls"],
    ),
    "Batch": (
        "Batch / lot numbers",
        "Batch IDs with manufacturing and expiry dates for traceability",
        ["batch_register.xlsx", "batch_tracking.xlsx"],
    ),
    "Delivery Note": (
        "Delivery / dispatch records",
        "Challans or shipping records showing which batch went to which customer",
        ["delivery_notes.xlsx", "dispatch_challan.xls"],
    ),
    "Warehouse": (
        "Warehouse / storage location list",
        "Simple list of storage zones (Raw Materials, Finished Goods, Quarantine)",
        ["warehouse_list.xlsx", "storage_locations.xls"],
    ),
    "Purchase Receipt": (
        "Goods receipt / GRN records",
        "Incoming raw material receipts with supplier batch numbers",
        ["grn_register.xlsx", "goods_receipt.xls"],
    ),
    "Job Card": (
        "Shop floor operation logs",
        "Dispersion, milling, letdown step records",
        ["job_cards.xlsx"],
    ),
    "Workstation": (
        "Production lines and machines",
        "Vats, curing areas, bottling lines — where Job Cards record time",
        ["workstation_list.xlsx", "machine_line_master.xls"],
    ),
    "Project": (
        "Installation / site projects",
        "Turnkey jobs linking factory output to field crews",
        ["project_list.xlsx"],
    ),
    "Customer": (
        "Customer / client records",
        "Who you sell to or bill",
        ["customers.xlsx", "client_list.xls"],
    ),
    "Supplier": (
        "Supplier records",
        "Raw material vendors",
        ["suppliers.xlsx", "vendor_list.xls"],
    ),
}


def _parse_llm_json(content: str) -> dict:
    start_idx = content.find("{")
    end_idx = content.rfind("}")
    if start_idx != -1 and end_idx != -1:
        clean_json = content[start_idx : end_idx + 1]
    else:
        clean_json = content.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)


def _default_expected_item(doctype: str) -> dict:
    if doctype in _DOCTYPE_LABELS:
        friendly, desc, examples = _DOCTYPE_LABELS[doctype]
        return {
            "doctype": doctype,
            "user_friendly_name": friendly,
            "description": desc,
            "example_files": examples,
        }
    slug = doctype.lower().replace(" ", "_")
    return {
        "doctype": doctype,
        "user_friendly_name": doctype,
        "description": f"Spreadsheets or exports for {doctype}",
        "example_files": [f"{slug}_master.xlsx"],
    }


def _build_discovery_context(
    *,
    coverage: Optional[Dict[str, Any]],
    chat_transcript: str,
    mvp_focus: Optional[Dict[str, Any]],
    scoping_reasoning: str = "",
) -> str:
    lines: list[str] = []
    if chat_transcript:
        lines.append(f"CHAT TRANSCRIPT (excerpt):\n{chat_transcript[:4000]}")
    if coverage:
        for key, label in (
            ("industry", "Industry"),
            ("strategy", "Fulfillment model"),
            ("scale", "Scale"),
            ("legacy_system", "Current accounting/ERP"),
            ("pain_point", "Pain point"),
        ):
            entry = coverage.get(key) or {}
            if entry.get("value"):
                lines.append(f"{label}: {entry['value']}")
    if mvp_focus:
        if mvp_focus.get("primary_bottleneck"):
            lines.append(f"Bottleneck: {mvp_focus['primary_bottleneck']}")
        for req in mvp_focus.get("functional_requirements") or []:
            lines.append(f"Requirement: {req}")
    if scoping_reasoning:
        lines.append(f"MVP scoping: {scoping_reasoning}")
    return "\n".join(lines) if lines else "No additional context."


def _reconcile_expected_data(
    explanation: Dict[str, Any],
    seed_doctypes: List[str],
) -> Dict[str, Any]:
    """Ensure every Day-1 seed doctype appears in expected_data."""
    by_doctype: dict[str, dict] = {}
    for item in explanation.get("expected_data") or []:
        dt = item.get("doctype")
        if dt:
            by_doctype[dt] = item

    merged = [_default_expected_item(dt) if dt not in by_doctype else by_doctype[dt] for dt in seed_doctypes]
    explanation["expected_data"] = merged

    if not explanation.get("upload_checklist"):
        explanation["upload_checklist"] = [
            f"Prepare {item['user_friendly_name']}"
            for item in merged[:8]
        ]
    return explanation


def _fallback_explanation(
    *,
    f3iche: str,
    industry: str,
    bottleneck: str,
    seed_doctypes: List[str],
    dual_system_note: str = "",
) -> Dict[str, Any]:
    """Deterministic fallback when LLM is unavailable."""
    expected_data = [_default_expected_item(dt) for dt in seed_doctypes]
    tally_line = f" {dual_system_note}" if dual_system_note else ""

    return {
        "workflow_summary": (
            f"Day-1 MVP for your {industry or 'business'} focuses on {bottleneck or 'your main bottleneck'}."
            f"{tally_line}"
        ),
        "business_flow_explanation": (
            "We connect your existing spreadsheets and order book to factory production — "
            "formulations (BOM), work orders, and stock movement — so WIP is visible before full ERP rollout."
        ),
        "expected_data": expected_data,
        "setup_phases": [
            {
                "phase": "Phase 1",
                "name": "Masters & formulations",
                "description": "Products and recipes everything else links to",
                "doctypes": [d for d in seed_doctypes if d in ("Item", "BOM", "Batch")],
            },
            {
                "phase": "Phase 2",
                "name": "Production bridge",
                "description": "Orders driving factory execution",
                "doctypes": [d for d in seed_doctypes if d not in ("Item", "BOM", "Batch")],
            },
        ],
        "upload_checklist": [f"Prepare {item['user_friendly_name']}" for item in expected_data[:6]],
    }


async def generate_workflow_explanation(
    *,
    f3iche: str,
    industry: str,
    bottleneck: str,
    target_structure: Dict[str, Any],
    coverage: Optional[Dict[str, Any]] = None,
    chat_transcript: str = "",
    mvp_focus: Optional[Dict[str, Any]] = None,
    deferred_seeds: Optional[List[str]] = None,
    dual_system_note: str = "",
    scoping_reasoning: str = "",
    clarification_answers: Optional[Dict[str, Any]] = None,
    plan_reasoning: str = "",
    closure_test: str = "",
) -> Dict[str, Any]:
    """LLM-backed workflow explanation with deterministic fallback."""
    from containers.discovery.discovery_clarification_policy import (
        clarification_context_for_explainer,
    )

    seed_doctypes = target_structure.get("seed_doctypes") or []
    deferred = deferred_seeds or target_structure.get("deferred_doctypes") or []
    discovery_context = _build_discovery_context(
        coverage=coverage,
        chat_transcript=chat_transcript,
        mvp_focus=mvp_focus,
        scoping_reasoning=scoping_reasoning,
    )
    clarification_context = clarification_context_for_explainer(clarification_answers)

    try:
        from llm_router import invoke_smart_llm

        prompt = WORKFLOW_EXPLANATION_PROMPT.format(
            f3iche=f3iche,
            industry=industry or "General",
            bottleneck=bottleneck or "Operational efficiency",
            discovery_context=discovery_context,
            dual_system_note=dual_system_note or "None",
            clarification_context=clarification_context,
            plan_reasoning=plan_reasoning or bottleneck or "See Day-1 module list.",
            closure_test=closure_test or "Day-1 modules close the stated operational loop.",
            mvp_seeds_json=json.dumps(seed_doctypes, indent=2),
            deferred_seeds_json=json.dumps(deferred, indent=2),
            target_json=json.dumps(
                {
                    "seed_doctypes": seed_doctypes,
                    "deferred_doctypes": deferred,
                    "required_doctypes": target_structure.get("required_doctypes", []),
                    "setup_steps": target_structure.get("setup_steps", [])[:20],
                },
                indent=2,
            ),
        )
        response = await invoke_smart_llm(
            [("human", prompt)],
            model_name=EXTRACT_MODEL,
            temperature=EXTRACT_TEMPERATURE,
            max_output_tokens=2500,
            response_mime_type="application/json",
        )
        explanation = _parse_llm_json(response.content)
        if not explanation.get("expected_data"):
            raise ValueError("LLM explanation missing expected_data")
        return _reconcile_expected_data(explanation, seed_doctypes)
    except Exception as exc:
        logger.warning("Workflow explanation LLM fallback: %r", exc)
        return _reconcile_expected_data(
            _fallback_explanation(
                f3iche=f3iche,
                industry=industry,
                bottleneck=bottleneck,
                seed_doctypes=seed_doctypes,
                dual_system_note=dual_system_note,
            ),
            seed_doctypes,
        )
