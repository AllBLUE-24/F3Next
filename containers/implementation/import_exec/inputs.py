"""Load Step 5 inputs from target, mapped data, and Step 4 gate."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ImportInputs:
    project_id: str
    setup_steps: List[Dict[str, Any]]
    target_structure: Dict[str, Any]
    mapped_data_dict: Dict[str, Dict[str, Any]]
    validation_level: str = "partial"
    import_ready_from_validate: bool = True
    criticality_map: Dict[str, str] = field(default_factory=dict)
    validation_failed_doctypes: List[str] = field(default_factory=list)


def build_import_inputs(
    *,
    project_id: str,
    setup_steps: List[Dict[str, Any]],
    target_structure: Dict[str, Any],
    mapped_data_dict: Dict[str, Dict[str, Any]],
    validation_level: Optional[str] = None,
    import_ready_from_validate: bool = True,
    criticality_map: Optional[Dict[str, str]] = None,
    validation_failed_doctypes: Optional[List[str]] = None,
) -> ImportInputs:
    return ImportInputs(
        project_id=project_id,
        setup_steps=list(setup_steps or []),
        target_structure=dict(target_structure or {}),
        mapped_data_dict=dict(mapped_data_dict or {}),
        validation_level=str(validation_level or "partial").lower(),
        import_ready_from_validate=import_ready_from_validate,
        criticality_map=dict(criticality_map or {}),
        validation_failed_doctypes=list(validation_failed_doctypes or []),
    )
