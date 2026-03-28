"""
Target Agent — Temporal activities for building the ERPNext action workflow.
Moved from: backend/app/services/implementation/target_structure.py
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from temporalio import activity

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge"


# ── Embedded service logic ────────────────────────────────────────────────────

class _TargetStructureService:
    def __init__(self):
        self._doctypes_graph: Optional[Dict] = None
        self._f3iche_cache: Dict[str, Dict] = {}

    def _load_graph(self) -> Dict:
        if self._doctypes_graph is None:
            with open(KNOWLEDGE_DIR / "doctypes_graph_ERPNext.json", "r", encoding="utf-8") as f:
                self._doctypes_graph = json.load(f)
        return self._doctypes_graph

    def _load_f3iche(self, f3iche_id: str) -> Dict:
        if f3iche_id not in self._f3iche_cache:
            path = KNOWLEDGE_DIR / f"f3iche_{f3iche_id}.json"
            self._f3iche_cache[f3iche_id] = json.load(open(path, "r", encoding="utf-8")) if path.exists() else {}
        return self._f3iche_cache[f3iche_id]

    def build(self, f3iche: str, industry: Optional[str] = None) -> Dict[str, Any]:
        f3iche_data = self._load_f3iche(f3iche)
        graph = self._load_graph()

        required_doctypes: List[str] = list(f3iche_data.get("required_doctypes", []))
        setup_order: List[str] = f3iche_data.get("setup_order", [])

        # Resolve conditional doctypes
        for dt, rule in f3iche_data.get("conditional_doctypes", {}).items():
            if rule == "always" and dt not in required_doctypes:
                required_doctypes.append(dt)
            elif rule == "never" and dt in required_doctypes:
                required_doctypes.remove(dt)

        # Order by dependency layers from the graph
        layers = graph.get("setup_layers", {})
        ordered_steps: List[Dict] = []
        seen: set = set()

        for layer_key, doctypes in layers.items():
            for dt in doctypes:
                if dt in required_doctypes and dt not in seen:
                    ordered_steps.append({"doctype": dt, "layer": layer_key, "phase": self._get_phase(dt, graph)})
                    seen.add(dt)

        for dt in setup_order:
            if dt not in seen and dt in required_doctypes:
                ordered_steps.append({"doctype": dt, "layer": "custom", "phase": self._get_phase(dt, graph)})
                seen.add(dt)

        return {
            "f3iche": f3iche,
            "industry": industry,
            "required_doctypes": required_doctypes,
            "setup_steps": ordered_steps,
            "import_phases": graph.get("import_phases", {}),
            "validation_rules": f3iche_data.get("validation_rules", {}),
        }

    def _get_phase(self, doctype: str, graph: Dict) -> str:
        for phase, doctypes in graph.get("import_phases", {}).items():
            if doctype in doctypes:
                return phase
        return "phase_b_master"


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class BuildTargetStructureInput:
    f3iche: str
    industry: Optional[str] = None


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="build_target_structure")
async def build_target_structure(inp: BuildTargetStructureInput) -> Dict[str, Any]:
    """
    Build the ordered ERPNext setup plan (doctype list, phases, validation rules)
    for the given F3iche and industry.
    """
    svc = _TargetStructureService()
    return svc.build(inp.f3iche, inp.industry)