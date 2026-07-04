"""
Post-Discovery Target Structure Generation (Corpus-Independent)

This module generates target structure immediately after discovery completion,
BEFORE file upload. It uses only f3iche templates and optional LLM enhancement
from discovery chat context.

Key Differences from legacy build_target_structure:
- NO corpus_understanding dependency
- NO defer_without_evidence logic
- NO seeds_from_corpus logic
- Uses f3iche template as single source of truth
- Optional LLM enhancement from discovery chat to add company-specific doctypes
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from containers.implementation.target_agent.mvp_boundary import (
    load_f3iche_template_seeds,
    merge_seed_sources,
    validation_rules_from_f3iche,
)
from containers.discovery.mvp_scoping import scope_mvp_seeds

logger = logging.getLogger(__name__)

# Knowledge base paths
_KB_ROOT = Path(__file__).parent.parent.parent / "knowledge_base" / "erpnext"
_DOCTYPE_GRAPH_PATH = _KB_ROOT / "erpnext_doctype_graph.json"
_BASELINE_PATH = _KB_ROOT / "erpnext_deafaults_baseline.json"
_F3ICHE_DIR = Path(__file__).parent.parent.parent / "knowledge_base" / "common" / "f3iches"

# Layer ordering for setup steps
_LAYER_ORDER = [
    "layer_0_system", "layer_1_config", "layer_2_org",
    "layer_3_master", "layer_4_master_extended",
    "layer_5_transaction", "layer_6_projects",
]

_LAYER_TO_PHASE = {
    "layer_0_system": "phase_a_config",
    "layer_1_config": "phase_a_config",
    "layer_2_org": "phase_a_config",
    "layer_3_master": "phase_b_master",
    "layer_4_master_extended": "phase_b_master",
    "layer_5_transaction": "phase_c_transactional",
    "layer_6_projects": "phase_d_projects",
}


def _get_f3iche_template_path(f3iche: str) -> Path:
    """Resolve f3iche ID to template JSON under common/f3iches/."""
    from containers.discovery.f3iche_resolver import f3iche_template_path

    return f3iche_template_path(f3iche)


def _load_graph_and_baseline() -> tuple[Dict[str, Any], Dict[str, List]]:
    """Load static knowledge base files."""
    with open(_DOCTYPE_GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    with open(_BASELINE_PATH, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    
    return graph, baseline


def _resolve_prerequisites(seed_doctypes: List[str], graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    BFS over the doctype dependency graph starting from the seed doctypes.
    Returns every doctype needed (including transitive prereqs) ordered by layer.
    """
    from typing import Set
    
    graph_dts = graph.get("doctypes", {})
    setup_layers = graph.get("setup_layers", {})

    all_required: Set[str] = set(seed_doctypes)
    queue = list(seed_doctypes)
    dependency_map: Dict[str, List[str]] = {}

    while queue:
        dt = queue.pop(0)
        dt_info = graph_dts.get(dt, {})
        raw_deps = dt_info.get("depends_on", [])
        # Strip parenthetical notes e.g. "Item (template)" → "Item"
        deps = [d.split(" (")[0].strip() for d in raw_deps
                if d and not d.startswith("all ")]
        dependency_map[dt] = deps
        for dep in deps:
            if dep not in all_required:
                all_required.add(dep)
                queue.append(dep)

    # Order by layer
    ordered_layers: List[Dict] = []
    seen: Set[str] = set()
    for layer_key in _LAYER_ORDER:
        layer_dts = setup_layers.get(layer_key, [])
        in_layer = [dt for dt in layer_dts if dt in all_required and dt not in seen]
        if in_layer:
            ordered_layers.append({"layer": layer_key, "doctypes": in_layer})
            seen.update(in_layer)

    unlayered = [dt for dt in all_required if dt not in seen]
    if unlayered:
        ordered_layers.append({"layer": "layer_unknown", "doctypes": sorted(unlayered)})

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
    """Classify doctypes based on baseline data and graph metadata."""
    seed_set = set(seed_doctypes or [])
    classifications = []
    
    for dt in all_required:
        bv = baseline.get(dt, [])
        has_baseline = len(bv) > 0
        dt_info = graph_dts.get(dt, {})
        layer = dt_info.get("layer", -1)
        sme = str(dt_info.get("sme_relevance") or "").lower()
        is_conditional = sme.startswith("conditional")

        if layer in (0, 1) and not has_baseline:
            action = "auto_created_by_erpnext"
        elif has_baseline:
            action = "use_default"
        elif is_conditional and dt not in seed_set:
            # Graph dependency but not in user's scope — optional
            action = "optional_if_absent"
        else:
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


def _build_graph_setup_steps(
    ordered_layers: List[Dict],
    classified_lookup: Dict[str, Dict],
    seed_doctypes: List[str],
) -> tuple[List[Dict], Dict[str, Any]]:
    """
    Build the authoritative setup_steps list from graph layer order.
    Returns (setup_steps, import_phases).
    """
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
        phase_id = _LAYER_TO_PHASE.get(layer_key, "phase_c_transactional")
        
        for dt in layer_entry["doctypes"]:
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


