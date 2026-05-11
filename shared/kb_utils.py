import json
from typing import Dict, Any, Optional
from sqlalchemy import text
from shared.database.db import AsyncSessionLocal
from shared.embedding_generator import generate_embedding

async def seed_company_context(project_id: str, profile_dict: Dict[str, Any], note_text: Optional[str] = None) -> int:
    """
    Idempotent seeding of company context into pgvector.
    Always replaces the existing context chunks for the given project_id.
    """
    kb_source = f"company_{project_id}"
    
    # 1. Prepare chunks
    chunks = []
    
    # Chunk 1: note.txt (if provided)
    if note_text:
        note_chunk = (
            f"[Company Context] project_id: {project_id}\n"
            f"Source: user_note  version: raw\n\n"
            f"{note_text}"
        )
        chunks.append(note_chunk)
        
    # Chunk 2: Profile summary
    f3iche = profile_dict.get("f3iche", "Unknown")
    industry = profile_dict.get("industry", "Unknown")
    company_name = profile_dict.get("company_name", "Unknown")
    size = profile_dict.get("company_size", "Unknown")
    business_reality = profile_dict.get("business_reality", "No business reality available.")
    context_flags = ", ".join(profile_dict.get("context_flags", [])) or "None"
    
    profile_chunk = (
        f"[Company Context] project_id: {project_id}\n"
        f"Source: company_profile  version: {profile_dict.get('version', 1)}\n\n"
        f"Company: {company_name}. Industry: {industry}.\n"
        f"Business type (f3iche): {f3iche}. Size: {size}.\n"
        f"Business reality: {business_reality}\n"
        f"Context flags: {context_flags}"
    )
    chunks.append(profile_chunk)
    
    # Chunk 3: Operational context
    req_modules = ", ".join(profile_dict.get("required_modules") or []) or "Unknown"
    req_doctypes = ", ".join(profile_dict.get("required_doctypes") or []) or "Unknown"
    
    operational_chunk = (
        f"[Company Context] project_id: {project_id}\n"
        f"Source: operational_context  version: {profile_dict.get('version', 1)}\n\n"
        f"Required ERPNext modules: {req_modules}.\n"
        f"Required doctypes: {req_doctypes}."
    )
    chunks.append(operational_chunk)
    
    # 2. Delete and insert
    async with AsyncSessionLocal() as session:
        # Delete old chunks
        await session.execute(
            text("DELETE FROM kb_embeddings WHERE kb_source = :src"),
            {"src": kb_source}
        )
        
        # Embed and insert new chunks
        for chunk in chunks:
            # generate_embedding returns a list of floats
            vec = await generate_embedding(chunk)
            
            await session.execute(
                text("INSERT INTO kb_embeddings (kb_source, content, embedding) VALUES (:src, :content, CAST(:vec AS vector))"),
                {"src": kb_source, "content": chunk, "vec": str(vec)}
            )
            
        await session.commit()
        
    return len(chunks)
