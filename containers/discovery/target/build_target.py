"""
Discovery target structure generation (corpus-independent).

Runs at discovery completion — before file upload. Uses F3iche templates,
bottleneck scoping, and ERPNext doctype graph only (no mapping/*.json).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from containers.discovery.mvp_scoping import scope_mvp_seeds
from containers.discovery.niche_resolver import f3iche_template_path, f3iche_template_status
from containers.discovery.target.f3iche_seeds import (
    load_f3iche_template_seeds,
    org_skeleton_from_f3iche,
    validation_rules_from_f3iche,
)

logger = logging.getLogger(__name__)

_KB_ROOT = Path(__file__).parent.parent.parent / "knowledge_base" / "erpnext"
_DOCTYPE_GRAPH_PATH = _KB_ROOT / "erpnext_doctype_graph.json"
_BASELINE_PATH = _KB_ROOT / "erpnext_deafaults_baseline.json"

def _layer_order_from_graph(setup_layers: Dict[str, Any]) -> List[str]:
    """Layer keys from graph setup_layers — single source of truth."""

    def _sort_key(key: str) -> tuple[int, str]:
        if not key.startswith("layer_"):
            return (99, key)
        rest = key[len("layer_") :]
        num_token = rest.split("_", 1)[0]
        try:
            return (int(num_token), key)
        except ValueError:
            return (99, key)

    keys = [
        key
        for key, value in setup_layers.items()
        if key.startswith("layer_") and isinstance(value, list)
    ]
    return sorted(keys, key=_sort_key)


def _layer_to_phase_from_graph(phase_mapping: Dict[str, Any]) -> Dict[str, str]:
    """Invert graph phase_mapping: layer_key → phase_id."""
    mapping: Dict[str, str] = {}
    for phase_id, layer_keys in phase_mapping.items():
        if not isinstance(layer_keys, list):
            continue
        for layer_key in layer_keys:
            mapping[str(layer_key)] = str(phase_id)
    return mapping


def _load_graph_and_baseline() -> tuple[Dict[str, Any], Dict[str, List]]:
    with open(_DOCTYPE_GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    with open(_BASELINE_PATH, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    return graph, baseline


def _resolve_prerequisites(seed_doctypes: List[str], graph: Dict[str, Any]) -> Dict[str, Any]:
    graph_dts = graph.get("doctypes", {})
    setup_layers = graph.get("setup_layers", {})
    layer_order = _layer_order_from_graph(setup_layers)

    all_required: Set[str] = set(seed_doctypes)
    queue = list(seed_doctypes)
    dependency_map: Dict[str, List[str]] = {}

    while queue:
        dt = queue.pop(0)
        dt_info = graph_dts.get(dt, {})
        raw_deps = dt_info.get("depends_on", [])
        deps = [
            d.split(" (")[0].strip()
            for d in raw_deps
            if d and not d.startswith("all ")
        ]
        dependency_map[dt] = deps
        for dep in deps:
            if dep not in all_required:
                all_required.add(dep)
                queue.append(dep)

    ordered_layers: List[Dict] = []
    seen: Set[str] = set()
    for layer_key in layer_order:
        layer_dts = setup_layers.get(layer_key, [])
        if not isinstance(layer_dts, list):
            continue
        in_layer = [dt for dt in layer_dts if dt in all_required and dt not in seen]
        if in_layer:
            ordered_layers.append({"layer": layer_key, "doctypes": in_layer})
            seen.update(in_layer)

    unlayered = [dt for dt in all_required if dt not in seen]
    if unlayered:
        unlayered.sort(
            key=lambda dt: (
                graph_dts.get(dt, {}).get("layer", 99)
                if isinstance(graph_dts.get(dt, {}).get("layer"), int)
                else 99,
                dt,
            )
        )
        ordered_layers.append({"layer": "layer_unknown", "doctypes": unlayered})

    return {
        "ordered_layers": ordered_layers,
        "dependency_map": dependency_map,
        "all_required": sorted(all_required),
    }


def _classify_against_baseline(
    all_required: List[str],
    baseline: Dict[str, List],
    graph_dts: Dict[str, Any],
    seed_doctypes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    classifications = []

    for dt in all_required:
        bv = baseline.get(dt, [])
        has_baseline = len(bv) > 0
        dt_info = graph_dts.get(dt, {})
        layer = dt_info.get("layer", -1)
        if layer in (0, 1) and not has_baseline:
            action = "auto_created_by_erpnext"
        elif has_baseline:
            action = "use_default"
        else:
            # all_required is the transitive dependency closure of the confirmed
            # seeds. A conditional module can be optional in general, but once it
            # is a dependency of a Day-1 seed it is required for this project.
            action = "must_create"

        classifications.append({
            "doctype": dt,
            "layer": layer,
            "action": action,
            "baseline_count": len(bv),
            "baseline_sample": bv[:3],
            "required_fields": dt_info.get("required_fields", []),
            "sme_relevance": dt_info.get("sme_relevance"),
        })

    classifications.sort(key=lambda x: (x["layer"] if x["layer"] >= 0 else 99, x["doctype"]))

    return {
        "must_create": [c for c in classifications if c["action"] == "must_create"],
        "use_default": [c for c in classifications if c["action"] == "use_default"],
        "auto_by_erpnext": [c for c in classifications if c["action"] == "auto_created_by_erpnext"],
        "optional_if_absent": [c for c in classifications if c["action"] == "optional_if_absent"],
        "all": classifications,
    }


def _phase_for_doctype(
    layer_key: str,
    doctype: str,
    graph_dts: Dict[str, Any],
    layer_to_phase: Dict[str, str],
) -> str:
    if layer_key != "layer_unknown":
        return layer_to_phase.get(layer_key, "phase_c_transactional")
    numeric = graph_dts.get(doctype, {}).get("layer", -1)
    if numeric in (0, 1):
        return "phase_a_config"
    if numeric in (2, 3):
        return "phase_b_master"
    if numeric == 8:
        return "phase_d_projects"
    return "phase_c_transactional"


def _build_graph_setup_steps(
    ordered_layers: List[Dict],
    classified_lookup: Dict[str, Dict],
    seed_doctypes: List[str],
    layer_to_phase: Dict[str, str],
    graph_dts: Dict[str, Any],
) -> tuple[List[Dict], Dict[str, Any]]:
    setup_steps: List[Dict] = []
    import_phases: Dict[str, Any] = {
        "phase_a_config": {"name": "Configuration Setup", "doctypes": []},
        "phase_b_master": {"name": "Master Data", "doctypes": []},
        "phase_c_transactional": {"name": "Transactional Data", "doctypes": []},
        "phase_d_projects": {"name": "Project Data", "doctypes": []},
    }
    step_num = 1

    for layer_entry in ordered_layers:
        layer_key = layer_entry["layer"]

        for dt in layer_entry["doctypes"]:
            phase_id = _phase_for_doctype(layer_key, dt, graph_dts, layer_to_phase)
            info = classified_lookup.get(dt, {})
            action = info.get("action", "must_create")

            setup_steps.append({
                "step": step_num,
                "phase": phase_id,
                "doctype": dt,
                "action": action,
                "layer": layer_key,
                "baseline_available": info.get("baseline_count", 0) > 0,
                "required_fields": info.get("required_fields", []),
            })

            import_phases[phase_id]["doctypes"].append(dt)
            step_num += 1

    return setup_steps, import_phases


async def build_discovery_target(
    *,
    f3iche: str,
    mvp_focus: Optional[Dict[str, Any]] = None,
    discovery_chat: Optional[List[Dict[str, str]]] = None,
    coverage: Optional[Dict[str, Any]] = None,
    chat_transcript: str = "",
    enhance_with_llm: bool = False,
    seed_doctypes_override: Optional[List[str]] = None,
    niche_resolution_source: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate target structure + MVP boundary after discovery chat completes."""
    logger.debug("Building discovery target | f3iche=%s", f3iche)

    template_path = f3iche_template_path(f3iche)
    template_status = f3iche_template_status(f3iche)
    f3iche_seeds, f3iche_data = load_f3iche_template_seeds(str(template_path))

    if not f3iche_seeds:
        if template_status["template_available"]:
            logger.debug("Empty seed list for %s despite template file", f3iche)
        else:
            logger.warning(
                "No F3iche template for niche %s — using minimal Day-1 seeds only",
                f3iche,
            )
        f3iche_seeds = ["Customer", "Supplier", "Item"]

    llm_enhanced_seeds: List[str] = []
    llm_reasoning = ""

    if enhance_with_llm and discovery_chat:
        llm_enhanced_seeds, llm_reasoning = await _enhance_seeds_from_discovery(
            f3iche=f3iche,
            template_seeds=f3iche_seeds,
            mvp_focus=mvp_focus,
            discovery_chat=discovery_chat,
        )
        if llm_enhanced_seeds:
            logger.debug("LLM enhanced: +%s additional doctypes", len(llm_enhanced_seeds))

    scoping = scope_mvp_seeds(
        template_seeds=f3iche_seeds,
        f3iche_id=f3iche,
        f3iche_data=f3iche_data,
        mvp_focus=mvp_focus,
        coverage=coverage,
        chat_transcript=chat_transcript,
        user_confirmed_override=seed_doctypes_override,
    )

    planner_seeds = (mvp_focus or {}).get("planner_day1_seeds") if not seed_doctypes_override else None
    if planner_seeds:
        planner_deferred = (mvp_focus or {}).get("defer_modules_mentioned") or []
        seed_doctypes = list(planner_seeds)
        deferred_doctypes = [
            d for d in f3iche_seeds if d not in seed_doctypes and d not in planner_deferred
        ] + [d for d in planner_deferred if d not in seed_doctypes]
        deferred_doctypes = list(dict.fromkeys(deferred_doctypes))
        scoping = {
            **scoping,
            "mvp_seeds": seed_doctypes,
            "deferred_seeds": deferred_doctypes,
            "scoping_mode": "planner_validated",
            "scoping_reasoning": (mvp_focus or {}).get("plan_reasoning")
            or "Day-1 scope from MVP planner + validator.",
            "dual_system_note": scoping.get("dual_system_note", ""),
        }
    else:
        seed_doctypes = scoping["mvp_seeds"]
        deferred_doctypes = scoping["deferred_seeds"]

    graph, baseline = _load_graph_and_baseline()
    graph_dts = graph.get("doctypes", {})

    resolution = _resolve_prerequisites(seed_doctypes, graph)
    all_required = resolution["all_required"]
    ordered_layers = resolution["ordered_layers"]
    layer_to_phase = _layer_to_phase_from_graph(graph.get("phase_mapping") or {})

    classified = _classify_against_baseline(
        all_required=all_required,
        baseline=baseline,
        graph_dts=graph_dts,
        seed_doctypes=seed_doctypes,
    )
    classified_lookup = {c["doctype"]: c for c in classified["all"]}

    setup_steps, import_phases = _build_graph_setup_steps(
        ordered_layers=ordered_layers,
        classified_lookup=classified_lookup,
        seed_doctypes=seed_doctypes,
        layer_to_phase=layer_to_phase,
        graph_dts=graph_dts,
    )

    validation_rules = validation_rules_from_f3iche(f3iche_data)
    org_skeleton = org_skeleton_from_f3iche(f3iche_data)

    mvp_boundary = {
        "mode": scoping["scoping_mode"],
        "f3iche": f3iche,
        "template_status": template_status,
        "org_skeleton": org_skeleton,
        "seed_doctypes": seed_doctypes,
        "deferred_doctypes": deferred_doctypes,
        "template_seeds": f3iche_seeds,
        "mvp_focus": mvp_focus or {},
        "scoping_reasoning": scoping["scoping_reasoning"],
        "dual_system_note": scoping.get("dual_system_note", ""),
        "archetype_id": scoping.get("archetype_id"),
        "archetype_source": scoping.get("archetype_source"),
        "signal_match_score": scoping.get("signal_match_score"),
        "graph_extensions": scoping.get("graph_extensions") or [],
        "niche_resolution_source": niche_resolution_source,
        "file_evidence": [],
        "llm_enhanced": bool(llm_enhanced_seeds) or scoping["scoping_mode"] == "planner_validated",
        "llm_reasoning": llm_reasoning or scoping.get("scoping_reasoning", ""),
        "plan_reasoning": (mvp_focus or {}).get("plan_reasoning"),
        "planner_validated": scoping["scoping_mode"] == "planner_validated",
        "promoted_doctypes": (mvp_focus or {}).get("promoted_doctypes") or [],
        "signal_match_candidates": scoping.get("signal_match_candidates") or [],
        "llm_archetype_id": scoping.get("llm_archetype_id"),
        "llm_archetype_signal_score": scoping.get("llm_archetype_signal_score"),
        "chosen_archetype_signal_score": scoping.get("chosen_archetype_signal_score"),
        "archetype_routing_mismatch": scoping.get("archetype_routing_mismatch", False),
        "archetype_routing_note": scoping.get("archetype_routing_note"),
        "signal_override_applied": scoping.get("signal_override_applied", False),
        "signal_override_note": scoping.get("signal_override_note"),
    }

    return {
        "f3iche": f3iche,
        "seed_doctypes": seed_doctypes,
        "required_doctypes": all_required,
        "setup_steps": setup_steps,
        "import_phases": import_phases,
        "validation_rules": validation_rules,
        "mvp_boundary": mvp_boundary,
        "deferred_doctypes": deferred_doctypes,
        "scoping": scoping,
        "graph_driven": True,
        "corpus_independent": True,
    }


async def _enhance_seeds_from_discovery(
    *,
    f3iche: str,
    template_seeds: List[str],
    mvp_focus: Optional[Dict[str, Any]],
    discovery_chat: List[Dict[str, str]],
) -> tuple[List[str], str]:
    # TODO: LLM enhancement from discovery chat (beyond f3iche template)
    return [], "LLM enhancement not yet implemented"


# Backward-compatible alias used by backend and legacy imports
build_post_discovery_target = build_discovery_target

__all__ = ["build_discovery_target", "build_post_discovery_target"]
