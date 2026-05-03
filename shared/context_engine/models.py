"""Domain objects returned by the Context Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ProjectContext:
    """Composed 3-tier + CVS context for a project."""

    project_id: str
    f3iche_id: str
    layers: list[str]
    tier1: dict[str, Any] = field(default_factory=dict)
    tier2_raw: dict[str, Any] = field(default_factory=dict)
    tier2_merged_graph: dict[str, Any] = field(default_factory=dict)
    cvs: dict[str, Any] = field(default_factory=dict)
    tier1_checksum: str = ""
    context_version: Optional[int] = None
