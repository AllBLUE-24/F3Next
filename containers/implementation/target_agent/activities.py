"""
Target Agent — Temporal activities for building the ERPNext action workflow.

This agent is the PREREQUISITE PLANNER for the implementation workflow.
After loading seed doctypes from the company profile or f3iche template, it:
  1. Walks erpnext_doctype_graph.json to resolve ALL transitive prerequisites
  2. Orders every doctype by graph layer (layer 0 → layer 7)
  3. Cross-checks each against erpnext_deafaults_baseline.json
  4. Logs a full human-readable plan with actions (MUST CREATE / USE DEFAULT / AUTO)
  5. Produces setup_steps driven by the graph — not by LLM guesswork
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import boto3
from botocore.config import Config
from sqlalchemy import select
from temporalio import activity

from shared.database.db import AsyncSessionLocal
from shared.models.is_models import ISCompanyProfile, ISTargetStructure, ISSession
from shared.models.is_status import NodeStatusEnvelope
from containers.implementation.utils.llm_helper import generate_json

# 🚀 Importing the prompt from your clean prompts.py file!
from containers.implementation.target_agent.prompts import TARGET_STRUCTURE_PROMPT


# ─── KNOWLEDGE BASE PATHS ─────────────────────────────────────────────────────

_KB_ERP = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "erpnext"
_DOCTYPE_GRAPH_PATH   = _KB_ERP / "erpnext_doctype_graph.json"
_DEFAULTS_BASELINE_PATH = _KB_ERP / "erpnext_deafaults_baseline.json"


# ─── PREREQUISITE PLANNER ─────────────────────────────────────────────────────

def _load_doctype_graph() -> Dict[str, Any]:
    if _DOCTYPE_GRAPH_PATH.exists():
        with open(_DOCTYPE_GRAPH_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_defaults_baseline() -> Dict[str, List]:
    if _DEFAULTS_BASELINE_PATH.exists():
        with open(_DEFAULTS_BASELINE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _normalize_doctype_name(name: str) -> str:
    from containers.implementation.shared.doctype_resolver import normalize_doctype_name

    return normalize_doctype_name(name)


from containers.knowledge_base.erpnext.schema.compose import compose_field_mappings


def _load_kb_doctypes() -> Dict[str, Any]:
    return compose_field_mappings().get("doctypes", {}) or {}


def _canonicalize_doctypes(doctypes: List[str], graph: Dict[str, Any]) -> List[str]:
    from containers.implementation.shared.doctype_resolver import resolve_doctype, unique_canonical

    graph_doctypes = graph.get("doctypes", {}) if isinstance(graph, dict) else {}
    kb_doctypes = _load_kb_doctypes()

    alias_map: Dict[str, str] = {}

    def _register(alias: str, canonical: str) -> None:
        alias_key = _normalize_doctype_name(alias)
        canonical_name = str(canonical or "").strip()
        if alias_key and canonical_name and alias_key not in alias_map:
            alias_map[alias_key] = canonical_name

    for dt_name in graph_doctypes.keys():
        _register(dt_name, dt_name)

    for dt_name, dt_cfg in kb_doctypes.items():
        canonical_name = dt_cfg.get("doctype_name") or dt_name
        _register(dt_name, canonical_name)
        _register(canonical_name, canonical_name)
        for hint in dt_cfg.get("doctype_classifier_hints") or []:
            _register(hint, canonical_name)

    canonicalized: List[str] = []
    seen: Set[str] = set()
    for dt in doctypes:
        dt_name = str(dt or "").strip()
        if not dt_name:
            continue
        resolved = alias_map.get(_normalize_doctype_name(dt_name), resolve_doctype(dt_name))
        if resolved not in seen:
            seen.add(resolved)
            canonicalized.append(resolved)
    return unique_canonical(canonicalized) if not alias_map else canonicalized


_LAYER_ORDER = [
    "layer_0_system",
    "layer_1_config",
    "layer_2_masters",
    "layer_3_parties",
    "layer_4_pricing",
    "layer_5_transactions",
    "layer_6_fulfillment",
    "layer_7_finance",
    "layer_8_projects",
]

_LAYER_TO_PHASE = {
    "layer_0_system":       "phase_a_config",
    "layer_1_config":       "phase_a_config",
    "layer_2_masters":      "phase_a_config",
    "layer_3_parties":      "phase_b_master",
    "layer_4_pricing":      "phase_b_master",
    "layer_5_transactions": "phase_c_transactional",
    "layer_6_fulfillment":  "phase_c_transactional",
    "layer_7_finance":      "phase_c_transactional",
    "layer_8_projects":      "phase_d_projects",
    "layer_unknown":        "phase_c_transactional",
}


def _resolve_prerequisites(seed_doctypes: List[str], graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    BFS over the doctype dependency graph starting from the seed doctypes.
    Returns every doctype needed (including transitive prereqs) ordered by layer.
    """
    graph_dts   = graph.get("doctypes", {})
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
            action = "must_create"

        classifications.append({
            "doctype":         dt,
            "layer":           layer,
            "action":          action,
            "baseline_count":  len(bv),
            "baseline_sample": bv[:3],
            "required_fields": dt_info.get("required_fields", []),
        })

    classifications.sort(key=lambda x: (x["layer"] if x["layer"] >= 0 else 99, x["doctype"]))
    return {
        "must_create":    [c for c in classifications if c["action"] == "must_create"],
        "use_default":    [c for c in classifications if c["action"] == "use_default"],
        "auto_by_erpnext":[c for c in classifications if c["action"] == "auto_created_by_erpnext"],
        "all":            classifications,
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
        "phase_a_config":        {"name": "Configuration Setup",  "doctypes": []},
        "phase_b_master":        {"name": "Master Data",           "doctypes": []},
        "phase_c_transactional": {"name": "Transactional Data",    "doctypes": []},
        "phase_d_projects":      {"name": "Project Data",         "doctypes": []},
    }
    step_num = 1

    for layer_entry in ordered_layers:
        layer_key = layer_entry["layer"]
        phase_id  = _LAYER_TO_PHASE.get(layer_key, "phase_c_transactional")
        for dt in layer_entry["doctypes"]:
            info   = classified_lookup.get(dt, {})
            action = info.get("action", "must_create")
            setup_steps.append({
                "step":    step_num,
                "phase":   phase_id,
                "doctype": dt,
                "action":  action,          # must_create | use_default | auto_created_by_erpnext
                "is_seed": dt in seed_doctypes,
                "required_fields": info.get("required_fields", []),
            })
            import_phases[phase_id]["doctypes"].append(dt)
            step_num += 1

    return setup_steps, import_phases


