"""
Implementation Launcher — connects the FastAPI layer to the Temporal IS workflow.

v2: Queries from normalised tables (ISCompanyProfile, ISValidationResult,
    ISImportPlan, ISImportLog) instead of old ISMapping/ISImportRun.
"""
from __future__ import annotations
import os
from dotenv import load_dotenv
load_dotenv()

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from temporalio.client import Client, WorkflowHandle
from temporalio.exceptions import WorkflowAlreadyStartedError
from sqlalchemy import select, update

from shared.database.db import AsyncSessionLocal
from shared.models.is_models import (
    ISSession, ISCompanyProfile, ISTargetStructure, ISDataReadinessAssessment,
    ISMappedData, ISFieldMapping, ISValidationResult, ISValidationError,
    ISImportPlan, ISImportLog, ISSupervisorPrompt, ISAuditTrail,
)
from shared.models.hooks import Hook

from containers.implementation.is_workflow.workflow import (
    ImplementationWorkflow,
    TASK_QUEUE,
    FilesUploadedSignal,
    F3icheConfirmedSignal,
    MappingConfirmedSignal,
    ValidationSubmittedSignal,
    SandboxApprovedSignal,
    SupervisorResponseSignal,
)

logger = logging.getLogger(__name__)

TEMPORAL_HOST = os.getenv("TEMPORAL_HOST")
_client: Optional[Client] = None

def _wf_id(project_id: str | UUID) -> str:
    return f"impl-{project_id}"

async def _get_client() -> Client:
    global _client
    if _client is None:
        host = os.getenv("TEMPORAL_HOST", TEMPORAL_HOST)
        _client = await Client.connect(host)
        logger.info("Temporal client connected to %s", host)
    return _client