async def build_post_discovery_target(
    *,
    f3iche: str,
    mvp_focus: Optional[Dict[str, Any]] = None,
    discovery_chat: Optional[List[Dict[str, str]]] = None,
    coverage: Optional[Dict[str, Any]] = None,
    chat_transcript: str = "",
    enhance_with_llm: bool = False,
    seed_doctypes_override: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate target structure post-discovery, before file upload.
    
    Args:
        f3iche: Business classification (e.g., "process_mfg_batch", "trading")
        mvp_focus: Optional dict with primary_bottleneck and functional_requirements
        discovery_chat: Optional full discovery chat transcript for LLM enhancement
        enhance_with_llm: If True, use LLM to extract company-specific doctype needs
    
    Returns:
        Dict with:
            - seed_doctypes: MVP seed doctypes from f3iche template
            - required_doctypes: All doctypes (seeds + transitive prereqs)
            - setup_steps: Ordered list of setup actions
            - import_phases: Doctypes grouped by import phase
            - validation_rules: F3iche-specific validation requirements
            - mvp_boundary: MVP definition
            - deferred_doctypes: Empty list (no corpus-based deferral)
    """
    logger.debug("Building post-discovery target | f3iche=%s", f3iche)
    
    # 1. Load f3iche template seeds
    template_path = _get_f3iche_template_path(f3iche)
    f3iche_seeds, f3iche_data = load_f3iche_template_seeds(str(template_path))
    
    if not f3iche_seeds:
        # Fallback to minimal defaults
        f3iche_seeds = ["Customer", "Supplier", "Item"]
        logger.debug("No template found for %s, using minimal defaults", f3iche)

    logger.debug("F3iche template seeds: %s doctypes", len(f3iche_seeds))
    
    # 2. Optional: Enhance with LLM reading discovery chat
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
    
    # 3. Bottleneck-driven MVP scoping (Day-1 seeds vs deferred)
    scoping = scope_mvp_seeds(
        template_seeds=f3iche_seeds,
        f3iche_data=f3iche_data,
        mvp_focus=mvp_focus,
        coverage=coverage,
        chat_transcript=chat_transcript,
        user_confirmed_override=seed_doctypes_override,
    )
    seed_doctypes = scoping["mvp_seeds"]
    deferred_doctypes = scoping["deferred_seeds"]
    logger.debug(
        "MVP scoped | mode=%s day1=%s deferred=%s",
        scoping["scoping_mode"],
        len(seed_doctypes),
        len(deferred_doctypes),
    )
    
    # 4. Load graph and baseline
    graph, baseline = _load_graph_and_baseline()
    graph_dts = graph.get("doctypes", {})
    
    # 5. Walk graph to resolve ALL prerequisites
    resolution = _resolve_prerequisites(seed_doctypes, graph)
    all_required = resolution["all_required"]
    ordered_layers = resolution["ordered_layers"]
    
    logger.debug("Graph walk: %s total doctypes (seeds + prereqs)", len(all_required))
    
    # 6. Classify doctypes against baseline
    classified = _classify_against_baseline(
        all_required=all_required,
        baseline=baseline,
        graph_dts=graph_dts,
        seed_doctypes=seed_doctypes,
    )
    
    classified_lookup = {c["doctype"]: c for c in classified["all"]}
    
    # 7. Build setup steps and import phases
    setup_steps, import_phases = _build_graph_setup_steps(
        ordered_layers=ordered_layers,
        classified_lookup=classified_lookup,
        seed_doctypes=seed_doctypes,
    )
    
    # 8. Validation rules from f3iche
    validation_rules = validation_rules_from_f3iche(f3iche_data)
    
    # 9. Build MVP boundary
    mvp_boundary = {
        "mode": scoping["scoping_mode"],
        "f3iche": f3iche,
        "seed_doctypes": seed_doctypes,
        "deferred_doctypes": deferred_doctypes,
        "template_seeds": f3iche_seeds,
        "mvp_focus": mvp_focus or {},
        "scoping_reasoning": scoping["scoping_reasoning"],
        "dual_system_note": scoping.get("dual_system_note", ""),
        "file_evidence": [],
        "llm_enhanced": bool(llm_enhanced_seeds),
        "llm_reasoning": llm_reasoning,
    }
    
    # 10. Assemble final structure
    result = {
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
        "corpus_independent": True,  # Flag for monitoring
    }
    
    logger.debug(
        "Target structure complete: %s seeds → %s total doctypes",
        len(seed_doctypes),
        len(all_required),
    )
    
    return result


async def _enhance_seeds_from_discovery(
    *,
    f3iche: str,
    template_seeds: List[str],
    mvp_focus: Optional[Dict[str, Any]],
    discovery_chat: List[Dict[str, str]],
) -> tuple[List[str], str]:
    """
    Use LLM to extract company-specific doctype needs from discovery chat.
    
    This is optional enhancement beyond the f3iche template.
    """
    # TODO: Implement LLM enhancement layer
    # For now, return empty (rely on f3iche template only)
    return [], "LLM enhancement not yet implemented"


# Export for external use
__all__ = ["build_post_discovery_target"]
