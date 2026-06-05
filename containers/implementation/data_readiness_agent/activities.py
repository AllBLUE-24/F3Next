"""
data_readiness_agent/activities.py

Temporal activity: assess_data_readiness (Step 8c)

Pipeline:
  1. Load ISTargetStructure from Supabase
  2. Download manifest (all uploaded files) from R2
  3. Load ISCompanyProfile from Supabase
  4. Run deterministic gap_analyzer → pre_analysis dict
  5. Call LLM (generate_typed → DataReadinessAssessment)
  6. Persist to is_data_readiness_assessments (Supabase)
  7. Return NodeStatusEnvelope:
       ok=True  → minimum_viable_import_possible (pipeline advances automatically)
       ok=False → user_action_required and not viable (UI gate shown)
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from sqlalchemy import select
from temporalio import activity

from shared.database.db import AsyncSessionLocal
from shared.models.is_models import (
    ISCompanyProfile,
    ISDataReadinessAssessment,
    ISSession,
    ISTargetStructure,
)
from shared.models.is_status import NodeStatusEnvelope
from shared.structured_llm import generate_typed

from containers.implementation.data_readiness_agent.gap_analyzer import analyze_gaps
from containers.implementation.data_readiness_agent.models import DataReadinessAssessment
from containers.implementation.data_readiness_agent.prompts import DATA_READINESS_PROMPT
from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings


# ── Input ─────────────────────────────────────────────────────────────────────

@dataclass
class AssessDataReadinessInput:
    session_id: str
    project_id: str
    company_slug: str
    r2_manifest_url: str
    user_import_note: Optional[str] = None


# ── S3 helper ─────────────────────────────────────────────────────────────────

def _get_s3():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


# ── DB loaders ────────────────────────────────────────────────────────────────

def _download_r2_json(r2_key: str) -> Dict[str, Any]:
    """Load a JSON artifact from R2 (clean-data bucket)."""
    if not r2_key:
        return {}
    try:
        s3 = _get_s3()
        resp = s3.get_object(Bucket="clean-data", Key=r2_key)
        data = json.loads(resp["Body"].read().decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        activity.logger.warning("  ⚠️ Could not load R2 JSON %s: %s", r2_key, e)
        return {}


async def _load_target_structure(session_id: str) -> Dict[str, Any]:
    try:
        async with AsyncSessionLocal() as db:
            stmt = (
                select(ISTargetStructure)
                .where(ISTargetStructure.session_id == uuid.UUID(session_id))
                .order_by(ISTargetStructure.created_at.desc())
                .limit(1)
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if not row:
                return {}
            required = row.required_doctypes
            if isinstance(required, str):
                required = json.loads(required)
            steps = row.setup_steps
            if isinstance(steps, str):
                steps = json.loads(steps)
            phases = row.import_phases
            if isinstance(phases, str):
                phases = json.loads(phases)
            result = {
                "required_doctypes": required or [],
                "setup_steps": steps or [],
                "import_phases": phases or {},
                "seed_doctypes": [],
                "deferred_doctypes": [],
            }
            if row.r2_path:
                r2_data = _download_r2_json(row.r2_path)
                result["seed_doctypes"] = r2_data.get("seed_doctypes") or []
                result["deferred_doctypes"] = r2_data.get("deferred_doctypes") or []
            return result
    except Exception as e:
        activity.logger.warning("  ⚠️ Could not load target structure: %s", e)
        return {}


async def _load_company_profile(session_id: str) -> Dict[str, Any]:
    try:
        async with AsyncSessionLocal() as db:
            stmt = (
                select(ISCompanyProfile)
                .where(ISCompanyProfile.session_id == uuid.UUID(session_id))
                .order_by(ISCompanyProfile.version.desc())
                .limit(1)
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if not row:
                return {}
            return {
                "f3iche": row.f3iche,
                "industry": row.industry,
                "industry_sub": row.industry_sub,
                "company_name": row.company_name,
                "company_size": row.company_size,
                "business_reality": row.business_reality,
                "data_quality_score": row.data_quality_score,
            }
    except Exception as e:
        activity.logger.warning("  ⚠️ Could not load company profile: %s", e)
        return {}


async def _load_session_context(session_id: str) -> Dict[str, Any]:
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(ISSession).where(ISSession.id == uuid.UUID(session_id))
            row = (await db.execute(stmt)).scalar_one_or_none()
            if not row:
                return {}
            note_lines: List[str] = []
            if row.user_import_note:
                note_lines.append(f"Initial upload: {row.user_import_note}")
            for entry in row.user_notes or []:
                if isinstance(entry, dict) and entry.get("note"):
                    note_type = entry.get("type", "note")
                    note_lines.append(f"{note_type}: {entry['note']}")
            return {
                "user_import_note": "\n".join(note_lines) or "",
                "user_notes": row.user_notes or [],
                "file_batches": row.file_batches or [],
            }
    except Exception as e:
        activity.logger.warning("  ⚠️ Could not load session context: %s", e)
        return {}


def _download_manifest(r2_manifest_url: str) -> Dict[str, Any]:
    """Download the full manifest JSON from R2 (v2 with file_meta, or legacy v1)."""
    try:
        s3 = _get_s3()
        resp = s3.get_object(Bucket="clean-data", Key=r2_manifest_url)
        manifest = json.loads(resp["Body"].read().decode("utf-8"))
        if isinstance(manifest, dict) and "files" in manifest:
            return manifest
        # Legacy v1: plain {filename: content}
        if isinstance(manifest, dict) and all(isinstance(v, str) for v in manifest.values()):
            return {"files": manifest}
        return {}
    except Exception as e:
        activity.logger.warning("  ⚠️ Could not download manifest from R2: %s", e)
        return {}


def _criticality_from_phase(phase: Optional[str]) -> str:
    phase_l = (phase or "").lower()
    if phase_l.startswith("phase_a") or phase_l.startswith("phase_b"):
        return "critical"
    if phase_l.startswith("phase_c") or phase_l.startswith("phase_d"):
        return "non_critical"
    return "optional"


def _tag_bottleneck_gaps(
    pre_analysis: Dict[str, Any],
    mvp_focus: Optional[Dict[str, Any]],
) -> None:
    """Flag gaps that matter for the stated MVP bottleneck (e.g. Stock Entry for material tracking)."""
    bottleneck = str((mvp_focus or {}).get("primary_bottleneck") or "").lower()
    if not bottleneck:
        return
    material_keywords = ("material", "inventory", "stock", "consumption", "tracking")
    if not any(kw in bottleneck for kw in material_keywords):
        return
    for bucket in ("missing_doctypes", "partial_doctypes"):
        for entry in pre_analysis.get(bucket) or []:
            if entry.get("doctype") == "Stock Entry":
                entry["bottleneck_relevant"] = True
                entry["can_proceed_without"] = True
                entry.setdefault(
                    "coverage_note",
                    "No stock movement file yet — import can proceed; add Stock Entry data for live consumption tracking",
                )


def _upload_readiness_report_r2(
    company_slug: str,
    project_id: str,
    *,
    pre_analysis: Dict[str, Any],
    assessment_dict: Dict[str, Any],
    target_structure: Dict[str, Any],
    mvp_focus: Optional[Dict[str, Any]],
) -> str:
    """Persist full readiness artifact to R2 for harness/debug."""
    key = f"{company_slug}/{project_id}/_readiness/data_readiness_report.json"
    payload = {
        "pre_analysis": pre_analysis,
        "assessment": assessment_dict,
        "target_scope": {
            "seed_doctypes": target_structure.get("seed_doctypes") or [],
            "deferred_doctypes": target_structure.get("deferred_doctypes") or [],
        },
        "mvp_focus": mvp_focus,
    }
    try:
        s3 = _get_s3()
        s3.put_object(
            Bucket="clean-data",
            Key=key,
            Body=json.dumps(payload, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info("  ✅ R2 uploaded: clean-data/%s", key)
        return key
    except Exception as e:
        activity.logger.warning("  ⚠️ R2 readiness report upload failed: %s", e)
        return ""


def _recompute_viability_summary(pre_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Refresh blocking counts after bottleneck tags mutate can_proceed_without."""
    summary = dict(pre_analysis.get("summary") or {})
    blocking_partial = [
        p for p in pre_analysis.get("partial_doctypes", [])
        if not p.get("can_proceed_without")
    ]
    blocking_missing = [
        m for m in pre_analysis.get("missing_doctypes", [])
        if not m.get("can_proceed_without")
    ]
    summary["n_blocking_partial"] = len(blocking_partial)
    summary["n_blocking_missing"] = len(blocking_missing)
    summary["minimum_viable_possible"] = (
        len(blocking_partial) == 0 and len(blocking_missing) == 0
    )
    pre_analysis["summary"] = summary
    return summary


