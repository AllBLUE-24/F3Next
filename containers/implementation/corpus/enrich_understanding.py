"""Step 2 — enrich_corpus_understanding activity."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from temporalio import activity

from containers.implementation.corpus.checkers import evaluate_step2_gate
from containers.implementation.corpus.discovery_context import (
    DiscoveryContextError,
    build_discovery_context_block,
)
from containers.implementation.corpus.manifest import extract_files_from_manifest
from containers.implementation.corpus.prompts import CORPUS_UNDERSTANDING_PROMPT
from containers.implementation.corpus.schemas import CorpusUnderstanding
from containers.implementation.corpus.validation import (
    merge_missing_file_entries,
    validate_corpus_understanding,
)
from shared.llm_schema_utils import repair_pydantic_dict
from shared.structured_llm import generate_typed


@dataclass
class EnrichCorpusUnderstandingInput:
    manifest_url: str
    user_import_note: Optional[str] = None
    discovery_chat_history: Optional[List[Dict[str, Any]]] = None
    discovery_metadata: Optional[Dict[str, Any]] = None
    discovery_status: Optional[str] = None


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


def _failed_response(
    manifest_url: str,
    code: str,
    message: str,
    *,
    extra_warnings: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    warnings = [{"code": code, "message": message}]
    if extra_warnings:
        warnings.extend(extra_warnings)
    return {
        "manifest_url": manifest_url,
        "files_understood": 0,
        "corpus_summary": "",
        "status": "failed",
        "gate_passed": False,
        "warnings": warnings,
        "error": message,
    }


@activity.defn(name="enrich_corpus_understanding")
async def enrich_corpus_understanding(inp: EnrichCorpusUnderstandingInput) -> Dict[str, Any]:
    activity.logger.info("▶ enrich_corpus_understanding | manifest=%s", inp.manifest_url)

    if not inp.manifest_url or inp.manifest_url.startswith("error"):
        activity.logger.warning("  ⚠️ No valid manifest URL — skipping corpus enrichment")
        return {
            "manifest_url": inp.manifest_url,
            "files_understood": 0,
            "corpus_summary": "",
            "status": "skipped",
            "gate_passed": False,
            "warnings": [],
        }

    s3 = _get_s3()
    try:
        resp = s3.get_object(Bucket="clean-data", Key=inp.manifest_url)
        manifest = json.loads(resp["Body"].read().decode("utf-8"))
    except Exception as e:
        activity.logger.error("  ❌ Failed to load manifest: %s", e)
        return _failed_response(inp.manifest_url, "MANIFEST_LOAD_FAILED", str(e))

    files = extract_files_from_manifest(manifest)
    if not files:
        activity.logger.warning("  ⚠️ Empty manifest — skipping")
        return {
            "manifest_url": inp.manifest_url,
            "files_understood": 0,
            "corpus_summary": "",
            "status": "skipped",
            "gate_passed": False,
            "warnings": [],
        }

    expected_filenames = list(files.keys())

    try:
        ctx_result = build_discovery_context_block(
            inp.discovery_chat_history,
            inp.discovery_metadata,
            discovery_status=inp.discovery_status,
        )
    except DiscoveryContextError as exc:
        activity.logger.error("  ❌ %s: %s", exc.code, exc.message)
        return _failed_response(inp.manifest_url, exc.code, exc.message)

    pre_warnings = list(ctx_result.warnings)
    if not ctx_result.ok and not ctx_result.context_block:
        activity.logger.warning("  ⚠️ No discovery context — proceeding with file evidence only")
        pre_warnings.append({
            "code": "DISCOVERY_CONTEXT_ABSENT",
            "message": "Corpus understanding running without discovery context (non-ideal).",
        })

    prompt = CORPUS_UNDERSTANDING_PROMPT.format(
        discovery_context=ctx_result.context_block or "(none — infer from file evidence only)",
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
        understanding = CorpusUnderstanding.model_validate(
            repair_pydantic_dict(llm_result, CorpusUnderstanding)
        )
        understanding = merge_missing_file_entries(understanding, expected_filenames)
        status, warnings = validate_corpus_understanding(understanding, expected_filenames)
        warnings = pre_warnings + warnings
    except Exception as e:
        activity.logger.error("  ❌ LLM corpus understanding failed: %s", e)
        return _failed_response(inp.manifest_url, "LLM_FAILED", str(e), extra_warnings=pre_warnings)

    corpus_dict = understanding.model_dump()
    corpus_dict["_validation"] = {"status": status, "warnings": warnings}
    corpus_dict["_discovery_source"] = ctx_result.source
    manifest["corpus_understanding"] = corpus_dict

    gate = evaluate_step2_gate(manifest, require_understanding=True)
    gate_passed = gate.passed and status != "failed"

    try:
        s3.put_object(
            Bucket="clean-data",
            Key=inp.manifest_url,
            Body=json.dumps(manifest, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info(
            "  ✅ Corpus understanding | status=%s | gate=%s | %d files | %d warnings",
            status, gate_passed, len(understanding.files), len(warnings),
        )
    except Exception as e:
        activity.logger.error("  ❌ Failed to write enriched manifest: %s", e)
        return {
            "manifest_url": inp.manifest_url,
            "files_understood": len(understanding.files),
            "corpus_summary": understanding.corpus_summary,
            "status": "partial",
            "gate_passed": False,
            "warnings": warnings + [{"code": "R2_WRITE_FAILED", "message": str(e)}],
            "error": str(e),
        }

    if status == "failed" or not gate_passed:
        activity.logger.warning(
            "  ⚠️ Corpus gate not passed (status=%s gate=%s) — review before mapping",
            status, gate_passed,
        )

    return {
        "manifest_url": inp.manifest_url,
        "files_understood": len(understanding.files),
        "corpus_summary": understanding.corpus_summary,
        "status": status,
        "gate_passed": gate_passed,
        "gate_status": gate.status,
        "warnings": warnings,
    }


from containers.implementation.corpus.discovery_context import extract_discovery_context as _extract_discovery_context
