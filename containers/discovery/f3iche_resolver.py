"""Resolve broad discovery f3iche to a concrete F3iche template ID."""

from __future__ import annotations

from pathlib import Path

from containers.implementation.signals_agent.discovery_niche_resolver import (
    resolve_niche_from_discovery,
)

_F3ICHE_DIR = Path(__file__).parent.parent / "knowledge_base" / "common" / "f3iches"


def list_f3iche_template_ids() -> list[str]:
    if not _F3ICHE_DIR.exists():
        return []
    return sorted(p.stem for p in _F3ICHE_DIR.glob("*.json"))


def resolve_discovery_f3iche_niche(
    *,
    discovery_f3iche: str,
    industry: str = "",
    chat_transcript: str = "",
) -> str:
    """Map trading|manufacturing|service to a template under common/f3iches/."""
    niche_ids = list_f3iche_template_ids()
    resolved = resolve_niche_from_discovery(
        discovery_f3iche=discovery_f3iche,
        discovery_industry=industry,
        chat_transcript=chat_transcript,
        niche_ids=niche_ids,
    )
    if resolved:
        return resolved
    if discovery_f3iche in niche_ids:
        return discovery_f3iche
    if niche_ids:
        prefix = f"{discovery_f3iche}_" if discovery_f3iche else ""
        matches = [n for n in niche_ids if n.startswith(prefix)] if prefix else niche_ids
        if matches:
            return matches[0]
        return niche_ids[0]
    return discovery_f3iche or "manufacturing_project_chemical"


def f3iche_template_path(f3iche_id: str) -> Path:
    path = _F3ICHE_DIR / f"{f3iche_id}.json"
    if path.exists():
        return path
    ids = list_f3iche_template_ids()
    if ids:
        return _F3ICHE_DIR / f"{ids[0]}.json"
    return path
