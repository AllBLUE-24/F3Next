"""
containers/OS/command_planner/kb_plans.py

Loads KB-03 (Command Patterns Library) at worker startup.
Provides three fast lookup indexes for the plan_builder:

  1. trigger_index   — lowercased trigger keyword → pattern dict
                       (for keyword matching against raw user prompt)
  2. intent_index    — intent_id → pattern dict
                       (for direct match: "complex_sales_cycle" → sales_cycle pattern)
  3. pattern_index   — pattern_id → pattern dict
                       (for direct retrieval by ID)

Also indexes KB-01 intent risk levels and required entities so the planner
can build single-step plans without loading KB-01 separately.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_KB_ROOT = Path(__file__).parent.parent.parent / "knowledge_base"
_COMMON  = _KB_ROOT / "common"


def _load(path: Path) -> dict:
    """Load a JSON file. Returns {} on any failure."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("KB file not found: %s — using empty dict", path)
        return {}
    except json.JSONDecodeError as e:
        logger.error("KB file invalid JSON: %s — %s", path, e)
        return {}


class PlanKnowledgeBase:
    """
    KB-03 + KB-01 subset, loaded once per worker process.
    Accessed via plans_kb() function.
    """

    def __init__(self) -> None:
        logger.info("Command Planner: loading knowledge base...")

        raw_kb03 = _load(_COMMON / "command_patterns.json")
        raw_kb01 = _load(_COMMON / "intent_definitions.json")

        patterns: list[dict] = raw_kb03.get("patterns", [])

        # ── Index 1: trigger keyword → pattern ────────────────────────────────
        # Every keyword in pattern.trigger_keywords, lowercased
        self._trigger_index: dict[str, dict] = {}
        for pattern in patterns:
            for kw in pattern.get("trigger_keywords", []):
                self._trigger_index[kw.lower()] = pattern

        # ── Index 2: intent_id → pattern ──────────────────────────────────────
        # Only for intents that map 1:1 to a pattern (complex_sales_cycle etc.)
        # We build this from KB-01 intent names + KB-03 pattern doctypes heuristically.
        # Manual mappings for known direct intent→pattern links:
        self._intent_to_pattern_id: dict[str, str] = {
            "complex_sales_cycle":     "sales_cycle_so_dn_si",
            "bulk_create_items":       "bulk_sales_orders",   # closest bulk pattern
            # Add more as needed
        }
        # Build full intent→pattern dict
        self._intent_index: dict[str, dict] = {}
        for intent_id, pattern_id in self._intent_to_pattern_id.items():
            for p in patterns:
                if p["pattern_id"] == pattern_id:
                    self._intent_index[intent_id] = p
                    break

        # ── Index 3: pattern_id → pattern ─────────────────────────────────────
        self._pattern_index: dict[str, dict] = {
            p["pattern_id"]: p for p in patterns
        }

        # ── KB-01 intent metadata (risk, required entities, action) ───────────
        self._intent_meta: dict[str, dict] = {
            i["intent_id"]: {
                "risk_level":        i.get("risk_level", "low"),
                "required_entities": i.get("required_entities", []),
                "optional_entities": i.get("optional_entities", []),
                "action":            i.get("action", "create"),
                "target_doctype":    i.get("target_doctype", ""),
                "category":          i.get("category", "create"),
            }
            for i in raw_kb01.get("intents", [])
        }

        # ── Rollback strategies ────────────────────────────────────────────────
        self._rollback_strategies: dict = raw_kb03.get("rollback_strategies", {})

        # ── Pattern matching rules ─────────────────────────────────────────────
        self._matching_rules: dict = raw_kb03.get("pattern_matching_rules", {})

        # ── Async pattern list ─────────────────────────────────────────────────
        async_cfg = raw_kb03.get("async_patterns", {})
        self._async_pattern_ids: set[str] = set(async_cfg.get("patterns", []))

        logger.info(
            "Plan KB loaded: %d patterns, %d trigger keywords, %d intent metas",
            len(self._pattern_index),
            len(self._trigger_index),
            len(self._intent_meta),
        )

    # ── Pattern lookups ───────────────────────────────────────────────────────

    def find_pattern_by_keywords(self, text: str) -> Optional[dict]:
        """
        Scan the raw prompt text for any known trigger keyword.
        Returns the first matching pattern, or None.
        Case-insensitive, full-substring match.
        """
        text_lower = text.lower()
        for keyword, pattern in self._trigger_index.items():
            if keyword in text_lower:
                return pattern
        return None

    def find_pattern_by_intent(self, intent_id: str) -> Optional[dict]:
        """Return the KB-03 pattern for a known multi-step intent_id, or None."""
        return self._intent_index.get(intent_id)

    def get_pattern(self, pattern_id: str) -> Optional[dict]:
        """Direct lookup by pattern_id."""
        return self._pattern_index.get(pattern_id)

    def all_patterns(self) -> list[dict]:
        return list(self._pattern_index.values())

    def is_async_pattern(self, pattern_id: str) -> bool:
        return pattern_id in self._async_pattern_ids

    # ── Intent metadata ───────────────────────────────────────────────────────

    def intent_meta(self, intent_id: str) -> dict:
        """
        Returns {risk_level, required_entities, optional_entities, action, target_doctype, category}
        for a given intent_id. Returns safe defaults if intent not found.
        """
        return self._intent_meta.get(intent_id, {
            "risk_level":        "low",
            "required_entities": [],
            "optional_entities": [],
            "action":            "create",
            "target_doctype":    "",
            "category":          "create",
        })

    def risk_requires_confirmation(self, risk_level: str) -> bool:
        """True if this risk level should trigger a confirmation gate."""
        return risk_level in ("high", "critical")

    # ── Rollback strategy lookup ──────────────────────────────────────────────

    def rollback_strategy_for_pattern(self, pattern: dict) -> str:
        """
        Determine rollback strategy for a pattern.
        If all steps are rollback_if_failed=True → draft_delete
        If any submitted docs involved → inform_user
        Read-only patterns → none
        """
        steps = pattern.get("steps", [])
        if not steps:
            return "none"

        has_submit = any(s.get("action") == "submit" for s in steps)
        has_rollback = any(s.get("rollback_if_failed", False) for s in steps)

        if has_submit:
            return "inform_user"   # Submitted docs can't be auto-rolled back
        if has_rollback:
            return "draft_delete"
        return "none"

    def rollback_strategy_for_single(self, action: str, category: str) -> str:
        """Rollback strategy for single-step plans."""
        if category in ("read", "search", "report"):
            return "none"
        if action in ("submit", "cancel"):
            return "inform_user"
        if action in ("create",):
            return "draft_delete"
        return "none"


# ── Module-level singleton ─────────────────────────────────────────────────────

_pkb_instance: Optional[PlanKnowledgeBase] = None


def plans_kb() -> PlanKnowledgeBase:
    """Return the module-level plan KB singleton. Loaded on first call."""
    global _pkb_instance
    if _pkb_instance is None:
        _pkb_instance = PlanKnowledgeBase()
    return _pkb_instance