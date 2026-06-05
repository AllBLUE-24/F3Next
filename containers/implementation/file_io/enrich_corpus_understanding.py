"""
File IO — enrich_corpus_understanding activity (Step 2b).

LLM pass over the v2 manifest's file_meta to produce semantic understanding
per file and a corpus-level summary. Writes results back to the same R2 manifest.

Downstream steps (signals, gap_analyzer, target) consume corpus_understanding
to avoid KB-only false positives (e.g. client_orders.csv ≠ Work Order).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from temporalio import activity

from containers.implementation.file_io.corpus_models import CorpusUnderstanding
from containers.implementation.file_io.manifest_utils import extract_files_from_manifest
from shared.structured_llm import generate_typed

_CORPUS_PROMPT = """\
You are the F3Next Corpus Understanding agent. Your job is to read uploaded business
files and describe what they ACTUALLY contain — not what column names superficially suggest.

CRITICAL RULES:
1. Read column names AND sample row values together. "Product" in a client order file
   is a sold SKU/service — NOT a manufacturing BOM item. "Project" is a client job site —
   NOT an ERPNext Work Order.
2. For each file, list likely_erpnext_doctypes (best matches) AND explicitly_not_doctypes
   (common false positives to suppress). Be specific.
3. "names" or "name" columns with person names (e.g. "Parth Kulkarni") = Employee data,
   even if the column is plural or informal.
4. Do NOT invent doctypes. Use standard ERPNext names: Customer, Supplier, Item, Employee,
   Purchase Order, Sales Order, Project, BOM, Work Order, etc.
5. If a file is clearly procurement, say Purchase Order — not Work Order.
6. If a file is client/project orders or installation jobs, say Sales Order or Project —
   explicitly NOT Work Order or BOM unless batch/manufacturing signals are present.

USER IMPORT NOTE (may clarify intent):
{user_import_note}

FILES TO ANALYZE:
{files_block}

Return structured JSON matching the schema exactly.
"""


@dataclass
class EnrichCorpusUnderstandingInput:
    manifest_url: str
    user_import_note: Optional[str] = None


def _get_s3():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def _build_files_block(manifest: Dict[str, Any]) -> str:
    file_meta = manifest.get("file_meta") or {}
    files = manifest.get("files") or {}
    blocks: List[str] = []

    for fname, meta in file_meta.items():
        content = files.get(fname, "")
        snippet = (content or "")[:800]
        block = (
            f"FILE: {fname}\n"
            f"COLUMNS: {json.dumps(meta.get('columns') or [])}\n"
            f"ROW_COUNT: {meta.get('row_count', 0)}\n"
            f"SAMPLE_ROWS: {json.dumps(meta.get('sample_rows') or [])}\n"
            f"CONTENT_SNIPPET:\n{snippet}\n"
            "---"
        )
        blocks.append(block)

    if not blocks and files:
        for fname, content in files.items():
            blocks.append(f"FILE: {fname}\nCONTENT_SNIPPET:\n{(content or '')[:800]}\n---")

    return "\n".join(blocks)


@activity.defn(name="enrich_corpus_understanding")
async def enrich_corpus_understanding(inp: EnrichCorpusUnderstandingInput) -> Dict[str, Any]:
    """
    LLM semantic pass over parsed manifest. Updates manifest in R2 with corpus_understanding.

    Returns: {manifest_url, files_understood, corpus_summary}
    """
    activity.logger.info("▶ enrich_corpus_understanding | manifest=%s", inp.manifest_url)

    if not inp.manifest_url or inp.manifest_url.startswith("error"):
        activity.logger.warning("  ⚠️ No valid manifest URL — skipping corpus enrichment")
        return {"manifest_url": inp.manifest_url, "files_understood": 0, "corpus_summary": ""}

    s3 = _get_s3()
    try:
        resp = s3.get_object(Bucket="clean-data", Key=inp.manifest_url)
        manifest = json.loads(resp["Body"].read().decode("utf-8"))
    except Exception as e:
        activity.logger.error("  ❌ Failed to load manifest: %s", e)
        return {"manifest_url": inp.manifest_url, "files_understood": 0, "corpus_summary": "", "error": str(e)}

    files = extract_files_from_manifest(manifest)
    if not files:
        activity.logger.warning("  ⚠️ Empty manifest — skipping")
        return {"manifest_url": inp.manifest_url, "files_understood": 0, "corpus_summary": ""}

    prompt = _CORPUS_PROMPT.format(
        user_import_note=inp.user_import_note or "(none)",
        files_block=_build_files_block(manifest),
    )

    try:
        llm_result = await generate_typed(
            prompt=prompt,
            schema=CorpusUnderstanding,
            temperature=0.1,
            max_output_tokens=4000,
        )
        understanding = CorpusUnderstanding.model_validate(llm_result)
    except Exception as e:
        activity.logger.error("  ❌ LLM corpus understanding failed: %s", e)
        return {
            "manifest_url": inp.manifest_url,
            "files_understood": 0,
            "corpus_summary": "",
            "error": str(e),
        }

    corpus_dict = understanding.model_dump()
    manifest["corpus_understanding"] = corpus_dict

    try:
        s3.put_object(
            Bucket="clean-data",
            Key=inp.manifest_url,
            Body=json.dumps(manifest, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info(
            "  ✅ Corpus understanding written | %d files | summary=%s",
            len(understanding.files),
            understanding.corpus_summary[:120],
        )
    except Exception as e:
        activity.logger.error("  ❌ Failed to write enriched manifest: %s", e)
        return {
            "manifest_url": inp.manifest_url,
            "files_understood": len(understanding.files),
            "corpus_summary": understanding.corpus_summary,
            "error": str(e),
        }

    return {
        "manifest_url": inp.manifest_url,
        "files_understood": len(understanding.files),
        "corpus_summary": understanding.corpus_summary,
    }
