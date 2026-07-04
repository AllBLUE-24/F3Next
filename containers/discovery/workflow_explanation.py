"""Generate plain-language workflow explanation for Discovery Assistant Step 1."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from containers.discovery.prompts import WORKFLOW_EXPLANATION_PROMPT

EXTRACT_MODEL = "gpt-4o-mini"
EXTRACT_TEMPERATURE = 0.1


def _parse_llm_json(content: str) -> dict:
    start_idx = content.find("{")
    end_idx = content.rfind("}")
    if start_idx != -1 and end_idx != -1:
        clean_json = content[start_idx : end_idx + 1]
    else:
        clean_json = content.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)


def _fallback_explanation(
    *,
    f3iche: str,
    industry: str,
    bottleneck: str,
    seed_doctypes: List[str],
) -> Dict[str, Any]:
    """Deterministic fallback when LLM is unavailable."""
    expected_data = []
    for dt in seed_doctypes[:12]:
        friendly = dt.replace("_", " ")
        slug = dt.lower().replace(" ", "_")
        expected_data.append({
            "doctype": dt,
            "user_friendly_name": friendly,
            "description": f"Data for {friendly} in your ERP setup",
            "example_files": [f"{slug}.csv", f"{slug}_list.xlsx"],
        })

    upload_checklist = [
        f"Upload a file for {item['user_friendly_name']}" for item in expected_data[:6]
    ]

    return {
        "workflow_summary": (
            f"We will configure ERPNext for your {industry or 'business'} operations "
            f"({f3iche.replace('_', ' ')}), focused on {bottleneck or 'your main bottleneck'}."
        ),
        "business_flow_explanation": (
            "We start with master data (customers, items, suppliers), then move to "
            "orders, production, and inventory so your team can run day-to-day work in one system."
        ),
        "expected_data": expected_data,
        "setup_phases": [
            {
                "phase": "Phase 1",
                "name": "Master data",
                "description": "Core records that other documents link to",
                "doctypes": [d for d in seed_doctypes if d in ("Customer", "Supplier", "Item", "Warehouse")][:4],
            },
            {
                "phase": "Phase 2",
                "name": "Operations",
                "description": "Orders, production, and stock movement",
                "doctypes": [d for d in seed_doctypes if d not in ("Customer", "Supplier", "Item", "Warehouse")][:6],
            },
        ],
        "upload_checklist": upload_checklist,
    }


async def generate_workflow_explanation(
    *,
    f3iche: str,
    industry: str,
    bottleneck: str,
    target_structure: Dict[str, Any],
) -> Dict[str, Any]:
    """LLM-backed workflow explanation with deterministic fallback."""
    seed_doctypes = target_structure.get("seed_doctypes") or []
    try:
        from llm_router import invoke_smart_llm

        prompt = WORKFLOW_EXPLANATION_PROMPT.format(
            f3iche=f3iche,
            industry=industry or "General",
            bottleneck=bottleneck or "Operational efficiency",
            target_json=json.dumps(
                {
                    "seed_doctypes": seed_doctypes,
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
            max_output_tokens=2000,
            response_mime_type="application/json",
        )
        explanation = _parse_llm_json(response.content)
        if not explanation.get("expected_data"):
            raise ValueError("LLM explanation missing expected_data")
        return explanation
    except Exception as exc:
        print(f"⚠️ Workflow explanation LLM fallback: {exc!r}")
        return _fallback_explanation(
            f3iche=f3iche,
            industry=industry,
            bottleneck=bottleneck,
            seed_doctypes=seed_doctypes,
        )