def _is_blocking_gap(gap: Dict[str, Any]) -> bool:
    """True when a gap should block minimum_viable_import_possible."""
    return not bool(gap.get("can_proceed_without"))


def _has_blocking_gaps(pre_analysis: Dict[str, Any]) -> bool:
    return not bool((pre_analysis.get("summary") or {}).get("minimum_viable_possible", True))


def _gap_from_deterministic_partial(p: Dict[str, Any]) -> "DoctypeGap":
    from containers.implementation.data_readiness_agent.models import DoctypeGap
    can_proceed = bool(p.get("can_proceed_without"))
    if not can_proceed:
        can_proceed = _criticality_from_phase(p.get("phase")) != "critical"
    assumed = p.get("assumed_fields") or []
    blocking = p.get("blocking_fields") or p.get("missing_required_fields") or []
    if assumed and not blocking:
        can_proceed = True
    reason = (
        f"Partial data coverage ({round(float(p.get('coverage_pct', 0)) * 100)}%) "
        f"from {p.get('source_file', 'uploaded file')}."
    )
    if assumed and can_proceed:
        fields = ", ".join(a.get("field", "") for a in assumed if a.get("field"))
        reason = (
            f"Data found in {p.get('source_file', 'uploaded file')}; "
            f"defaults will be applied for: {fields}."
        )
    return DoctypeGap(
        doctype=p.get("doctype", ""),
        criticality=_criticality_from_phase(p.get("phase")),
        reason=reason,
        missing_fields=p.get("missing_required_fields") or p.get("missing_fields") or [],
        recommendation="Review mapped fields before import." if blocking else "Proceed — defaults will be applied at mapping.",
        can_proceed_without=can_proceed,
    )


