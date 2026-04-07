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
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from containers.implementation.signals_agent.activities    import infer_f3iche, verify_f3iche, InferF3icheInput, VerifyF3icheInput
    from containers.implementation.profile_agent.activities    import build_company_profile, merge_company_profile, BuildProfileInput, MergeProfileInput
    from containers.implementation.target_agent.activities     import build_target_structure, BuildTargetStructureInput
    from containers.implementation.mapping_agent.activities    import map_file_to_erpnext, MapFileInput
    from containers.implementation.validation_agent.activities import validate_mapped_data, ValidateInput
    from containers.implementation.import_agent.activities     import build_import_plan, execute_import_phase, BuildImportPlanInput, ExecutePhaseInput
    from containers.implementation.virus_scan_agent.activities import virus_scan_quarantine
    from containers.implementation.file_io.fetch_clean_files   import fetch_clean_files, FetchCleanFilesInput
    from containers.implementation.file_io.persist_session     import persist_session, PersistSessionInput

TASK_QUEUE = "is-queue"

_RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0)
_ACT   = {"start_to_close_timeout": timedelta(minutes=5), "retry_policy": _RETRY}
_LONG  = {"start_to_close_timeout": timedelta(minutes=30), "retry_policy": _RETRY}


# ── Signal / query payloads ───────────────────────────────────────────────────

@dataclass
class FilesUploadedSignal:
    uploaded_files: List[Dict]
    company_slug: Optional[str] = None


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
class SandboxApprovedSignal:
    erpnext_base_url: str
    erpnext_api_key: str
    dry_run: bool = False


# ── Workflow ──────────────────────────────────────────────────────────────────

