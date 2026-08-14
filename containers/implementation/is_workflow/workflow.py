"""
IS Workflow — Temporal workflow for the full ERPNext implementation pipeline.

Human-in-the-loop flow:
  1. Workflow starts with project_id, immediately creates session_id in Supabase.
  2. Signal: files_uploaded       → run signals inference
  3. Signal: f3iche_confirmed     → build profile + target structure
  4. (No signal)                  → auto mapping
  5. (No signal)                  → auto validation
  6. Signal: validation_submitted → resolve issues, build import plan
  7. Signal: sandbox_approved     → execute live import (phase A → B → C)

State is offloaded to Supabase/R2. Temporal only stores strings/UUIDs.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from dataclasses import asdict
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

# IMPORTANT: Activities with heavy I/O dependencies (SQLAlchemy, boto3, etc.) that access
# os.environ during module initialization MUST be called via string name, not direct import.
# These should NEVER be imported here, even inside imports_passed_through().
# Examples: load_discovery_context, load_target_structure
# Pattern: await workflow.execute_activity("activity_name", {"param": value}, **_ACT)

with workflow.unsafe.imports_passed_through():
    from containers.implementation.profile_agent.activities    import build_company_profile, merge_company_profile, BuildProfileInput, MergeProfileInput
    from containers.implementation.target_agent.activities     import build_target_structure, BuildTargetInput
    from containers.implementation.data_readiness_agent.activities import assess_data_readiness, AssessDataReadinessInput
    from containers.implementation.mapping_agent.activities    import map_file_to_erpnext, MapFileInput, refine_mapping_with_llm, RefineMappingInput, assign_corpus_doctypes, AssignCorpusDoctypesInput
    from containers.implementation.validation_agent.activities import validate_mapped_data, ValidateInput, bootstrap_site_config, BootstrapSiteConfigInput
    from containers.implementation.import_agent.activities     import build_import_plan, execute_import_phase, get_import_plan_phases, finalize_import_plan, preflight_import, BuildImportPlanInput, ExecutePhaseInput, GetImportPlanPhasesInput, FinalizeImportPlanInput, PreflightImportInput
    from containers.implementation.corpus.activities import (
        enrich_corpus_understanding,
        EnrichCorpusUnderstandingInput,
        fetch_clean_files,
        FetchCleanFilesInput,
        virus_scan_quarantine,
    )
    from containers.implementation.file_io.persist_session     import persist_session, CompleteSessionInput, PersistSessionInput
    from containers.implementation.supervisor_agent.activities import supervise_step, SuperviseStepInput
    from containers.implementation.supervisor_agent.activities import apply_supervisor_actions
    from shared.models.is_status import ApplySupervisorActionsInput, NodeStatusEnvelope, SupervisorAction
    from containers.implementation.file_io.persist_supervisor_prompt import (
        persist_supervisor_prompt,
        PersistSupervisorPromptInput,
        mark_supervisor_prompt_answered,
        MarkSupervisorPromptAnsweredInput,
        obsolete_supervisor_prompts,
        ObsoleteSupervisorPromptsInput,
    )
    from containers.context_versioning.context_store.activities import (
        register_frappe_webhooks,
    )
    from shared.models.quality_gate import QualityGateInput, build_node_report
    from containers.implementation.is_workflow.step_contracts import contract_as_dict
    from shared.quality_gate.activity import quality_gate
    from containers.implementation.is_workflow.quality_gate_hooks import (
        coerce_envelope,
        mapping_summary_envelope,
    )

TASK_QUEUE = "is-queue"
V1_PIPELINE_STEPS = 5

_RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0)
_ACT   = {"start_to_close_timeout": timedelta(minutes=5), "retry_policy": _RETRY}
_LONG  = {"start_to_close_timeout": timedelta(minutes=30), "retry_policy": _RETRY}


# ═══════════════════════════════════════════════════════════════════════════════
# Log helpers — structured, readable step banners
# ═══════════════════════════════════════════════════════════════════════════════

_BANNER = "═" * 72
_DIVIDER = "─" * 72
_DOT_LINE = "· " * 36

def _step_start(logger, step_num: int | str, title: str, detail: str = "", *, total: int | None = None):
    logger.info("")
    logger.info("")
    logger.info(_BANNER)
    step_total = total if total is not None else V1_PIPELINE_STEPS
    logger.info("  STEP %s / %s  │  %s", step_num, step_total, title)
    if detail:
        logger.info("  %s", detail)
    logger.info(_BANNER)
    logger.info("")


def _substep(logger, label: str):
    logger.info("      ▸ %s", label)

def _step_ok(logger, step_num: int | str, title: str, summary: str = ""):
    logger.info("")
    logger.info("  ✅  STEP %s COMPLETE  │  %s", step_num, title)
    if summary:
        logger.info("      → %s", summary)
    logger.info(_DIVIDER)
    logger.info("")

def _step_fail(logger, step_num: int | str, title: str, error: str):
    logger.info("")
    logger.info("  ❌  STEP %s FAILED    │  %s", step_num, title)
    logger.info("      ERROR: %s", error)
    logger.info(_DIVIDER)
    logger.info("")

def _signal_banner(logger, signal_name: str, detail: str = ""):
    logger.info("")
    logger.info("")
    logger.info(_DOT_LINE)
    logger.info("  🚦  SIGNAL RECEIVED  │  %s", signal_name)
    if detail:
        logger.info("      %s", detail)
    logger.info(_DOT_LINE)
    logger.info("")

def _kv(logger, key: str, value: Any):
    logger.info("      %-24s : %s", key, value)


# ── Signal / query payloads ───────────────────────────────────────────────────

@dataclass
class FilesUploadedSignal:
    uploaded_files: List[Dict]
    company_slug: Optional[str] = None
    user_note: Optional[str] = None


@dataclass
class F3icheConfirmedSignal:
    f3iche_user: str
    industry: str
    industry_sub: Optional[str] = None
    company_name: Optional[str] = None
    company_size: Optional[str] = None


@dataclass
class ValidationSubmittedSignal:
    responses: Dict[str, Any]
    profile_edits: Dict[str, Any] = field(default_factory=dict)
    note: Optional[str] = None


@dataclass
class MappingConfirmedSignal:
    user_feedback: Optional[str] = None
    approved: bool = False


@dataclass
class SandboxApprovedSignal:
    erpnext_base_url: str = ""      # Optional — auto-resolved from Project.deployment_details if empty
    erpnext_api_key: str = ""       # Optional — auto-resolved from Project.deployment_details if empty
    dry_run: bool = False


@dataclass
class SupervisorResponseSignal:
    prompt_id: str
    chosen_action_id: str
    extra_data: Dict[str, Any] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
# Workflow
# ══════════════════════════════════════════════════════════════════════════════

@workflow.defn(name="ImplementationWorkflow")
class ImplementationWorkflow:
    def __init__(self) -> None:
        # PURE ORCHESTRATION STATE (No massive dicts)
        self._session_id: str = ""
        self._stage: str = "awaiting_files"
        self._analysis_tasks: List[Dict] = []
        self._company_slug: str = "unknown"
        self._all_uploaded_files: List[Dict] = []
        self._latest_upload_note: Optional[str] = None
        self._corpus_assignments: Dict[str, Dict[str, Any]] = {}
        self._gate_retry_counts: Dict[str, int] = {}
        self._last_retry_feedback: Optional[str] = None
        self._f3iche_confirmation: Optional[Dict[str, Any]] = None
        self._infer_result: Optional[Dict[str, Any]] = None
        self._corpus_understanding: Optional[Dict[str, Any]] = None
        self._r2_manifest_url: str = ""
        self._parsed_files: List[str] = []

        # Signal gates
        self._files_uploaded_event     = asyncio.Event()
        self._f3iche_confirmed_event   = asyncio.Event()
        self._mapping_confirmed_event  = asyncio.Event()
        self._validation_submitted_event = asyncio.Event()
        self._sandbox_approved_event   = asyncio.Event()
        self._supervisor_response_event = asyncio.Event()

        # Signal payloads
        self._sig_files:      Optional[FilesUploadedSignal]      = None
        self._sig_f3iche:     Optional[F3icheConfirmedSignal]    = None
        self._sig_mapping:    Optional[MappingConfirmedSignal]   = None
        self._sig_validation: Optional[ValidationSubmittedSignal] = None
        self._sig_sandbox:    Optional[SandboxApprovedSignal]    = None
        self._sig_supervisor: Optional[SupervisorResponseSignal] = None

    # ── Signals ──────────────────────────────────────────────────────────────

    @workflow.signal
    async def files_uploaded(self, sig: FilesUploadedSignal) -> None:
        self._sig_files = sig
        self._latest_upload_note = sig.user_note
        self._files_uploaded_event.set()

    @workflow.signal
    async def f3iche_confirmed(self, sig: F3icheConfirmedSignal) -> None:
        self._sig_f3iche = sig
        self._f3iche_confirmed_event.set()

    @workflow.signal
    async def mapping_confirmed(self, sig: MappingConfirmedSignal) -> None:
        self._sig_mapping = sig
        self._mapping_confirmed_event.set()

    @workflow.signal
    async def validation_submitted(self, sig: ValidationSubmittedSignal) -> None:
        self._sig_validation = sig
        self._validation_submitted_event.set()

    @workflow.signal
    async def sandbox_approved(self, sig: SandboxApprovedSignal) -> None:
        self._sig_sandbox = sig
        self._sandbox_approved_event.set()

    @workflow.signal
    async def supervisor_response(self, sig: SupervisorResponseSignal) -> None:
        self._sig_supervisor = sig
        self._supervisor_response_event.set()

    # ── Queries ───────────────────────────────────────────────────────────────

    @workflow.query
    def get_stage(self) -> str:
        return self._stage

    @workflow.query
    def get_analysis_tasks(self) -> List[Dict]:
        return self._analysis_tasks

    @workflow.query
    def get_f3iche_confirmation(self) -> Optional[Dict[str, Any]]:
        return self._f3iche_confirmation

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _task(self, id_: str, label: str, status: str = "idle", detail: Optional[str] = None) -> Dict:
        return {"id": id_, "label": label, "status": status, "detail": detail}

    def _set_task(self, id_: str, status: str, detail: Optional[str] = None) -> None:
        for t in self._analysis_tasks:
            if t["id"] == id_:
                t["status"] = status
                if detail is not None:
                    t["detail"] = detail
                return

    async def _run_is_quality_gate(
        self,
        step_name: str,
        env: Any,
        project_id: str,
        L: Any,
        *,
        actual_outputs: Optional[Dict[str, Any]] = None,
        hard_block_raises: bool = False,
    ) -> Dict[str, Any]:
        """Schedule quality_gate; pre-patch runs honor IS_QUALITY_GATE_ENABLED in workflow."""
        if not workflow.patched("is-quality-gate-always-scheduled"):
            with workflow.unsafe.sandbox_unrestricted():
                qg_enabled = os.getenv("IS_QUALITY_GATE_ENABLED", "0") == "1"
            if not qg_enabled:
                return {"verdict": "ok", "analysis": "quality gate disabled"}

        retry_count = self._gate_retry_counts.get(step_name, 0)
        env_obj = coerce_envelope(env, fallback_primary=actual_outputs)
        node_report = build_node_report(
            step_name,
            "IS",
            env_obj,
            actual_outputs=actual_outputs or {},
            feedback_from_previous_retry=self._last_retry_feedback,
        )
        gate = await workflow.execute_activity(
            quality_gate,
            QualityGateInput(
                pipeline="IS",
                step_name=step_name,
                contract=contract_as_dict(step_name),
                node_report=asdict(node_report),
                session_id=self._session_id,
                project_id=project_id,
                company_slug=self._company_slug,
                retry_count=retry_count,
            ),
            **_ACT,
        )
        gate_verdict = gate.get("verdict", "ok") if isinstance(gate, dict) else "ok"
        gate_analysis = gate.get("analysis", "") if isinstance(gate, dict) else ""
        _kv(L, "quality_gate", f"{step_name} → {gate_verdict}: {gate_analysis}")
        if gate_verdict == "hard_block" and hard_block_raises:
            _step_fail(L, step_name, "Quality gate", gate_analysis)
            self._stage = "error"
            raise ApplicationError(f"Quality gate blocked at {step_name}: {gate_analysis}")
        if gate.get("retry_feedback"):
            self._last_retry_feedback = str(gate.get("retry_feedback"))
        return gate if isinstance(gate, dict) else {"verdict": gate_verdict, "analysis": gate_analysis}

    def _gate_allows_retry(self, step_name: str, gate: Dict[str, Any]) -> bool:
        from containers.implementation.is_workflow.step_contracts import IS_STEP_CONTRACTS

        if gate.get("verdict") != "retry":
            return False
        contract = IS_STEP_CONTRACTS.get(step_name)
        max_r = contract.max_retries if contract else 2
        count = self._gate_retry_counts.get(step_name, 0)
        return count < max_r

    async def _process_gap_file_upload(
        self,
        project_id: str,
        newly_uploaded: List[Dict[str, Any]],
        L: Any,
    ) -> None:
        """Merge newly uploaded files, refresh corpus, and map only the new batch."""
        L.info("      ▶ Processing %d gap-upload file(s) ...", len(newly_uploaded))
        scan_res = await workflow.execute_activity(
            virus_scan_quarantine,
            args=[newly_uploaded, self._session_id],
            **_ACT,
        )
        if not scan_res.get("safe", False):
            _step_fail(L, "gap_scan", "Virus Scan", "INFECTED FILES DETECTED — halting workflow")
            self._stage = "infected_halt"
            raise ApplicationError("Implementation halted due to malicious payload.")

        all_files_map = {f["file_name"]: f for f in self._all_uploaded_files}
        for f in newly_uploaded:
            all_files_map[f["file_name"]] = f
        self._all_uploaded_files = list(all_files_map.values())

        fetch_results = await workflow.execute_activity(
            fetch_clean_files,
            FetchCleanFilesInput(
                uploaded_files=self._all_uploaded_files,
                project_id=project_id,
                company_slug=self._company_slug,
            ),
            **_ACT,
        )
        r2_manifest_url = fetch_results.get("manifest_url", self._r2_manifest_url)
        self._r2_manifest_url = r2_manifest_url
        self._parsed_files = fetch_results.get("parsed_files", self._parsed_files)

        if r2_manifest_url and not str(r2_manifest_url).startswith("error"):
            try:
                from containers.implementation.supervisor_agent.activities import fetch_discovery_context
                re_discovery = await fetch_discovery_context(project_id)
                enrich_result = await workflow.execute_activity(
                    enrich_corpus_understanding,
                    EnrichCorpusUnderstandingInput(
                        manifest_url=r2_manifest_url,
                        user_import_note=getattr(self, "_latest_upload_note", None),
                        discovery_chat_history=re_discovery.get("chat_history"),
                        discovery_metadata=re_discovery.get("discovery_metadata"),
                        discovery_status=re_discovery.get("discovery_status"),
                    ),
                    **_LONG,
                )
                self._corpus_understanding = enrich_result
            except Exception as enrich_err:
                L.info("      ⚠️  Corpus re-enrichment after gap upload failed: %s", enrich_err)

        try:
            corpus_env = await workflow.execute_activity(
                assign_corpus_doctypes,
                AssignCorpusDoctypesInput(
                    session_id=self._session_id,
                    project_id=project_id,
                    r2_manifest_url=r2_manifest_url,
                    company_slug=self._company_slug,
                ),
                **_ACT,
            )
            if isinstance(corpus_env, dict):
                corpus_env = (
                    NodeStatusEnvelope(**corpus_env)
                    if "status" in corpus_env
                    else NodeStatusEnvelope.success(primary_result=corpus_env)
                )
            assignments = (corpus_env.primary_result or {}).get("assignments", []) if hasattr(corpus_env, "primary_result") else []
            for a in assignments:
                if isinstance(a, dict) and a.get("file"):
                    self._corpus_assignments[a["file"]] = a
        except Exception as corpus_err:
            L.info("      ⚠️  Corpus assignment after gap upload failed: %s", corpus_err)

        new_names = {f["file_name"] for f in newly_uploaded}
        files_to_map = [f for f in self._parsed_files if f in new_names]
        L.info("      ▶ Mapping %d new file(s) after gap upload ...", len(files_to_map))
        for fname in files_to_map:
            try:
                mapped_env = await workflow.execute_activity(
                    map_file_to_erpnext,
                    MapFileInput(
                        r2_manifest_url=r2_manifest_url,
                        filename=fname,
                        project_id=project_id,
                        company_slug=self._company_slug,
                        session_id=self._session_id,
                        corpus_assignment=self._corpus_assignments.get(fname),
                    ),
                    **_ACT,
                )
                pr = mapped_env.primary_result if hasattr(mapped_env, "primary_result") else {}
                mapped_dts = (pr or {}).get("doctypes_mapped", []) if isinstance(pr, dict) else []
                L.info("             → %s mapped to %s", fname, ",".join(mapped_dts) or "unmapped")
            except Exception as map_err:
                L.info("             → ❌ %s mapping failed: %s", fname, map_err)

    # ── Main run ─────────────────────────────────────────────────────────────

    @workflow.run
    async def run(self, project_id: str, discovery_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        workflow_id = workflow.info().workflow_id
        L = workflow.logger

        L.info("")
        L.info("╔" + "═" * 70 + "╗")
        L.info("║   IMPLEMENTATION SYSTEM — WORKFLOW STARTED                          ║")
        L.info("║   project : %-56s ║", project_id)
        L.info("║   workflow: %-56s ║", workflow_id)
        L.info("╚" + "═" * 70 + "╝")
        L.info("")

        self._discovery_f3iche = discovery_meta.get("f3iche") if discovery_meta else None
        self._discovery_industry = discovery_meta.get("industry") if discovery_meta else None

        # ══════════════════════════════════════════════════════════════════════
        # STEP 0 / 9  —  Session Creation
        # ══════════════════════════════════════════════════════════════════════
        _step_start(L, 0, "Session Creation", "Creating is_sessions row in Supabase")

        try:
            self._session_id = await workflow.execute_activity(
                persist_session,
                PersistSessionInput(
                    project_id=project_id, 
                    workflow_id=workflow_id, 
                    status="awaiting_files",
                    discovery_f3iche=discovery_meta.get("f3iche") if discovery_meta else None,
                    discovery_industry=discovery_meta.get("industry") if discovery_meta else None,
                    discovery_company_size=discovery_meta.get("company_size") if discovery_meta else None,
                ),
                **_ACT,
            )
            _kv(L, "session_id", self._session_id)
            _kv(L, "table", "is_sessions")
            _kv(L, "status", "awaiting_files")
            _step_ok(L, 0, "Session Creation", f"session_id = {self._session_id}")
        except Exception as e:
            _step_fail(L, 0, "Session Creation", str(e))
            raise ApplicationError(f"Failed to initialize session: {e}")

        self._analysis_tasks = [
            self._task("t1", "Parsing uploaded files"),
            self._task("t2", "Detecting file formats"),
            self._task("t3", "Extracting company metadata"),
            self._task("t4", "Inferring business type (F3iche)"),
            self._task("t5", "Building target structure"),
            self._task("t6", "Mapping data to ERPNext fields"),
            self._task("t7", "Running pre-import validation"),
            self._task("t8", "Generating import plan"),
        ]

        # ══════════════════════════════════════════════════════════════════════
        # AWAIT SIGNAL: files_uploaded
        # ══════════════════════════════════════════════════════════════════════
        self._stage = "awaiting_files"
        L.info("  ⏳ Waiting for files_uploaded signal ...")
        L.info("")
        await workflow.wait_condition(lambda: self._files_uploaded_event.is_set())

        sig = self._sig_files
        self._all_uploaded_files = list(sig.uploaded_files) if sig else []
        _signal_banner(L, "files_uploaded", f"{len(sig.uploaded_files)} files | slug={sig.company_slug}")
        if self._latest_upload_note:
            _kv(L, "user_note", self._latest_upload_note[:160])
        self._set_task("t1", "running")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 2 / 5  —  Corpus Intake & Understanding
        # ══════════════════════════════════════════════════════════════════════
        _step_start(
            L, 2, "Corpus Intake & Understanding",
            "virus scan → parse manifest → LLM understand (discovery-first)",
        )

        _substep(L, "Virus scan & quarantine")

        try:
            scan_result: Dict = await workflow.execute_activity(
                virus_scan_quarantine,
                args=[sig.uploaded_files, self._session_id],
                **_ACT,
            )
            _kv(L, "safe", scan_result.get("safe"))
            _kv(L, "clean_count", scan_result.get("clean_count"))
            _kv(L, "infected_count", scan_result.get("infected_count"))
            _kv(L, "table written", "is_files (virus_scan_status, clean/virus r2 paths)")
        except Exception as e:
            _step_fail(L, 2, "Corpus Intake & Understanding", f"Virus scan: {e}")
            self._stage = "error"
            raise ApplicationError(f"Virus scan failed: {e}")

        if not scan_result.get("safe", False):
            _step_fail(L, 2, "Corpus Intake & Understanding", "INFECTED FILES DETECTED — halting workflow")
            self._stage = "infected_halt"
            raise ApplicationError("Implementation halted due to malicious payload.")

        self._company_slug = sig.company_slug or "unknown"
        _substep(L, f"Virus scan OK — {scan_result.get('clean_count')} clean files")

        _substep(L, "Fetch & parse clean files → manifest v2")

        try:
            fetch_results: Dict = await workflow.execute_activity(
                fetch_clean_files,
                FetchCleanFilesInput(uploaded_files=sig.uploaded_files, project_id=project_id, company_slug=self._company_slug),
                **_ACT,
            )
            r2_manifest_url = fetch_results.get("manifest_url", "error")
            self._r2_manifest_url = r2_manifest_url
            self._parsed_files = fetch_results.get("parsed_files", [])
            _kv(L, "manifest_url", r2_manifest_url)
            _kv(L, "parsed_files", self._parsed_files)
            _kv(L, "R2 path", f"clean-data/{self._company_slug}/{project_id}/_manifest/")
            _substep(L, f"Parsed {len(self._parsed_files)} files → {r2_manifest_url}")
        except Exception as e:
            _substep(L, f"Fetch & parse failed: {e}")
            L.info("      ⚠️  Continuing with empty manifest — corpus understanding will be limited")
            r2_manifest_url = "error"
            self._r2_manifest_url = r2_manifest_url
            self._parsed_files = []

        _substep(L, "LLM corpus understanding (discovery context required)")
        discovery_context = {}
        try:
            from containers.implementation.supervisor_agent.activities import fetch_discovery_context
            discovery_context = await fetch_discovery_context(project_id)
            if discovery_context.get("chat_history"):
                L.info(
                    "      ✓ Discovery context loaded: %d messages, status=%s",
                    len(discovery_context.get("chat_history", [])),
                    discovery_context.get("discovery_status"),
                )
        except Exception as e:
            L.info("      ⚠️  Could not load discovery context: %s", e)

        if r2_manifest_url and not r2_manifest_url.startswith("error"):
            try:
                enrich_result: Dict = await workflow.execute_activity(
                    enrich_corpus_understanding,
                    EnrichCorpusUnderstandingInput(
                        manifest_url=r2_manifest_url,
                        user_import_note=sig.user_note,
                        discovery_chat_history=discovery_context.get("chat_history"),
                        discovery_metadata=discovery_context.get("discovery_metadata"),
                        discovery_status=discovery_context.get("discovery_status"),
                    ),
                    **_LONG,
                )
                self._corpus_understanding = enrich_result
                _kv(L, "corpus_summary", (enrich_result.get("corpus_summary") or "")[:120])
                _kv(L, "files_understood", enrich_result.get("files_understood", 0))
                _kv(L, "corpus_status", enrich_result.get("status", "unknown"))
                _kv(L, "corpus_gate", enrich_result.get("gate_passed", False))
                for w in enrich_result.get("warnings") or []:
                    L.info("      ⚠️  corpus: [%s] %s", w.get("code"), w.get("message"))
                if enrich_result.get("status") == "failed":
                    L.info("      ⚠️  Corpus understanding failed — check discovery completion before mapping")
            except Exception as e:
                L.info("      ⚠️  Corpus understanding activity error: %s", e)
        else:
            L.info("      ⚠️  Skipping corpus understanding — no valid manifest")

        self._set_task("t1", "done")
        self._set_task("t2", "done")
        self._stage = "analyzing"
        _step_ok(
            L, 2, "Corpus Intake & Understanding",
            f"{len(self._parsed_files)} files | gate={getattr(self, '_corpus_understanding', {}).get('gate_passed', 'n/a')}",
        )

        # ── Step 2b block merged above ──
        # Legacy marker removed: fetch + enrich are sub-steps of Step 2 / 5

        # ══════════════════════════════════════════════════════════════════════════════
        # P1 OPTIMIZATION: Steps 3-6a REMOVED — Read f3iche + MVP focus from discovery
        # ══════════════════════════════════════════════════════════════════════════════
        _step_start(L, 3, "Load Discovery Context", "Reading f3iche, industry, and MVP focus from discovery")
        
        try:
            discovery_context = await workflow.execute_activity(
                "load_discovery_context",
                {"project_id": project_id},
                **_ACT,
            )
            
            self._discovery_f3iche = discovery_context.get("f3iche", "trading")
            self._discovery_industry = discovery_context.get("industry", "general")
            
            _kv(L, "f3iche", self._discovery_f3iche)
            _kv(L, "industry", self._discovery_industry)
            mvp_bottleneck = discovery_context.get("mvp_focus", {}).get("primary_bottleneck", "N/A")
            _kv(L, "mvp_focus", mvp_bottleneck if mvp_bottleneck != "N/A" else "not specified")
            _kv(L, "source", discovery_context.get("source", "unknown"))
            _step_ok(L, 3, "Load Discovery Context", f"f3iche={self._discovery_f3iche}")
            
        except Exception as e:
            _step_fail(L, 3, "Load Discovery Context", str(e))
            L.info("      ⚠️  Failed to load discovery context — using defaults")
            self._discovery_f3iche = "trading"
            self._discovery_industry = "general"
            discovery_context = {
                "f3iche": "trading",
                "industry": "general",
                "mvp_focus": {},
                "source": "error_fallback",
            }

        # Create a synthetic "confirmation" object for compatibility with downstream code
        conf = F3icheConfirmedSignal(
            f3iche_user=self._discovery_f3iche,
            industry=self._discovery_industry,
            industry_sub=discovery_context.get("industry_sub"),
            company_name=discovery_context.get("company_name"),
            company_size=discovery_context.get("company_size"),
        )
        
        # Create synthetic results for compatibility
        infer_result = {
            "f3iche": self._discovery_f3iche,
            "confidence": 1.0,  # Discovery is always 100% confident (user confirmed)
            "collected_signals": [],
        }
        
        verify_result = {"status": "exact_match"}
        
        alignment_result = {
            "alignment_score": 1.0,
            "mismatches": [],
            "reasoning": "Discovery pre-confirmed",
            "mvp_focus": discovery_context.get("mvp_focus", {}),
        }
        
        self._infer_result = infer_result
        self._f3iche_confirmation = {
            "proposed_f3iche": self._discovery_f3iche,
            "proposed_industry": self._discovery_industry,
            "display_name": self._discovery_f3iche,
            "confidence": 1.0,
            "alignment": "exact",
        }
        
        self._stage = "building_profile"
        self._set_task("t2", "done")
        self._set_task("t3", "done")
        self._set_task("t4", "done", f"Loaded: {self._discovery_f3iche}")
        self._set_task("t5", "running")
        # ══════════════════════════════════════════════════════════════════════
        # STEP 4 / 9  —  Build Company Profile (Simplified)
        # ══════════════════════════════════════════════════════════════════════
        # P1: Steps 7a (Industry Knowledge) and 7b (LLM Profile Generation) REMOVED
        # Industry insights now come from discovery, profile is built in one pass
        _step_start(L, 4, "Build Company Profile",
                    f"f3iche={conf.f3iche_user} | industry={conf.industry}")

        try:
            await workflow.execute_activity(
                build_company_profile,
                BuildProfileInput(
                    project_id=project_id,
                    version=1,
                    f3iche=conf.f3iche_user,
                    industry=conf.industry,
                    session_id=self._session_id,
                    company_slug=self._company_slug,
                    action="create",
                    industry_sub=conf.industry_sub,
                    company_name=conf.company_name,
                    company_size=conf.company_size,
                    f3iche_user=conf.f3iche_user,
                    f3iche_signals=infer_result["f3iche"],
                    f3iche_match_status=verify_result.get("status", "exact_match"),
                    uploaded_files=sig.uploaded_files,
                    r2_manifest_url=r2_manifest_url,
                    collected_signals=infer_result["collected_signals"],
                    discovery_alignment_score=alignment_result.get("alignment_score", 1.0),
                    discovery_alignment_mismatches=alignment_result.get("mismatches") or [],
                    discovery_alignment_reasoning=alignment_result.get("reasoning", "Discovery pre-confirmed"),
                    mvp_focus=alignment_result.get("mvp_focus"),
                    corpus_understanding=self._corpus_understanding,
                    synthesis_proposal=self._f3iche_confirmation,
                ),
                **_ACT,
            )
            _kv(L, "table", "is_company_profiles (v1)")
            _kv(L, "R2", f"clean-data/{self._company_slug}/{project_id}/_profile/company_context_v1.json")
            _kv(L, "audit", "is_audit_trail → profile_built")
            _step_ok(L, 4, "Build Company Profile", "version=1 persisted")
        except Exception as e:
            _step_fail(L, 4, "Build Company Profile", str(e))
            self._stage = "error"
            raise ApplicationError(f"Profile build failed: {e}")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 8 / 9  —  Load Target Structure (Project-Level, Corpus-Independent)
        # ══════════════════════════════════════════════════════════════════════
        _step_start(L, 8, "Load Target Structure",
                    f"f3iche={conf.f3iche_user} | industry={conf.industry}")

        try:
            # Try to load project-level target structure (generated post-discovery)
            target = await workflow.execute_activity(
                "load_project_target_structure",
                {"session_id": self._session_id},
                **_ACT,
            )
            
            if target.get("exists") and target.get("required_doctypes"):
                # ✅ Target structure exists at project level (corpus-independent)
                _kv(L, "source", "project_level (corpus-independent)")
                _kv(L, "generated_at", "post_discovery")
                target_env = NodeStatusEnvelope.success(primary_result={"target_structure": target})
                n_doctypes = len(target.get("required_doctypes", []))
                n_seeds = len(target.get("seed_doctypes", []))
                n_steps = len(target.get("setup_steps", []))
                _kv(L, "seed_doctypes", n_seeds)
                _kv(L, "required_doctypes", n_doctypes)
                _kv(L, "setup_steps", n_steps)
                _kv(L, "mvp_boundary", "loaded from project")
                _step_ok(L, 8, "Load Target Structure", f"{n_seeds} seeds → {n_doctypes} total doctypes (project-level)")
            else:
                # ⚠️ FALLBACK: Legacy generation (should not happen for new flows)
                _kv(L, "source", "legacy_generation_in_is")
                _kv(L, "corpus_dependent", "true (legacy)")
                L.info("      ⚠️  No project-level target found, falling back to legacy generation")
                L.info("      ⚠️  This should only happen for old projects created before project-level targets")
                
                target_env = await workflow.execute_activity(
                    build_target_structure,
                    BuildTargetInput(
                        session_id=self._session_id,
                        project_id=project_id,
                        f3iche=conf.f3iche_user,
                        company_slug=self._company_slug,
                        r2_manifest_url=r2_manifest_url,
                        corpus_understanding=self._corpus_understanding,
                        corpus_summary=(self._corpus_understanding or {}).get("corpus_summary"),
                        mvp_focus=alignment_result.get("mvp_focus"),
                        synthesis_proposal=self._f3iche_confirmation,
                        discovery_alignment={
                            "alignment_score": alignment_result.get("alignment_score"),
                            "mismatches": alignment_result.get("mismatches"),
                            "reasoning": alignment_result.get("reasoning"),
                        } if alignment_result else None,
                    ),
                    **_ACT,
                )
                if isinstance(target_env, dict):
                    if "status" in target_env:
                        target_env = NodeStatusEnvelope(**target_env)
                    else:
                        target_env = NodeStatusEnvelope.success(primary_result={"target_structure": target_env})
                elif isinstance(target_env, str):
                    target_env = NodeStatusEnvelope.success(primary_result={"target_structure": {}})
                    
                target = (target_env.primary_result or {}).get("target_structure") if hasattr(target_env, "primary_result") else {}
                n_doctypes = len(target.get("required_doctypes", [])) if isinstance(target, dict) else 0
                n_steps = len(target.get("setup_steps", [])) if isinstance(target, dict) else 0
                _kv(L, "required_doctypes", n_doctypes)
                _kv(L, "setup_steps", n_steps)
                _step_ok(L, 8, "Build Target Structure (Legacy)", f"{n_doctypes} doctypes, {n_steps} steps")
            
            _kv(L, "table", "project_target_structures, project_mvp_boundaries")
            _kv(L, "R2", target.get("r2_target_path", f"clean-data/{self._company_slug}/project_{project_id}/_discovery/target_structure.json"))
            _kv(L, "mvp_boundary", target.get("r2_mvp_path", f"clean-data/{self._company_slug}/project_{project_id}/_discovery/mvp_boundary.json"))
            
        except Exception as e:
            _step_fail(L, 8, "Target Structure", str(e))
            self._stage = "error"
            raise ApplicationError(f"Target structure failed: {e}")

        # Supervisor hook (non-blocking): persist prompt if target load/build not OK
        with workflow.unsafe.sandbox_unrestricted():
            supervisor_enabled = os.getenv("IS_SUPERVISOR_ENABLED", "0") == "1"
        if supervisor_enabled and not getattr(target_env, "ok", False):
            try:
                sup = await workflow.execute_activity(
                    supervise_step,
                    SuperviseStepInput(
                        project_id=project_id,
                        session_id=self._session_id,
                        node_name="target_structure",
                        step="8",
                        f3iche_id=conf.f3iche_user,
                        phase="phase_a_config",
                        doctypes_in_focus=[],
                        status=target_env,
                    ),
                    **_ACT,
                )
                await workflow.execute_activity(
                    persist_supervisor_prompt,
                    PersistSupervisorPromptInput(
                        session_id=self._session_id,
                        step="target_structure",
                        status="open",
                        node_status=asdict(target_env),
                        actions=[asdict(a) for a in (sup.actions or [])],
                        summary_for_ui=sup.summary_for_ui,
                    ),
                    **_ACT,
                )
            except Exception as e:
                L.info("      ⚠️  Supervisor hook for target_structure failed (non-fatal): %s", e)

        self._set_task("t5", "done", f"{len(target.get('required_doctypes', []))} doctypes target")

        # P1: Step 8b (Derive Required Records) REMOVED - rarely used, adds complexity

        # ══════════════════════════════════════════════════════════════════════
        # STEP 5 / 9  —  Data Readiness Assessment
        # ══════════════════════════════════════════════════════════════════════
        _step_start(L, 5, "Data Readiness Assessment", "Comparing uploaded data against target structure")

        readiness_env: Optional[NodeStatusEnvelope] = None
        readiness: Dict[str, Any] = {}

        try:
            readiness_env = await workflow.execute_activity(
                assess_data_readiness,
                AssessDataReadinessInput(
                    session_id=self._session_id,
                    project_id=project_id,
                    company_slug=self._company_slug,
                    r2_manifest_url=r2_manifest_url,
                ),
                **_ACT,
            )
            if isinstance(readiness_env, dict):
                if "status" in readiness_env:
                    readiness_env = NodeStatusEnvelope(**readiness_env)
                else:
                    readiness_env = NodeStatusEnvelope.success(primary_result=readiness_env)
            elif isinstance(readiness_env, str):
                readiness_env = NodeStatusEnvelope.success(primary_result={"assessment": {}})

            readiness = (readiness_env.primary_result or {}).get("assessment", {}) if isinstance(readiness_env.primary_result, dict) else {}
            score = float(readiness.get("import_readiness_score", 0.0) or 0.0)
            _kv(L, "import_readiness_score", f"{score*100:.0f}%")
            _kv(L, "ready_doctypes", len(readiness.get("ready_doctypes", [])))
            _kv(L, "partial_doctypes", len(readiness.get("partial_doctypes", [])))
            _kv(L, "missing_doctypes", len(readiness.get("missing_doctypes", [])))
            _kv(L, "unmappable_chunks", len(readiness.get("unmappable_chunks", [])))
            _kv(L, "minimum_viable_possible", readiness.get("minimum_viable_import_possible"))
            _kv(L, "user_action_required", readiness.get("user_action_required"))
            _step_ok(
                L,
                5,
                "Data Readiness Assessment",
                f"score={score*100:.0f}% | viable={readiness.get('minimum_viable_import_possible')}",
            )
        except Exception as e:
            _step_fail(L, 5, "Data Readiness Assessment", str(e))
            readiness_env = NodeStatusEnvelope.failed(
                errors=[{"code": "READINESS_FAILED", "message": str(e)}],
                primary_result={"assessment": {}},
            )
            readiness = {}

        with workflow.unsafe.sandbox_unrestricted():
            supervisor_enabled = os.getenv("IS_SUPERVISOR_ENABLED", "0") == "1"

        readiness_needs_input = not bool(readiness.get("minimum_viable_import_possible", True))
        readiness_failed = getattr(readiness_env, "status", "") == "failed"
        readiness_prompt_id: Optional[str] = None

        if supervisor_enabled and readiness_env and readiness and not readiness_failed:
            try:
                sup = await workflow.execute_activity(
                    supervise_step,
                    SuperviseStepInput(
                        project_id=project_id,
                        session_id=self._session_id,
                        node_name="assess_data_readiness",
                        step="8c",
                        f3iche_id=conf.f3iche_user,
                        phase="pre_mapping",
                        doctypes_in_focus=[
                            *(g.get("doctype", "") for g in (readiness.get("missing_doctypes", []) or [])),
                            *(g.get("doctype", "") for g in (readiness.get("partial_doctypes", []) or [])),
                        ],
                        status=readiness_env,
                    ),
                    **_ACT,
                )

                if readiness_needs_input or (sup.actions or []):
                    readiness_prompt_id = await workflow.execute_activity(
                        persist_supervisor_prompt,
                        PersistSupervisorPromptInput(
                            session_id=self._session_id,
                            step="data_readiness",
                            status="open",
                            node_status=asdict(readiness_env),
                            actions=[asdict(a) for a in (sup.actions or [])],
                            summary_for_ui=sup.summary_for_ui,
                        ),
                        **_ACT,
                    )

                if readiness_needs_input:
                    self._stage = "awaiting_data_readiness_confirmation"
                    await workflow.execute_activity(
                        persist_session,
                        PersistSessionInput(
                            project_id=project_id,
                            workflow_id=workflow_id,
                            status=self._stage,
                        ),
                        **_ACT,
                    )

                    readiness_cycle = 0
                    while readiness_needs_input:
                        readiness_cycle += 1
                        _signal_banner(L, "data_readiness_prompt", f"prompt_id={readiness_prompt_id}")
                        self._supervisor_response_event.clear()
                        L.info("  ⏳ Waiting for supervisor_response signal ...")
                        await workflow.wait_condition(lambda: self._supervisor_response_event.is_set())

                        ssig = self._sig_supervisor
                        selected_option = ""
                        if ssig:
                            selected_option = str((ssig.extra_data or {}).get("selected_option", ""))
                            await workflow.execute_activity(
                                mark_supervisor_prompt_answered,
                                MarkSupervisorPromptAnsweredInput(
                                    prompt_id=str(readiness_prompt_id),
                                    answer_payload={
                                        "chosen_action_id": ssig.chosen_action_id,
                                        "extra_data": ssig.extra_data,
                                    },
                                    status="answered",
                                ),
                                **_ACT,
                            )

                        chosen_action = next(
                            (a for a in (sup.actions or []) if getattr(a, "id", None) == (ssig.chosen_action_id if ssig else "")),
                            None,
                        )

                        if selected_option.lower().startswith("upload") and readiness_cycle <= 1:
                            self._files_uploaded_event.clear()
                            L.info("  ⏳ Waiting for additional files_uploaded signal ...")
                            await workflow.wait_condition(lambda: self._files_uploaded_event.is_set())

                            newly_uploaded = self._sig_files.uploaded_files if self._sig_files else []
                            L.info("      ▶ Running virus scan on %d newly uploaded files...", len(newly_uploaded))
                            
                            scan_res = await workflow.execute_activity(
                                virus_scan_quarantine,
                                args=[newly_uploaded, self._session_id],
                                **_ACT,
                            )
                            if not scan_res.get("safe", False):
                                _step_fail(L, "8c_scan", "Virus Scan", "INFECTED FILES DETECTED — halting workflow")
                                self._stage = "infected_halt"
                                raise ApplicationError("Implementation halted due to malicious payload.")

                            # Deduplicate and combine by file_name
                            all_files_map = {f["file_name"]: f for f in self._all_uploaded_files}
                            for f in newly_uploaded:
                                all_files_map[f["file_name"]] = f
                            self._all_uploaded_files = list(all_files_map.values())
                            updated_files = self._all_uploaded_files
                            L.info("      ✅ Re-running readiness with %d total file(s) after union merge", len(updated_files))

                            fetch_results = await workflow.execute_activity(
                                fetch_clean_files,
                                FetchCleanFilesInput(
                                    uploaded_files=updated_files,
                                    project_id=project_id,
                                    company_slug=self._company_slug,
                                ),
                                **_ACT,
                            )
                            r2_manifest_url = fetch_results.get("manifest_url", r2_manifest_url)
                            self._r2_manifest_url = r2_manifest_url
                            self._parsed_files = fetch_results.get("parsed_files", self._parsed_files)

                            # Re-enrich corpus understanding on merged manifest (Step 2b loop)
                            if r2_manifest_url and not str(r2_manifest_url).startswith("error"):
                                try:
                                    from containers.implementation.supervisor_agent.activities import (
                                        fetch_discovery_context,
                                    )
                                    re_discovery = await fetch_discovery_context(project_id)
                                    enrich_result = await workflow.execute_activity(
                                        enrich_corpus_understanding,
                                        EnrichCorpusUnderstandingInput(
                                            manifest_url=r2_manifest_url,
                                            user_import_note=getattr(self, "_latest_upload_note", None),
                                            discovery_chat_history=re_discovery.get("chat_history"),
                                            discovery_metadata=re_discovery.get("discovery_metadata"),
                                            discovery_status=re_discovery.get("discovery_status"),
                                        ),
                                        **_LONG,
                                    )
                                    self._corpus_understanding = enrich_result
                                    L.info(
                                        "      ✅ Corpus re-enriched after upload | %d files | status=%s",
                                        enrich_result.get("files_understood", 0),
                                        enrich_result.get("status", "unknown"),
                                    )
                                except Exception as enrich_err:
                                    L.info(
                                        "      ⚠️  Corpus re-enrichment failed (non-fatal): %s",
                                        enrich_err,
                                    )

                            readiness_env = await workflow.execute_activity(
                                assess_data_readiness,
                                AssessDataReadinessInput(
                                    session_id=self._session_id,
                                    project_id=project_id,
                                    company_slug=self._company_slug,
                                    r2_manifest_url=r2_manifest_url,
                                ),
                                **_ACT,
                            )
                            if isinstance(readiness_env, dict):
                                if "status" in readiness_env:
                                    readiness_env = NodeStatusEnvelope(**readiness_env)
                                else:
                                    readiness_env = NodeStatusEnvelope.success(primary_result=readiness_env)
                            readiness = (readiness_env.primary_result or {}).get("assessment", {}) if isinstance(readiness_env.primary_result, dict) else {}
                            readiness_needs_input = not bool(readiness.get("minimum_viable_import_possible", True))
                            if not readiness_needs_input:
                                _step_ok(L, "8c", "Data Readiness Recheck", "Fresh files make minimum viable import possible")
                                break
                            L.info("      ⚠️  Readiness still not viable after re-upload; proceeding with the user's decision path.")
                            break

                        # Proceed / skip / anything else continues to mapping.
                        if chosen_action and getattr(chosen_action, "type", "") == "auto_fix":
                            await workflow.execute_activity(
                                apply_supervisor_actions,
                                ApplySupervisorActionsInput(
                                    project_id=project_id,
                                    session_id=self._session_id,
                                    step="data_readiness",
                                    company_slug=self._company_slug,
                                    actions=[chosen_action],
                                ),
                                **_ACT,
                            )
                        break
            except Exception as e:
                L.info("      ⚠️  Supervisor hook for data_readiness failed (non-fatal): %s", e)
        elif readiness_failed:
            L.info("  ⚠️  Readiness assessment failed — proceeding without gate")
        elif not readiness_needs_input:
            L.info("  ✅ Minimum viable data confirmed — proceeding to mapping without gate")
        else:
            L.info("  ⚠️  Supervisor disabled — proceeding despite readiness gaps")

        try:
            await workflow.execute_activity(
                obsolete_supervisor_prompts,
                ObsoleteSupervisorPromptsInput(session_id=self._session_id),
                **_ACT,
            )
        except Exception as e:
            L.info("      ⚠️  obsolete_supervisor_prompts after readiness failed: %s", e)

        # ══════════════════════════════════════════════════════════════════════
        # STEP 7 / 9  —  Build Import Plan
        # ══════════════════════════════════════════════════════════════════════
        self._set_task("t8", "running")
        _step_start(L, 7, "Build Import Plan",
                    "3-phase plan: Config → Master Data → Transactional")

        try:
            plan_status: str = await workflow.execute_activity(
                build_import_plan,
                BuildImportPlanInput(session_id=self._session_id, project_id=project_id, company_slug=self._company_slug),
                **_ACT,
            )
            _kv(L, "plan_status", plan_status)
            _kv(L, "reads from", "is_target_structures, is_data_readiness_assessments")
            _kv(L, "table", "is_import_plans")
            _kv(L, "R2", f"clean-data/{self._company_slug}/{project_id}/_import_plan/plan.json")
            _kv(L, "audit", "is_audit_trail → import_plan_created")
            _step_ok(L, 7, "Build Import Plan", f"status={plan_status}")
            self._set_task("t8", "done", f"Plan: {plan_status}")
        except Exception as e:
            _step_fail(L, 7, "Build Import Plan", str(e))
            self._set_task("t8", "failed", str(e))

        # ══════════════════════════════════════════════════════════════════════
        # STEP 8 / 9  —  Corpus Doctype Assignment
        # ══════════════════════════════════════════════════════════════════════
        _step_start(L, 8, "Corpus Doctype Assignment", "Classifying uploaded files using corpus context")
        try:
            corpus_env = await workflow.execute_activity(
                assign_corpus_doctypes,
                AssignCorpusDoctypesInput(
                    session_id=self._session_id,
                    project_id=project_id,
                    r2_manifest_url=r2_manifest_url,
                    company_slug=self._company_slug,
                ),
                **_ACT,
            )
            if isinstance(corpus_env, dict):
                if "status" in corpus_env:
                    corpus_env = NodeStatusEnvelope(**corpus_env)
                else:
                    corpus_env = NodeStatusEnvelope.success(primary_result=corpus_env)
            assignments = (corpus_env.primary_result or {}).get("assignments", []) if hasattr(corpus_env, "primary_result") else []
            self._corpus_assignments = {
                a.get("file"): a for a in assignments if isinstance(a, dict) and a.get("file")
            }
            _kv(L, "assignments", len(self._corpus_assignments))
            _step_ok(L, 8, "Corpus Doctype Assignment", f"{len(self._corpus_assignments)} files classified")
            await self._run_is_quality_gate(
                "assign_corpus_doctypes",
                corpus_env,
                project_id,
                L,
                actual_outputs={
                    "assignment_count": len(self._corpus_assignments),
                    "assignments": list(self._corpus_assignments.values())[:20],
                },
            )
        except Exception as e:
            _step_fail(L, 8, "Corpus Doctype Assignment", str(e))

        self._stage = "mapping"

        # ══════════════════════════════════════════════════════════════════════
        # STEP 8 / 14  —  Update Session to Mapping
        # ══════════════════════════════════════════════════════════════════════
        _step_start(L, 8, "Update Session Status", "→ mapping")

        try:
            await workflow.execute_activity(
                persist_session,
                PersistSessionInput(project_id=project_id, workflow_id=workflow_id, status="mapping"),
                **_ACT,
            )
            _kv(L, "table", "is_sessions")
            _kv(L, "status", "mapping")
            _step_ok(L, 8, "Session Status Update", "status=mapping")
        except Exception as e:
            _step_fail(L, 8, "Session Status Update", str(e))

        # ══════════════════════════════════════════════════════════════════════
        # STEP 9 / 9  —  Automated File Mapping
        # ══════════════════════════════════════════════════════════════════════
        self._stage = "mapping_files"
        self._set_task("t6", "running")

        _step_start(L, 9, "Automated File Mapping",
                    f"{len(self._parsed_files)} files to map")

        mapped_count = 0
        map_failures: List[str] = []
        # ── SORT: structured files first (.csv, .xlsx), then unstructured (.txt, .pdf) ──
        structured_ext = {".csv", ".xlsx", ".xls", ".tsv"}
        sorted_files = sorted(
            self._parsed_files,
            key=lambda f: (0 if any(f.lower().endswith(e) for e in structured_ext) else 1, f)
        )
        for i, fname in enumerate(sorted_files):
            L.info("      [%d/%d] Mapping: %s", i + 1, len(self._parsed_files), fname)
            try:
                mapped_env = await workflow.execute_activity(
                    map_file_to_erpnext,
                    MapFileInput(
                        r2_manifest_url=r2_manifest_url,
                        filename=fname,
                        project_id=project_id,
                        company_slug=self._company_slug,
                        session_id=self._session_id,
                        corpus_assignment=self._corpus_assignments.get(fname),
                    ),
                    **_ACT,
                )
                if isinstance(mapped_env, dict):
                    if "status" in mapped_env:
                        mapped_env = NodeStatusEnvelope(**mapped_env)
                    else:
                        mapped_env = NodeStatusEnvelope.success(primary_result={"file": fname, "doctypes_mapped": [mapped_env] if mapped_env else []})
                elif isinstance(mapped_env, str):
                    mapped_doctypes = [mapped_env] if mapped_env not in ["error", "unmapped"] else []
                    mapped_env = NodeStatusEnvelope.success(primary_result={"file": fname, "doctypes_mapped": mapped_doctypes})

                pr = mapped_env.primary_result if hasattr(mapped_env, "primary_result") else {}
                mapped_doctypes = (pr or {}).get("doctypes_mapped", []) if isinstance(pr, dict) else []
                if getattr(mapped_env, "ok", False) and mapped_doctypes:
                    mapped_count += 1
                    L.info("             → ✅ %s → %s", fname, ",".join(mapped_doctypes))
                else:
                    L.info("             → ⚠️  %s → %s", fname, ",".join(mapped_doctypes) if mapped_doctypes else "unmapped")

                # Supervisor hook (non-blocking): persist mapping prompt for this file if needed
                with workflow.unsafe.sandbox_unrestricted():
                    supervisor_enabled = os.getenv("IS_SUPERVISOR_ENABLED", "0") == "1"
                if supervisor_enabled and not getattr(mapped_env, "ok", False):
                    try:
                        sup = await workflow.execute_activity(
                            supervise_step,
                            SuperviseStepInput(
                                project_id=project_id,
                                session_id=self._session_id,
                                node_name="map_file_to_erpnext",
                                step="9",
                                f3iche_id=conf.f3iche_user,
                                phase="phase_b_master",
                                doctypes_in_focus=mapped_doctypes,
                                status=mapped_env,
                            ),
                            **_ACT,
                        )
                        await workflow.execute_activity(
                            persist_supervisor_prompt,
                            PersistSupervisorPromptInput(
                                session_id=self._session_id,
                                step="mapping",
                                status="open",
                                node_status=asdict(mapped_env),
                                actions=[asdict(a) for a in (sup.actions or [])],
                                summary_for_ui=sup.summary_for_ui,
                            ),
                            **_ACT,
                        )
                    except Exception as e:
                        L.info("             → ⚠️  Supervisor hook for mapping failed: %s", e)
            except Exception as e:
                L.info("             → ❌ %s FAILED: %s", fname, e)
                map_failures.append(f"{fname}: {e}")

        _kv(L, "files_mapped", f"{mapped_count}/{len(self._parsed_files)}")
        _kv(L, "tables written", "is_field_mappings, is_mapped_data")
        _kv(L, "R2", f"clean-data/{self._company_slug}/{project_id}/mappings/")
        _kv(L, "audit", "is_audit_trail → mapping_completed (per file)")
        _step_ok(L, 9, "File Mapping", f"{mapped_count}/{len(self._parsed_files)} files mapped")

        map_gate = await self._run_is_quality_gate(
            "map_file_to_erpnext",
            mapping_summary_envelope(mapped_count, len(self._parsed_files), map_failures),
            project_id,
            L,
            actual_outputs={
                "mapped_count": mapped_count,
                "total_files": len(self._parsed_files),
                "failures": map_failures[:10],
            },
        )
        while self._gate_allows_retry("map_file_to_erpnext", map_gate):
            self._gate_retry_counts["map_file_to_erpnext"] = (
                self._gate_retry_counts.get("map_file_to_erpnext", 0) + 1
            )
            retry_names = [
                f.split(":")[0].strip()
                for f in map_failures
                if ":" in f
            ] or list(sorted_files)
            L.info("      ↻ Quality gate retry map (%d files)", len(retry_names))
            for fname in retry_names:
                try:
                    mapped_env = await workflow.execute_activity(
                        map_file_to_erpnext,
                        MapFileInput(
                            r2_manifest_url=r2_manifest_url,
                            filename=fname,
                            project_id=project_id,
                            company_slug=self._company_slug,
                            session_id=self._session_id,
                            corpus_assignment=self._corpus_assignments.get(fname),
                            retry_feedback=self._last_retry_feedback,
                        ),
                        **_ACT,
                    )
                    if isinstance(mapped_env, dict) and "status" in mapped_env:
                        mapped_env = NodeStatusEnvelope(**mapped_env)
                    pr = mapped_env.primary_result if hasattr(mapped_env, "primary_result") else {}
                    if getattr(mapped_env, "ok", False) and (pr or {}).get("doctypes_mapped"):
                        mapped_count = max(mapped_count, 1)
                except Exception as e:
                    L.info("             → ↻ retry failed %s: %s", fname, e)
            map_gate = await self._run_is_quality_gate(
                "map_file_to_erpnext",
                mapping_summary_envelope(mapped_count, len(self._parsed_files), map_failures),
                project_id,
                L,
                actual_outputs={
                    "mapped_count": mapped_count,
                    "total_files": len(self._parsed_files),
                    "failures": map_failures[:10],
                },
            )

        self._set_task("t6", "done", f"{mapped_count} files mapped")

        try:
            await workflow.execute_activity(
                obsolete_supervisor_prompts,
                ObsoleteSupervisorPromptsInput(session_id=self._session_id),
                **_ACT,
            )
        except Exception as e:
            L.info("      ⚠️  obsolete_supervisor_prompts after mapping failed: %s", e)

        # ══════════════════════════════════════════════════════════════════════
        # AWAIT SIGNAL: mapping_confirmed
        # ══════════════════════════════════════════════════════════════════════
        self._stage = "awaiting_mapping_confirmation"
        try:
            await workflow.execute_activity(
                persist_session,
                PersistSessionInput(
                    project_id=project_id,
                    workflow_id=workflow_id,
                    status=self._stage,
                ),
                **_ACT,
            )
            _kv(L, "status", self._stage)
        except Exception as e:
            L.info("      ⚠️  Failed to persist session status: %s", e)
        
        while True:
            self._mapping_confirmed_event.clear()
            L.info("  ⏳ Waiting for mapping_confirmed signal ...")
            L.info("")
            await workflow.wait_condition(lambda: self._mapping_confirmed_event.is_set())
            
            msig = self._sig_mapping
            _signal_banner(L, "mapping_confirmed", f"approved={msig.approved} | feedback={'present' if msig.user_feedback else 'none'}")
            
            if msig.approved and not msig.user_feedback:
                _step_ok(L, 9, "Mapping Confirmation", "Mappings explicitly approved.")
                break
                
            if msig.user_feedback:
                # ══════════════════════════════════════════════════════════════════════
                # STEP 10 / 14  —  Conversational Mapping Refinement
                # ══════════════════════════════════════════════════════════════════════
                _step_start(L, 10, "Conversational Mapping Refinement", "Refining mappings based on user feedback.")
                self._stage = "refining_mapping"
                try:
                    await workflow.execute_activity(
                        persist_session,
                        PersistSessionInput(
                            project_id=project_id,
                            workflow_id=workflow_id,
                            status=self._stage,
                        ),
                        **_ACT,
                    )
                except Exception as e:
                    L.info("      ⚠️  Failed to persist session status: %s", e)

                try:
                    ref_res = await workflow.execute_activity(
                        refine_mapping_with_llm,
                        RefineMappingInput(
                            session_id=self._session_id,
                            user_feedback=msig.user_feedback,
                            project_id=project_id,
                            company_slug=self._company_slug
                        ),
                        **_ACT,
                    )
                    changes = ref_res.get('changes_count', 0)
                    _kv(L, "Updated Mappings", len(ref_res.get("updated_mappings", [])))
                    _kv(L, "Removed Mappings", len(ref_res.get("removed_mappings", [])))
                    _step_ok(L, 10, "Conversational Mapping Refinement", f"Processed feedback, {changes} mappings changed.")
                    
                    if msig.approved:
                        break
                    else:
                        self._stage = "awaiting_mapping_confirmation"
                        try:
                            await workflow.execute_activity(
                                persist_session,
                                PersistSessionInput(
                                    project_id=project_id,
                                    workflow_id=workflow_id,
                                    status=self._stage,
                                ),
                                **_ACT,
                            )
                        except Exception as e:
                            pass
                        continue
                except Exception as e:
                    _step_fail(L, 10, "Conversational Mapping Refinement", str(e))
                    # Fallback out of loop if it crashes, or keep waiting
                    pass

        # ══════════════════════════════════════════════════════════════════════
        # STEP 10b / 14  —  Site Config Bootstrap (SCB)
        # ══════════════════════════════════════════════════════════════════════
        _step_start(L, "10b", "Site Config Bootstrap",
                    "VTL + live ERP fuzzy match; derive missing config masters")

        try:
            scb_env = await workflow.execute_activity(
                bootstrap_site_config,
                BootstrapSiteConfigInput(
                    session_id=self._session_id,
                    project_id=project_id,
                    company_slug=self._company_slug,
                ),
                **_ACT,
            )
            if isinstance(scb_env, dict):
                scb_env = NodeStatusEnvelope(**scb_env) if "status" in scb_env else NodeStatusEnvelope.success(primary_result=scb_env)
            scb_primary = scb_env.primary_result if hasattr(scb_env, "primary_result") else {}
            if isinstance(scb_primary, dict):
                _kv(L, "derived_doctypes", scb_primary.get("derived_doctypes"))
                _kv(L, "patch_count", scb_primary.get("patch_count"))
            _step_ok(L, "10b", "Site Config Bootstrap", "config masters derived where needed")
        except Exception as e:
            _step_fail(L, "10b", "Site Config Bootstrap", str(e))
            L.warning("  ⚠️ SCB failed (non-fatal) — continuing to validation")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 11 / 14  —  Pre-Import Validation
        # ══════════════════════════════════════════════════════════════════════
        self._set_task("t7", "running")
        self._stage = "validating"

        _step_start(L, 11, "Pre-Import Validation",
                    "Checking mapped data vs target structure rules")

        try:
            v_env = await workflow.execute_activity(
                validate_mapped_data,
                ValidateInput(session_id=self._session_id, project_id=project_id, company_slug=self._company_slug),
                **_ACT,
            )
            if isinstance(v_env, dict):
                if "status" in v_env:
                    v_env = NodeStatusEnvelope(**v_env)
                else:
                    v_env = NodeStatusEnvelope.success(primary_result={"overall": v_env})
            elif isinstance(v_env, str):
                v_env = NodeStatusEnvelope.success(primary_result={"overall": v_env}) if v_env in ("passed", "success") else NodeStatusEnvelope.failed(primary_result={"overall": v_env})

            v_primary = v_env.primary_result if hasattr(v_env, "primary_result") else {}
            v_status = v_primary.get("overall") if isinstance(v_primary, dict) else None
            _kv(L, "overall_status", v_status or getattr(v_env, "status", "unknown"))
            _kv(L, "reads from", "is_target_structures, is_mapped_data, R2 extracted rows")
            _kv(L, "tables written", "is_validation_results, is_validation_errors")
            _kv(L, "also updates", "is_mapped_data.validation_status, is_sessions.status")
            _kv(L, "R2", f"clean-data/{self._company_slug}/{project_id}/_validation/report.json")
            _kv(L, "audit", "is_audit_trail → validation_run")
            _step_ok(L, 11, "Validation", f"overall={v_status or getattr(v_env, 'status', 'unknown')}")
        except Exception as e:
            _step_fail(L, 11, "Validation", str(e))
            self._stage = "error"
            raise ApplicationError(f"Validation failed: {e}")

        # ── Quality gate (feature-flagged) ───────────────────────────────────
        v_gate = await self._run_is_quality_gate(
            "validate_mapped_data",
            v_env,
            project_id,
            L,
            actual_outputs=v_primary if isinstance(v_primary, dict) else {},
            hard_block_raises=True,
        )
        while self._gate_allows_retry("validate_mapped_data", v_gate):
            self._gate_retry_counts["validate_mapped_data"] = (
                self._gate_retry_counts.get("validate_mapped_data", 0) + 1
            )
            L.info("      ↻ Quality gate retry validate")
            v_env = await workflow.execute_activity(
                validate_mapped_data,
                ValidateInput(
                    session_id=self._session_id,
                    project_id=project_id,
                    company_slug=self._company_slug,
                    retry_feedback=self._last_retry_feedback,
                ),
                **_ACT,
            )
            if isinstance(v_env, dict):
                v_env = NodeStatusEnvelope(**v_env) if "status" in v_env else NodeStatusEnvelope.success(primary_result=v_env)
            v_primary = v_env.primary_result if hasattr(v_env, "primary_result") else {}
            v_gate = await self._run_is_quality_gate(
                "validate_mapped_data",
                v_env,
                project_id,
                L,
                actual_outputs=v_primary if isinstance(v_primary, dict) else {},
                hard_block_raises=True,
            )

        # ── Supervisor correction loop (feature-flagged) ─────────────────────
        with workflow.unsafe.sandbox_unrestricted():
            supervisor_enabled = os.getenv("IS_SUPERVISOR_ENABLED", "0") == "1"
        if supervisor_enabled:
            auto_fix_attempted = False
            ask_cycles = 0

            while True:
                if getattr(v_env, "ok", False):
                    break

                sup = await workflow.execute_activity(
                    supervise_step,
                    SuperviseStepInput(
                        project_id=project_id,
                        session_id=self._session_id,
                        node_name="validate_mapped_data",
                        step="11",
                        f3iche_id=conf.f3iche_user,
                        phase="phase_c_transactional",
                        doctypes_in_focus=[],
                        status=v_env,
                    ),
                    **_ACT,
                )
                _kv(L, "supervisor", sup.summary_for_ui)

                auto_fixes = [a for a in (sup.actions or []) if getattr(a, "type", "") == "auto_fix"]
                if auto_fixes and not auto_fix_attempted:
                    await workflow.execute_activity(
                        apply_supervisor_actions,
                        ApplySupervisorActionsInput(
                            project_id=project_id,
                            session_id=self._session_id,
                            step="validation",
                            company_slug=self._company_slug,
                            actions=auto_fixes,
                        ),
                        **_ACT,
                    )
                    auto_fix_attempted = True
                    v_env = await workflow.execute_activity(
                        validate_mapped_data,
                        ValidateInput(
                            session_id=self._session_id,
                            project_id=project_id,
                            company_slug=self._company_slug,
                            retry_feedback=self._last_retry_feedback,
                        ),
                        **_ACT,
                    )
                    v_env = NodeStatusEnvelope(**v_env) if isinstance(v_env, dict) else v_env
                    if isinstance(v_env, dict) and "status" not in v_env:
                        v_env = NodeStatusEnvelope.success(primary_result=v_env)
                    continue

                if sup.final_status in ("needs_user_input", "hard_block"):
                    ask_cycles += 1
                    if ask_cycles > 2:
                        L.info("      ⚠️  Supervisor ask_user cycles exceeded; stopping correction loop.")
                        await workflow.execute_activity(
                            obsolete_supervisor_prompts,
                            ObsoleteSupervisorPromptsInput(session_id=self._session_id),
                            **_ACT,
                        )
                        break

                    # Persist prompt for UI consumption
                    prompt_id = await workflow.execute_activity(
                        persist_supervisor_prompt,
                        PersistSupervisorPromptInput(
                            session_id=self._session_id,
                            step="validation",
                            status="open",
                            node_status=asdict(v_env),
                            actions=[asdict(a) for a in (sup.actions or [])],
                            summary_for_ui=sup.summary_for_ui,
                        ),
                        **_ACT,
                    )

                    self._stage = "validating"
                    await workflow.execute_activity(
                        persist_session,
                        PersistSessionInput(
                            project_id=project_id,
                            workflow_id=workflow_id,
                            status=self._stage,
                        ),
                        **_ACT,
                    )

                    self._supervisor_response_event.clear()
                    L.info("  ⏳ Waiting for supervisor_response signal ...")
                    await workflow.wait_condition(lambda: self._supervisor_response_event.is_set())

                    ssig = self._sig_supervisor
                    if ssig:
                        await workflow.execute_activity(
                            mark_supervisor_prompt_answered,
                            MarkSupervisorPromptAnsweredInput(
                                prompt_id=str(prompt_id),
                                answer_payload={"chosen_action_id": ssig.chosen_action_id, "extra_data": ssig.extra_data},
                                status="answered",
                            ),
                            **_ACT,
                        )

                        # If chosen action is an auto_fix action, apply it.
                        chosen = ssig.chosen_action_id
                        chosen_action = next((a for a in (sup.actions or []) if getattr(a, "id", None) == chosen), None)
                        if chosen_action and getattr(chosen_action, "type", "") == "auto_fix":
                            await workflow.execute_activity(
                                apply_supervisor_actions,
                                ApplySupervisorActionsInput(
                                    project_id=project_id,
                                    session_id=self._session_id,
                                    step="validation",
                                    company_slug=self._company_slug,
                                    actions=[chosen_action],
                                ),
                                **_ACT,
                            )
                        elif chosen_action and getattr(chosen_action, "type", "") == "ask_user":
                            extra = (ssig.extra_data or {}) if ssig else {}
                            selected = str(extra.get("selected_option", "")).lower()
                            create_master = extra.get("create_master") if isinstance(extra.get("create_master"), dict) else None
                            if create_master or extra.get("create_master_intent"):
                                cm = create_master if isinstance(create_master, dict) else {}
                                await workflow.execute_activity(
                                    apply_supervisor_actions,
                                    ApplySupervisorActionsInput(
                                        project_id=project_id,
                                        session_id=self._session_id,
                                        step="validation",
                                        company_slug=self._company_slug,
                                        actions=[
                                            SupervisorAction(
                                                id="auto_fix_create_party_stub",
                                                type="auto_fix",
                                                scope=str(cm.get("doctype") or "Customer"),
                                                changes=[
                                                    {
                                                        "target": "r2",
                                                        "op": "create_party_stub",
                                                        "doctype": str(cm.get("doctype") or "Customer"),
                                                        "name": str(cm.get("name") or ""),
                                                    }
                                                ],
                                                metadata=cm,
                                            )
                                        ],
                                    ),
                                    **_ACT,
                                )
                            elif selected.startswith("upload"):
                                self._files_uploaded_event.clear()
                                L.info("  ⏳ Waiting for files_uploaded after validation supervisor upload ...")
                                await workflow.wait_condition(lambda: self._files_uploaded_event.is_set())
                                gap_files = self._sig_files.uploaded_files if self._sig_files else []
                                if gap_files:
                                    await self._process_gap_file_upload(project_id, gap_files, L)
                            elif "continue" in selected or "default" in selected:
                                await workflow.execute_activity(
                                    apply_supervisor_actions,
                                    ApplySupervisorActionsInput(
                                        project_id=project_id,
                                        session_id=self._session_id,
                                        step="validation",
                                        company_slug=self._company_slug,
                                        actions=[
                                            SupervisorAction(
                                                id="auto_fix_vtl_defaults",
                                                type="auto_fix",
                                                scope="validation",
                                                changes=[
                                                    {
                                                        "target": "r2",
                                                        "op": "apply_value_translation",
                                                        "overwrite": True,
                                                    }
                                                ],
                                                metadata={"origin": "continue_with_defaults"},
                                            )
                                        ],
                                    ),
                                    **_ACT,
                                )
                            elif extra.get("apply_user_note") or extra.get("user_note"):
                                note = str(extra.get("user_note") or "").strip()
                                sample_gaps = extra.get("sample_gaps")
                                if not isinstance(sample_gaps, list):
                                    meta = getattr(chosen_action, "metadata", None) or {}
                                    sample_gaps = meta.get("sample_gaps") if isinstance(meta, dict) else []
                                await workflow.execute_activity(
                                    apply_supervisor_actions,
                                    ApplySupervisorActionsInput(
                                        project_id=project_id,
                                        session_id=self._session_id,
                                        step="validation",
                                        company_slug=self._company_slug,
                                        actions=[
                                            SupervisorAction(
                                                id="auto_fix_user_note_resolutions",
                                                type="auto_fix",
                                                scope="validation",
                                                changes=[
                                                    {
                                                        "target": "r2",
                                                        "op": "apply_user_note_resolutions",
                                                    }
                                                ],
                                                metadata={
                                                    "user_note": note,
                                                    "sample_gaps": sample_gaps or [],
                                                },
                                            )
                                        ],
                                    ),
                                    **_ACT,
                                )

                    # Re-run validation after user response (or no-op)
                    v_env = await workflow.execute_activity(
                        validate_mapped_data,
                        ValidateInput(session_id=self._session_id, project_id=project_id, company_slug=self._company_slug),
                        **_ACT,
                    )
                    v_env = NodeStatusEnvelope(**v_env) if isinstance(v_env, dict) else v_env
                    continue

                # Nothing else to do (either already tried auto-fix, or no actionable items)
                break

            await workflow.execute_activity(
                obsolete_supervisor_prompts,
                ObsoleteSupervisorPromptsInput(session_id=self._session_id),
                **_ACT,
            )

        def _blocking_mvp_seeds(env: Any) -> List[str]:
            pr = env.primary_result if hasattr(env, "primary_result") else {}
            if not isinstance(pr, dict):
                return []
            return list(pr.get("blocking_unmapped_seeds") or [])

        # ── MVP gap upload loop (deterministic — re-upload → map → re-validate) ──
        while _blocking_mvp_seeds(v_env):
            blocking = _blocking_mvp_seeds(v_env)
            names = ", ".join(blocking)
            L.info("      ⏸  Unmapped MVP seeds: %s — awaiting gap upload", names)

            self._stage = "awaiting_validation_gap_upload"
            await workflow.execute_activity(
                persist_session,
                PersistSessionInput(
                    project_id=project_id,
                    workflow_id=workflow_id,
                    status=self._stage,
                ),
                **_ACT,
            )

            L.info("  ⏳ Waiting for files_uploaded signal (validation gap) ...")
            if not self._files_uploaded_event.is_set():
                await workflow.wait_condition(lambda: self._files_uploaded_event.is_set())

            newly_uploaded = self._sig_files.uploaded_files if self._sig_files else []
            if newly_uploaded:
                await self._process_gap_file_upload(project_id, newly_uploaded, L)
            else:
                L.info("      ⚠️  files_uploaded received with no payload — waiting again")
                self._files_uploaded_event.clear()
                continue

            self._files_uploaded_event.clear()

            try:
                await workflow.execute_activity(
                    obsolete_supervisor_prompts,
                    ObsoleteSupervisorPromptsInput(session_id=self._session_id),
                    **_ACT,
                )
            except Exception as obs_err:
                L.info("      ⚠️  obsolete_supervisor_prompts after gap upload failed: %s", obs_err)

            v_env = await workflow.execute_activity(
                validate_mapped_data,
                ValidateInput(
                    session_id=self._session_id,
                    project_id=project_id,
                    company_slug=self._company_slug,
                ),
                **_ACT,
            )
            if isinstance(v_env, dict):
                v_env = (
                    NodeStatusEnvelope(**v_env)
                    if "status" in v_env
                    else NodeStatusEnvelope.success(primary_result=v_env)
                )
            v_primary = v_env.primary_result if hasattr(v_env, "primary_result") else {}
            v_status = v_primary.get("overall") if isinstance(v_primary, dict) else None
            L.info("      ✅ Re-validation after gap upload | overall=%s blocking=%s", v_status, _blocking_mvp_seeds(v_env))

        self._set_task("t7", "done", f"Status: {v_status or getattr(v_env, 'status', 'unknown')}")
        self._stage = "awaiting_validation_submission"

        # ══════════════════════════════════════════════════════════════════════
        # AWAIT SIGNAL: validation_submitted
        # ══════════════════════════════════════════════════════════════════════
        L.info("  ⏳ Waiting for validation_submitted signal ...")
        L.info("")
        await workflow.wait_condition(lambda: self._validation_submitted_event.is_set())

        vsub = self._sig_validation
        _signal_banner(L, "validation_submitted",
                       f"responses={len(vsub.responses)} keys | edits={len(vsub.profile_edits)} keys")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 11a / 14  —  Merge Profile Edits (conditional)
        # ══════════════════════════════════════════════════════════════════════
        if vsub.profile_edits:
            _step_start(L, "11a", "Merge Profile Edits",
                        f"Patching {len(vsub.profile_edits)} fields")
            try:
                await workflow.execute_activity(
                    merge_company_profile,
                    MergeProfileInput(session_id=self._session_id, patch=vsub.profile_edits, action="user_edit"),
                    **_ACT,
                )
                _kv(L, "table", "is_company_profiles (new version)")
                _kv(L, "patch_keys", list(vsub.profile_edits.keys()))
                _kv(L, "audit", "is_audit_trail → profile_merged")
                _step_ok(L, "11a", "Merge Profile Edits", "New profile version created")
            except Exception as e:
                _step_fail(L, "11a", "Merge Profile Edits", str(e))
        else:
            _step_start(L, "11a", "Merge Profile Edits", "No edits submitted — skipping")
            _step_ok(L, "11a", "Merge Profile Edits", "SKIPPED (no edits)")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 12 / 14  —  Finalize Import Plan
        # ══════════════════════════════════════════════════════════════════════
        self._set_task("t8", "running")

        _step_start(L, 5, "Finalize Import Plan",
                    "Updating import plan with mapped paths and row counts", total=V1_PIPELINE_STEPS)

        try:
            plan_status: str = await workflow.execute_activity(
                finalize_import_plan,
                FinalizeImportPlanInput(session_id=self._session_id, project_id=project_id, company_slug=self._company_slug),
                **_ACT,
            )
            _kv(L, "plan_status", plan_status)
            _kv(L, "reads from", "is_import_plans, is_mapped_data, is_validation_results")
            _kv(L, "table", "is_import_plans (updated)")
            _kv(L, "R2", f"clean-data/{self._company_slug}/{project_id}/_import_plan/plan.json")

            if plan_status == "blocked":
                L.info("")
                L.info("      ⚠️  Plan is BLOCKED — critical gaps or validation failures must be resolved first")
            elif plan_status == "ready_with_gaps":
                L.info("")
                L.info("      ℹ️  Plan is READY WITH GAPS — import will proceed for mapped data; optional doctypes deferred")

            _step_ok(L, 5, "Finalize Import Plan", f"status={plan_status}")
            await self._run_is_quality_gate(
                "finalize_import_plan",
                plan_status,
                project_id,
                L,
                actual_outputs={"plan_status": plan_status},
                hard_block_raises=(plan_status == "blocked"),
            )
        except Exception as e:
            _step_fail(L, 5, "Finalize Import Plan", str(e))
            self._stage = "error"
            raise ApplicationError(f"Import plan finalization failed: {e}")

        self._set_task("t8", "done", f"Finalized Status: {plan_status}")
        self._stage = "awaiting_sandbox_approval"

        # ══════════════════════════════════════════════════════════════════════
        # AWAIT SIGNAL: sandbox_approved
        # ══════════════════════════════════════════════════════════════════════
        L.info("  ⏳ Waiting for sandbox_approved signal ...")
        L.info("")
        await workflow.wait_condition(lambda: self._sandbox_approved_event.is_set())

        sb = self._sig_sandbox
        _signal_banner(L, "sandbox_approved",
                       f"dry_run={sb.dry_run} | erpnext={sb.erpnext_base_url}")

        if plan_status == "blocked" and not sb.dry_run:
            L.info("")
            L.info("      ⛔  Import plan is BLOCKED — live import refused.")
            L.info("      Resolve data gaps / validation failures, then re-run finalize.")
            self._stage = "import_blocked"
            raise ApplicationError(
                "Import plan is blocked — resolve data gaps and validation failures "
                "before live import. Use dry_run=true to preview phases without writing."
            )

        self._stage = "importing"

        # ══════════════════════════════════════════════════════════════════════
        # STEP 13 / 14  —  Execute Import Phases
        # ══════════════════════════════════════════════════════════════════════
        # ── PROTOCOL-COMPLIANT: Read phases from the dynamically built plan ──
        phases = await workflow.execute_activity(
            get_import_plan_phases,
            GetImportPlanPhasesInput(session_id=self._session_id),
            **_ACT,
        )

        _step_start(L, 5, "Execute Import Phases",
                    f"dry_run={sb.dry_run} | {len(phases)} phases", total=V1_PIPELINE_STEPS)

        import_phases_succeeded = False
        import_phase_failures: List[str] = []
        import_phases_aborted = False
        for phase_id, phase_label in phases:
            if import_phases_aborted:
                break
            L.info("      ┌── %s ──┐", phase_label)
            try:
                execution_confirmed = False
                skip_gate = sb.dry_run or phase_id not in ("phase_c_transactional", "phase_b_master")

                if not skip_gate:
                    try:
                        supervisor_enabled = os.getenv("IS_SUPERVISOR_ENABLED", "0") == "1"
                    except Exception:
                        supervisor_enabled = False

                    preflight = await workflow.execute_activity(
                        preflight_import,
                        PreflightImportInput(
                            session_id=self._session_id,
                            phase_id=phase_id,
                            project_id=project_id,
                            company_slug=self._company_slug,
                            erpnext_base_url=sb.erpnext_base_url,
                            erpnext_api_key=sb.erpnext_api_key,
                        ),
                        **_ACT,
                    )

                    if preflight.get("requires_execution_gate") and supervisor_enabled:
                        gate_env = NodeStatusEnvelope(
                            status="needs_user_input",
                            primary_result={"preflight": preflight},
                            errors=[],
                            warnings=preflight.get("confirmation_preview", {}).get("warnings", []),
                        )
                        sup_gate = await workflow.execute_activity(
                            supervise_step,
                            SuperviseStepInput(
                                project_id=project_id,
                                session_id=self._session_id,
                                node_name="execute_import_phase",
                                step="13",
                                f3iche_id=self._f3iche_id or "",
                                phase=phase_id,
                                doctypes_in_focus=[
                                    s.get("doctype", "")
                                    for s in preflight.get("confirmation_preview", {}).get("create_steps", [])
                                ],
                                status=gate_env,
                            ),
                            **_ACT,
                        )
                        if sup_gate.actions:
                            gate_prompt_id = await workflow.execute_activity(
                                persist_supervisor_prompt,
                                PersistSupervisorPromptInput(
                                    session_id=self._session_id,
                                    step="import_execution",
                                    status="open",
                                    node_status={
                                        "status": gate_env.status,
                                        "primary_result": gate_env.primary_result,
                                    },
                                    actions=[a.model_dump() if hasattr(a, "model_dump") else dict(a) for a in sup_gate.actions],
                                    summary_for_ui=sup_gate.summary_for_ui,
                                ),
                                **_ACT,
                            )
                            self._supervisor_response_event.clear()
                            L.info("  ⏳ Waiting for import execution confirmation ...")
                            await workflow.wait_condition(lambda: self._supervisor_response_event.is_set())
                            ssig = self._sig_supervisor
                            selected_option = str((ssig.extra_data or {}).get("selected_option", "")) if ssig else ""
                            if ssig:
                                await workflow.execute_activity(
                                    mark_supervisor_prompt_answered,
                                    MarkSupervisorPromptAnsweredInput(
                                        prompt_id=str(gate_prompt_id),
                                        answer_payload={
                                            "chosen_action_id": ssig.chosen_action_id,
                                            "extra_data": ssig.extra_data,
                                        },
                                        status="answered",
                                    ),
                                    **_ACT,
                                )
                            confirm_ids = ("ask_user_confirm_import_execution",)
                            confirm_options = ("Confirm and run import", "confirm", "yes", "continue")
                            if (
                                ssig
                                and (
                                    ssig.chosen_action_id in confirm_ids
                                    or selected_option in confirm_options
                                )
                            ):
                                execution_confirmed = True
                            else:
                                raise ApplicationError(
                                    f"Import phase {phase_label} cancelled by user at execution gate"
                                )
                    elif preflight.get("requires_execution_gate"):
                        execution_confirmed = True

                result = await workflow.execute_activity(
                    execute_import_phase,
                    ExecutePhaseInput(
                        session_id=self._session_id,
                        phase_id=phase_id,
                        project_id=project_id,
                        company_slug=self._company_slug,
                        dry_run=sb.dry_run,
                        erpnext_base_url=sb.erpnext_base_url,
                        erpnext_api_key=sb.erpnext_api_key,
                        execution_confirmed=execution_confirmed,
                        skip_execution_gate=skip_gate or execution_confirmed,
                    ),
                    **_LONG,
                )
                if isinstance(result, dict) and result.get("status") == "awaiting_confirmation":
                    raise ApplicationError(
                        f"Import phase {phase_label} blocked at execution gate — enable supervisor or use harness --confirm-execution"
                    )
                if isinstance(result, dict):
                    if result.get("status") == "error":
                        import_phase_failures.append(
                            f"{phase_label}: {result.get('error', 'unknown error')}"
                        )
                    elif result.get("steps_failed", 0) > 0:
                        import_phase_failures.append(
                            f"{phase_label}: {result.get('steps_failed')} step(s) failed"
                        )
                if workflow.patched("is-quality-gate-always-scheduled"):
                    await self._run_is_quality_gate(
                        "execute_import_phase",
                        result if isinstance(result, dict) else {"status": str(result)},
                        project_id,
                        L,
                        actual_outputs={
                            "phase_id": phase_id,
                            "phase_label": phase_label,
                            "result": result if isinstance(result, dict) else {"raw": str(result)},
                        },
                    )
                L.info("      └── ✅ %s → %s", phase_label, result)
            except Exception as e:
                L.info("      └── ❌ %s FAILED: %s", phase_label, e)
                import_phase_failures.append(f"{phase_label}: {e}")
                import_phases_aborted = True

        _kv(L, "reads from", "is_import_plans, R2 extracted rows")
        _kv(L, "tables written", "is_import_logs (per step), is_import_plans (status)")
        _kv(L, "audit", "is_audit_trail → import_executed")
        if import_phases_aborted or import_phase_failures:
            _step_fail(
                L, 13, "Execute Import Phases",
                "; ".join(import_phase_failures) or "phase aborted",
            )
        else:
            _step_ok(L, 5, "Execute Import Phases", f"phases executed (dry_run={sb.dry_run})")
        import_phases_succeeded = not import_phases_aborted and not import_phase_failures

        # ══════════════════════════════════════════════════════════════════════
        # STEP 13.5 / 14  —  CVS Bootstrap (Baseline Sync + Webhook Registration)
        # ══════════════════════════════════════════════════════════════════════
        # Now that ERPNext has all data imported, we:
        #   a) Run the baseline force-sync to populate Supabase CVS tables.
        #   b) Register Frappe webhooks so all future changes arrive in real-time.
        # This activates the full EDA pipeline for this project.
        # ══════════════════════════════════════════════════════════════════════
        _step_start(L, "13.5", "CVS Bootstrap — Baseline Sync + Webhook Registration",
                    "Seeding Supabase CVS tables and activating real-time event pipeline")

        if not import_phases_succeeded:
            _step_fail(L, "13.5", "CVS Bootstrap", "Skipped — import phases did not complete successfully")
            L.info("      ⚠️  CVS bootstrap skipped. Run /api/cvs/force-sync manually once IS is complete.")
        else:
            cvs_bootstrap_ok = False
            try:
                # a) Trigger baseline CVS force-sync via Temporal workflow
                #    We call the launcher activity directly rather than starting a workflow,
                #    since the IS worker doesn't have direct Temporal client access in activities.
                #    The force-sync endpoint does this asynchronously; we fire and move on.
                # Note: We do not import OS or perform DB fetches here to avoid sandbox violations.
                force_sync_result = await workflow.execute_activity(
                    "cvs_force_sync_for_project",
                    args=[{
                        "project_id":   project_id,
                        "company_slug": self._company_slug,
                    }],
                    task_queue             = "cvs-main-queue",
                    start_to_close_timeout = timedelta(seconds=30),
                    retry_policy           = _RETRY,
                )
                _kv(L, "cvs_force_sync", force_sync_result.get("workflow_id", "started"))

                # b) Register Frappe webhooks on the customer's ERPNext instance
                webhook_secret = f"f3cvs-{project_id[:8]}"  # deterministic per project
                webhook_result = await workflow.execute_activity(
                    register_frappe_webhooks,
                    args=[{
                        "project_id":     project_id,
                        "erp_url":        sb.erpnext_base_url or "",
                        "api_key":        sb.erpnext_api_key or "",
                        "api_secret":     "",   # resolved from deployment_details in the activity
                        "webhook_secret": webhook_secret,
                    }],
                    task_queue             = "cvs-main-queue",
                    start_to_close_timeout = timedelta(seconds=120),
                    retry_policy           = _RETRY,
                )
                _kv(L, "webhooks_registered", webhook_result.get("registered"))
                _kv(L, "webhooks_skipped",    webhook_result.get("skipped"))
                _kv(L, "webhooks_failed",     webhook_result.get("failed"))

                cvs_bootstrap_ok = True
                _step_ok(L, "13.5", "CVS Bootstrap",
                         f"sync started + {webhook_result.get('registered')} webhooks registered")

            except Exception as e:
                # Non-fatal — IS succeeded; CVS bootstrap can be re-run via force-sync
                _step_fail(L, "13.5", "CVS Bootstrap", str(e))
                L.info("      ⚠️  CVS bootstrap failed but IS is complete. "
                       "Run /api/cvs/force-sync manually to seed context.")

        # ══════════════════════════════════════════════════════════════════════
        # STEP 14 / 14  —  Complete Session
        # ══════════════════════════════════════════════════════════════════════
        _step_start(L, 14, "Complete Session", "Final status update")

        final_stage = "complete_with_errors" if import_phase_failures else "complete"
        self._stage = final_stage
        try:
            await workflow.execute_activity(
                persist_session,
                CompleteSessionInput(session_id=self._session_id, status=self._stage),
                **_ACT,
            )
            _kv(L, "table", "is_sessions")
            _kv(L, "status", final_stage)
            if import_phase_failures:
                _kv(L, "import_failures", "; ".join(import_phase_failures))
            _kv(L, "completed_at", "now()")
            _step_ok(L, 14, "Complete Session", final_stage.upper())
        except Exception as e:
            _step_fail(L, 14, "Complete Session", str(e))

        # ══════════════════════════════════════════════════════════════════════
        # WORKFLOW COMPLETE
        # ══════════════════════════════════════════════════════════════════════
        L.info("")
        L.info("╔" + "═" * 70 + "╗")
        if import_phase_failures:
            L.info("║   IMPLEMENTATION SYSTEM — WORKFLOW COMPLETE (WITH ERRORS) ⚠️         ║")
        else:
            L.info("║   IMPLEMENTATION SYSTEM — WORKFLOW COMPLETE ✅                      ║")
        L.info("║   project   : %-54s ║", project_id)
        L.info("║   session   : %-54s ║", self._session_id)
        L.info("║   final     : %-54s ║", final_stage)
        L.info("╚" + "═" * 70 + "╝")
        L.info("")

        return {
            "project_id": project_id,
            "session_id": self._session_id,
            "stage": final_stage,
            "import_failures": import_phase_failures,
        }