class ImplementationLauncher:
    def __init__(self):
        pass

    async def _resolve_project_id(self, input_id: str | UUID) -> UUID:
        """
        Accepts either a project_id or a session_id.
        Queries the database to check if input_id is a session_id.
        If yes, returns the corresponding project_id.
        Otherwise, returns the input_id as a UUID.
        """
        try:
            val_uuid = UUID(str(input_id))
        except ValueError:
            return input_id

        async with AsyncSessionLocal() as session:
            # Check if there is a session with this ID
            stmt = select(ISSession).where(ISSession.id == val_uuid)
            res = await session.execute(stmt)
            is_session = res.scalar_one_or_none()
            if is_session:
                return is_session.project_id
            
            # If not a session ID, assume it is a project ID
            return val_uuid

    async def _handle(self, project_id: str | UUID) -> WorkflowHandle:
        resolved_project_id = await self._resolve_project_id(project_id)
        client = await _get_client()
        return client.get_workflow_handle(_wf_id(resolved_project_id))

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self, project_id: str | UUID) -> Dict[str, Any]:
        resolved_project_id = await self._resolve_project_id(project_id)
        client = await _get_client()
        wf_id = _wf_id(resolved_project_id)
        
        discovery_meta = None
        async with AsyncSessionLocal() as session:
            stmt = select(Hook).where(Hook.project_id == UUID(str(resolved_project_id)))
            res = await session.execute(stmt)
            hook = res.scalar_one_or_none()
            if hook and hook.discovery_metadata:
                discovery_meta = hook.discovery_metadata

        try:
            handle = await client.start_workflow(
                ImplementationWorkflow.run,
                args=[str(resolved_project_id), discovery_meta],
                id=wf_id,
                task_queue=TASK_QUEUE,
            )
            return {"workflow_id": wf_id, "run_id": handle.first_execution_run_id, "started": True}
        except WorkflowAlreadyStartedError:
            return {"workflow_id": wf_id, "started": False, "detail": "Workflow already running"}

    async def terminate(self, project_id: str | UUID, reason: str = "cancelled") -> None:
        handle = await self._handle(project_id)
        await handle.terminate(reason=reason)

    # ── Signals ───────────────────────────────────────────────────────────────

    async def signal_files_uploaded(
        self,
        project_id: str | UUID,
        uploaded_files: List[Dict],
        company_slug: Optional[str] = None,
        user_note: Optional[str] = None,
    ) -> None:
        is_session = await self._get_session(project_id)
        if is_session:
            file_batches = list(is_session.file_batches or [])
            batch_index = len(file_batches) + 1
            file_batches.append({
                "batch_index": batch_index,
                "uploaded_at": datetime.utcnow().isoformat() + "Z",
                "files": uploaded_files,
                "note": user_note or "",
            })

            user_notes = list(is_session.user_notes or [])
            if user_note:
                user_notes.append({
                    "type": "initial_upload",
                    "batch_index": batch_index,
                    "note": user_note,
                    "uploaded_at": datetime.utcnow().isoformat() + "Z",
                })

            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(ISSession)
                    .where(ISSession.id == is_session.id)
                    .values(
                        file_batches=file_batches,
                        user_notes=user_notes,
                        user_import_note=user_note or is_session.user_import_note,
                        updated_at=datetime.utcnow(),
                    )
                )
                await session.commit()

        handle = await self._handle(project_id)
        await handle.signal(
            ImplementationWorkflow.files_uploaded,
            FilesUploadedSignal(
                uploaded_files=uploaded_files,
                company_slug=company_slug,
                user_note=user_note,
            ),
        )

    async def get_f3iche_confirmation(self, project_id: str | UUID) -> Dict[str, Any]:
        """Return synthesis proposal for the f3iche confirmation gate."""
        try:
            handle = await self._handle(project_id)
            confirmation = await handle.query(ImplementationWorkflow.get_f3iche_confirmation)
            if confirmation:
                return confirmation
        except Exception as exc:
            logger.debug("Workflow f3iche confirmation query failed: %s", exc)

        # Fallback: latest audit trail entry
        is_session = await self._get_session(project_id)
        if not is_session:
            return {}
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISAuditTrail)
                .where(
                    ISAuditTrail.session_id == is_session.id,
                    ISAuditTrail.action == "f3iche_confirmation_synthesized",
                )
                .order_by(ISAuditTrail.created_at.desc())
                .limit(1)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row and row.details:
                return dict(row.details)
        return {}

    async def confirm_f3iche(
        self,
        project_id: str | UUID,
        *,
        accepted: bool,
        correction_text: Optional[str] = None,
        f3iche_user: Optional[str] = None,
        industry: Optional[str] = None,
        industry_sub: Optional[str] = None,
        company_name: Optional[str] = None,
        company_size: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve user yes/no on f3iche synthesis and signal the workflow."""
        synthesis = await self.get_f3iche_confirmation(project_id)

        if accepted:
            resolved_f3iche = f3iche_user or synthesis.get("proposed_f3iche") or ""
            resolved_industry = industry or synthesis.get("proposed_industry") or "general"
        else:
            if not correction_text or not correction_text.strip():
                raise ValueError("correction_text is required when accepted=false")
            from containers.implementation.signals_agent.f3iche_confirmation_activities import (
                ResolveF3icheCorrectionInput,
                resolve_f3iche_correction_core,
            )
            is_session = await self._get_session(project_id)
            resolved = await resolve_f3iche_correction_core(
                ResolveF3icheCorrectionInput(
                    correction_text=correction_text.strip(),
                    synthesis=synthesis,
                    session_id=str(is_session.id) if is_session else None,
                )
            )
            resolved_f3iche = resolved.get("f3iche") or synthesis.get("proposed_f3iche") or ""
            resolved_industry = resolved.get("industry") or synthesis.get("proposed_industry") or "general"

        if not resolved_f3iche:
            raise ValueError("Could not resolve f3iche for confirmation")

        from containers.implementation.signals_agent.discovery_context import load_discovery_context
        from containers.implementation.profile_agent.profile_identity import resolve_profile_identity
        from shared.models.core import Project

        is_session = await self._get_session(project_id)
        discovery_ctx: Dict[str, Any] = {}
        company_slug: Optional[str] = None
        if is_session:
            async with AsyncSessionLocal() as session:
                discovery_ctx = await load_discovery_context(
                    db=session,
                    project_id=str(is_session.project_id),
                    session_row=is_session,
                )
                proj = (
                    await session.execute(
                        select(Project).where(Project.id == is_session.project_id)
                    )
                ).scalar_one_or_none()
                if proj and proj.company_slug:
                    company_slug = proj.company_slug

        identity = resolve_profile_identity(
            company_slug=company_slug,
            company_name=company_name,
            industry=resolved_industry,
            industry_sub=industry_sub,
            company_size=company_size,
            discovery_ctx=discovery_ctx,
            synthesis=synthesis,
        )

        await self.signal_f3iche_confirmed(
            project_id,
            resolved_f3iche,
            identity["industry"] or resolved_industry,
            industry_sub=identity["industry_sub"] or industry_sub,
            company_name=identity["company_name"] or company_name,
            company_size=identity["company_size"] or company_size,
        )
        return {
            "f3iche_user": resolved_f3iche,
            "industry": identity["industry"] or resolved_industry,
            "industry_sub": identity["industry_sub"],
            "company_name": identity["company_name"],
            "company_size": identity["company_size"],
            "accepted": accepted,
        }

    async def signal_f3iche_confirmed(
        self,
        project_id: str | UUID,
        f3iche_user: str,
        industry: str,
        industry_sub: Optional[str] = None,
        company_name: Optional[str] = None,
        company_size: Optional[str] = None,
    ) -> None:
        handle = await self._handle(project_id)
        await handle.signal(
            ImplementationWorkflow.f3iche_confirmed,
            F3icheConfirmedSignal(
                f3iche_user=f3iche_user,
                industry=industry,
                industry_sub=industry_sub,
                company_name=company_name,
                company_size=company_size,
            ),
        )

    async def signal_mapping_confirmed(
        self,
        project_id: str | UUID,
        user_feedback: Optional[str] = None,
        approved: bool = False,
    ) -> None:
        handle = await self._handle(project_id)
        await handle.signal(
            ImplementationWorkflow.mapping_confirmed,
            MappingConfirmedSignal(
                user_feedback=user_feedback,
                approved=approved,
            ),
        )

    async def signal_validation_submitted(
        self,
        project_id: str | UUID,
        responses: Dict[str, Any],
        profile_edits: Optional[Dict[str, Any]] = None,
        note: Optional[str] = None,
    ) -> None:
        handle = await self._handle(project_id)
        await handle.signal(
            ImplementationWorkflow.validation_submitted,
            ValidationSubmittedSignal(
                responses=responses,
                profile_edits=profile_edits or {},
                note=note,
            ),
        )

    async def signal_sandbox_approved(
        self,
        project_id: str | UUID,
        erpnext_base_url: str,
        erpnext_api_key: str,
        dry_run: bool = False,
    ) -> None:
        from temporalio.service import RPCError
        handle = await self._handle(project_id)
        try:
            await handle.signal(
                ImplementationWorkflow.sandbox_approved,
                SandboxApprovedSignal(
                    erpnext_base_url=erpnext_base_url,
                    erpnext_api_key=erpnext_api_key,
                    dry_run=dry_run,
                ),
            )
        except RPCError as e:
            logger.warning(f"Failed to signal sandbox approved (likely completed/failed): {e}")

    async def signal_supervisor_response(
        self,
        project_id: str | UUID,
        prompt_id: str,
        chosen_action_id: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        handle = await self._handle(project_id)
        await handle.signal(
            ImplementationWorkflow.supervisor_response,
            SupervisorResponseSignal(
                prompt_id=prompt_id,
                chosen_action_id=chosen_action_id,
                extra_data=extra_data or {},
            ),
        )

    async def signal_validation_gap_upload_intent(
        self,
        project_id: str | UUID,
        *,
        selected_option: str = "Upload the missing files",
    ) -> None:
        """Tell the workflow the user is uploading missing MVP files (no DB prompt required)."""
        await self.signal_supervisor_response(
            project_id,
            prompt_id="validation_gap",
            chosen_action_id="ask_user_missing_mvp_files",
            extra_data={"selected_option": selected_option},
        )

    # ── Queries ───────────────────────────────────────────────────────────────

    async def get_stage(self, project_id: str | UUID) -> str:
        handle = await self._handle(project_id)
        return await handle.query(ImplementationWorkflow.get_stage)

    async def get_analysis_tasks(self, project_id: str | UUID) -> List[Dict]:
        handle = await self._handle(project_id)
        return await handle.query(ImplementationWorkflow.get_analysis_tasks)

    # ── Supabase State Reading (v2 schema) ────────────────────────────────────

    async def _get_session(self, project_id: str | UUID) -> Optional[ISSession]:
        resolved_project_id = await self._resolve_project_id(project_id)
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISSession)
                .where(ISSession.project_id == UUID(str(resolved_project_id)))
                .order_by(ISSession.created_at.desc())
                .limit(1)
            )
            res = await session.execute(stmt)
            return res.scalars().first()

    async def get_profile(self, project_id: str | UUID) -> Dict[str, Any]:
        """Query latest ISCompanyProfile for this project."""
        is_session = await self._get_session(project_id)
        if not is_session:
            return {}
        
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISCompanyProfile)
                .where(ISCompanyProfile.session_id == is_session.id)
                .order_by(ISCompanyProfile.version.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            profile = result.scalar_one_or_none()
            
            if not profile:
                return {}
            
            return {
                "version": profile.version,
                "f3iche": profile.f3iche,
                "industry": profile.industry,
                "industry_sub": profile.industry_sub,
                "company_name": profile.company_name,
                "company_size": profile.company_size,
                "workflows": profile.workflows,
                "modules": profile.required_modules,
                "required_doctypes": profile.required_doctypes,
                "business_reality": profile.business_reality,
                "context_flags": profile.context_flags,
                "data_quality_score": profile.data_quality_score,
                "llm_confidence": profile.llm_confidence,
                "r2_path": profile.r2_path,
            }

    async def _load_r2_json(self, bucket: str, key: str) -> Optional[Dict]:
        import json
        import boto3
        from botocore.config import Config

        if not key:
            return None
        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=os.getenv("R2_ENDPOINT"),
                aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
                config=Config(signature_version="s3v4"),
                region_name="auto",
            )
            obj = s3.get_object(Bucket=bucket, Key=key)
            return json.loads(obj["Body"].read().decode("utf-8"))
        except Exception as e:
            logger.warning("Failed to load R2 %s/%s: %s", bucket, key, e)
            return None

    async def get_validation_report(self, project_id: str | UUID) -> Optional[Dict]:
        """Canonical ValidationReport from R2 artifact + DB fallback."""
        from shared.models.validation_report import merge_db_checks_with_r2, normalize_validation_report

        is_session = await self._get_session(project_id)
        if not is_session:
            return None

        async with AsyncSessionLocal() as session:
            results = (
                await session.execute(
                    select(ISValidationResult)
                    .where(ISValidationResult.session_id == is_session.id)
                    .limit(50)
                )
            ).scalars().all()

            if not results:
                return None

            vr_ids = [vr.id for vr in results]
            mapped_data_ids = [vr.mapped_data_id for vr in results if vr.mapped_data_id]

            errors_by_vr_id: Dict[Any, List[Any]] = {}
            if vr_ids:
                err_rows = (
                    await session.execute(
                        select(ISValidationError)
                        .where(ISValidationError.validation_result_id.in_(vr_ids))
                        .limit(500)
                    )
                ).scalars().all()
                for e in err_rows:
                    errors_by_vr_id.setdefault(e.validation_result_id, []).append(e)

            md_by_id: Dict[Any, Any] = {}
            if mapped_data_ids:
                md_rows = (
                    await session.execute(
                        select(ISMappedData).where(ISMappedData.id.in_(mapped_data_ids))
                    )
                ).scalars().all()
                for md in md_rows:
                    md_by_id[md.id] = md

            db_checks: List[Dict[str, Any]] = []
            report_r2_path: Optional[str] = None

            for vr in results:
                if vr.report_r2_path and not report_r2_path:
                    report_r2_path = vr.report_r2_path
                errors = errors_by_vr_id.get(vr.id, [])
                check_errors = [e.error_message for e in errors if e.severity == "error"]
                check_warnings = [e.error_message for e in errors if e.severity == "warning"]

                source_files: List[str] = []
                if vr.mapped_data_id:
                    md = md_by_id.get(vr.mapped_data_id)
                    if md and md.source_filename:
                        source_files = [md.source_filename]

                db_checks.append(
                    {
                        "doctype": vr.doctype,
                        "status": vr.overall_status,
                        "errors": check_errors,
                        "warnings": check_warnings,
                        "row_count": vr.row_count or vr.total_records_checked or 0,
                        "source_files": source_files,
                    }
                )

            r2_report = None
            if report_r2_path:
                r2_report = await self._load_r2_json("clean-data", report_r2_path)

            merged = merge_db_checks_with_r2(db_checks, r2_report)
            return normalize_validation_report(merged)

    async def get_corpus_assignments(self, project_id: str | UUID) -> List[Dict[str, Any]]:
        """Per-file classification from latest session file_batches."""
        is_session = await self._get_session(project_id)
        if not is_session:
            return []

        batches = list(is_session.file_batches or [])
        if not batches:
            return []

        assignments = (batches[-1] or {}).get("corpus_assignments") or []
        out: List[Dict[str, Any]] = []
        for a in assignments:
            if not isinstance(a, dict):
                continue
            cls = a.get("classification") or {}
            out.append(
                {
                    "file": a.get("file"),
                    "doctypes": a.get("doctypes") or [],
                    "classification": {
                        "doctype": cls.get("doctype"),
                        "confidence": cls.get("confidence"),
                        "method": cls.get("method"),
                        "candidates": cls.get("candidates"),
                    },
                    "split": a.get("split"),
                }
            )
        return out

    async def get_data_readiness(self, project_id: str | UUID) -> Optional[Dict[str, Any]]:
        """Query ISDataReadinessAssessment for this project."""
        is_session = await self._get_session(project_id)
        if not is_session:
            return None

        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISDataReadinessAssessment)
                .where(ISDataReadinessAssessment.session_id == is_session.id)
                .order_by(ISDataReadinessAssessment.created_at.desc())
                .limit(1)
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if not row:
                return None

            return {
                "ready_doctypes": row.ready_doctypes or [],
                "partial_doctypes": row.partial_doctypes or [],
                "missing_doctypes": row.missing_doctypes or [],
                "unmappable_chunks": row.unmappable_chunks or [],
                "gap_report": row.gap_report or {},
                "minimum_viable_possible": row.minimum_viable_possible,
                "user_action_required": row.user_action_required,
                "questions_for_user": row.questions_for_user or [],
                "import_readiness_score": row.import_readiness_score,
                "executive_summary": row.executive_summary,
                "user_decision": row.user_decision,
            }

    async def get_supervisor_prompts(self, project_id: str | UUID, status: str = "open") -> List[Dict[str, Any]]:
        """
        Return Supervisor prompts for the latest IS session of this project.
        """
        is_session = await self._get_session(project_id)
        if not is_session:
            return []

        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISSupervisorPrompt)
                .where(ISSupervisorPrompt.session_id == is_session.id)
                .where(ISSupervisorPrompt.status == status)
                .order_by(ISSupervisorPrompt.created_at.desc())
                .limit(50)
            )
            rows = (await session.execute(stmt)).scalars().all()
            out: List[Dict[str, Any]] = []
            for r in rows:
                out.append(
                    {
                        "id": str(r.id),
                        "session_id": str(r.session_id),
                        "step": r.step,
                        "status": r.status,
                        "summary_for_ui": r.summary_for_ui,
                        "actions": r.actions or [],
                        "node_status": r.node_status or {},
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                )
            return out

    async def answer_supervisor_prompt(
        self,
        project_id: str | UUID,
        prompt_id: str,
        chosen_action_id: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Persist the user's answer and signal the workflow.
        """
        is_session = await self._get_session(project_id)
        if not is_session:
            raise ValueError("Implementation session not found")

        answer_payload = {"chosen_action_id": chosen_action_id, "extra_data": extra_data or {}}
        user_note = (extra_data or {}).get("user_note")

        from sqlalchemy import update

        async with AsyncSessionLocal() as session:
            stmt = select(ISSession).where(ISSession.id == is_session.id)
            row = (await session.execute(stmt)).scalar_one_or_none()
            await session.execute(
                update(ISSupervisorPrompt)
                .where(ISSupervisorPrompt.id == UUID(prompt_id))
                .values(status="answered", answer_payload=answer_payload)
            )

            if user_note:
                if row:
                    notes = list(row.user_notes or [])
                    notes.append({
                        "type": "supervisor_prompt",
                        "prompt_id": prompt_id,
                        "chosen_action_id": chosen_action_id,
                        "note": user_note,
                        "answered_at": datetime.utcnow().isoformat() + "Z",
                    })
                    await session.execute(
                        update(ISSession)
                        .where(ISSession.id == is_session.id)
                        .values(user_notes=notes, updated_at=datetime.utcnow())
                    )
            await session.commit()

        await self.signal_supervisor_response(project_id, prompt_id, chosen_action_id, extra_data=extra_data)

    async def get_import_plan(self, project_id: str | UUID) -> Optional[Dict]:
        """Query ISImportPlan for this project."""
        is_session = await self._get_session(project_id)
        if not is_session:
            return None
            
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISImportPlan)
                .where(ISImportPlan.session_id == is_session.id)
                .order_by(ISImportPlan.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            plan = result.scalar_one_or_none()
            
            if not plan:
                return None
                
            blocked_reasons: List[str] = []
            optional_gaps: List[str] = []
            company_slug = "unknown"
            from shared.models.core import Project

            proj = (
                await session.execute(
                    select(Project).where(Project.id == is_session.project_id)
                )
            ).scalar_one_or_none()
            if proj and proj.company_slug:
                company_slug = proj.company_slug

            plan_key = f"{company_slug}/{is_session.project_id}/_import_plan/plan.json"
            r2_plan = await self._load_r2_json("clean-data", plan_key)
            if isinstance(r2_plan, dict):
                optional_gaps = list(r2_plan.get("optional_gaps") or [])
                if r2_plan.get("status") == "blocked":
                    blocked_reasons.append("Import plan blocked due to validation or critical gaps")

            val_stmt = select(ISValidationResult).where(
                ISValidationResult.session_id == is_session.id
            )
            for vr in (await session.execute(val_stmt)).scalars().all():
                if vr.overall_status == "fail":
                    blocked_reasons.append(f"Validation failed for {vr.doctype}")

            return {
                "status": plan.status,
                "plan_status": plan.status,
                "phases": plan.phases or [],
                "total_steps": plan.total_steps or 0,
                "current_phase": plan.current_phase,
                "blocked_reasons": blocked_reasons,
                "optional_gaps": optional_gaps,
            }

    async def get_import_results(self, project_id: str | UUID) -> List[Dict]:
        """Query ISImportLog entries for this project."""
        is_session = await self._get_session(project_id)
        if not is_session:
            return []
            
        async with AsyncSessionLocal() as session:
            # Get the plan first
            plan_stmt = (
                select(ISImportPlan)
                .where(ISImportPlan.session_id == is_session.id)
                .order_by(ISImportPlan.created_at.desc())
                .limit(1)
            )
            plan = (await session.execute(plan_stmt)).scalar_one_or_none()
            if not plan:
                return []
            
            # Get all logs for this plan
            log_stmt = (
                select(ISImportLog)
                .where(ISImportLog.import_plan_id == plan.id)
                .order_by(ISImportLog.phase, ISImportLog.step_number)
                .limit(200)
            )
            logs = (await session.execute(log_stmt)).scalars().all()
            
            return [{
                "phase": log.phase,
                "step_number": log.step_number,
                "doctype": log.doctype,
                "action": log.action,
                "status": log.status,
                "records_attempted": log.records_attempted,
                "records_succeeded": log.records_succeeded,
                "records_failed": log.records_failed,
                "error_message": log.error_message,
            } for log in logs]

    async def re_finalize_import_plan(self, project_id: str | UUID) -> Dict[str, Any]:
        """
        Re-run finalize_import_plan for the latest session — refreshes stale DB plans
        after worker/KB fixes without restarting the Temporal workflow.
        """
        from containers.implementation.import_agent.activities import (
            FinalizeImportPlanInput,
            finalize_import_plan,
        )

        is_session = await self._get_session(project_id)
        if not is_session:
            raise ValueError("No implementation session found")

        company_slug = "unknown"
        async with AsyncSessionLocal() as session:
            from shared.models.core import Project
            proj = (
                await session.execute(
                    select(Project).where(Project.id == is_session.project_id)
                )
            ).scalar_one_or_none()
            if proj and proj.company_slug:
                company_slug = proj.company_slug

        status = await finalize_import_plan(
            FinalizeImportPlanInput(
                session_id=str(is_session.id),
                project_id=str(is_session.project_id),
                company_slug=company_slug,
            )
        )
        plan = await self.get_import_plan(project_id)
        return {"finalize_status": status, "import_plan": plan}

    async def get_validate_preview(self, project_id: str | UUID) -> Dict[str, Any]:
        """
        Fetch ALL mapped data payloads from R2 along with profile and validation results.
        Returns the complete dataset that will be imported — for user review.
        """
        import json
        import boto3
        from botocore.config import Config

        is_session = await self._get_session(project_id)
        if not is_session:
            return {"error": "No implementation session found"}

        # 1. Company profile
        profile = await self.get_profile(project_id)

        # 2. All mapped data rows + per-column mapping methods for preview classification
        mapping_methods_by_doctype: Dict[str, Dict[str, Any]] = {}
        async with AsyncSessionLocal() as session:
            mapped_stmt = (
                select(ISMappedData)
                .where(ISMappedData.session_id == is_session.id)
                .order_by(ISMappedData.target_doctype)
                .limit(100)
            )
            mapped_rows = (await session.execute(mapped_stmt)).scalars().all()

            field_mapping_rows = (
                await session.execute(
                    select(ISFieldMapping)
                    .where(ISFieldMapping.session_id == is_session.id)
                    .limit(2000)
                )
            ).scalars().all()
            for fm in field_mapping_rows:
                dt = fm.target_doctype
                entry = mapping_methods_by_doctype.setdefault(dt, {"methods": {}, "counts": {}})
                method = fm.mapping_method or "exact_match"
                if fm.source_column:
                    entry["methods"][fm.source_column] = method
                entry["counts"][method] = entry["counts"].get(method, 0) + 1

            # 3. Validation results + errors per doctype
            val_rows = (
                await session.execute(
                    select(ISValidationResult)
                    .where(ISValidationResult.session_id == is_session.id)
                    .limit(50)
                )
            ).scalars().all()

            vr_ids = [vr.id for vr in val_rows]
            errors_by_vr_id: Dict[Any, List[Any]] = {}
            if vr_ids:
                err_rows = (
                    await session.execute(
                        select(ISValidationError)
                        .where(ISValidationError.validation_result_id.in_(vr_ids))
                        .limit(500)
                    )
                ).scalars().all()
                for e in err_rows:
                    errors_by_vr_id.setdefault(e.validation_result_id, []).append(e)

            val_map: Dict[str, Dict] = {}
            for vr in val_rows:
                errors = errors_by_vr_id.get(vr.id, [])
                val_map[vr.doctype] = {
                    "status": vr.overall_status,
                    "row_count": vr.row_count or 0,
                    "errors": [
                        {"message": e.error_message, "severity": e.severity, "field": e.field_name}
                        for e in errors
                    ],
                }

            # 4. Import plan (target structure phases)
            target_stmt = (
                select(ISTargetStructure)
                .where(ISTargetStructure.session_id == is_session.id)
                .order_by(ISTargetStructure.created_at.desc())
                .limit(1)
            )
            target_row = (await session.execute(target_stmt)).scalar_one_or_none()

            readiness_stmt = (
                select(ISDataReadinessAssessment)
                .where(ISDataReadinessAssessment.session_id == is_session.id)
                .order_by(ISDataReadinessAssessment.created_at.desc())
                .limit(1)
            )
            readiness_row = (await session.execute(readiness_stmt)).scalar_one_or_none()

        # 5. Download actual payloads from R2
        s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

        doctypes = []
        from containers.implementation.mapping_agent.corpus_merge import (
            aggregate_mapped_data_rows,
            load_r2_json,
        )

        aggregated = aggregate_mapped_data_rows(mapped_rows)

        for dt, agg in sorted(aggregated.items()):
            records = []
            columns = []
            r2_path = agg.get("r2_path")

            if r2_path:
                try:
                    payload = load_r2_json(s3, "clean-data", r2_path)
                    if isinstance(payload, dict):
                        from containers.implementation.mapping_agent.defaults import normalize_mapped_payload

                        payload = normalize_mapped_payload(dt, payload)
                        records = payload.get("records", [])
                        if records:
                            from containers.implementation.mapping_agent.preview_flatten import (
                                flatten_records_for_preview,
                            )

                            records, columns = flatten_records_for_preview(records)
                        if records and not columns:
                            columns = list(records[0].keys())
                except Exception as e:
                    logger.warning("Failed to fetch R2 payload %s: %s", r2_path, e)

            validation = val_map.get(dt, {
                "status": "pending", "row_count": 0, "errors": []
            })

            cls = mapping_methods_by_doctype.get(dt, {})
            method_counts = cls.get("counts") or {}
            primary_method = "exact_match"
            if method_counts:
                primary_method = max(method_counts, key=method_counts.get)

            doctypes.append({
                "doctype": dt,
                "source_file": ", ".join(agg.get("source_files") or []),
                "source_files": agg.get("source_files") or [],
                "total_rows": len(records) or agg.get("total_rows") or 0,
                "total_mapped_fields": len(columns),
                "validation_status": validation["status"],
                "errors": [e for e in validation["errors"] if e["severity"] == "error"],
                "warnings": [e for e in validation["errors"] if e["severity"] == "warning"],
                "columns": columns,
                "records": records,
                "classification": {
                    "primary_method": primary_method,
                    "method_counts": method_counts,
                    "column_methods": cls.get("methods") or {},
                },
            })

        # 6. Import summary from target structure
        import_summary = {}
        if target_row:
            try:
                phases_raw = target_row.import_phases
                phases = json.loads(phases_raw) if isinstance(phases_raw, str) else (phases_raw or {})
                for phase_key, phase_val in phases.items():
                    if isinstance(phase_val, dict):
                        import_summary[phase_key] = phase_val.get("doctypes", [])
                    elif isinstance(phase_val, list):
                        import_summary[phase_key] = phase_val
            except Exception:
                pass

        validation_overall = "pass"
        for dt in doctypes:
            st = dt["validation_status"]
            if st in ("fail", "failed"):
                validation_overall = "fail"
                break
            if st in ("partial", "passed_with_warnings"):
                validation_overall = "partial"

        # Honesty: open critical gaps or missing MVP mapped payloads downgrade overall
        gap_report = (readiness_row.gap_report or {}) if readiness_row else {}
        gap_items = list(gap_report.get("gap_items") or [])
        mapping_preflight = list(gap_report.get("mapping_preflight_blocks") or [])
        open_critical = [
            g for g in gap_items
            if str((g.get("metadata") or {}).get("tier", "")).lower() == "critical"
            and str(g.get("severity", "blocking")).lower() in ("blocking", "")
        ]

        from containers.implementation.import_agent.mvp_import_scope import (
            blocking_unmapped_seeds,
            parse_mvp_scope_from_target,
        )

        seed_doctypes: List[str] = []
        deferred_set: set = set()
        if target_row and target_row.r2_path:
            try:
                target_r2 = load_r2_json(s3, "clean-data", target_row.r2_path)
                if isinstance(target_r2, dict):
                    seed_doctypes = list(target_r2.get("seed_doctypes") or [])
                    _, deferred_set = parse_mvp_scope_from_target(target_r2)
            except Exception:
                pass
        if not seed_doctypes and target_row:
            required_raw = target_row.required_doctypes
            if isinstance(required_raw, str):
                required_raw = json.loads(required_raw)
            seed_doctypes = list(required_raw or [])

        mapped_set = {d["doctype"] for d in doctypes if (d.get("total_rows") or 0) > 0}
        unmapped_seeds = [
            s for s in seed_doctypes
            if s not in mapped_set
            and s not in ("Company", "Warehouse", "UOM")
        ]
        blocking_unmapped = blocking_unmapped_seeds(
            seed_doctypes,
            mapped_set,
            deferred_set,
        )
        import_ready = (
            not open_critical
            and not mapping_preflight
            and validation_overall != "fail"
            and not blocking_unmapped
        )

        if open_critical or mapping_preflight:
            validation_overall = "fail"
        elif unmapped_seeds and validation_overall == "pass":
            validation_overall = "partial"

        warning_count = sum(len(d.get("warnings") or []) for d in doctypes)
        if isinstance(profile, dict):
            profile = dict(profile)
            dqs = profile.get("data_quality_score")
            if dqs is not None and (warning_count > 0 or validation_overall == "partial"):
                try:
                    profile["data_quality_score"] = min(float(dqs), 0.85)
                    profile["data_quality_capped"] = True
                except (TypeError, ValueError):
                    pass

        mapping_gaps = [
            {
                "doctype": b.get("doctype"),
                "source_file": b.get("source_file"),
                "missing_fields": b.get("missing_fields") or [],
                "message": (
                    f"{b.get('doctype')} not mapped from {b.get('source_file')} — "
                    f"missing {', '.join(b.get('missing_fields') or []) or 'required fields'}."
                ),
            }
            for b in mapping_preflight
            if isinstance(b, dict)
        ]

        mapped_source_files: set = set()
        for dt_row in doctypes:
            for sf in dt_row.get("source_files") or []:
                if sf:
                    mapped_source_files.add(str(sf))
            raw_sf = dt_row.get("source_file")
            if raw_sf:
                for part in str(raw_sf).split(","):
                    part = part.strip()
                    if part:
                        mapped_source_files.add(part)

        tracked_files: set = set()
        for row in (gap_report.get("file_doctype_matrix") or {}).get("rows") or []:
            if isinstance(row, dict) and row.get("filename"):
                tracked_files.add(str(row["filename"]))
        if readiness_row:
            for bucket in ("ready_doctypes", "partial_doctypes", "missing_doctypes"):
                for item in (gap_report.get(bucket) or []):
                    if isinstance(item, dict) and item.get("source_file"):
                        tracked_files.add(str(item["source_file"]))

        unmapped_files = [
            {
                "filename": fname,
                "status": "not_mapped",
                "message": f"{fname} was uploaded but did not produce a mapped payload.",
            }
            for fname in sorted(tracked_files - mapped_source_files)
        ]

        validation_report = await self.get_validation_report(project_id)
        import_preview = (validation_report or {}).get("import_preview") or {}

        return {
            "profile": profile,
            "doctypes": doctypes,
            "import_summary": import_summary,
            "import_preview": import_preview,
            "validation_overall": validation_overall,
            "open_critical_gaps": len(open_critical),
            "unmapped_seeds": unmapped_seeds,
            "blocking_unmapped_seeds": blocking_unmapped,
            "import_ready": import_ready,
            "mvp_seed_doctypes": seed_doctypes,
            "mapping_gaps": mapping_gaps,
            "tracked_files": sorted(tracked_files),
            "unmapped_files": unmapped_files,
            "post_mapping_readiness_score": (
                (gap_report.get("summary") or {}).get("n_dry_run_ready")
                if gap_report.get("summary")
                else None
            ),
        }

    async def get_full_state(self, project_id: str | UUID) -> Dict[str, Any]:
        """Convenience: returns everything in one round-trip batch."""
        import asyncio
        h = await self._handle(project_id)
        stage, tasks, f3iche_confirmation = await asyncio.gather(
            h.query(ImplementationWorkflow.get_stage),
            h.query(ImplementationWorkflow.get_analysis_tasks),
            h.query(ImplementationWorkflow.get_f3iche_confirmation),
        )
        session = await self._get_session(project_id)
        file_batches = list(session.file_batches or []) if session else []
        total_files = sum(len((batch or {}).get("files") or []) for batch in file_batches)
        if not f3iche_confirmation:
            f3iche_confirmation = await self.get_f3iche_confirmation(project_id)
        return {
            "stage": stage, 
            "profile": await self.get_profile(project_id), 
            "analysis_tasks": tasks,
            "f3iche_confirmation": f3iche_confirmation or None,
            "session": {
                "status": session.status if session else None,
                "user_import_note": session.user_import_note if session else None,
                "file_batches": file_batches,
                "user_notes": list(session.user_notes or []) if session else [],
                "total_files": total_files,
                "batch_count": len(file_batches),
                "completed_at": session.completed_at.isoformat() if session and session.completed_at else None,
                "updated_at": session.updated_at.isoformat() if session and session.updated_at else None,
            } if session else None,
        }

    # ── Chat bar ─────────────────────────────────────────────────────────────

    async def get_chat_messages(
        self,
        project_id: str | UUID,
        step: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        from app.services.is_chat_dispatcher import get_chat_messages as _get_msgs

        is_session = await self._get_session(project_id)
        if not is_session:
            return []
        return await _get_msgs(str(is_session.id), step=step, limit=limit)

    async def send_chat_message(
        self,
        project_id: str | UUID,
        message: str,
        step: str = "analyze",
    ) -> Dict[str, Any]:
        from app.services.is_chat_dispatcher import dispatch_chat_message

        is_session = await self._get_session(project_id)
        if not is_session:
            raise ValueError("Implementation session not found")
        return await dispatch_chat_message(is_session, message, step)
