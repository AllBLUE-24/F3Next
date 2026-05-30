"""KB-driven document lifecycle policy for IS import."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

AutoSubmitPolicy = Literal["auto", "ask_user", "skip"]

_GRAPH_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "containers"
    / "knowledge_base"
    / "erpnext"
    / "erpnext_doctype_graph.json"
)

_LIFECYCLE_DEFAULTS: dict[str, Any] = {
    "is_submittable": False,
    "auto_submit_on_import": "skip",
    "children_requiring_submitted": [],
    "import_risk_tier": "low",
}

# Doctypes where ERPNext API rejects disabled in list queries.
DOCTYPES_WITHOUT_DISABLED_FILTER: frozenset[str] = frozenset({
    "BOM",
    "Item Group",
    "UOM",
})

# Per-doctype overrides when graph has no lifecycle block yet.
_BUILTIN_LIFECYCLE: dict[str, dict[str, Any]] = {
    "BOM": {
        "is_submittable": True,
        "auto_submit_on_import": "ask_user",
        "children_requiring_submitted": ["Work Order"],
        "import_risk_tier": "medium",
    },
    "Price List": {
        "is_submittable": True,
        "auto_submit_on_import": "ask_user",
        "import_risk_tier": "medium",
    },
    "Sales Order": {
        "is_submittable": True,
        "auto_submit_on_import": "ask_user",
        "import_risk_tier": "high",
    },
    "Purchase Order": {
        "is_submittable": True,
        "auto_submit_on_import": "ask_user",
        "import_risk_tier": "high",
    },
    "Sales Invoice": {
        "is_submittable": True,
        "auto_submit_on_import": "ask_user",
        "import_risk_tier": "high",
    },
    "Purchase Invoice": {
        "is_submittable": True,
        "auto_submit_on_import": "ask_user",
        "import_risk_tier": "high",
    },
    "Payment Entry": {
        "is_submittable": True,
        "auto_submit_on_import": "ask_user",
        "import_risk_tier": "high",
    },
    "Stock Entry": {
        "is_submittable": True,
        "auto_submit_on_import": "ask_user",
        "import_risk_tier": "high",
    },
    "Purchase Receipt": {
        "is_submittable": True,
        "auto_submit_on_import": "ask_user",
        "import_risk_tier": "high",
    },
    "Journal Entry": {
        "is_submittable": True,
        "auto_submit_on_import": "ask_user",
        "import_risk_tier": "high",
    },
    "Work Order": {
        "is_submittable": True,
        "auto_submit_on_import": "skip",
        "import_risk_tier": "medium",
    },
}


@lru_cache(maxsize=1)
def _load_graph() -> dict[str, Any]:
    if not _GRAPH_PATH.exists():
        return {}
    with open(_GRAPH_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_lifecycle_config(doctype: str) -> dict[str, Any]:
    """Return merged lifecycle config for a doctype."""
    cfg = dict(_LIFECYCLE_DEFAULTS)
    graph = _load_graph()
    doctype_cfg = (graph.get("doctypes") or {}).get(doctype) or {}
    lifecycle = doctype_cfg.get("lifecycle") or {}
    cfg.update(lifecycle)
    if doctype in _BUILTIN_LIFECYCLE:
        for key, val in _BUILTIN_LIFECYCLE[doctype].items():
            if key not in lifecycle:
                cfg[key] = val
    return cfg


def should_auto_submit_on_import(
    doctype: str,
    override: bool | None = None,
    *,
    commit_confidence: float = 1.0,
    phase_child_doctypes: set[str] | None = None,
    execution_confirmed: bool = False,
) -> bool:
    """True when import should submit immediately after create."""
    from shared.erp_policies.submit_gate import should_submit_after_create

    return should_submit_after_create(
        doctype,
        context="import",
        commit_confidence=commit_confidence,
        phase_child_doctypes=phase_child_doctypes,
        execution_confirmed=execution_confirmed,
        override=override,
    )


def is_submittable(doctype: str) -> bool:
    return bool(get_lifecycle_config(doctype).get("is_submittable"))


def children_requiring_submitted(doctype: str) -> list[str]:
    return list(get_lifecycle_config(doctype).get("children_requiring_submitted") or [])
