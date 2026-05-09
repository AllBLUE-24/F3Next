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





def _chunks_from_f3iche(defn: dict[str, Any], *, f3iche_id: str) -> list[str]:
    chunks: list[str] = []

    business_reality = defn.get("business_reality")
    if isinstance(business_reality, str) and business_reality.strip():
        chunks.append(
            "[F3iche]\n"
            f"F3iche ID: {f3iche_id}\n"
            "Section: business_reality\n\n"
            f"{business_reality.strip()}"
        )

    critical_checks = defn.get("critical_checks")
    if isinstance(critical_checks, list):
        for idx, chk in enumerate(critical_checks, 1):
            if isinstance(chk, str) and chk.strip():
                chunks.append(
                    "[F3iche]\n"
                    f"F3iche ID: {f3iche_id}\n"
                    f"Section: critical_checks[{idx}]\n\n"
                    f"{chk.strip()}"
                )
            elif isinstance(chk, dict):
                txt = json.dumps(chk, ensure_ascii=False)
                chunks.append(
                    "[F3iche]\n"
                    f"F3iche ID: {f3iche_id}\n"
                    f"Section: critical_checks[{idx}]\n\n"
                    f"{txt}"
                )

    known_workflows = defn.get("known_workflows") or defn.get("workflows")
    if isinstance(known_workflows, list):
        for idx, wf in enumerate(known_workflows, 1):
            if isinstance(wf, str) and wf.strip():
                chunks.append(
                    "[F3iche]\n"
                    f"F3iche ID: {f3iche_id}\n"
                    f"Section: known_workflows[{idx}]\n\n"
                    f"{wf.strip()}"
                )

    regulatory = defn.get("regulatory_context")
    if isinstance(regulatory, str) and regulatory.strip():
        chunks.append(
            "[F3iche]\n"
            f"F3iche ID: {f3iche_id}\n"
            "Section: regulatory_context\n\n"
            f"{regulatory.strip()}"
        )

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
            with open(f, encoding="utf-8") as fh:
                defn = json.load(fh)

            chunks = _chunks_from_f3iche(defn, f3iche_id=f3iche_id)
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

