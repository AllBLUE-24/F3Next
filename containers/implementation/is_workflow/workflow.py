"""
IS Workflow — Temporal workflow for the full ERPNext implementation pipeline.

Human-in-the-loop flow:
  1. Workflow starts with project_id
  2. Signal: files_uploaded       → run signals inference
  3. Signal: f3iche_confirmed     → build profile + target structure
  4. Signal: files_mapped         → ingest mapping results, run validation
  5. Signal: validation_submitted → resolve issues, build import plan
  6. Signal: sandbox_approved     → execute live import (phase A → B → C)

Queries expose read-only state to the launcher at any point.
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


TASK_QUEUE = "is-queue"

_RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0)
_ACT   = {"start_to_close_timeout": timedelta(minutes=5), "retry_policy": _RETRY}
_LONG  = {"start_to_close_timeout": timedelta(minutes=30), "retry_policy": _RETRY}


# ── Signal / query payloads ───────────────────────────────────────────────────

@dataclass
class FilesUploadedSignal:
    uploaded_files: List[Dict]
    file_contents: Optional[Dict[str, str]] = None   # filename → raw text


@dataclass
class F3icheConfirmedSignal:
    f3iche_user: str
    industry: str
    industry_sub: Optional[str] = None
    company_name: Optional[str] = None
    company_size: Optional[str] = None


@dataclass
class FilesMappedSignal:
    mapped_data: Dict[str, Any]   # {doctype: {field_mapping, rows, ...}}


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
    """
    Long-running workflow for one company's ERPNext implementation.
    ID convention: impl-{project_id}
    """

    def __init__(self) -> None:
        # Mutable workflow state
        self._profile: Dict[str, Any] = {}
        self._target_structure: Optional[Dict] = None
        self._mapped_data: Dict[str, Any] = {}
        self._validation_report: Optional[Dict] = None
        self._import_plan: Optional[Dict] = None
        self._import_results: List[Dict] = []
        self._stage: str = "awaiting_files"      # coarse UI stage
        self._analysis_tasks: List[Dict] = []    # granular task list for /analyze page

        # Signal gates
        self._files_uploaded_event     = asyncio.Event()
        self._f3iche_confirmed_event   = asyncio.Event()
        self._files_mapped_event       = asyncio.Event()
        self._validation_submitted_event = asyncio.Event()
        self._sandbox_approved_event   = asyncio.Event()

        # Signal payloads
        self._sig_files:      Optional[FilesUploadedSignal]      = None
        self._sig_f3iche:     Optional[F3icheConfirmedSignal]    = None
        self._sig_mapped:     Optional[FilesMappedSignal]        = None
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
    async def files_mapped(self, sig: FilesMappedSignal) -> None:
        self._sig_mapped = sig
        self._files_mapped_event.set()

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
    def get_profile(self) -> Dict[str, Any]:
        return self._profile

    @workflow.query
    def get_analysis_tasks(self) -> List[Dict]:
        return self._analysis_tasks

    @workflow.query
    def get_validation_report(self) -> Optional[Dict]:
        return self._validation_report

    @workflow.query
    def get_import_plan(self) -> Optional[Dict]:
        return self._import_plan

    @workflow.query
    def get_import_results(self) -> List[Dict]:
        return self._import_results

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

        # ── Stage 1: Await file upload ─────────────────────────────────────
        self._stage = "awaiting_files"
        await workflow.wait_condition(lambda: self._files_uploaded_event.is_set())
        sig = self._sig_files

        self._set_task("t1", "running")
        n_files = len(sig.uploaded_files)
        self._set_task("t1", "done", f"{n_files} file(s) received")
        self._set_task("t2", "running")
        self._stage = "analyzing"

        # ── Stage 2: Signals inference ────────────────────────────────────
        infer_result: Dict = await workflow.execute_activity(
            infer_f3iche,
            InferF3icheInput(sig.uploaded_files, sig.file_contents),
            **_ACT,
        )
        self._set_task("t2", "done", f"Confidence: {infer_result['confidence']*100:.0f}%")
        self._set_task("t3", "running")
        self._set_task("t4", "running")

        # Partial profile (pre-confirmation)
        self._profile = {
            "project_id": project_id,
            "version": 1,
            "f3iche_signals": infer_result["f3iche"],
            "f3iche_match_status": "pending_clarification",
            "uploaded_files": sig.uploaded_files,
            "collected_signals": infer_result["collected_signals"],
        }
        self._set_task("t3", "done", f"Signals: {len(infer_result['collected_signals'])}")
        self._set_task("t4", "done", f"Inferred: {infer_result['f3iche']}")
        self._stage = "awaiting_f3iche_confirmation"

        # ── Stage 3: Await user F3iche confirmation ───────────────────────
        await workflow.wait_condition(lambda: self._f3iche_confirmed_event.is_set())
        conf = self._sig_f3iche

        # Verify user vs inferred
        verify_result: Dict = await workflow.execute_activity(
            verify_f3iche,
            VerifyF3icheInput(conf.f3iche_user, infer_result["f3iche"], infer_result["confidence"]),
            **_ACT,
        )

        # Build full profile (v1)
        self._set_task("t5", "running")
        profile_snapshot: Dict = await workflow.execute_activity(
            build_company_profile,
            BuildProfileInput(
                project_id=project_id,
                version=1,
                f3iche=conf.f3iche_user,
                industry=conf.industry,
                action="create",
                industry_sub=conf.industry_sub,
                company_name=conf.company_name,
                company_size=conf.company_size,
                f3iche_user=conf.f3iche_user,
                f3iche_signals=infer_result["f3iche"],
                f3iche_match_status=verify_result["status"],
                uploaded_files=sig.uploaded_files,
                collected_signals=infer_result["collected_signals"],
            ),
            **_ACT,
        )
        self._profile = profile_snapshot

        # Build target structure
        target: Dict = await workflow.execute_activity(
            build_target_structure,
            BuildTargetStructureInput(conf.f3iche_user, conf.industry),
            **_ACT,
        )
        self._target_structure = target
        self._profile["target_structure"] = target
        self._set_task("t5", "done", f"{len(target.get('required_doctypes', []))} doctypes resolved")
        self._stage = "awaiting_file_mapping"

        # ── Stage 4: Await mapped file data ──────────────────────────────
        await workflow.wait_condition(lambda: self._files_mapped_event.is_set())
        self._mapped_data = self._sig_mapped.mapped_data
        self._set_task("t6", "done", f"{len(self._mapped_data)} doctype(s) mapped")

        # ── Stage 5: Validate ─────────────────────────────────────────────
        self._set_task("t7", "running")
        self._stage = "validating"
        validation_report: Dict = await workflow.execute_activity(
            validate_mapped_data,
            ValidateInput(self._mapped_data, self._target_structure),
            **_ACT,
        )
        self._validation_report = validation_report
        self._profile["validation_report"] = validation_report
        v_status = validation_report.get("overall", "pass")
        n_errors = len(validation_report.get("errors", []))
        self._set_task("t7", "done", f"{v_status} — {n_errors} error(s)")
        self._stage = "awaiting_validation_submission"

        # ── Stage 6: Await human validation resolution ────────────────────
        await workflow.wait_condition(lambda: self._validation_submitted_event.is_set())
        vsub = self._sig_validation

        # Merge any profile edits the user made on the validate page
        if vsub.profile_edits:
            self._profile = await workflow.execute_activity(
                merge_company_profile,
                MergeProfileInput(existing_profile=self._profile, patch=vsub.profile_edits, action="user_edit"),
                **_ACT,
            )

        # Build import plan
        self._set_task("t8", "running")
        import_plan: Dict = await workflow.execute_activity(
            build_import_plan,
            BuildImportPlanInput(self._target_structure, self._mapped_data, self._validation_report),
            **_ACT,
        )
        self._import_plan = import_plan
        self._set_task("t8", "done", f"{import_plan.get('total_steps', 0)} steps queued")
        self._stage = "awaiting_sandbox_approval"

        # ── Stage 7: Await sandbox approval → live import ────────────────
        await workflow.wait_condition(lambda: self._sandbox_approved_event.is_set())
        sb = self._sig_sandbox
        self._stage = "importing"

        for phase_def in import_plan.get("phases", []):
            phase_result: Dict = await workflow.execute_activity(
                execute_import_phase,
                ExecutePhaseInput(
                    phase_id=phase_def["phase"],
                    steps=phase_def["steps"],
                    dry_run=sb.dry_run,
                    erpnext_base_url=sb.erpnext_base_url,
                    erpnext_api_key=sb.erpnext_api_key,
                ),
                **_LONG,
            )
            self._import_results.append(phase_result)

        self._stage = "complete"
        return {
            "project_id": project_id,
            "profile": self._profile,
            "import_results": self._import_results,
            "stage": "complete",
        }