def _log_prerequisite_plan(
    seed_doctypes: List[str],
    resolution: Dict[str, Any],
    classified: Dict[str, Any],
    dependency_map: Dict[str, List[str]],
) -> None:
    """Write the full prerequisite plan to activity logs."""
    L   = activity.logger
    BAR = "═" * 72
    DIV = "─" * 72
    DOT = "· " * 36

    ordered_layers = resolution["ordered_layers"]
    all_required   = resolution["all_required"]
    classified_lookup = {c["doctype"]: c for c in classified["all"]}

    L.info("")
    L.info(DOT)
    L.info("  📋  TARGET STRUCTURE — PREREQUISITE PLAN")
    L.info("        Resolving full dependency graph before building setup_steps")
    L.info(DOT)
    L.info("")

    L.info("  Seed Doctypes (from f3iche / company profile):")
    for dt in seed_doctypes:
        L.info("      → %s", dt)
    L.info("")

    # ── Layer-by-layer creation order ────────────────────────────────────────
    L.info(BAR)
    L.info("  STEP-BY-STEP PREREQUISITE CREATION ORDER  (graph-authoritative)")
    L.info(BAR)
    L.info("")

    step_num = 1
    for layer_entry in ordered_layers:
        layer_key   = layer_entry["layer"]
        layer_label = layer_key.replace("_", " ").title()
        phase_id    = _LAYER_TO_PHASE.get(layer_key, "phase_c_transactional")

        L.info("  ┌── %s  [→ %s] ──┐", layer_label, phase_id)
        for dt in layer_entry["doctypes"]:
            info   = classified_lookup.get(dt, {})
            action = info.get("action", "unknown")
            deps   = dependency_map.get(dt, [])
            is_seed = dt in seed_doctypes

            if action == "use_default":
                icon   = "🟢"
                alabel = f"USE DEFAULT  ({info.get('baseline_count', 0)} baseline values)"
            elif action == "auto_created_by_erpnext":
                icon   = "🔵"
                alabel = "AUTO-CREATED by ERPNext on Company setup"
            elif action == "must_create":
                icon   = "🔴"
                alabel = "MUST CREATE  ← needs data or seed record"
            else:
                icon   = "⚪"
                alabel = action

            tag = " [SEED]" if is_seed else " [PREREQ]"
            L.info("  │  Step %-3d  %s  %-28s %s%s", step_num, icon, dt, alabel, tag)

            if deps:
                L.info("  │            depends_on     : %s", ", ".join(deps))
            req_fields = info.get("required_fields", [])
            if req_fields and action == "must_create":
                L.info("  │            required_fields: %s", ", ".join(req_fields))
            if action == "use_default" and info.get("baseline_sample"):
                L.info("  │            baseline_sample: %s", info["baseline_sample"])

            step_num += 1

        L.info("  └%s", "─" * 60)
        L.info("")

    # ── Summary ──────────────────────────────────────────────────────────────
    L.info(BAR)
    L.info("  PREREQUISITE PLAN SUMMARY")
    L.info(BAR)
    L.info("")
    L.info("  %-38s : %d", "Seed doctypes (f3iche / profile)", len(seed_doctypes))
    L.info("  %-38s : %d", "Total required (incl. prereqs)", len(all_required))
    L.info("  %-38s : %d", "🔴 Must be explicitly created", len(classified["must_create"]))
    L.info("  %-38s : %d", "🟢 Already exist as ERPNext defaults", len(classified["use_default"]))
    L.info("  %-38s : %d", "🔵 Auto-created by ERPNext on setup", len(classified["auto_by_erpnext"]))
    L.info("")

    if classified["must_create"]:
        L.info("  🔴 MUST CREATE — need explicit records before import:")
        for c in classified["must_create"]:
            tag = " ← import file" if c["doctype"] in seed_doctypes else " ← create seed/default"
            L.info("      %-28s  required: %s%s",
                   c["doctype"],
                   ", ".join(c["required_fields"]) or "(see ERPNext docs)",
                   tag)
        L.info("")

    if classified["use_default"]:
        L.info("  🟢 USE DEFAULT — already in erpnext_deafaults_baseline.json:")
        for c in classified["use_default"]:
            L.info("      %-28s  %d values  e.g. %s",
                   c["doctype"], c["baseline_count"], c["baseline_sample"])
        L.info("")

    L.info(DOT)
    L.info("  📋  PREREQUISITE PLAN COMPLETE — setup_steps built from graph")
    L.info(DOT)
    L.info("")


