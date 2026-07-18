"""
Step 2 — enrich_corpus_understanding activity.

LLM pass over manifest file_meta; writes corpus_understanding back to R2 manifest.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from temporalio import activity

from containers.implementation.corpus.manifest import extract_files_from_manifest
from containers.implementation.corpus.prompts import CORPUS_UNDERSTANDING_PROMPT
from containers.implementation.corpus.schemas import CorpusUnderstanding
from containers.implementation.corpus.validation import (
    merge_missing_file_entries,
    validate_corpus_understanding,
)
from shared.llm_schema_utils import repair_pydantic_dict
from shared.structured_llm import generate_typed


def _extract_discovery_context(
    chat_history: Optional[List[Dict[str, Any]]] = None,
    discovery_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    if not chat_history and not discovery_metadata:
        return ""

    context_parts = ["BUSINESS CONTEXT FROM DISCOVERY CHAT:"]

    if discovery_metadata:
        bottleneck = discovery_metadata.get("bottleneck") or discovery_metadata.get("pain_point")
        if bottleneck:
            context_parts.append(f"- User's stated bottleneck/pain point: {bottleneck}")

        industry = discovery_metadata.get("industry") or discovery_metadata.get("f3iche_industry")
        if industry:
            context_parts.append(f"- Industry/business type: {industry}")

        scale = discovery_metadata.get("scale") or discovery_metadata.get("company_scale")
        if scale:
            context_parts.append(f"- Company scale: {scale}")

        legacy_system = discovery_metadata.get("legacy_system")
        if legacy_system:
            context_parts.append(f"- Current system: {legacy_system}")

    if chat_history and isinstance(chat_history, list):
        user_messages = [
            msg.get("content", "")
            for msg in chat_history
            if isinstance(msg, dict) and msg.get("role") == "user"
        ]
        if user_messages:
            recent = user_messages[-3:]
            context_parts.append("- Recent user statements:")
            for i, msg in enumerate(recent, 1):
                snippet = str(msg)[:200].strip()
                if snippet:
                    context_parts.append(f"  {i}. {snippet}")

    if len(context_parts) == 1:
        return ""

    context_parts.append(
        "\nUse this business context to inform your interpretation of the uploaded files. "
        "If the user said they track 'chemical batches' and you see manufacturing data, "
        "prioritize BOM/Work Order classifications. If they said 'construction projects', "
        "prioritize Project + Sales Order classifications."
    )

    return "\n".join(context_parts)


@dataclass
class EnrichCorpusUnderstandingInput:
    manifest_url: str
    user_import_note: Optional[str] = None
    discovery_chat_history: Optional[List[Dict[str, Any]]] = None
    discovery_metadata: Optional[Dict[str, Any]] = None


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
    activity.logger.info("▶ enrich_corpus_understanding | manifest=%s", inp.manifest_url)

    if not inp.manifest_url or inp.manifest_url.startswith("error"):
        activity.logger.warning("  ⚠️ No valid manifest URL — skipping corpus enrichment")
        return {
            "manifest_url": inp.manifest_url,
            "files_understood": 0,
            "corpus_summary": "",
            "status": "skipped",
            "warnings": [],
        }

    s3 = _get_s3()
    try:
        resp = s3.get_object(Bucket="clean-data", Key=inp.manifest_url)
        manifest = json.loads(resp["Body"].read().decode("utf-8"))
    except Exception as e:
        activity.logger.error("  ❌ Failed to load manifest: %s", e)
        return {
            "manifest_url": inp.manifest_url,
            "files_understood": 0,
            "corpus_summary": "",
            "status": "failed",
            "warnings": [{"code": "MANIFEST_LOAD_FAILED", "message": str(e)}],
            "error": str(e),
        }

    files = extract_files_from_manifest(manifest)
    if not files:
        activity.logger.warning("  ⚠️ Empty manifest — skipping")
        return {
            "manifest_url": inp.manifest_url,
            "files_understood": 0,
            "corpus_summary": "",
            "status": "skipped",
            "warnings": [],
        }

    expected_filenames = list(files.keys())
    discovery_context = _extract_discovery_context(
        inp.discovery_chat_history,
        inp.discovery_metadata,
    )

    prompt = CORPUS_UNDERSTANDING_PROMPT.format(
        discovery_context=discovery_context,
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
    except Exception as e:
        activity.logger.error("  ❌ LLM corpus understanding failed: %s", e)
        return {
            "manifest_url": inp.manifest_url,
            "files_understood": 0,
            "corpus_summary": "",
            "status": "failed",
            "warnings": [{"code": "LLM_FAILED", "message": str(e)}],
            "error": str(e),
        }

    corpus_dict = understanding.model_dump()
    corpus_dict["_validation"] = {"status": status, "warnings": warnings}
    manifest["corpus_understanding"] = corpus_dict

    try:
        s3.put_object(
            Bucket="clean-data",
            Key=inp.manifest_url,
            Body=json.dumps(manifest, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        activity.logger.info(
            "  ✅ Corpus understanding | status=%s | %d files | %d warnings",
            status, len(understanding.files), len(warnings),
        )
    except Exception as e:
        activity.logger.error("  ❌ Failed to write enriched manifest: %s", e)
        return {
            "manifest_url": inp.manifest_url,
            "files_understood": len(understanding.files),
            "corpus_summary": understanding.corpus_summary,
            "status": "partial",
            "warnings": warnings + [{"code": "R2_WRITE_FAILED", "message": str(e)}],
            "error": str(e),
        }

    if status == "failed":
        activity.logger.warning(
            "  ⚠️ Corpus understanding validation failed — downstream uses deterministic fallback",
        )

    return {
        "manifest_url": inp.manifest_url,
        "files_understood": len(understanding.files),
        "corpus_summary": understanding.corpus_summary,
        "status": status,
        "warnings": warnings,
    }
