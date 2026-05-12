"""
containers/knowledge_base/seed_module_docs.py

Seeds ERPNext module docs from module_docs.json into kb_embeddings for RAG retrieval.
Replaces the old noisy scraped docs.

kb_source: erpnext_module_docs
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_ROOT))

load_dotenv()

from shared.database.db import AsyncSessionLocal
from shared.embedding_generator import generate_embedding

RATE_LIMIT_DELAY = 0.5
MODULE_DOCS_PATH = _HERE / "erpnext" / "docs" / "module_docs.json"


def _chunks_from_module_docs(defn: dict) -> list[str]:
    chunks = []
    
    modules = defn.get("modules", {})
    for mod_name, mod_data in modules.items():
        mod_display = mod_data.get("display_name", mod_name)
        
        # 1. Doctype Chunks (Highest Signal)
        for dt in mod_data.get("key_doctypes", []):
            doctype = dt.get("doctype")
            if not doctype: continue
            
            purpose = dt.get("purpose", "")
            key_fields = ", ".join(dt.get("key_fields", []))
            workflow = dt.get("workflow", "None")
            common_use = dt.get("common_use", "")
            
            chunk = (
                f"[ERPNext Docs] {mod_display} Module\n"
                f"Doctype: {doctype}\n"
                f"Purpose: {purpose}\n"
                f"Key fields: {key_fields}\n"
                f"Workflow: {workflow}\n"
                f"Business use: {common_use}"
            )
            chunks.append(chunk)
            
        # 2. Workflow Chunks
        for wf in mod_data.get("common_workflows", []):
            wf_name = wf.get("workflow_name")
            steps = " → ".join(wf.get("steps", []))
            chunk = (
                f"[ERPNext Docs] {mod_display} Module - Workflow\n"
                f"Workflow: {wf_name}\n"
                f"Steps: {steps}"
            )
            chunks.append(chunk)

    # 3. India Compliance Chunks
    india = defn.get("india_compliance", {})
    for k, v in india.items():
        desc = v.get("description", "")
        features = ", ".join(v.get("features", []))
        chunk = (
            f"[ERPNext Docs] India Compliance\n"
            f"Topic: {k}\n"
            f"Description: {desc}\n"
            f"Features: {features}"
        )
        chunks.append(chunk)

    return chunks


async def seed_database() -> None:
    if not MODULE_DOCS_PATH.exists():
        raise FileNotFoundError(f"module_docs.json not found: {MODULE_DOCS_PATH}")

    with open(MODULE_DOCS_PATH, "r", encoding="utf-8") as fh:
        defn = json.load(fh)
        
    chunks = _chunks_from_module_docs(defn)
    kb_source = "erpnext_module_docs"
    
    print(f"Loaded {len(chunks)} prose chunks from module_docs.json")

    async with AsyncSessionLocal() as session:
        # Idempotent: wipe existing
        await session.execute(
            text("DELETE FROM kb_embeddings WHERE kb_source = :src"),
            {"src": kb_source},
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
        print(f"Seeded {len(chunks)} chunks for {kb_source}")


if __name__ == "__main__":
    asyncio.run(seed_database())
