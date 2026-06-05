"""Tier-2 LLM column → ERP field mapping (primary for unmapped / required gaps)."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from shared.structured_llm import generate_typed


class ColumnMapOutput(BaseModel):
    mappings: Dict[str, str] = Field(default_factory=dict)
    confidence: float = 0.0
    notes: str = ""


def _field_schema_summary(doctype: str, kb: Dict[str, Any]) -> str:
    dt_cfg = (kb.get("doctypes") or {}).get(doctype) or {}
    lines: List[str] = []
    for _fn, cfg in (dt_cfg.get("field_mappings") or {}).items():
        fname = cfg.get("fieldname", _fn)
        mandatory = cfg.get("mandatory") or (fname in (dt_cfg.get("mandatory_fields") or []))
        syns = cfg.get("user_input_synonyms") or []
        lines.append(
            f"- {fname} ({cfg.get('fieldtype', 'Data')})"
            + (" [required]" if mandatory else "")
            + (f" synonyms={syns[:5]}" if syns else "")
        )
    return "\n".join(lines[:40]) or "(no KB fields)"


async def llm_map_columns(
    *,
    doctype: str,
    columns: List[str],
    sample_rows: List[Dict[str, Any]],
    required_fields: List[str],
    unmapped_columns: List[str],
    kb: Dict[str, Any],
    corpus_hints: Optional[Dict[str, Any]] = None,
    model_name: Optional[str] = None,
) -> Dict[str, str]:
    """
    Map source columns to ERPNext fieldnames using LLM + sample values.

    Returns {source_column: erp_fieldname} for confident mappings only.
    """
    if not unmapped_columns and not required_fields:
        return {}

    col_interp = ""
    if corpus_hints:
        for entry in corpus_hints.get("column_interpretations") or []:
            if isinstance(entry, dict):
                col_interp += f"  {entry.get('column')}: {entry.get('meaning')}\n"

    samples = json.dumps(sample_rows[:3], indent=2, default=str)[:2000]

    prompt = f"""You are an ERPNext data mapping expert.

Doctype: {doctype}
Required ERP fields for import: {required_fields}

Source columns (need mapping): {unmapped_columns}
All file columns: {columns}

Sample rows:
{samples}

Corpus column interpretations:
{col_interp or "(none)"}

ERP field schema:
{_field_schema_summary(doctype, kb)}

TASK: Map each source column to the best ERPNext fieldname for this doctype.
Rules:
- Use sample VALUES not just header names (Vendor_Name → supplier, Target_Date → delivery_date).
- Only map to valid fieldnames from the schema above.
- Map child line fields as items.item_code, items.qty when appropriate.
- Do NOT invent fieldnames.
- Return empty mappings if unsure.

Return JSON with mappings: {{ "source_col": "erp_fieldname", ... }}
"""

    try:
        res = await generate_typed(
            prompt=prompt,
            schema=ColumnMapOutput,
            model_name=model_name or os.getenv("MAPPING_EXTRACTION_MODEL", "gpt-4o-mini"),
            temperature=0.0,
            max_output_tokens=1200,
            system_instruction="Return only the JSON object. No markdown.",
        )
        raw = res.get("mappings") if isinstance(res, dict) else {}
        if not isinstance(raw, dict):
            return {}
        valid_fields = {
            cfg.get("fieldname", fn)
            for fn, cfg in ((kb.get("doctypes") or {}).get(doctype) or {}).get("field_mappings", {}).items()
        }
        valid_child = {f"items.{c}" for c in ("item_code", "qty", "rate", "uom", "warehouse")}
        out: Dict[str, str] = {}
        for src, tgt in raw.items():
            if not src or not tgt:
                continue
            tgt_s = str(tgt).strip()
            if tgt_s in valid_fields or tgt_s in valid_child or "." in tgt_s:
                out[str(src)] = tgt_s
        return out
    except Exception:
        return {}
