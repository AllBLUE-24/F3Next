"""Target Structure — action workflow from F3iche + doctypes graph + company profile."""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "implementation" / "knowledge"


class TargetStructureService:
    """Builds the final action workflow (target structure) for implementation."""

    def __init__(self):
        self._doctypes_graph = None
        self._f3iche_cache = {}

    def _load_doctypes_graph(self) -> Dict:
        if self._doctypes_graph is None:
            path = KNOWLEDGE_DIR / "doctypes_graph_ERPNext.json"
            with open(path, "r", encoding="utf-8") as f:
                self._doctypes_graph = json.load(f)
        return self._doctypes_graph

    def _load_f3iche(self, f3iche_id: str) -> Dict:
        if f3iche_id not in self._f3iche_cache:
            path = KNOWLEDGE_DIR / f"f3iche_{f3iche_id}.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._f3iche_cache[f3iche_id] = json.load(f)
            else:
                self._f3iche_cache[f3iche_id] = {}
        return self._f3iche_cache[f3iche_id]

    def build_target_structure(
        self,
        f3iche: str,
        industry: Optional[str] = None,
        company_profile: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Build the target structure — ordered list of setup steps and data mappings.
        """
        f3iche_data = self._load_f3iche(f3iche)
        graph = self._load_doctypes_graph()

        required_doctypes = f3iche_data.get("required_doctypes", [])
        setup_order = f3iche_data.get("setup_order", [])
        conditional = f3iche_data.get("conditional_doctypes", {})

        # Resolve conditional doctypes based on f3iche
        for dt, rule in conditional.items():
            if rule == "always" and dt not in required_doctypes:
                required_doctypes.append(dt)
            elif rule == "never" and dt in required_doctypes:
                required_doctypes.remove(dt)

        # Use setup_layers from graph for dependency order
        layers = graph.get("setup_layers", {})
        ordered_steps = []
        seen = set()

        for layer_key, doctypes in layers.items():
            for dt in doctypes:
                if dt in required_doctypes and dt not in seen:
                    ordered_steps.append({
                        "doctype": dt,
                        "layer": layer_key,
                        "phase": self._get_phase(dt, graph),
                    })
                    seen.add(dt)

        # Add any from setup_order not yet included
        for dt in setup_order:
            if dt not in seen and dt in required_doctypes:
                ordered_steps.append({
                    "doctype": dt,
                    "layer": "custom",
                    "phase": self._get_phase(dt, graph),
                })
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
        phases = graph.get("import_phases", {})
        for phase, doctypes in phases.items():
            if doctype in doctypes:
                return phase
        return "phase_b_master"
