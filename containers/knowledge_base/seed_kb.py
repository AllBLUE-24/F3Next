import asyncio
import os
import sys
import requests
from dotenv import load_dotenv

# Add project root to sys.path so 'shared' and 'llm_router' imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.database.db import AsyncSessionLocal
from sqlalchemy import text

# Import your custom API key switcher logic!
from llm_router import api_keys, key_pool

# Import the data from the new files
from containers.knowledge_base.manufacturing_kb_chunks import ALL_MANUFACTURING_CHUNKS
from containers.knowledge_base.trading_kb_chunks import ALL_TRADING_CHUNKS

load_dotenv()

def prepare_documents():
    """Flattens the nested structures into a single list of formatted strings."""
    documents = []
    master_list = ALL_MANUFACTURING_CHUNKS + ALL_TRADING_CHUNKS
    
    for category in master_list:
        industry = category["industry"]
        kb_type = category["kb_type"].replace("_", " ").title()
        
        for chunk in category["chunks"]:
            # Format the text so the embedding captures all the rich metadata!
            tags = ", ".join(chunk["tags"])
            formatted_text = (
                f"Industry: {industry}\n"
                f"Category: {kb_type}\n"
                f"Title: {chunk['title']}\n"
                f"Tags: {tags}\n\n"
                f"{chunk['content']}"
            )
            
            documents.append({
                "source": industry,
                "content": formatted_text
            })
            
    return documents

async def seed_database():
    if not api_keys:
        print("❌ ERROR: No API keys found in GEMINI_API_KEYS.")
        return

    docs = prepare_documents()
    total_docs = len(docs)
    print(f"📦 Loaded {total_docs} high-quality chunks from files.")

    async with AsyncSessionLocal() as session:
        # 1. WIPE OLD TEST DATA FIRST
        print("🧹 Clearing old test data from kb_embeddings...")
        await session.execute(text("DELETE FROM kb_embeddings"))
        await session.commit()
        print("✅ Old data cleared.")

        # 2. SLOW DRIP THE NEW EMBEDDINGS
        print(f"🚀 Starting embedding process for {total_docs} chunks. (Going slow to respect API limits...)")
        
        for index, doc in enumerate(docs):
            chunk_content = doc["content"]
            source = doc["source"]
            
            print(f"[{index + 1}/{total_docs}] Embedding: {doc['source']} - {chunk_content.split('Title: ')[1].split('Tags:')[0].strip()}...")

            max_attempts = len(api_keys) + 1
            success = False

            for attempt in range(max_attempts):
                current_key = next(key_pool)
                
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={current_key}"
                    headers = {'Content-Type': 'application/json'}
                    payload = {
                        "model": "models/gemini-embedding-001",
                        "content": {
                            "parts": [{"text": chunk_content}]
                        }
                    }

                    # Use loop.run_in_executor if you want to make requests non-blocking, 
                    # but for a simple seed script, sync requests is fine.
                    response = requests.post(url, headers=headers, json=payload)
                    response_data = response.json()

                    # Handle Quota / 429 Errors
                    if "error" in response_data:
                        error_msg = response_data["error"].get("message", "").lower()
                        if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
                            print(f"   [Warning] Quota hit. Rotating to next Gemini key...")
                            await asyncio.sleep(5) # Back off if we hit a limit
                            continue
                        else:
                            raise Exception(f"Gemini API Error: {response_data['error']}")

                    # Extract vector and insert
                    vector = response_data['embedding']['values']
                    vector_str = "[" + ",".join(map(str, vector)) + "]"
                    
                    stmt = text("""
                        INSERT INTO kb_embeddings (kb_source, content, embedding)
                        VALUES (:source, :content, CAST(:vector AS vector))
                    """)
                    await session.execute(stmt, {
                        "source": source,
                        "content": chunk_content,
                        "vector": vector_str
                    })
                    
                    success = True
                    break # Success! Break retry loop.
                    
                except Exception as e:
                    print(f"❌ Failed. Error: {e}")
                    if attempt == max_attempts - 1:
                        raise e
            
            if not success:
                raise Exception("Critical: All API keys failed or rate limit completely blocked us!")
            
            # MANDATORY DELAY to avoid hitting the 60 Requests Per Minute limit
            await asyncio.sleep(2) 
        
        # 3. COMMIT ALL TO DATABASE
        await session.commit()
        print(f"🎉 SUCCESS! All {total_docs} chunks successfully embedded and saved to Supabase.")

if __name__ == "__main__":
    asyncio.run(seed_database())