# ─── DATACLASSES ──────────────────────────────────────────────────────────────

@dataclass
class BuildTargetInput:
    session_id: str
    project_id: str
    f3iche: str
    company_slug: str = "unknown"
    user_import_note: Optional[str] = None
    r2_manifest_url: Optional[str] = None


# ─── ACTIVITIES ───────────────────────────────────────────────────────────────

@activity.defn(name="build_target_structure")
async def build_target_structure(inp: BuildTargetInput) -> Any:
    """
    Step 8: Generates the Target Structure (Blueprint) for ERPNext mapping.

    Now graph-driven:
      1. Loads seed doctypes from company profile or f3iche template
      2. Walks erpnext_doctype_graph.json — resolves ALL transitive prerequisites
      3. Cross-checks against erpnext_deafaults_baseline.json
      4. Logs the full prerequisite plan (Step 8 is the PLANNER)
      5. Produces setup_steps / import_phases ordered by graph layer — not LLM
      6. LLM is still called for reasoning notes only
    """
    activity.logger.info("▶ build_target_structure started | session=%s f3iche=%s", inp.session_id, inp.f3iche)

    # 1. Fetch the enriched Company Profile and Session from DB
    profile_dict = {}
    mvp_focus = None
    try:
        async with AsyncSessionLocal() as session:
            # Profile
            stmt_prof = select(ISCompanyProfile).where(
                ISCompanyProfile.session_id == uuid.UUID(inp.session_id)
            ).order_by(ISCompanyProfile.version.desc()).limit(1)
            res_prof = await session.execute(stmt_prof)
            latest = res_prof.scalar_one_or_none()
            if latest:
                profile_dict = {
                    "industry":                latest.industry,
                    "required_modules":        latest.required_modules,
                    "required_doctypes":       latest.required_doctypes,
                    "industry_best_practices": latest.industry_best_practices,
                    "data_quality_score":      latest.data_quality_score,
                    "completeness_score":      latest.completeness_score,
                }
            
            # Session (for mvp_focus)
            stmt_sess = select(ISSession).where(ISSession.id == uuid.UUID(inp.session_id))
            res_sess = await session.execute(stmt_sess)
            sess_row = res_sess.scalar_one_or_none()
            if sess_row and sess_row.mvp_focus:
                mvp_focus = sess_row.mvp_focus
            if sess_row:
                corpus_lines: List[str] = []
                for batch in sess_row.file_batches or []:
                    if not isinstance(batch, dict):
                        continue
                    batch_files = []
                    for file_entry in batch.get("files") or []:
                        if isinstance(file_entry, dict):
                            batch_files.append(file_entry.get("file_name") or file_entry.get("name") or file_entry.get("original_filename"))
                        elif isinstance(file_entry, str):
                            batch_files.append(file_entry)
                    batch_files = [str(name) for name in batch_files if name]
                    if batch_files:
                        corpus_lines.append(f"Batch {batch.get('batch_index', '?')}: {', '.join(batch_files)}")
                if sess_row.user_import_note:
                    corpus_lines.append(f"User note: {sess_row.user_import_note}")
                if corpus_lines:
                    profile_dict["uploaded_corpus_summary"] = "\n".join(corpus_lines)

                note_lines: List[str] = []
                if sess_row.user_import_note:
                    note_lines.append(f"Initial upload: {sess_row.user_import_note}")
                for entry in sess_row.user_notes or []:
                    if isinstance(entry, dict) and entry.get("note"):
                        note_lines.append(f"{entry.get('type', 'note')}: {entry['note']}")
                if inp.user_import_note:
                    note_lines.append(f"Fixture note: {inp.user_import_note}")
                if note_lines:
                    profile_dict["user_import_note"] = "\n".join(note_lines)

        if inp.r2_manifest_url:
            try:
                s3 = boto3.client(
                    "s3",
                    endpoint_url=os.getenv("R2_ENDPOINT"),
                    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
                    config=Config(signature_version="s3v4"),
                    region_name="auto",
                )
                response = s3.get_object(Bucket="clean-data", Key=inp.r2_manifest_url)
                manifest = json.loads(response["Body"].read().decode("utf-8"))
                corpus_lines = [profile_dict.get("uploaded_corpus_summary", "").strip()] if profile_dict.get("uploaded_corpus_summary") else []
                for filename, content in (manifest.get("files") or {}).items():
                    if not content:
                        continue
                    if filename.lower().endswith((".csv", ".tsv")):
                        try:
                            import csv as _csv
                            import io as _io
                            rows = list(_csv.DictReader(_io.StringIO(content)))
                            columns = list(rows[0].keys()) if rows else []
                            corpus_lines.append(f"{filename}: {', '.join(columns[:10])}")
                        except Exception:
                            corpus_lines.append(filename)
                    else:
                        corpus_lines.append(filename)
                if corpus_lines:
                    profile_dict["uploaded_corpus_summary"] = "\n".join([line for line in corpus_lines if line])
            except Exception as e:
                activity.logger.warning("  ⚠️ Could not build uploaded corpus summary: %s", e)
    except Exception as e:
        activity.logger.error("  ❌ Failed to fetch profile/session from DB: %s", e)

    seed_doctypes: List[str] = []
    
    # ── MVP MODE: LLM Translation Node ──
    if mvp_focus and mvp_focus.get("functional_requirements"):
        activity.logger.info("  🎯 MVP mode active. Translating functional requirements: %s", mvp_focus["functional_requirements"])
        from containers.implementation.target_agent.prompts import MVP_TRANSLATION_PROMPT
        from containers.implementation.utils.llm_helper import generate_json
        
        # We can grab a little ERPNext context to help the LLM
        from containers.implementation.utils.rag_helper import rag_retrieve
        erp_context = ""
        try:
            req_str = " ".join(mvp_focus["functional_requirements"])
            chunks = await rag_retrieve(f"ERPNext {req_str} doctypes modules", "erpnext_docs", top_k=3)
            erp_context = "\n".join(chunks)
        except Exception:
            pass

        prompt = MVP_TRANSLATION_PROMPT.format(
            primary_bottleneck=mvp_focus.get("primary_bottleneck", "General Operations"),
            functional_requirements=json.dumps(mvp_focus["functional_requirements"]),
            erpnext_context=erp_context
        )
        
        try:
            translation = generate_json(prompt, temperature=0.1)
            seed_doctypes = translation.get("seed_doctypes", [])
            activity.logger.info("  ✅ MVP Translation Node output %d seed doctypes: %s", len(seed_doctypes), seed_doctypes)
        except Exception as e:
            activity.logger.warning("  ⚠️ MVP Translation failed: %s", e)
    
    # ── FALLBACK: load seed doctypes from profile or f3iche template ──
    if not seed_doctypes:
        activity.logger.info("  📋 Full mode: Falling back to f3iche template required_doctypes")
        if not profile_dict.get("required_doctypes"):
            f3iche_path = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "common" / "f3iches" / f"{inp.f3iche}.json"
            if f3iche_path.exists():
                try:
                    with open(f3iche_path, "r", encoding="utf-8") as f:
                        f3iche_data = json.load(f)
                    template_doctypes = f3iche_data.get("required_doctypes", f3iche_data.get("mandatory_doctypes", []))
                    template_modules  = f3iche_data.get("required_modules", f3iche_data.get("absolute_profile", {}).get("mandatory_modules", []))
                    if template_doctypes:
                        profile_dict["required_doctypes"] = template_doctypes
                        activity.logger.info("  📋 Loaded %d required_doctypes from f3iche template '%s'",
                                             len(template_doctypes), inp.f3iche)
                    if template_modules and not profile_dict.get("required_modules"):
                        profile_dict["required_modules"] = template_modules
                except Exception as e:
                    activity.logger.warning("  ⚠️ Could not load f3iche template: %s", e)

        seed_doctypes = profile_dict.get("required_doctypes") or []

    # ── 2. GRAPH RESOLUTION ───────────────────────────────────────────────────
    graph    = _load_doctype_graph()
    baseline = _load_defaults_baseline()
    seed_doctypes = _canonicalize_doctypes(seed_doctypes, graph)
    profile_dict["required_doctypes"] = seed_doctypes

    graph_driven          = False
    setup_steps: List[Dict]    = []
    import_phases: Dict[str, Any] = {}
    all_required_doctypes: List[str] = list(seed_doctypes)

    if graph and seed_doctypes:
        graph_driven      = True
        graph_dts         = graph.get("doctypes", {})
        resolution        = _resolve_prerequisites(seed_doctypes, graph)
        classified        = _classify_against_baseline(resolution["all_required"], baseline, graph_dts)
        classified_lookup = {c["doctype"]: c for c in classified["all"]}

        # ── 3. LOG THE FULL PREREQUISITE PLAN ────────────────────────────────
        try:
            _log_prerequisite_plan(
                seed_doctypes=seed_doctypes,
                resolution=resolution,
                classified=classified,
                dependency_map=resolution["dependency_map"],
            )
        except Exception as log_err:
            activity.logger.warning("  ⚠️ Prerequisite plan logging failed (non-fatal): %s", log_err)

        # ── 4. BUILD GRAPH-AUTHORITATIVE setup_steps & import_phases ─────────
        setup_steps, import_phases = _build_graph_setup_steps(
            ordered_layers=resolution["ordered_layers"],
            classified_lookup=classified_lookup,
            seed_doctypes=seed_doctypes,
        )
        all_required_doctypes = resolution["all_required"]
        activity.logger.info("  ✅ Graph resolution complete | total=%d steps=%d",
                             len(all_required_doctypes), len(setup_steps))
    else:
        activity.logger.warning("  ⚠️ Graph not available — falling back to seed doctypes only")

    # ── 5. LLM — reasoning annotation only, does NOT change step order ───────
    llm_reasoning = "Graph-driven: setup_steps produced from erpnext_doctype_graph.json"
    llm_enhanced  = False
    try:
        # RAG: fetch ERPNext + APQC context to guide reasoning annotation (G4)
        from containers.implementation.utils.rag_helper import rag_retrieve
        target_rag_query = (
            f"{inp.f3iche} ERPNext phase setup doctype dependencies implementation"
        )
        erp_ctx_chunks  = await rag_retrieve(target_rag_query, "erpnext_docs", top_k=5)
        apqc_ctx_chunks = await rag_retrieve(target_rag_query, "apqc_pcf",    top_k=4)
        company_ctx_chunks = await rag_retrieve(target_rag_query, f"company_{inp.project_id}", top_k=3)
        industry_ctx_chunks = await rag_retrieve(target_rag_query, f"industry_reality_{inp.f3iche}", top_k=3)

        activity.logger.info(
            "  RAG target | erpnext=%d  apqc=%d company=%d industry=%d chunks",
            len(erp_ctx_chunks), len(apqc_ctx_chunks), len(company_ctx_chunks), len(industry_ctx_chunks)
        )
        erp_ctx_str  = "\n\n".join(erp_ctx_chunks[:3])  or "No ERPNext docs retrieved."
        apqc_ctx_str = "\n\n".join(apqc_ctx_chunks[:3]) or "No APQC context retrieved."
        company_ctx_str = "\n\n".join(company_ctx_chunks[:3]) or "No Company context retrieved."
        industry_ctx_str = "\n\n".join(industry_ctx_chunks[:3]) or "No Industry context retrieved."

        prompt  = TARGET_STRUCTURE_PROMPT.format(
            company_profile=json.dumps(profile_dict, indent=2),
            uploaded_corpus_summary=profile_dict.get("uploaded_corpus_summary", "No corpus summary available."),
            user_import_note=profile_dict.get("user_import_note", ""),
            erpnext_context=erp_ctx_str,
            apqc_context=apqc_ctx_str,
            company_context=company_ctx_str,
            industry_context=industry_ctx_str,
        )
        llm_out = generate_json(prompt, temperature=0.1, max_output_tokens=2000)
        llm_reasoning = llm_out.get("llm_reasoning") or llm_reasoning
        llm_enhanced  = True
        activity.logger.info("  💬 LLM reasoning appended")
    except Exception as e:
        activity.logger.warning("  ⚠️ LLM call failed (non-fatal, graph steps already built): %s", e)


    # ── Bare fallback if graph produced nothing ───────────────────────────────
    if not setup_steps:
        activity.logger.warning("  ⚠️ No setup_steps from graph — using seed list directly")
        for i, dt in enumerate(seed_doctypes, 1):
            setup_steps.append({"step": i, "phase": "phase_a_config", "doctype": dt})
        import_phases = {"phase_a_config": {"name": "Configuration Setup", "doctypes": seed_doctypes}}

    # ── Resolve industry label ────────────────────────────────────────────────
    resolved_industry = profile_dict.get("industry")
    if not resolved_industry or resolved_industry == "Unknown":
        _f_path = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "common" / "f3iches" / f"{inp.f3iche}.json"
        if _f_path.exists():
            try:
                with open(_f_path, "r", encoding="utf-8") as _f:
                    resolved_industry = json.load(_f).get("industry", "Unknown")
            except Exception:
                resolved_industry = "Unknown"
        else:
            resolved_industry = "Unknown"

    result = {
        "f3iche":            inp.f3iche,
        "industry":          resolved_industry,
        "required_doctypes": all_required_doctypes,   # full graph-resolved list (incl. prereqs)
        "import_phases":     import_phases,
        "setup_steps":       setup_steps,             # graph-authoritative, layer-ordered
        "graph_driven":      graph_driven,
        "validation_rules":  {}
    }

    # 6. Save to R2
    r2_key = f"{inp.company_slug}/{inp.project_id}/_target/target_structure.json"
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
        s3.put_object(
            Bucket="clean-data",
            Key=r2_key,
            Body=json.dumps(result, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info("  ✅ R2 uploaded: clean-data/%s", r2_key)
    except Exception as e:
        activity.logger.error("  ❌ R2 upload failed: %s", e)

    # 7. Save to Supabase + audit
    target_id = uuid.uuid4()
    try:
        async with AsyncSessionLocal() as session:
            session.add(ISTargetStructure(
                id=target_id,
                session_id=uuid.UUID(inp.session_id),
                f3iche=inp.f3iche,
                llm_enhanced=llm_enhanced,
                llm_reasoning=llm_reasoning,
                total_doctypes=len(result.get("required_doctypes", [])),
                total_setup_steps=len(result.get("setup_steps", [])),
                required_doctypes=json.dumps(result.get("required_doctypes", [])),
                setup_steps=json.dumps(result.get("setup_steps", [])),
                import_phases=json.dumps(result.get("import_phases", {})),
                r2_path=r2_key,
            ))
            await session.commit()

        from containers.implementation.file_io.persist_audit import log_audit
        await log_audit(
            session_id=inp.session_id,
            action="target_generated",
            actor="system",
            entity_type="target_structure",
            entity_id=str(target_id),
            details={
                "f3iche":       inp.f3iche,
                "doctypes":     len(result.get("required_doctypes", [])),
                "setup_steps":  len(result.get("setup_steps", [])),
                "graph_driven": graph_driven,
                "llm_enhanced": llm_enhanced,
            },
            result="success",
        )
        activity.logger.info("  ✅ ISTargetStructure persisted.")
    except Exception as e:
        activity.logger.error("  ❌ ISTargetStructure persistence failed: %s", e)

    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    if not seed_doctypes:
        errors.append({
            "code": "NO_SEED_DOCTYPES",
            "message": "No seed doctypes found from company profile or f3iche template; target structure may be incomplete",
            "details": {"f3iche": inp.f3iche},
        })

    if not result.get("required_doctypes"):
        errors.append({"code": "EMPTY_REQUIRED_DOCTYPES", "message": "Target structure produced no required_doctypes"})

    if graph_driven is False:
        warnings.append({"code": "GRAPH_NOT_USED", "message": "Doctype graph not available; fell back to seed doctypes only"})

    activity.logger.info("✅ build_target_structure done | doctypes=%d steps=%d graph_driven=%s",
                         len(result.get("required_doctypes", [])), len(result.get("setup_steps", [])), graph_driven)

    primary = {
        "target_structure": result,
        "graph_driven": graph_driven,
        "llm_enhanced": llm_enhanced,
    }
    if errors:
        return NodeStatusEnvelope.failed(primary_result=primary, errors=errors, warnings=warnings)
    if warnings:
        return NodeStatusEnvelope.partial(primary_result=primary, warnings=warnings)
    return NodeStatusEnvelope.success(primary_result=primary)

