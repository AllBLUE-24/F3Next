"""
Profile Agent — Temporal activities for company profile build & update.
Moved from: backend/app/services/implementation/company_profile.py
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from temporalio import activity

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge"


# ── Embedded service logic ────────────────────────────────────────────────────

class _CompanyProfileService:
    @staticmethod
    def _load_f3iche(f3iche_id: str) -> Optional[Dict]:
        path = KNOWLEDGE_DIR / f"f3iche_{f3iche_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def build(
        cls,
        project_id: str,
        version: int,
        f3iche: str,
        industry: str,
        action: str = "update",
        **kwargs,
    ) -> Dict[str, Any]:
        f3iche_data = cls._load_f3iche(f3iche) or {}
        return {
            "project_id": project_id,
            "version": version,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "f3iche": f3iche,
            "industry": industry,
            "industry_sub":        kwargs.get("industry_sub"),
            "company_size":        kwargs.get("company_size"),
            "company_name":        kwargs.get("company_name"),
            "workflows":           [w.get("name", "") for w in f3iche_data.get("workflows", [])],
            "modules":             f3iche_data.get("required_modules", []),
            "required_doctypes":   f3iche_data.get("required_doctypes", []),
            "f3iche_user":         kwargs.get("f3iche_user"),
            "f3iche_signals":      kwargs.get("f3iche_signals"),
            "f3iche_match_status": kwargs.get("f3iche_match_status", "matched"),
            "uploaded_files":      kwargs.get("uploaded_files") or [],
            "collected_signals":   kwargs.get("collected_signals") or [],
            "target_structure":    kwargs.get("target_structure"),
            "field_mappings":      kwargs.get("field_mappings"),
            "validation_report":   kwargs.get("validation_report"),
            "import_phase":        kwargs.get("import_phase"),
        }


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class BuildProfileInput:
    project_id: str
    version: int
    f3iche: str
    industry: str
    action: str = "create"
    industry_sub: Optional[str] = None
    company_size: Optional[str] = None
    company_name: Optional[str] = None
    f3iche_user: Optional[str] = None
    f3iche_signals: Optional[str] = None
    f3iche_match_status: str = "matched"
    uploaded_files: List[Dict] = field(default_factory=list)
    collected_signals: List[str] = field(default_factory=list)
    target_structure: Optional[Dict] = None
    field_mappings: Optional[Dict] = None
    validation_report: Optional[Dict] = None
    import_phase: Optional[str] = None


@dataclass
class MergeProfileInput:
    """Merge partial update onto existing profile snapshot."""
    existing_profile: Dict[str, Any]
    patch: Dict[str, Any]            # only the fields that changed
    action: str = "update"


# ── Activity definitions ─────────────────────────────────────────────────────

@activity.defn(name="build_company_profile")
async def build_company_profile(inp: BuildProfileInput) -> Dict[str, Any]:
    """Build a fresh versioned company profile snapshot."""
    return _CompanyProfileService.build(
        project_id=inp.project_id,
        version=inp.version,
        f3iche=inp.f3iche,
        industry=inp.industry,
        action=inp.action,
        industry_sub=inp.industry_sub,
        company_size=inp.company_size,
        company_name=inp.company_name,
        f3iche_user=inp.f3iche_user,
        f3iche_signals=inp.f3iche_signals,
        f3iche_match_status=inp.f3iche_match_status,
        uploaded_files=inp.uploaded_files,
        collected_signals=inp.collected_signals,
        target_structure=inp.target_structure,
        field_mappings=inp.field_mappings,
        validation_report=inp.validation_report,
        import_phase=inp.import_phase,
    )


@activity.defn(name="merge_company_profile")
async def merge_company_profile(inp: MergeProfileInput) -> Dict[str, Any]:
    """
    Merge a patch dict onto the latest profile and bump the version.
    Returns the updated profile — the workflow is responsible for persisting it.
    """
    existing = dict(inp.existing_profile)
    new_version = existing.get("version", 0) + 1

    # Prefer patch values; fall back to existing
    merged = {**existing, **{k: v for k, v in inp.patch.items() if v is not None}}
    merged["version"] = new_version
    merged["action"] = inp.action
    merged["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return merged