def _gap_from_deterministic_missing(m: Dict[str, Any]) -> "DoctypeGap":
    from containers.implementation.data_readiness_agent.models import DoctypeGap
    can_proceed = bool(m.get("can_proceed_without"))
    if not can_proceed:
        can_proceed = _criticality_from_phase(m.get("phase")) != "critical"
    reason = m.get("coverage_note") or "No uploaded file covers this doctype."
    recommendation = (
        "Continue import — add this data later for full bottleneck coverage."
        if m.get("bottleneck_relevant") and can_proceed
        else "Upload a file containing this data, or use ERPNext defaults."
    )
    return DoctypeGap(
        doctype=m.get("doctype", ""),
        criticality=_criticality_from_phase(m.get("phase")),
        reason=reason,
        missing_fields=m.get("missing_required_fields") or m.get("missing_fields") or [],
        recommendation=recommendation,
        can_proceed_without=can_proceed,
    )


def _gap_from_llm_entry(entry: Dict[str, Any], *, default_reason: str) -> "DoctypeGap":
    from containers.implementation.data_readiness_agent.models import DoctypeGap
    return DoctypeGap(
        doctype=entry.get("doctype", ""),
        criticality=entry.get("criticality") or _criticality_from_phase(entry.get("phase")),
        reason=entry.get("reason") or default_reason,
        missing_fields=entry.get("missing_fields") or entry.get("missing_required_fields") or [],
        recommendation=entry.get("recommendation", "Review before import."),
        can_proceed_without=bool(
            entry.get(
                "can_proceed_without",
                _criticality_from_phase(entry.get("phase")) != "critical",
            )
        ),
    )