@workflow.defn(name="ImplementationWorkflow")
class ImplementationWorkflow:
    def __init__(self) -> None:
        # PURE ORCHESTRATION STATE (No massive dicts)
        self._session_id: str = ""
        self._stage: str = "awaiting_files"
        self._analysis_tasks: List[Dict] = []
        self._company_slug: str = "unknown"

        # Signal gates
        self._files_uploaded_event     = asyncio.Event()
        self._f3iche_confirmed_event   = asyncio.Event()
        self._validation_submitted_event = asyncio.Event()
        self._sandbox_approved_event   = asyncio.Event()

        # Signal payloads
        self._sig_files:      Optional[FilesUploadedSignal]      = None
        self._sig_f3iche:     Optional[F3icheConfirmedSignal]    = None
        self._sig_validation: Optional[ValidationSubmittedSignal] = None
        self._sig_sandbox:    Optional[SandboxApprovedSignal]    = None

    # ── Signals ──────────────────────────────────────────────────────────────

    @workflow.signal
    async def files_uploaded(self, sig: FilesUploadedSignal) -> None:
        self._sig_files = sig
        self._files_uploaded_event.set()

    @workflow.signal
    async def f3iche_confirmed(self, sig: F3icheConfirmedSignal) -> None:
        self._sig_f3iche = sig
        self._f3iche_confirmed_event.set()

    @workflow.signal
    async def validation_submitted(self, sig: ValidationSubmittedSignal) -> None:
        self._sig_validation = sig
        self._validation_submitted_event.set()

    @workflow.signal
    async def sandbox_approved(self, sig: SandboxApprovedSignal) -> None:
        self._sig_sandbox = sig
        self._sandbox_approved_event.set()

    # ── Queries ───────────────────────────────────────────────────────────────

    @workflow.query
    def get_stage(self) -> str:
        return self._stage

    @workflow.query
    def get_analysis_tasks(self) -> List[Dict]:
        return self._analysis_tasks

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

    # ── Main run ─────────────────────────────────────────────────────────────

    @workflow.run
    async def run(self, project_id: str) -> Dict[str, Any]:
        workflow_id = workflow.info().workflow_id
        workflow.logger.info("═══ ImplementationWorkflow STARTED | project=%s ═══", project_id)

        # ── 0. Create session in Supabase ────────────────────────────────────
        try:
            self._session_id = await workflow.execute_activity(
                persist_session,
                PersistSessionInput(project_id=project_id, workflow_id=workflow_id, status="awaiting_files"),
                **_ACT,
            )
        except Exception as e:
            workflow.logger.error("❌ persist_session FAILED: %s", e)
            return {"error": f"Failed to initialize session: {e}"}

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

        # ── Stage 1: Await file upload ───────────────────────────────────────
        self._stage = "awaiting_files"
        workflow.logger.info("⏳ Stage 1 | awaiting_files — waiting for files_uploaded signal")
        await workflow.wait_condition(lambda: self._files_uploaded_event.is_set())
        sig = self._sig_files
        workflow.logger.info("📥 Stage 1 | files_uploaded signal received — %d files", len(sig.uploaded_files))

        self._set_task("t1", "running")

        # ---> VIRUS SCANNING (S3 Tri-Bucket Protocol) <---
        try:
            scan_result: Dict = await workflow.execute_activity(
                virus_scan_quarantine,
                sig.uploaded_files,
                **_ACT,
            )
        except Exception as e:
            workflow.logger.error("❌ virus_scan_quarantine FAILED: %s", e)
            self._stage = "error"
            return {"error": f"Virus scan failed: {e}"}

        if not scan_result.get("safe", False):
            self._stage = "infected_halt"
            return {"error": "Implementation halted due to malicious payload."}

        self._company_slug = sig.company_slug or "unknown"
        workflow.logger.info("✅ Stage 1 done | slug=%s", self._company_slug)

        # ── Stage 1b: Fetch file text to R2 manifest ─────────────────────────
        self._set_task("t1", "done")
        self._set_task("t2", "running")
        self._stage = "analyzing"
        
        try:
            fetch_results: Dict = await workflow.execute_activity(
                fetch_clean_files,
                FetchCleanFilesInput(uploaded_files=sig.uploaded_files, project_id=project_id, company_slug=self._company_slug),
                **_ACT,
            )
            r2_manifest_url = fetch_results.get("manifest_url", "error")
            self._parsed_files = fetch_results.get("parsed_files", [])
        except Exception as e:
            workflow.logger.warning("⚠️ fetch_clean_files failed: %s", e)
            r2_manifest_url = "error"
            self._parsed_files = []

        # ── Stage 2: Signals inference ───────────────────────────────────────
        workflow.logger.info("🔬 Stage 2 | Running infer_f3iche")
        try:
            infer_result: Dict = await workflow.execute_activity(
                infer_f3iche,
                InferF3icheInput(sig.uploaded_files, r2_manifest_url),
                **_ACT,
            )
        except Exception as e:
            workflow.logger.error("❌ infer_f3iche FAILED: %s", e)
            self._stage = "error"
            return {"error": f"F3iche inference failed: {e}"}

        self._set_task("t2", "done")
        self._set_task("t3", "done")
        self._set_task("t4", "done", f"Inferred: {infer_result['f3iche']}")
        
        self._stage = "awaiting_f3iche_confirmation"
        # Update session status
        try:
            await workflow.execute_activity(
                persist_session,
                PersistSessionInput(project_id=project_id, workflow_id=workflow_id, status=self._stage),
                **_ACT,
            )
        except: pass

        # ── Stage 3: Await user F3iche confirmation ──────────────────────────
        await workflow.wait_condition(lambda: self._f3iche_confirmed_event.is_set())
        conf = self._sig_f3iche
        self._stage = "building_profile"
        self._set_task("t5", "running")

        # Verify user vs inferred
        try:
            verify_result: Dict = await workflow.execute_activity(
                verify_f3iche,
                VerifyF3icheInput(conf.f3iche_user, infer_result["f3iche"], infer_result["confidence"]),
                **_ACT,
            )
        except Exception as e:
            workflow.logger.error("❌ verify_f3iche FAILED: %s", e)

        # Build full profile (persists to Supabase + R2 automatically)
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
                    f3iche_match_status=verify_result["status"] if "verify_result" in locals() else "unknown",
                    uploaded_files=sig.uploaded_files,
                    r2_manifest_url=r2_manifest_url,
                    collected_signals=infer_result["collected_signals"],
                ),
                **_ACT,
            )
        except Exception as e:
            workflow.logger.error("❌ build_company_profile FAILED: %s", e)
            self._stage = "error"
            return {"error": f"Profile build failed: {e}"}

        # Build target structure (persists to Supabase via persist_session)
        try:
            target: Dict = await workflow.execute_activity(
                build_target_structure,
                BuildTargetStructureInput(conf.f3iche_user, conf.industry),
                **_ACT,
            )
            await workflow.execute_activity(
                persist_session,
                PersistSessionInput(project_id=project_id, workflow_id=workflow_id, status="mapping", target_structure=target),
                **_ACT,
            )
        except Exception as e:
            workflow.logger.error("❌ target_structure FAILED: %s", e)
            self._stage = "error"
            return {"error": f"Target structure failed: {e}"}

        self._set_task("t5", "done", f"{len(target.get('required_doctypes', []))} doctypes target")
        
        # ── Stage 4: Automated file mapping ──────────────────────────────────
        self._stage = "mapping_files"
        self._set_task("t6", "running")
        workflow.logger.info("🔧 Stage 4 | Running automated map_file_to_erpnext")
        
        mapped_count = 0
        for fname in self._parsed_files:
            try:
                mapped_doctype: str = await workflow.execute_activity(
                    map_file_to_erpnext,
                    MapFileInput(
                        r2_manifest_url=r2_manifest_url,
                        filename=fname,
                        project_id=project_id,
                        company_slug=self._company_slug,
                        session_id=self._session_id,
                    ),
                    **_ACT,
                )
                if mapped_doctype not in ["error", "unmapped"]:
                    mapped_count += 1
            except Exception as e:
                workflow.logger.warning("  ⚠️ map_file_to_erpnext failed: %s", e)

        self._set_task("t6", "done", f"{mapped_count} files mapped")

        # ── Stage 5: Validate ────────────────────────────────────────────────
        self._set_task("t7", "running")
        self._stage = "validating"
        workflow.logger.info("🔍 Stage 5 | Running validate_mapped_data")
        
        try:
            v_status: str = await workflow.execute_activity(
                validate_mapped_data,
                ValidateInput(session_id=self._session_id, project_id=project_id, company_slug=self._company_slug),
                **_ACT,
            )
        except Exception as e:
            workflow.logger.error("❌ validate_mapped_data FAILED: %s", e)
            self._stage = "error"
            return {"error": f"Validation failed: {e}"}

        self._set_task("t7", "done", f"Status: {v_status}")
        self._stage = "awaiting_validation_submission"

        # ── Stage 6: Await human validation resolution ───────────────────────
        await workflow.wait_condition(lambda: self._validation_submitted_event.is_set())
        vsub = self._sig_validation
        
        # Merge profile edits if any
        if vsub.profile_edits:
            try:
                await workflow.execute_activity(
                    merge_company_profile,
                    MergeProfileInput(session_id=self._session_id, patch=vsub.profile_edits, action="user_edit"),
                    **_ACT,
                )
            except Exception as e:
                workflow.logger.error("❌ merge_company_profile FAILED: %s", e)

        # Build import plan
        self._set_task("t8", "running")
        try:
            plan_status: str = await workflow.execute_activity(
                build_import_plan,
                BuildImportPlanInput(session_id=self._session_id, project_id=project_id, company_slug=self._company_slug),
                **_ACT,
            )
        except Exception as e:
            workflow.logger.error("❌ build_import_plan FAILED: %s", e)
            self._stage = "error"
            return {"error": f"Import plan build failed: {e}"}

        if plan_status == "blocked":
            workflow.logger.warning("⚠️ Import plan is blocked due to validation failures.")
            
        self._set_task("t8", "done", f"Status: {plan_status}")
        self._stage = "awaiting_sandbox_approval"

        # ── Stage 7: Await sandbox approval → live import ────────────────────
        await workflow.wait_condition(lambda: self._sandbox_approved_event.is_set())
        sb = self._sig_sandbox
        self._stage = "importing"
        
        # We know there are 3 standard phases (A, B, C)
        phases = ["phase_a_config", "phase_b_master", "phase_c_transactional"]
        for phase in phases:
            try:
                await workflow.execute_activity(
                    execute_import_phase,
                    ExecutePhaseInput(
                        session_id=self._session_id,
                        phase_id=phase,
                        project_id=project_id,
                        company_slug=self._company_slug,
                        dry_run=sb.dry_run,
                        erpnext_base_url=sb.erpnext_base_url,
                        erpnext_api_key=sb.erpnext_api_key,
                    ),
                    **_LONG,
                )
            except Exception as e:
                workflow.logger.error("❌ execute_import_phase FAILED for %s: %s", phase, e)

        self._stage = "complete"
        try:
            await workflow.execute_activity(
                persist_session,
                PersistSessionInput(project_id=project_id, workflow_id=workflow_id, status=self._stage),
                **_ACT,
            )
        except: pass

        workflow.logger.info("═══ ImplementationWorkflow COMPLETE | project=%s ═══", project_id)
        return {
            "project_id": project_id,
            "session_id": self._session_id,
            "stage": "complete",
        }