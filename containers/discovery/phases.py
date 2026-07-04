"""Discovery Assistant phase constants (Step 1 nomenclature)."""

from __future__ import annotations

from enum import Enum


class DiscoveryPhase(str, Enum):
    INITIAL_CHAT = "initial_chat"
    WORKFLOW_DISPLAY = "workflow_display"
    MODULE_CONFIRMATION = "module_confirmation"
    FINALIZED = "finalized"


def get_phase(metadata: dict | None) -> DiscoveryPhase:
    if not metadata:
        return DiscoveryPhase.INITIAL_CHAT
    raw = metadata.get("phase")
    if raw:
        try:
            return DiscoveryPhase(raw)
        except ValueError:
            pass
    # Legacy projects: discovery completed before phased workflow
    if metadata.get("f3iche") and metadata.get("target_structure"):
        return DiscoveryPhase.FINALIZED
    if metadata.get("f3iche"):
        return DiscoveryPhase.MODULE_CONFIRMATION
    return DiscoveryPhase.INITIAL_CHAT


def is_upload_ready(metadata: dict | None) -> bool:
    return get_phase(metadata) == DiscoveryPhase.FINALIZED
