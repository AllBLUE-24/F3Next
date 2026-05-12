"""
containers/knowledge_base/seed_f3iches.py

Seeds F3iche narrative content into kb_embeddings for RAG retrieval.

kb_source convention:
  f3iche_<f3iche_id>

This is designed to complement:
  - Layer 1: apqc_pcf
  - Layer 2: erpnext_docs
  - Layer 3: CVS + structured F3iche JSON (still used deterministically)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from sqlalchemy import text

# Path bootstrap so 'shared' and 'llm_router' imports resolve
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_ROOT))

load_dotenv()

from shared.database.db import AsyncSessionLocal  # noqa: E402
from shared.embedding_generator import generate_embedding  # noqa: E402

RATE_LIMIT_DELAY = 0.5

F3ICHE_DIR = _HERE / "common" / "f3iches"





def _chunks_from_md(file_path: Path) -> list[str]:
    """Parse pre-generated narrative prose chunks from a Markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    chunks = []
    # Split by the exact header used in our prose templates
    for block in content.split("[F3iche]"):
        block = block.strip()
        if not block:
            continue
        chunks.append(f"[F3iche]\n{block}")
    return chunks

def _chunks_from_f3iche(defn: dict[str, Any], *, f3iche_id: str) -> list[str]:
    chunks: list[str] = []

    # Helper to append a chunk
    def add_chunk(section: str, content: str):
        if not content.strip(): return
        chunks.append(
            f"[F3iche]\n"
            f"F3iche ID: {f3iche_id}\n"
            f"Section: {section}\n\n"
            f"{content.strip()}"
        )

    # 1. Handle V2 'business_reality' (Dict) or V1 (String)
    br = defn.get("business_reality")
    if isinstance(br, str):
        add_chunk("business_reality", br)
    elif isinstance(br, dict):
        # Flatten the typical profile
        if "typical_company_profile" in br:
            add_chunk("business_reality.typical_company_profile", json.dumps(br["typical_company_profile"], indent=2))
        
        # Flatten the actual workflow
        if "actual_workflow" in br:
            for step_name, step_data in br["actual_workflow"].items():
                if isinstance(step_data, dict):
                    add_chunk(f"business_reality.actual_workflow.{step_name}", json.dumps(step_data, indent=2))
                elif isinstance(step_data, str):
                    add_chunk(f"business_reality.actual_workflow", step_data)
                    
        # Flatten pain points
        if "key_pain_points" in br:
            add_chunk("business_reality.key_pain_points", json.dumps(br["key_pain_points"], indent=2))
            
        # Flatten compliance
        if "compliance_requirements" in br:
            add_chunk("business_reality.compliance_requirements", json.dumps(br["compliance_requirements"], indent=2))

    # 2. Handle ERPNext Masters Setup
    masters = defn.get("erpnext_masters_setup")
    if isinstance(masters, dict):
        for k, v in masters.items():
            add_chunk(f"erpnext_masters_setup.{k}", json.dumps(v, indent=2))

    # 3. Handle Default Settings
    defaults = defn.get("default_settings")
    if isinstance(defaults, dict):
        add_chunk("default_settings", json.dumps(defaults, indent=2))

    # 4. Handle Workflow Processes
    workflows = defn.get("workflow_processes") or defn.get("known_workflows") or defn.get("workflows")
    if isinstance(workflows, list):
        for idx, wf in enumerate(workflows, 1):
            if isinstance(wf, dict):
                add_chunk(f"workflow_processes[{idx}]: {wf.get('process_name', 'Unknown')}", json.dumps(wf, indent=2))
            else:
                add_chunk(f"workflow_processes[{idx}]", str(wf))

    # 5. Handle Common Failures
    failures = defn.get("common_failures")
    if isinstance(failures, list):
        for idx, fail in enumerate(failures, 1):
            add_chunk(f"common_failures[{idx}]", json.dumps(fail, indent=2))

    # 6. Fallback for V1 schemas
    critical_checks = defn.get("critical_checks")
    if isinstance(critical_checks, list):
        for idx, chk in enumerate(critical_checks, 1):
            add_chunk(f"critical_checks[{idx}]", str(chk))
            
    regulatory = defn.get("regulatory_context")
    if isinstance(regulatory, str):
        add_chunk("regulatory_context", regulatory)

    return chunks


async def seed_database(target_file: str | None = None) -> None:
    if not F3ICHE_DIR.exists():
        raise FileNotFoundError(f"F3iche dir not found: {F3ICHE_DIR}")

    if target_file:
        files = [F3ICHE_DIR / target_file]
        if not files[0].exists():
             raise FileNotFoundError(f"Target file not found: {files[0]}")
    else:
        files = sorted(F3ICHE_DIR.glob("*.json"))
        if not files:
            raise RuntimeError(f"No f3iche json files found in {F3ICHE_DIR}")

    async with AsyncSessionLocal() as session:
        for f in files:
            f3iche_id = f.stem
            kb_source = f"f3iche_{f3iche_id}"
            
            # Prefer pre-generated Markdown prose chunks if they exist
            md_file = f.with_suffix(".md")
            if md_file.exists():
                chunks = _chunks_from_md(md_file)
                print(f"📖 Loaded {len(chunks)} prose chunks from {md_file.name}")
            else:
                with open(f, encoding="utf-8") as fh:
                    defn = json.load(fh)
                chunks = _chunks_from_f3iche(defn, f3iche_id=f3iche_id)
                print(f"⚙️ Loaded {len(chunks)} raw JSON chunks from {f.name}")

            if not chunks:
                continue

            # Idempotent: wipe existing rows for this f3iche prefix
            await session.execute(
                text("DELETE FROM kb_embeddings WHERE kb_source LIKE :pfx"),
                {"pfx": f"{kb_source}%"},
            )
            await session.commit()

            for chunk in chunks:
                vec = await generate_embedding(chunk)
                vec_str = "[" + ",".join(map(str, vec)) + "]"
                await session.execute(
                    text(
                        """
                        INSERT INTO kb_embeddings (kb_source, content, embedding)
                        VALUES (:source, :content, CAST(:vector AS vector))
                        """
                    ),
                    {"source": kb_source, "content": chunk, "vector": vec_str},
                )
                await asyncio.sleep(RATE_LIMIT_DELAY)

            await session.commit()
            print(f"✅ Seeded {len(chunks)} chunks for {kb_source}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(seed_database(target))

