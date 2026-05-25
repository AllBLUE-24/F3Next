"""
containers/OS/context_retrieval/kb_context.py

Loads KB-02 (ERPNext Module Docs) and KB-07 (ERPNext Doctype Graph)
at worker startup and provides fast in-memory lookups for Context Retrieval.

Design:
  - Module-level singleton — loaded once per worker process
  - KB-07 (doctype_graph.json) may not exist yet → graceful fallback to KB-02 data
  - All lookups are O(1) dict access after startup
  - Accessed via context_kb() function

Used by: retrieve_context activity
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from containers.knowledge_base.erpnext.schema.compose import compose_field_mappings

logger = logging.getLogger(__name__)

_KB_ROOT   = Path(__file__).parent.parent.parent / "knowledge_base"
_ERPNEXT   = _KB_ROOT / "erpnext"
_COMMON    = _KB_ROOT / "common"


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


class ContextKnowledgeBase:
    """
    Knowledge base bundle for the Context Retrieval agent.
    Provides doctype schema, module context, and field mapping data.
    """

    def __init__(self) -> None:
        logger.info("Context Retrieval: loading knowledge base...")

        # ── KB-02: ERPNext Module Docs ─────────────────────────────────────
        self._module_docs = _load(_ERPNEXT / "docs" / "module_docs.json")

        # ── KB-04: Field Mapping Rules ─────────────────────────────────────
        # Used here to provide mandatory/optional field lists per doctype
        self._field_maps  = compose_field_mappings()

        # ── KB-07: ERPNext Doctype Graph (may not exist yet) ───────────────
        # If missing, we synthesise a basic graph from KB-02 doctype lists
        raw_graph = _load(_ERPNEXT / "schema" / "doctype_graph.json")
        if raw_graph:
            self._doctype_graph = raw_graph.get("doctypes", {})
            logger.info("KB-07 doctype_graph loaded (%d doctypes)", len(self._doctype_graph))
        else:
            self._doctype_graph = self._synthesise_graph_from_kb02()
            logger.info(
                "KB-07 not found — synthesised basic graph from KB-02 (%d doctypes)",
                len(self._doctype_graph),
            )

        # ── Build fast lookup indexes ──────────────────────────────────────
        # doctype → module name  (e.g. "Sales Order" → "Sales")
        self._doctype_to_module: dict[str, str] = {}
        for mod_name, mod in self._module_docs.get("modules", {}).items():
            for dt in mod.get("key_doctypes", []):
                self._doctype_to_module[dt["doctype"]] = mod_name

        # module name → full module dict
        self._module_index: dict[str, dict] = {
            name: data
            for name, data in self._module_docs.get("modules", {}).items()
        }

        # doctype → doctype record from KB-02 (for workflow, key_fields etc.)
        self._doctype_detail: dict[str, dict] = {}
        for mod in self._module_docs.get("modules", {}).values():
            for dt in mod.get("key_doctypes", []):
                self._doctype_detail[dt["doctype"]] = dt

        logger.info(
            "Context KB ready — %d modules, %d doctypes indexed",
            len(self._module_index),
            len(self._doctype_to_module),
        )

    # ── Graph synthesis fallback ───────────────────────────────────────────────

    def _synthesise_graph_from_kb02(self) -> dict:
        """
        If KB-07 isn't available yet, build a minimal doctype graph from KB-02.
        Provides: module, key_fields, workflow_states.
        Missing: full depends_on edges, child_tables detail — but enough for MVP.
        """
        graph: dict = {}
        for mod_name, mod in self._module_docs.get("modules", {}).items():
            for dt in mod.get("key_doctypes", []):
                doctype = dt["doctype"]
                graph[doctype] = {
                    "module":          mod_name,
                    "key_fields":      dt.get("key_fields", []),
                    "workflow_states": _parse_workflow_states(dt.get("workflow", "")),
                    "depends_on":      [],   # Cannot derive without KB-07
                    "child_tables":    {},
                    "purpose":         dt.get("purpose", ""),
                    "common_use":      dt.get("common_use", ""),
                }
        return graph

    # ── Module lookups ────────────────────────────────────────────────────────

    def module_for_doctype(self, doctype: str) -> Optional[str]:
        """e.g. 'Sales Order' → 'Sales'"""
        return self._doctype_to_module.get(doctype)

    def module_context(self, module_name: str) -> dict:
        """
        Full module dict from KB-02 for a given module name.
        Returns {} if module not found.
        """
        return self._module_index.get(module_name, {})

    def module_context_for_doctype(self, doctype: str) -> dict:
        """Convenience: get module context by doctype name."""
        module = self.module_for_doctype(doctype)
        return self.module_context(module) if module else {}

    # ── Doctype lookups ───────────────────────────────────────────────────────

    def doctype_schema(self, doctype: str) -> dict:
        """
        Combined schema entry for a doctype.
        Merges KB-07 graph entry + KB-02 key_fields + KB-04 field mappings.
        """
        graph_entry   = self._doctype_graph.get(doctype, {})
        detail_entry  = self._doctype_detail.get(doctype, {})
        field_mapping = self._field_maps.get("doctypes", {}).get(doctype, {})

        # Mandatory fields: from KB-04 (most complete) or KB-07
        mandatory_fields: list[str] = []
        if field_mapping:
            for fname, fdata in field_mapping.get("field_mappings", {}).items():
                if fdata.get("mandatory"):
                    mandatory_fields.append(fname)
        if not mandatory_fields:
            mandatory_fields = graph_entry.get("mandatory_fields", [])

        return {
            "doctype":         doctype,
            "module":          self.module_for_doctype(doctype),
            "mandatory_fields": mandatory_fields,
            "key_fields":      detail_entry.get("key_fields", graph_entry.get("key_fields", [])),
            "workflow_states": graph_entry.get("workflow_states", []),
            "depends_on":      graph_entry.get("depends_on", []),
            "child_tables":    graph_entry.get("child_tables", {}),
            "purpose":         detail_entry.get("purpose", graph_entry.get("purpose", "")),
            "field_mappings":  field_mapping.get("field_mappings", {}),  # full KB-04 data
        }

    def workflow_for_doctype(self, doctype: str) -> str:
        """e.g. 'Sales Order' → 'Draft → Submitted → Delivered → Completed'"""
        dt = self._doctype_detail.get(doctype, {})
        return dt.get("workflow", "")

    def related_doctypes(self, doctype: str) -> list[str]:
        """
        Doctypes that are commonly used alongside this one.
        Derived from: depends_on (KB-07) + same-module doctypes (KB-02).
        """
        depends_on  = self._doctype_graph.get(doctype, {}).get("depends_on", [])
        module      = self.module_for_doctype(doctype)
        same_module = [
            dt for dt, mod in self._doctype_to_module.items()
            if mod == module and dt != doctype
        ]
        # Depends_on first (most relevant), then same-module
        seen: set[str] = set()
        result: list[str] = []
        for dt in depends_on + same_module:
            if dt not in seen:
                seen.add(dt)
                result.append(dt)
        return result[:8]   # Cap at 8 to keep context bundle lean

    # ── Cross-module workflows ────────────────────────────────────────────────

    def cross_module_workflows(self) -> dict:
        return self._module_docs.get("cross_module_workflows", {})

    def india_compliance(self) -> dict:
        return self._module_docs.get("india_compliance", {})

    # ── Summary for debugging ─────────────────────────────────────────────────

    def summary(self) -> str:
        return (
            f"ContextKB: {len(self._module_index)} modules, "
            f"{len(self._doctype_to_module)} doctypes, "
            f"{len(self._doctype_graph)} graph nodes"
        )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_workflow_states(workflow_str: str) -> list[str]:
    """'Draft → Submitted → Paid' → ['Draft', 'Submitted', 'Paid']"""
    if not workflow_str:
        return []
    # Handle both → and ->
    return [s.strip() for s in workflow_str.replace("->", "→").split("→") if s.strip()]


# ── Module-level singleton ─────────────────────────────────────────────────────

_ckb_instance: Optional[ContextKnowledgeBase] = None


def context_kb() -> ContextKnowledgeBase:
    """Return the module-level KB singleton. Loaded on first call."""
    global _ckb_instance
    if _ckb_instance is None:
        _ckb_instance = ContextKnowledgeBase()
    return _ckb_instance