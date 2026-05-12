"""
containers/knowledge_base/seed_erpnext_prose.py

Seeds AI-generated, high-fidelity ERPNext narrative prose into kb_embeddings.
This replaces the old HTML-scraped docs with dense, clean semantic chunks.

kb_source convention:
  erpnext_docs
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

# Path bootstrap so 'shared' imports resolve
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_ROOT))

load_dotenv()

from shared.database.db import AsyncSessionLocal
from shared.embedding_generator import generate_embedding

RATE_LIMIT_DELAY = 0.5
ERPNEXT_DIR = _HERE / "common" / "erpnext"


def _chunks_from_md(file_path: Path) -> list[str]:
    """Parse narrative prose chunks from the ERPNext markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    chunks = []
    # Split by the exact header used in our prose templates
    for block in content.split("[ERPNext Docs]"):
        block = block.strip()
        if not block:
            continue
        # Check if it's the actual chunk or just the file comment block
        if block.startswith("<!--"):
            continue
            
        chunks.append(f"[ERPNext Docs]\n{block}")
    return chunks


async def seed_database(target_file: str | None = None) -> None:
    if not ERPNEXT_DIR.exists():
        raise FileNotFoundError(f"ERPNext directory not found: {ERPNEXT_DIR}")

    if target_file:
        files = [ERPNEXT_DIR / target_file]
        if not files[0].exists():
             raise FileNotFoundError(f"Target file not found: {files[0]}")
    else:
        files = sorted(ERPNEXT_DIR.glob("*.md"))
        if not files:
            raise RuntimeError(f"No .md files found in {ERPNEXT_DIR}")

    kb_source = "erpnext_docs"

    async with AsyncSessionLocal() as session:
        for f in files:
            if f.suffix != ".md":
                continue
                
            chunks = _chunks_from_md(f)
            if not chunks:
                print(f"⚠️ No chunks found in {f.name}")
                continue
                
            print(f"📖 Loaded {len(chunks)} ERPNext prose chunks from {f.name}")

            # Idempotent: wipe existing rows for ERPNext docs
            await session.execute(
                text("DELETE FROM kb_embeddings WHERE kb_source = :src"),
                {"src": kb_source},
            )
            await session.commit()
            print("🧹 Cleared existing legacy ERPNext docs from database.")

            print("🚀 Starting embedding process...")
            for i, chunk in enumerate(chunks, 1):
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
                if i % 10 == 0:
                    print(f"   Embedded {i}/{len(chunks)} chunks...")
                await asyncio.sleep(RATE_LIMIT_DELAY)

            await session.commit()
            print(f"✅ Successfully seeded {len(chunks)} chunks for {kb_source}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(seed_database(target))
