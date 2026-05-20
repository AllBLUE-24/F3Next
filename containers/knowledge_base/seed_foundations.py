"""
Script to seed the 'erp_implementation_playbook' collection in pgvector.
"""
import asyncio
import os
from pathlib import Path

from shared.database.db import AsyncSessionLocal
from shared.embedding_generator import generate_embedding
from sqlalchemy import text

async def seed_playbooks():
    print("Connecting to VectorStore...")
    
    playbook_dir = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "common" / "playbooks"
    
    if not playbook_dir.exists():
        print(f"Playbook directory not found: {playbook_dir}")
        return
        
    docs = []
    
    for md_file in playbook_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        
        # Determine f3iche applicability based on filename
        f3iche_tag = "universal"
        if "manufacturing" in md_file.name:
            f3iche_tag = "manufacturing"
        elif "trading" in md_file.name:
            f3iche_tag = "trading"
            
        doc_content = f"[Playbook: {f3iche_tag}]\n\n{content}"
        docs.append(doc_content)
        
    if docs:
        print(f"Adding {len(docs)} playbook narratives to pgvector...")
        kb_source = "erp_implementation_playbook"
        
        async with AsyncSessionLocal() as session:
            # Delete old chunks
            await session.execute(
                text("DELETE FROM kb_embeddings WHERE kb_source = :src"),
                {"src": kb_source}
            )
            
            # Embed and insert new chunks
            for chunk in docs:
                vec = await generate_embedding(chunk)
                await session.execute(
                    text("INSERT INTO kb_embeddings (kb_source, content, embedding) VALUES (:src, :content, CAST(:vec AS vector))"),
                    {"src": kb_source, "content": chunk, "vec": str(vec)}
                )
                
            await session.commit()
            
        print("Playbook seeding complete.")
    else:
        print("No playbook files found to seed.")

if __name__ == "__main__":
    asyncio.run(seed_playbooks())
