"""Command Planning Agent: Single-step execution plan (Phase 1 MVP)."""
import json
from typing import Any

from config import KNOWLEDGE_DIR


def _load_command_patterns() -> list:
    """Load patterns from command_patterns.json."""
    path = KNOWLEDGE_DIR / "command_patterns.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("patterns", [])


def get_execution_plan(intent: str, context: dict) -> dict[str, Any]:
    """
    Return execution plan for given intent.
    Uses command_patterns.json when available.
    """
    patterns = _load_command_patterns()
    for p in patterns:
        if p.get("pattern_id") == "create_sales_order" and intent == "create_sales_order":
            steps = p.get("steps", [])
            return {
                "plan_id": p.get("pattern_id", "create_so"),
                "steps": [{**s, "step": i + 1} for i, s in enumerate(steps)],
                "risk_level": p.get("risk_level", "low"),
                "requires_confirmation": p.get("requires_confirmation", False),
                "estimated_api_calls": len(steps),
            }
    if intent == "create_sales_order":
        return {
            "plan_id": "create_so",
            "steps": [{"step": 1, "action": "create", "doctype": "Sales Order", "depends_on": None, "rollback_if_failed": True}],
            "risk_level": "low",
            "requires_confirmation": False,
            "estimated_api_calls": 1,
        }
    return {"plan_id": "unsupported", "steps": [], "risk_level": "unknown", "requires_confirmation": False, "estimated_api_calls": 0}
