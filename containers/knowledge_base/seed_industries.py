"""
containers/knowledge_base/seed_industries.py

Seeds broad Industry narrative content into kb_embeddings for RAG retrieval.

kb_source convention:
  industry_<industry_id>
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

# Path bootstrap so 'shared' and 'llm_router' imports resolve
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_ROOT))

load_dotenv()

from shared.database.db import AsyncSessionLocal
from shared.embedding_generator import generate_embedding

RATE_LIMIT_DELAY = 0.5
INDUSTRIES_DIR = _HERE / "common" / "industries"


def _chunks_from_md(file_path: Path) -> list[str]:
    """Parse narrative prose chunks from a Markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    chunks = []
    # Split by the exact header used in our prose templates
    for block in content.split("[Industry]"):
        block = block.strip()
        if not block:
            continue
        chunks.append(f"[Industry]\n{block}")
    return chunks


async def seed_database(target_file: str | None = None) -> None:
    if not INDUSTRIES_DIR.exists():
        raise FileNotFoundError(f"Industries dir not found: {INDUSTRIES_DIR}")

    if target_file:
        files = [INDUSTRIES_DIR / target_file]
        if not files[0].exists():
             raise FileNotFoundError(f"Target file not found: {files[0]}")
    else:
        files = sorted(INDUSTRIES_DIR.glob("*.md"))
        if not files:
            raise RuntimeError(f"No .md files found in {INDUSTRIES_DIR}")

    async with AsyncSessionLocal() as session:
        for f in files:
            if f.suffix != ".md":
                continue
                
            industry_id = f.stem
            kb_source = f"industry_{industry_id}"
            
            chunks = _chunks_from_md(f)
            if not chunks:
                print(f"⚠️ No chunks found in {f.name}")
                continue
                
            print(f"📖 Loaded {len(chunks)} prose chunks from {f.name}")

            # Idempotent: wipe existing rows for this industry prefix
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
