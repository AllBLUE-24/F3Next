"""Load Step 3 inputs from project artifacts or in-memory fixtures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings
from containers.implementation.readiness.config import require_discovery_context


class ReadinessInputError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ReadinessInputs:
    project_id: str
    manifest: Dict[str, Any]
    target_structure: Dict[str, Any]
    field_mappings_kb: Dict[str, Any] = field(default_factory=_kb_field_mappings)
    f3iche_id: Optional[str] = None
    user_decisions: Dict[str, Any] = field(default_factory=dict)


def build_readiness_inputs(
    *,
    project_id: str,
    manifest: Dict[str, Any],
    target_structure: Dict[str, Any],
    f3iche_id: Optional[str] = None,
    field_mappings_kb: Optional[Dict[str, Any]] = None,
    user_decisions: Optional[Dict[str, Any]] = None,
) -> ReadinessInputs:
    """Build inputs from an in-memory manifest + Discovery target (tests and harness)."""
    seeds = list(target_structure.get("seed_doctypes") or [])
    if require_discovery_context() and not seeds:
        raise ReadinessInputError(
            "missing_discovery_scope",
            "seed_doctypes required for readiness (set READINESS_REQUIRE_DISCOVERY=false to bypass)",
        )
    f3iche = f3iche_id
    if not f3iche:
        meta = manifest.get("discovery_metadata") or target_structure.get("discovery_metadata") or {}
        if isinstance(meta, dict):
            f3 = meta.get("f3iche")
            f3iche = f3 if isinstance(f3, str) else (f3 or {}).get("id") if isinstance(f3, dict) else None
    return ReadinessInputs(
        project_id=project_id,
        manifest=manifest,
        target_structure=target_structure,
        field_mappings_kb=field_mappings_kb or _kb_field_mappings(),
        f3iche_id=f3iche,
        user_decisions=dict(user_decisions or {}),
    )


async def load_readiness_inputs(
    project_id: str,
    *,
    session_id: Optional[str] = None,
    r2_manifest_url: Optional[str] = None,
) -> ReadinessInputs:
    """
    Load manifest + target structure for a project session.

    Pass ``r2_manifest_url`` when calling from workflow activities; Phase D
    will resolve it from session state automatically.
    """
    from containers.implementation.data_readiness_agent.activities import (
        _download_manifest,
        _load_target_structure,
    )

    sid = session_id or project_id
    target_structure = await _load_target_structure(sid)
    if not r2_manifest_url:
        raise ReadinessInputError(
            "missing_manifest_url",
            "r2_manifest_url required until readiness API resolves manifest from session",
        )
    manifest = _download_manifest(r2_manifest_url)
    if not manifest:
        raise ReadinessInputError("missing_manifest", f"Empty manifest at {r2_manifest_url}")
    return build_readiness_inputs(
        project_id=project_id,
        manifest=manifest,
        target_structure=target_structure,
    )
