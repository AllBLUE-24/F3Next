"""Load Step 4 inputs from manifest + target + assignments."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from containers.implementation.mapping_agent.kb import field_mappings as _kb_field_mappings


@dataclass
class MapValidateInputs:
    project_id: str
    files: Dict[str, str]
    target_structure: Dict[str, Any]
    file_doctype_pairs: List[Tuple[str, str]]
    field_mappings_kb: Dict[str, Any] = field(default_factory=_kb_field_mappings)
    company_context: Dict[str, Any] = field(default_factory=dict)
    readiness_level: Optional[str] = None


def _pairs_from_corpus(
    files: Dict[str, str],
    corpus_understanding: Optional[Dict[str, Any]],
    seed_doctypes: List[str],
) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    seed_set = set(seed_doctypes or [])
    if not corpus_understanding:
        return pairs
    for entry in corpus_understanding.get("files") or []:
        if not isinstance(entry, dict):
            continue
        fname = str(entry.get("filename") or "")
        if fname not in files:
            continue
        for dt in entry.get("likely_erpnext_doctypes") or []:
            dt_s = str(dt)
            if dt_s in seed_set or not seed_set:
                pairs.append((fname, dt_s))
    # Party split: always attempt Customer/Supplier on partners file
    for fname in files:
        if "partner" in fname.lower():
            pairs.append((fname, "Customer"))
            pairs.append((fname, "Supplier"))
    return list(dict.fromkeys(pairs))


def build_map_validate_inputs(
    *,
    project_id: str,
    files: Dict[str, str],
    target_structure: Dict[str, Any],
    corpus_understanding: Optional[Dict[str, Any]] = None,
    file_doctype_pairs: Optional[List[Tuple[str, str]]] = None,
    field_mappings_kb: Optional[Dict[str, Any]] = None,
    company_context: Optional[Dict[str, Any]] = None,
    readiness_level: Optional[str] = None,
) -> MapValidateInputs:
    seeds = list(target_structure.get("seed_doctypes") or [])
    pairs = file_doctype_pairs or _pairs_from_corpus(files, corpus_understanding, seeds)
    return MapValidateInputs(
        project_id=project_id,
        files=files,
        target_structure=target_structure,
        file_doctype_pairs=pairs,
        field_mappings_kb=field_mappings_kb or _kb_field_mappings(),
        company_context=dict(company_context or {"company_name": "Session Company"}),
        readiness_level=readiness_level,
    )