def _merge_deterministic_and_llm_gaps(
    deterministic: List[Dict[str, Any]],
    llm_entries: List[Dict[str, Any]],
    *,
    default_reason: str,
    to_gap,
) -> List["DoctypeGap"]:
    """Deterministic gap scan is authoritative; LLM adds narrative where available."""
    from containers.implementation.data_readiness_agent.models import DoctypeGap

    merged: Dict[str, DoctypeGap] = {}
    for item in deterministic:
        dt = item.get("doctype")
        if dt:
            merged[dt] = to_gap(item)

    for entry in llm_entries or []:
        if not isinstance(entry, dict):
            continue
        dt = entry.get("doctype")
        if not dt:
            continue
        if dt in merged:
            existing = merged[dt]
            merged[dt] = DoctypeGap(
                doctype=dt,
                criticality=entry.get("criticality") or existing.criticality,
                reason=entry.get("reason") or existing.reason,
                missing_fields=(
                    entry.get("missing_fields")
                    or entry.get("missing_required_fields")
                    or existing.missing_fields
                ),
                recommendation=entry.get("recommendation") or existing.recommendation,
                can_proceed_without=bool(
                    entry.get("can_proceed_without", existing.can_proceed_without)
                ),
            )
        else:
            merged[dt] = _gap_from_llm_entry(entry, default_reason=default_reason)

    return list(merged.values())


# ── Persist ───────────────────────────────────────────────────────────────────

async def _persist_assessment(
    session_id: str,
    assessment: DataReadinessAssessment,
) -> str:
    """Write ISDataReadinessAssessment row and return its UUID."""
    row_id = uuid.uuid4()
    try:
        async with AsyncSessionLocal() as db:
            db.add(ISDataReadinessAssessment(
                id=row_id,
                session_id=uuid.UUID(session_id),
                ready_doctypes=[r.model_dump() for r in assessment.ready_doctypes],
                partial_doctypes=[p.model_dump() for p in assessment.partial_doctypes],
                missing_doctypes=[m.model_dump() for m in assessment.missing_doctypes],
                unmappable_chunks=[u.model_dump() for u in assessment.unmappable_chunks],
                gap_report=assessment.gap_report or {
                    "ready_doctypes": [r.model_dump() for r in assessment.ready_doctypes],
                    "partial_doctypes": [p.model_dump() for p in assessment.partial_doctypes],
                    "missing_doctypes": [m.model_dump() for m in assessment.missing_doctypes],
                    "unmappable_chunks": [u.model_dump() for u in assessment.unmappable_chunks],
                },
                minimum_viable_possible=assessment.minimum_viable_import_possible,
                user_action_required=assessment.user_action_required,
                questions_for_user=[q.model_dump() for q in assessment.questions_for_user],
                import_readiness_score=assessment.import_readiness_score,
                executive_summary=assessment.executive_summary,
            ))
            await db.commit()
        activity.logger.info("  ✅ ISDataReadinessAssessment persisted | id=%s", row_id)
    except Exception as e:
        activity.logger.error("  ❌ Failed to persist ISDataReadinessAssessment: %s", e)
    return str(row_id)


# ── Main activity ─────────────────────────────────────────────────────────────

@activity.defn(name="assess_data_readiness")
async def assess_data_readiness(inp: AssessDataReadinessInput) -> Any:
    """
    Step 8c — Data Readiness Assessment (LLM Node 4).

    Deterministically scans all uploaded files against the target structure,
    then uses an LLM to rank gaps and generate user-facing questions.
    """
    activity.logger.info(
        "▶ assess_data_readiness started | session=%s project=%s manifest=%s",
        inp.session_id, inp.project_id, inp.r2_manifest_url,
    )

    # 1. Load target structure
    target_structure = await _load_target_structure(inp.session_id)
    required_doctypes = target_structure.get("required_doctypes", [])
    seed_doctypes = target_structure.get("seed_doctypes") or []
    scope_doctypes = seed_doctypes or required_doctypes
    activity.logger.info(
        "  Target structure: %d required, %d seed (scope=%d)",
        len(required_doctypes),
        len(seed_doctypes),
        len(scope_doctypes),
    )

    if not scope_doctypes:
        activity.logger.warning("  ⚠️ No required_doctypes in target structure — skipping assessment")
        empty = DataReadinessAssessment(
            minimum_viable_import_possible=True,
            user_action_required=False,
            executive_summary="No target structure found; proceeding with best-effort mapping.",
            import_readiness_score=1.0,
        )
        await _persist_assessment(inp.session_id, empty)
        return NodeStatusEnvelope.success(primary_result={
            "assessment": empty.model_dump(),
            "skipped": True,
        })

    # 2. Download manifest (all uploaded file contents)
    manifest = _download_manifest(inp.r2_manifest_url)
    manifest_files = manifest.get("files") or {}
    activity.logger.info("  Manifest: %d files", len(manifest_files))

    if not manifest_files:
        activity.logger.warning("  ⚠️ Empty manifest — cannot assess readiness, skipping gate")
        empty = DataReadinessAssessment(
            minimum_viable_import_possible=True,
            user_action_required=False,
            executive_summary="No uploaded files found in manifest; proceeding with best-effort mapping.",
            import_readiness_score=0.0,
        )
        await _persist_assessment(inp.session_id, empty)
        return NodeStatusEnvelope.partial(
            primary_result={"assessment": empty.model_dump(), "skipped": True},
            warnings=[{"code": "EMPTY_MANIFEST", "message": "No files in manifest to assess"}],
        )

    # 3. Load company profile and session context
    company_profile = await _load_company_profile(inp.session_id)
    session_context = await _load_session_context(inp.session_id)
    if inp.user_import_note:
        session_context["user_import_note"] = (
            f"{session_context.get('user_import_note', '')}\n{inp.user_import_note}".strip()
        )
    
    mvp_focus = None
    try:
        from shared.models.is_models import ISSession
        async with AsyncSessionLocal() as db:
            stmt = select(ISSession).where(ISSession.id == uuid.UUID(inp.session_id))
            sess_row = (await db.execute(stmt)).scalar_one_or_none()
            if sess_row and sess_row.mvp_focus:
                mvp_focus = sess_row.mvp_focus
    except Exception as e:
        activity.logger.warning("  ⚠️ Could not load session mvp_focus: %s", e)

    # 4. Deterministic gap analysis (no LLM)
    kb = _kb_field_mappings() or {}
    pre_analysis = analyze_gaps(
        manifest=manifest,
        target_structure=target_structure,
        field_mappings_kb=kb,
    )
    _tag_bottleneck_gaps(pre_analysis, mvp_focus)
    summary = _recompute_viability_summary(pre_analysis)
    activity.logger.info(
        "  Gap scan: ready=%d partial=%d missing=%d unmappable=%d score=%.0f%%",
        summary.get("n_ready", 0),
        summary.get("n_partial", 0),
        summary.get("n_missing", 0),
        summary.get("n_unmappable_files", 0),
        summary.get("raw_readiness_score", 0) * 100,
    )

    # 4b. Live ERP master check (LER — not CVS-only)
    live_erp_overlay: dict = {}
    try:
        from containers.implementation.data_readiness_agent.live_erp import assess_live_erp_masters

        live_erp_overlay = await assess_live_erp_masters(
            inp.project_id,
            scope_doctypes,
            ready_doctypes=pre_analysis.get("ready_doctypes", []),
            partial_doctypes=pre_analysis.get("partial_doctypes", []),
            log=activity.logger,
        )
        if not live_erp_overlay.get("skipped") and live_erp_overlay.get("live_empty"):
            for dt in live_erp_overlay.get("live_empty_blocking", []):
                pre_analysis.setdefault("missing_doctypes", []).append({
                    "doctype": dt,
                    "phase": "live_erp",
                    "reason": f"No {dt} records on live ERP site and no upload covers it",
                    "missing_fields": [],
                    "source": "live_erp",
                })
            summary["n_live_erp_empty"] = len(live_erp_overlay.get("live_empty", []))
            summary["n_live_erp_blocking"] = len(live_erp_overlay.get("live_empty_blocking", []))
            summary["n_live_erp_covered_by_import"] = len(
                live_erp_overlay.get("live_empty_covered_by_import", [])
            )
    except Exception as e:
        activity.logger.warning("  Live ERP readiness check skipped: %s", e)

    # 5. LLM ranking + question generation
    assessment: Optional[DataReadinessAssessment] = None
    try:
        prompt = DATA_READINESS_PROMPT.format(
            company_profile=json.dumps(company_profile, indent=2),
            user_import_note=session_context.get("user_import_note", "") or "No user note provided.",
            mvp_primary_bottleneck=mvp_focus.get("primary_bottleneck", "General Operations") if mvp_focus else "General Operations",
            mvp_focus_json=json.dumps(mvp_focus or {}, indent=2, default=str),
            deferred_doctypes=json.dumps(target_structure.get("deferred_doctypes") or [], indent=2),
            target_structure=json.dumps({
                "required_doctypes": required_doctypes,
                "seed_doctypes": target_structure.get("seed_doctypes", []),
                "deferred_doctypes": target_structure.get("deferred_doctypes", []),
                "import_phases": target_structure.get("import_phases", {}),
            }, indent=2),
            pre_analysis=json.dumps({
                "ready_doctypes": pre_analysis.get("ready_doctypes", []),
                "partial_doctypes": pre_analysis.get("partial_doctypes", []),
                "missing_doctypes": pre_analysis.get("missing_doctypes", []),
                "unmappable_chunks": pre_analysis.get("unmappable_chunks", []),
                "assumptions": pre_analysis.get("assumptions", []),
                "summary": summary,
            }, indent=2),
        )

        llm_raw = await generate_typed(
            prompt=prompt,
            schema=DataReadinessAssessment,
            model_name=os.getenv("MAPPING_EXTRACTION_MODEL", "gpt-4o-mini"),
            temperature=0.1,
            max_output_tokens=4000,
            system_instruction="Return only the JSON object. No markdown.",
        )

        # Merge LLM output with deterministic ready_doctypes (LLM may not list them)
        from containers.implementation.data_readiness_agent.models import (
            DoctypeGap, DoctypeReady, UnmappableChunk, UserQuestion
        )

        ready_list = [DoctypeReady(**r) for r in pre_analysis.get("ready_doctypes", [])]

        partial_list = _merge_deterministic_and_llm_gaps(
            pre_analysis.get("partial_doctypes", []),
            llm_raw.get("partial_doctypes") or [],
            default_reason="Partial data coverage detected.",
            to_gap=_gap_from_deterministic_partial,
        )
        missing_list = _merge_deterministic_and_llm_gaps(
            pre_analysis.get("missing_doctypes", []),
            llm_raw.get("missing_doctypes") or [],
            default_reason="No uploaded file covers this doctype.",
            to_gap=_gap_from_deterministic_missing,
        )

        deterministic_gap_report = {
            "summary": summary,
            "ready_doctypes": pre_analysis.get("ready_doctypes", []),
            "partial_doctypes": pre_analysis.get("partial_doctypes", []),
            "missing_doctypes": pre_analysis.get("missing_doctypes", []),
            "unmappable_chunks": pre_analysis.get("unmappable_chunks", []),
            "complete_gaps": live_erp_overlay.get("complete_gaps", []),
            "link_cache_meta": {
                k: len(v) for k, v in (live_erp_overlay.get("link_cache") or {}).items()
            },
        }
        assessment = DataReadinessAssessment(
            ready_doctypes=ready_list,
            partial_doctypes=partial_list,
            missing_doctypes=missing_list,
            unmappable_chunks=[
                UnmappableChunk(**u) for u in (llm_raw.get("unmappable_chunks") or pre_analysis.get("unmappable_chunks") or [])
            ],
            gap_report={
                **deterministic_gap_report,
                "ready_doctypes": [r.model_dump() for r in ready_list],
                "partial_doctypes": [
                    {
                        "doctype": p.doctype,
                        "phase": next(
                            (x.get("phase") for x in pre_analysis.get("partial_doctypes", []) if x.get("doctype") == p.doctype),
                            None,
                        ),
                        "criticality": p.criticality,
                        "reason": p.reason,
                        "recommendation": p.recommendation,
                        "missing_fields": p.missing_fields,
                        "can_proceed_without": p.can_proceed_without,
                    }
                    for p in partial_list
                ],
                "missing_doctypes": [
                    {
                        "doctype": m.doctype,
                        "phase": next(
                            (x.get("phase") for x in pre_analysis.get("missing_doctypes", []) if x.get("doctype") == m.doctype),
                            None,
                        ),
                        "criticality": m.criticality,
                        "reason": m.reason,
                        "recommendation": m.recommendation,
                        "missing_fields": m.missing_fields,
                        "can_proceed_without": m.can_proceed_without,
                    }
                    for m in missing_list
                ],
                "unmappable_chunks": pre_analysis.get("unmappable_chunks", []),
            },
            minimum_viable_import_possible=(
                bool(summary.get("minimum_viable_possible"))
                and not bool(live_erp_overlay.get("live_empty_blocking"))
            ),
            user_action_required=(
                _has_blocking_gaps(pre_analysis)
                or bool(pre_analysis.get("unmappable_chunks"))
                or bool(live_erp_overlay.get("live_empty_blocking"))
            ),
            questions_for_user=[
                UserQuestion(**q) for q in (llm_raw.get("questions_for_user") or [])
                if not q.get("is_blocking") or _has_blocking_gaps(pre_analysis)
            ],
            executive_summary=llm_raw.get("executive_summary", ""),
            import_readiness_score=float(llm_raw.get("import_readiness_score", summary.get("raw_readiness_score", 1.0))),
            user_decision=llm_raw.get("user_decision"),
        )
        activity.logger.info(
            "  ✅ LLM assessment complete | score=%.0f%% viable=%s action_required=%s questions=%d",
            assessment.import_readiness_score * 100,
            assessment.minimum_viable_import_possible,
            assessment.user_action_required,
            len(assessment.questions_for_user),
        )

    except Exception as e:
        activity.logger.warning("  ⚠️ LLM assessment failed (%s) — using deterministic fallback", e)
        # Deterministic fallback: build a conservative assessment from the scan
        from containers.implementation.data_readiness_agent.models import DoctypeReady, DoctypeGap, UnmappableChunk
        ready_list = [DoctypeReady(**r) for r in pre_analysis.get("ready_doctypes", [])]
        partial_list = [
            DoctypeGap(
                doctype=p["doctype"],
                criticality=_criticality_from_phase(p.get("phase")),
                reason="Partial data coverage detected.",
                missing_fields=p.get("missing_required_fields", []),
                recommendation="Review and supplement data before import.",
                can_proceed_without=_criticality_from_phase(p.get("phase")) != "critical",
            )
            for p in pre_analysis.get("partial_doctypes", [])
        ]
        missing_list = [
            DoctypeGap(
                doctype=m["doctype"],
                criticality=_criticality_from_phase(m.get("phase")),
                reason="No uploaded file covers this doctype.",
                missing_fields=m.get("missing_required_fields", []),
                recommendation="Upload a file containing this data, or use ERPNext defaults.",
                can_proceed_without=_criticality_from_phase(m.get("phase")) != "critical",
            )
            for m in pre_analysis.get("missing_doctypes", [])
        ]
        unmappable_list = [
            UnmappableChunk(
                filename=u["filename"],
                description="Uploaded file with unrecognised structure.",
                reason="No ERPNext doctype matched the file columns or content.",
            )
            for u in pre_analysis.get("unmappable_chunks", [])
        ]
        raw_score = summary.get("raw_readiness_score", 1.0)
        critical_missing = [m for m in missing_list if m.criticality == "critical" and not m.can_proceed_without]
        critical_partial = [p for p in partial_list if p.criticality == "critical" and not p.can_proceed_without]
        assessment = DataReadinessAssessment(
            ready_doctypes=ready_list,
            partial_doctypes=partial_list,
            missing_doctypes=missing_list,
            unmappable_chunks=unmappable_list,
            gap_report={
                "summary": summary,
                "ready_doctypes": pre_analysis.get("ready_doctypes", []),
                "partial_doctypes": pre_analysis.get("partial_doctypes", []),
                "missing_doctypes": pre_analysis.get("missing_doctypes", []),
                "unmappable_chunks": pre_analysis.get("unmappable_chunks", []),
                "complete_gaps": live_erp_overlay.get("complete_gaps", []),
                "link_cache_meta": {
                    k: len(v) for k, v in (live_erp_overlay.get("link_cache") or {}).items()
                },
            },
            minimum_viable_import_possible=(
                bool(summary.get("minimum_viable_possible"))
                and not live_erp_overlay.get("live_empty_blocking")
            ),
            user_action_required=_has_blocking_gaps(pre_analysis) or len(unmappable_list) > 0,
            questions_for_user=[],
            executive_summary=(
                f"Import readiness: {raw_score*100:.0f}%. "
                f"{len(missing_list)} doctype(s) missing. "
                f"{'Critical gaps detected — user action required.' if critical_missing else 'Proceeding with available data.'}"
            ),
            import_readiness_score=raw_score,
        )

    # 6. Persist to Supabase
    await _persist_assessment(inp.session_id, assessment)

    assessment_dict = assessment.model_dump()
    readiness_r2_key = _upload_readiness_report_r2(
        inp.company_slug,
        inp.project_id,
        pre_analysis=pre_analysis,
        assessment_dict=assessment_dict,
        target_structure=target_structure,
        mvp_focus=mvp_focus,
    )

    # 7. Audit log
    try:
        from containers.implementation.file_io.persist_audit import log_audit
        await log_audit(
            session_id=inp.session_id,
            action="data_readiness_assessed",
            actor="system",
            entity_type="data_readiness",
            details={
                "import_readiness_score": assessment.import_readiness_score,
                "ready_count": len(assessment.ready_doctypes),
                "partial_count": len(assessment.partial_doctypes),
                "missing_count": len(assessment.missing_doctypes),
                "minimum_viable": assessment.minimum_viable_import_possible,
                "user_action_required": assessment.user_action_required,
            },
            result="success",
        )
    except Exception as e:
        activity.logger.warning("  ⚠️ Audit log failed (non-fatal): %s", e)

    activity.logger.info("✅ assess_data_readiness done")

    primary = {"assessment": assessment_dict, "readiness_r2_key": readiness_r2_key}

    if assessment.minimum_viable_import_possible:
        return NodeStatusEnvelope.success(primary_result=primary)

    # Not viable → return partial so Supervisor + workflow gate can act
    return NodeStatusEnvelope.partial(
        primary_result=primary,
        warnings=[
            {
                "code": "MINIMUM_VIABLE_NOT_MET",
                "message": (
                    f"Import readiness {assessment.import_readiness_score*100:.0f}% — "
                    f"{len(assessment.missing_doctypes)} doctype(s) missing data. "
                    "User confirmation required before mapping."
                ),
            }
        ],
    )
