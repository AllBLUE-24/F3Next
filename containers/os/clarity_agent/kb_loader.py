"""
containers/OS/clarity_agent/kb_loader.py

Loads knowledge base JSON files at worker startup and provides
fast in-memory lookups for the Clarity Agent.

Design:
  - Module-level singleton (loaded once per worker process, never reloaded)
  - Reads from containers/knowledge_base/common/ and knowledge_base/{erp_type}/
  - Provides typed accessors — no raw dict access in agent code
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from containers.knowledge_base.erpnext.schema.compose import compose_field_mappings

logger = logging.getLogger(__name__)

# ─── KB file paths (relative to the containers/ root) ────────────────────────

_KB_ROOT  = Path(__file__).parent.parent.parent / "knowledge_base"
_COMMON   = _KB_ROOT / "common"
_ERPNEXT  = _KB_ROOT / "erpnext"


def _load(path: Path) -> dict:
    """Load a JSON file. Returns {} on any failure."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("KB file not found: %s — using fallback", path)
        return {}
    except json.JSONDecodeError as e:
        logger.error("KB file invalid JSON: %s — %s", path, e)
        return {}


# ─── Singleton KB bundle ──────────────────────────────────────────────────────

class KnowledgeBase:
    """
    Loaded once. Accessed everywhere.
    Access via kb() module-level function.
    """

    def __init__(self) -> None:
        logger.info("Loading ERP-OS Knowledge Base...")

        # ── Load raw JSON ──────────────────────────────────────────────────
        self._intent_defs   = _load(_COMMON / "intent_definitions.json")
        self._field_maps    = compose_field_mappings()
        self._cmd_patterns  = _load(_COMMON  / "command_patterns.json")
        self._module_docs   = _load(_ERPNEXT / "docs"   / "module_docs.json")

        # ── Build fast lookup indexes ──────────────────────────────────────
        self._intent_index: dict[str, dict] = {
            i["intent_id"]: i
            for i in self._intent_defs.get("intents", [])
        }

        # synonym → intent_id  (lowercase → canonical id)
        self._synonym_index: dict[str, str] = {}
        for intent in self._intent_defs.get("intents", []):
            iid = intent["intent_id"]
            for syn in intent.get("synonyms", []):
                self._synonym_index[syn.lower()] = iid

        # Abbreviation mappings: SO → Sales Order
        self._abbreviations: dict[str, str] = self._intent_defs.get("synonym_mappings", {})

        # Ambiguity question templates
        self._ambiguity_templates: dict = self._intent_defs.get("ambiguity_resolution", {})

        # Contextual inference rules
        self._inference_rules: dict = self._intent_defs.get("contextual_inference_rules", {})

        # Confidence scoring thresholds
        self._confidence_bands: dict = self._intent_defs.get("confidence_scoring", {})

        intents_loaded = len(self._intent_index)
        synonyms_loaded = len(self._synonym_index)
        logger.info(
            "KB loaded: %d intents, %d synonyms, %d abbreviations",
            intents_loaded, synonyms_loaded, len(self._abbreviations),
        )

    # ── Intent accessors ──────────────────────────────────────────────────────

    def all_intents(self) -> list[dict]:
        return list(self._intent_index.values())

    def get_intent(self, intent_id: str) -> Optional[dict]:
        return self._intent_index.get(intent_id)

    def get_intent_by_synonym(self, text: str) -> Optional[dict]:
        iid = self._synonym_index.get(text.lower())
        return self._intent_index.get(iid) if iid else None

    def intent_ids(self) -> list[str]:
        return list(self._intent_index.keys())

    # ── Abbreviation expansion ────────────────────────────────────────────────

    def expand_abbreviation(self, abbr: str) -> str:
        """'SO' → 'Sales Order', 'PO' → 'Purchase Order', etc."""
        return self._abbreviations.get(abbr, abbr)

    def abbreviations(self) -> dict[str, str]:
        return dict(self._abbreviations)

    # ── Ambiguity questions ───────────────────────────────────────────────────

    def ambiguity_question(self, field: str) -> str:
        """Return the clarification question for a missing/ambiguous field."""
        template = self._ambiguity_templates.get(f"missing_{field}", {})
        return template.get("question", f"What is the {field.replace('_', ' ')}?")

    # ── Contextual inference ──────────────────────────────────────────────────

    def inference_rules(self, doctype_key: str) -> dict:
        """Return inference rules for a doctype (e.g. 'payment_entry')."""
        return self._inference_rules.get(doctype_key, {})

    # ── Field mappings ────────────────────────────────────────────────────────

    def field_mappings_for(self, doctype: str) -> dict:
        return self._field_maps.get("doctypes", {}).get(doctype, {})

    # ── Prompt builder helpers ────────────────────────────────────────────────

    def intent_summary_for_prompt(self) -> str:
        """
        Compact intent index for injection into the LLM system prompt.
        Format: intent_id | synonyms | required_entities | doctype
        """
        lines: list[str] = []
        for intent in self.all_intents():
            syns      = ", ".join(intent.get("synonyms", [])[:4])
            required  = ", ".join(intent.get("required_entities", []))
            optional  = ", ".join(intent.get("optional_entities", [])[:4])
            risk      = intent.get("risk_level", "low")
            lines.append(
                f"- {intent['intent_id']:40} | doc: {intent['target_doctype']:25} "
                f"| risk: {risk:8} | required: [{required}] | optional: [{optional}]\n"
                f"  synonyms: {syns}"
            )
        return "\n".join(lines)

    def abbreviation_summary_for_prompt(self) -> str:
        """'SO'=Sales Order, 'PO'=Purchase Order ..."""
        return ", ".join(f"'{k}'={v}" for k, v in self._abbreviations.items())

    def examples_for_intent(self, intent_id: str, max_examples: int = 3) -> list[str]:
        intent = self.get_intent(intent_id)
        if not intent:
            return []
        return intent.get("examples", [])[:max_examples]

    def context_hints_for_intent(self, intent_id: str) -> dict:
        intent = self.get_intent(intent_id)
        return intent.get("context_hints", {}) if intent else {}


# ─── Module-level singleton ───────────────────────────────────────────────────

_kb_instance: Optional[KnowledgeBase] = None


def kb() -> KnowledgeBase:
    """
    Return the module-level KB singleton.
    Loads on first call, cached for the process lifetime.
    """
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance