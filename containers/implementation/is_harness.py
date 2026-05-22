"""
IS Step Harness — Dev/Test Individual Steps Without Full Workflow

Run any single IS activity function in isolation.
No Temporal worker. No Docker spin-up. No signal chain. Just .env + one step.

Usage:
    python -m containers.implementation.is_harness --step <step_name> [OPTIONS]

Options:
    --step          Required. Name of the activity to run (see list below).
    --fixture       Path to a JSON input file. Defaults to dev_fixtures/<step>.json.
    --phase         For execute_import_phase only: which phase to run.
                    One of: phase_a_config | phase_b_master | phase_c_transactional
    --mock-llm      Stub all LLM calls with a canned no-op response (saves tokens).
    --dry-run       Forward dry_run=True to execute_import_phase (no ERPNext writes).
    --output        Path to write JSON result to (default: stdout).

Steps available:
    virus_scan_quarantine
    fetch_clean_files
    infer_f3iche
    verify_f3iche
    align_discovery_and_signals
    retrieve_industry_knowledge
    build_company_profile
    enrich_company_profile
    merge_company_profile
    build_target_structure
    derive_required_records       ← NEW (Plan Step 8b)
    assess_data_readiness         ← NEW (Plan Step 8c)
    supervise_step                ← NEW (Supervisor Agent)
    apply_supervisor_actions      ← NEW (Supervisor Agent)
    map_file_to_erpnext
    refine_mapping_with_llm
    validate_mapped_data
    build_import_plan
    execute_import_phase

Examples:
    # Test the import plan builder (no LLM, just DB reads):
    python -m containers.implementation.is_harness --step build_import_plan

    # Dry-run Phase A without touching ERPNext:
    python -m containers.implementation.is_harness --step execute_import_phase --phase phase_a_config --dry-run

    # Test target structure without burning Gemini tokens:
    python -m containers.implementation.is_harness --step build_target_structure --mock-llm

    # Test Phase A against a real ERPNext sandbox:
    python -m containers.implementation.is_harness --step execute_import_phase --phase phase_a_config
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import types
import unittest.mock
from pathlib import Path
from typing import Any, Dict, Optional

# ── Load .env before any shared/db imports ────────────────────────────────────
_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / ".env")

# ── Fixtures directory ────────────────────────────────────────────────────────
_FIXTURES_DIR = Path(__file__).resolve().parent / "dev_fixtures"


# ══════════════════════════════════════════════════════════════════════════════
# Fake Temporal activity context
# The activity.logger, activity.info() etc. all crash outside a real worker.
# We install a lightweight substitute so production code runs unchanged.
# ══════════════════════════════════════════════════════════════════════════════

def _install_fake_activity_context() -> None:
    """Patch temporalio.activity so activity.logger works outside a worker."""
    try:
        import temporalio.activity as _ta

        _log = logging.getLogger("is_harness.activity")

        class _FakeActivity:
            logger = _log

            @staticmethod
            def info(msg, *args):
                _log.info(msg, *args)

            @staticmethod
            def heartbeat(*args, **kwargs):
                pass

            @staticmethod
            def defn(*args, **kwargs):
                """Mock the @activity.defn decorator so imports don't crash."""
                def decorator(func):
                    return func
                if len(args) == 1 and callable(args[0]):
                    return args[0]
                return decorator

        # Replace the module-level 'activity' that all agents import
        sys.modules["temporalio.activity"] = _FakeActivity  # type: ignore
        # Also patch the already-imported reference inside each activities module
        import temporalio
        temporalio.activity = _FakeActivity  # type: ignore

    except ImportError:
        pass  # temporalio not installed — user running outside venv, skip


# ══════════════════════════════════════════════════════════════════════════════
# Mock LLM router
# When --mock-llm is set, replace generate_json / key_pool with stubs so we
# never hit Gemini.
# ══════════════════════════════════════════════════════════════════════════════

_LLM_MOCK_RESPONSES: Dict[str, Any] = {
    "infer_f3iche":        {"f3iche": "manufacturing_project_chemical", "confidence": 0.85, "collected_signals": ["[MOCK] batch tickets", "[MOCK] warehouse"]},
    "build_target":        {"required_doctypes": ["Item", "Customer", "BOM", "Work Order"], "setup_steps": [], "llm_reasoning": "[MOCK]"},
    "map_columns":         {"doctype": "Item", "field_mapping": {"Name": "item_code"}},
    "map_file":            {"doctype": "Item", "field_mapping": {}, "rows": []},
    "build_profile":       {"business_reality": "[MOCK] Chemical manufacturer", "context_flags": [], "data_quality_score": "High", "llm_confidence": 1.0},
    "refine_mapping":      {"updated_mappings": [], "removed_mappings": [], "changes_count": 0},
    "align_discovery":     {"alignment_score": 0.9, "mismatches": [], "recommended_f3iche": "manufacturing_project_chemical", "reasoning": "[MOCK]"},
    "industry_knowledge":  {"industry_differentiators": ["[MOCK] Batch tracking", "[MOCK] QC protocols"], "industry_best_practices": {}},
    "enrich_profile":      {"data_quality_score": 0.8, "completeness_score": 0.75, "data_observations": ["[MOCK] batch data present"], "recommended_customizations": []},
    "data_readiness":      {
        "ready_doctypes": [
            {"doctype": "Item", "source_file": "items.csv", "coverage_pct": 0.9, "mapped_fields": ["item_code"], "missing_optional_fields": []},
        ],
        "partial_doctypes": [
            {
                "doctype": "Work Order",
                "criticality": "critical",
                "reason": "[MOCK] Missing bom_no and required routing fields.",
                "missing_fields": ["bom_no", "workstation"],
                "recommendation": "Upload BOM and routing data before import.",
                "can_proceed_without": False,
            }
        ],
        "missing_doctypes": [
            {
                "doctype": "BOM",
                "criticality": "critical",
                "reason": "[MOCK] No BOM file detected.",
                "missing_fields": ["items", "quantity"],
                "recommendation": "Upload a BOM export.",
                "can_proceed_without": False,
            }
        ],
        "unmappable_chunks": [
            {"filename": "notes.txt", "description": "[MOCK] Freeform notes", "reason": "No ERPNext doctype matched."}
        ],
        "gap_report": {"summary": {"raw_readiness_score": 0.25}},
        "minimum_viable_import_possible": False,
        "user_action_required": True,
        "questions_for_user": [
            {
                "id": "upload_bom_data",
                "doctype": "BOM",
                "question": "BOM data is missing. Upload BOM files now?",
                "options": ["Upload Missing Files", "Proceed with Partial Data", "Skip These Doctypes"],
                "is_blocking": True,
            }
        ],
        "executive_summary": "[MOCK] Readiness is low; BOM and Work Order data are missing.",
        "import_readiness_score": 0.25,
        "user_decision": None,
    },
    "supervise_step":      {"actions": [], "summary_for_ui": "[MOCK] No issues detected.", "final_status": "resolved"},
    "generic":             {"status": "mock_ok", "result": "[MOCK LLM RESPONSE]"},
}


def _install_mock_llm() -> None:
    """Stub generate_json and the key_pool so no real LLM calls are made."""
    log = logging.getLogger("is_harness.mock_llm")

    def _mock_generate_json(prompt: str, **kwargs) -> Dict:
        # Pick the most relevant canned response based on prompt keywords
        prompt_lower = prompt.lower()
        if "f3iche" in prompt_lower and "infer" in prompt_lower:
            resp = _LLM_MOCK_RESPONSES["infer_f3iche"]
        elif "target" in prompt_lower or "setup_steps" in prompt_lower:
            resp = _LLM_MOCK_RESPONSES["build_target"]
        elif "map" in prompt_lower and "columns" in prompt_lower:
            resp = _LLM_MOCK_RESPONSES["map_columns"]
        elif "map" in prompt_lower and ("file" in prompt_lower or "doctype" in prompt_lower):
            resp = _LLM_MOCK_RESPONSES["map_file"]
        elif "profile" in prompt_lower and "business" in prompt_lower:
            resp = _LLM_MOCK_RESPONSES["build_profile"]
        elif "refine" in prompt_lower or "feedback" in prompt_lower:
            resp = _LLM_MOCK_RESPONSES["refine_mapping"]
        elif "alignment" in prompt_lower or "discovery" in prompt_lower:
            resp = _LLM_MOCK_RESPONSES["align_discovery"]
        elif "industry" in prompt_lower and "knowledge" in prompt_lower:
            resp = _LLM_MOCK_RESPONSES["industry_knowledge"]
        elif "enrich" in prompt_lower or "quality" in prompt_lower:
            resp = _LLM_MOCK_RESPONSES["enrich_profile"]
        else:
            resp = _LLM_MOCK_RESPONSES["generic"]
        log.info("  🤖 [MOCK LLM] returning canned response (skipping Gemini)")
        return resp

    async def _mock_generate_typed(*, prompt: str, schema, **kwargs) -> Dict:
        prompt_lower = prompt.lower()
        schema_name = getattr(schema, "__name__", "")
        if "data readiness analyst" in prompt_lower or schema_name == "DataReadinessAssessment":
            resp = _LLM_MOCK_RESPONSES["data_readiness"]
        else:
            resp = _LLM_MOCK_RESPONSES["generic"]
        log.info("  🤖 [MOCK LLM] returning structured canned response")
        return resp

    # Patch the shared llm_helper module
    try:
        import containers.implementation.utils.llm_helper as _lh
        _lh.generate_json = _mock_generate_json
    except ImportError:
        pass

    try:
        import shared.structured_llm as _sl
        _sl.generate_typed = _mock_generate_typed
    except ImportError:
        pass

    # Patch llm_router key_pool (used by retrieve_industry_knowledge)
    try:
        import llm_router as _lr
        _lr.key_pool = iter(["MOCK_KEY"] * 1000)
        _lr.invoke_structured_llm = _mock_generate_typed
    except ImportError:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# Step dispatcher
# Maps step name → (coroutine_fn, fixture_file_name)
# Each entry returns (activity_fn, fixture_name).
# The fixture is loaded and destructured into the activity's input dataclass.
# ══════════════════════════════════════════════════════════════════════════════

async def _run_step(step: str, fixture: Dict, phase: Optional[str], dry_run: bool) -> Any:
    """Dispatch to the right activity function with the right input object."""

    # Strip metadata/comment keys (e.g. "_comment") so they don't leak into
    # dataclass constructors. All fixture annotation keys must start with "_".
    fixture = {k: v for k, v in fixture.items() if not k.startswith("_")}

    # ── virus_scan_quarantine ─────────────────────────────────────────────────
    if step == "virus_scan_quarantine":
        from containers.implementation.virus_scan_agent.activities import virus_scan_quarantine
        return await virus_scan_quarantine(
            files=fixture["uploaded_files"],
            session_id=fixture["session_id"],
        )

    # ── fetch_clean_files ─────────────────────────────────────────────────────
    elif step == "fetch_clean_files":
        from containers.implementation.file_io.fetch_clean_files import fetch_clean_files, FetchCleanFilesInput
        return await fetch_clean_files(FetchCleanFilesInput(**fixture))

    # ── infer_f3iche ──────────────────────────────────────────────────────────
    elif step == "infer_f3iche":
        from containers.implementation.signals_agent.activities import infer_f3iche, InferF3icheInput
        return await infer_f3iche(InferF3icheInput(**fixture))

    # ── verify_f3iche ─────────────────────────────────────────────────────────
    elif step == "verify_f3iche":
        from containers.implementation.signals_agent.activities import verify_f3iche, VerifyF3icheInput
        return await verify_f3iche(VerifyF3icheInput(**fixture))

    # ── align_discovery_and_signals ───────────────────────────────────────────
    elif step == "align_discovery_and_signals":
        from containers.implementation.profile_agent.activities import align_discovery_and_signals, AlignDiscoverySignalsInput
        return await align_discovery_and_signals(AlignDiscoverySignalsInput(**fixture))

    # ── retrieve_industry_knowledge ───────────────────────────────────────────
    elif step == "retrieve_industry_knowledge":
        from containers.implementation.profile_agent.activities import retrieve_industry_knowledge, RetrieveIndustryKnowledgeInput
        return await retrieve_industry_knowledge(RetrieveIndustryKnowledgeInput(**fixture))

    # ── build_company_profile ─────────────────────────────────────────────────
    elif step == "build_company_profile":
        from containers.implementation.profile_agent.activities import build_company_profile, BuildProfileInput
        return await build_company_profile(BuildProfileInput(**fixture))

    # ── enrich_company_profile ────────────────────────────────────────────────
    elif step == "enrich_company_profile":
        from containers.implementation.profile_agent.activities import enrich_company_profile, EnrichCompanyProfileInput
        return await enrich_company_profile(EnrichCompanyProfileInput(**fixture))

    # ── merge_company_profile ─────────────────────────────────────────────────
    elif step == "merge_company_profile":
        from containers.implementation.profile_agent.activities import merge_company_profile, MergeProfileInput
        return await merge_company_profile(MergeProfileInput(**fixture))

    # ── build_target_structure ────────────────────────────────────────────────
    elif step == "build_target_structure":
        from containers.implementation.target_agent.activities import build_target_structure, BuildTargetInput
        return await build_target_structure(BuildTargetInput(**fixture))

    # ── assess_data_readiness (Step 8c) ───────────────────────────────────────
    elif step == "assess_data_readiness":
        from containers.implementation.data_readiness_agent.activities import assess_data_readiness, AssessDataReadinessInput
        return await assess_data_readiness(AssessDataReadinessInput(**fixture))

    # ── derive_required_records (Step 8b) ─────────────────────────────────────
    elif step == "derive_required_records":
        from containers.implementation.derive_agent.activities import derive_required_records, DeriveRequiredRecordsInput
        return await derive_required_records(DeriveRequiredRecordsInput(**fixture))

    # ── supervise_step (Supervisor Agent) ─────────────────────────────────────
    elif step == "supervise_step":
        from containers.implementation.supervisor_agent.activities import supervise_step, SuperviseStepInput
        from shared.models.is_status import NodeStatusEnvelope
        # status field is a NodeStatusEnvelope — deserialize from dict if needed
        raw_status = fixture.pop("status", None)
        if isinstance(raw_status, dict):
            fixture["status"] = NodeStatusEnvelope(**raw_status)
        return await supervise_step(SuperviseStepInput(**fixture))

    # ── apply_supervisor_actions (Supervisor Agent) ───────────────────────────
    elif step == "apply_supervisor_actions":
        from containers.implementation.supervisor_agent.activities import apply_supervisor_actions
        from shared.models.is_status import ApplySupervisorActionsInput, SupervisorAction
        raw_actions = fixture.pop("actions", [])
        actions = [SupervisorAction(**a) if isinstance(a, dict) else a for a in raw_actions]
        fixture["actions"] = actions
        return await apply_supervisor_actions(ApplySupervisorActionsInput(**fixture))

    # ── map_file_to_erpnext ───────────────────────────────────────────────────
    elif step == "map_file_to_erpnext":
        from containers.implementation.mapping_agent.activities import map_file_to_erpnext, MapFileInput
        return await map_file_to_erpnext(MapFileInput(**fixture))

    # ── refine_mapping_with_llm ───────────────────────────────────────────────
    elif step == "refine_mapping_with_llm":
        from containers.implementation.mapping_agent.activities import refine_mapping_with_llm, RefineMappingInput
        return await refine_mapping_with_llm(RefineMappingInput(**fixture))

    # ── validate_mapped_data ──────────────────────────────────────────────────
    elif step == "validate_mapped_data":
        from containers.implementation.validation_agent.activities import validate_mapped_data, ValidateInput
        return await validate_mapped_data(ValidateInput(**fixture))

    # ── build_import_plan ─────────────────────────────────────────────────────
    elif step == "build_import_plan":
        from containers.implementation.import_agent.activities import build_import_plan, BuildImportPlanInput
        return await build_import_plan(BuildImportPlanInput(**fixture))

    # ── finalize_import_plan ──────────────────────────────────────────────────
    elif step == "finalize_import_plan":
        from containers.implementation.import_agent.activities import finalize_import_plan, FinalizeImportPlanInput
        return await finalize_import_plan(FinalizeImportPlanInput(**fixture))

    # ── execute_import_phase ──────────────────────────────────────────────────
    elif step == "execute_import_phase":
        from containers.implementation.import_agent.activities import execute_import_phase, ExecutePhaseInput
        # CLI --phase flag overrides fixture, --dry-run flag overrides fixture
        if phase:
            fixture["phase_id"] = phase
        if dry_run:
            fixture["dry_run"] = True
        return await execute_import_phase(ExecutePhaseInput(**fixture))

    else:
        raise ValueError(f"Unknown step: '{step}'. Run with --help to see available steps.")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

BANNER = "═" * 72

VALID_STEPS = [
    "virus_scan_quarantine",
    "fetch_clean_files",
    "infer_f3iche",
    "verify_f3iche",
    "align_discovery_and_signals",
    "retrieve_industry_knowledge",
    "build_company_profile",
    "enrich_company_profile",
    "merge_company_profile",
    "build_target_structure",
    "derive_required_records",
    "assess_data_readiness",
    "supervise_step",
    "apply_supervisor_actions",
    "map_file_to_erpnext",
    "refine_mapping_with_llm",
    "validate_mapped_data",
    "build_import_plan",
    "finalize_import_plan",
    "execute_import_phase",
]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="IS Step Harness — run any single IS activity without Temporal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(["Available steps:"] + [f"  {s}" for s in VALID_STEPS]),
    )
    p.add_argument("--step", required=True, choices=VALID_STEPS, metavar="STEP",
                   help="Activity to run.")
    p.add_argument("--fixture", default=None, metavar="PATH",
                   help="JSON file with input data. Default: dev_fixtures/<step>.json")
    p.add_argument("--phase", default=None,
                   choices=["phase_a_config", "phase_b_master", "phase_c_transactional", "phase_d_projects"],
                   help="(execute_import_phase only) Which phase to run.")
    p.add_argument("--mock-llm", action="store_true",
                   help="Replace all Gemini calls with canned responses. Saves tokens during iteration.")
    p.add_argument("--dry-run", action="store_true",
                   help="(execute_import_phase) Skip actual ERPNext API writes.")
    p.add_argument("--output", default=None, metavar="PATH",
                   help="Write JSON result to this file instead of stdout.")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                   help="Log verbosity.")
    return p


async def _main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # ── Logging setup ─────────────────────────────────────────────────────────
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  %(levelname)-8s  %(name)s  │  %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("is_harness")

    log.info("")
    log.info(BANNER)
    log.info("  IS STEP HARNESS")
    log.info("  step     : %s", args.step)
    log.info("  mock_llm : %s", args.mock_llm)
    log.info("  dry_run  : %s", args.dry_run)
    log.info(BANNER)
    log.info("")

    # ── Install fake Temporal activity context ────────────────────────────────
    _install_fake_activity_context()

    # ── Install mock LLM if requested ─────────────────────────────────────────
    if args.mock_llm:
        _install_mock_llm()
        log.info("  ⚠️  --mock-llm active: Gemini will NOT be called")
        log.info("")

    # ── Load fixture ──────────────────────────────────────────────────────────
    fixture_path = Path(args.fixture) if args.fixture else _FIXTURES_DIR / f"{args.step}.json"

    if not fixture_path.exists():
        log.error("Fixture not found: %s", fixture_path)
        log.error("Create it or pass --fixture <path>. See dev_fixtures/README.md for help.")
        sys.exit(1)

    with open(fixture_path, "r", encoding="utf-8") as fh:
        fixture: Dict = json.load(fh)

    log.info("  Fixture  : %s", fixture_path)
    log.info("  Input    : %s", json.dumps(fixture, indent=None)[:200] + ("..." if len(str(fixture)) > 200 else ""))
    log.info("")

    # ── Run step ──────────────────────────────────────────────────────────────
    try:
        result = await _run_step(
            step=args.step,
            fixture=fixture,
            phase=args.phase,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        log.error("")
        log.error("  ❌  STEP FAILED: %s", exc)
        log.error("")
        raise

    # ── Output result ─────────────────────────────────────────────────────────
    # Convert dataclasses (NodeStatusEnvelope, etc.) to dicts before serializing
    import dataclasses as _dc
    if _dc.is_dataclass(result) and not isinstance(result, type):
        result = _dc.asdict(result)
    result_json = json.dumps(result, indent=2, default=str)

    log.info("")
    log.info(BANNER)
    log.info("  ✅  STEP COMPLETE: %s", args.step)
    log.info(BANNER)
    log.info("")

    if args.output:
        Path(args.output).write_text(result_json, encoding="utf-8")
        log.info("  Result written to: %s", args.output)
    else:
        print("\n" + result_json + "\n")


if __name__ == "__main__":
    asyncio.run(_main())
