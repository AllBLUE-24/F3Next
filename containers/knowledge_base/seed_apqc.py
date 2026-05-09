"""
containers/knowledge_base/seed_apqc.py

Seeds the APQC Process Classification Framework (PCF) v8.0 data into
the kb_embeddings table in Supabase, using Gemini embeddings.

This populates Layer 1 of the F3Next knowledge stack:
  Layer 1 — APQC PCF  (business process standards, ERP-agnostic)  ← THIS FILE
  Layer 2 — ERPNext Docs  (system-specific knowledge)
  Layer 3 — F3iche + CVS  (company-specific knowledge)

Usage:
  1. Place the APQC Excel file in containers/knowledge_base/ or set FILE_PATH below.
  2. Run from the F3Next project root:
       python -m containers.knowledge_base.seed_apqc
     OR from this directory:
       python seed_apqc.py

Columns expected in the "Combined" sheet of the APQC v8.0 Excel:
  PCF ID, Hierarchy ID, Element Description
  The "name" column may be called "Name" or "Process/Activity Name" —
  both are handled below.
"""

import asyncio
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# ── Path bootstrap so 'shared' and 'llm_router' imports resolve ───────────────
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_ROOT))

load_dotenv()

from shared.database.db import AsyncSessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402
from shared.embedding_generator import generate_embedding  # noqa: E402

# ── Config ────────────────────────────────────────────────────────────────────

# Accepts absolute path OR a filename relative to this script's directory.
_DEFAULT_FILENAME = (
    "K016808_APQC Process Classification Framework (PCF)"
    " - Cross-Industry - Excel Version 8.0.xlsx"
)
FILE_PATH = Path(os.getenv("APQC_FILE_PATH", _HERE / _DEFAULT_FILENAME))

SHEET_NAME = "Combined"
KB_SOURCE  = "apqc_pcf"

# APQC PCF v8.0 column name variants (handle both naming conventions)
_NAME_COLS   = ["Name", "Process/Activity Name", "Process Name"]
_DESC_COLS   = ["Element Description", "Description"]
_ID_COLS     = ["PCF ID", "ID"]
_HIER_COLS   = ["Hierarchy ID", "Hierarchy"]

RATE_LIMIT_DELAY = 0.5   # seconds between embeds


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_col(df: pd.DataFrame, candidates: list[str]) -> str:
    """Return the first column name from `candidates` that exists in df."""
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(
        f"None of {candidates} found in sheet columns: {list(df.columns)}"
    )


def _safe_pcf_id(val) -> str:
    """Convert a PCF ID cell (may be float like 4001.0) to a clean string."""
    try:
        return str(int(float(val)))
    except (ValueError, TypeError):
        return str(val).strip()


# ── Step 1: Parse & Chunk ─────────────────────────────────────────────────────

def build_chunks() -> list[dict]:
    """
    Parse the APQC Excel and return a list of semantic chunks ready for embedding.

    Skips Level 1 (categories) and Level 2 (process groups) — they are too broad.
    Embeds Level 3 (Processes) and Level 4+ (Activities / Tasks).

    Each chunk:
      {
        "text":      str,   # rich text sent to the embedding model
        "kb_source": str,   # "apqc_pcf"
        "pcf_id":    str,   # e.g. "10045"
      }
    """
    print(f"📂 Loading: {FILE_PATH}")
    if not FILE_PATH.exists():
        raise FileNotFoundError(
            f"APQC Excel not found at: {FILE_PATH}\n"
            "Set the APQC_FILE_PATH env var or place the file in "
            "containers/knowledge_base/"
        )

    df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME, engine="openpyxl")
    print(f"   Loaded {len(df)} rows from sheet '{SHEET_NAME}'.")

    # Resolve actual column names
    name_col = _find_col(df, _NAME_COLS)
    desc_col = _find_col(df, _DESC_COLS)
    id_col   = _find_col(df, _ID_COLS)
    hier_col = _find_col(df, _HIER_COLS)

    # Drop rows with no ID or no description
    df = df.dropna(subset=[id_col, desc_col])
    df = df[df[desc_col].astype(str).str.strip() != ""]

    current_category  = ""
    current_group     = ""
    chunks: list[dict] = []

    print("🔪 Chunking...")
    for _, row in df.iterrows():
        hierarchy_id = str(row[hier_col]).strip()
        level        = len(hierarchy_id.split("."))
        name         = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""

        # Track breadcrumb context — do NOT embed these levels
        if level == 1:
            current_category = name
            continue
        if level == 2:
            current_group = name
            continue

        # Level 3+ → embed
        description = str(row[desc_col]).strip()
        pcf_id      = _safe_pcf_id(row[id_col])

        rich_text = (
            "[APQC Business Process Standard]\n"
            f"Category: {current_category}\n"
            f"Process Group: {current_group}\n"
            f"Process ID: {hierarchy_id} (PCF ID: {pcf_id})\n"
            f"Name: {name}\n\n"
            f"Description: {description}"
        )

        chunks.append({
            "text":      rich_text,
            "kb_source": f"{KB_SOURCE}",  # filter-friendly: "apqc_pcf"
            "pcf_id":    pcf_id,
        })

    print(f"✅ Generated {len(chunks)} semantic chunks.")
    return chunks


# ── Step 2: Embed ─────────────────────────────────────────────────────────────




async def seed_database(chunks: list[dict], reset: bool = False) -> None:
    """Embed each chunk and upsert into kb_embeddings."""
    total = len(chunks)

    async with AsyncSessionLocal() as session:
        if reset:
            # Wipe existing APQC data
            print(f"\n🧹 Clearing existing '{KB_SOURCE}' rows from kb_embeddings...")
            await session.execute(
                text("DELETE FROM kb_embeddings WHERE kb_source LIKE :pfx"),
                {"pfx": f"{KB_SOURCE}%"},
            )
            await session.commit()
            print("   Cleared.")
            existing_pcf_ids = set()
        else:
            # Fetch existing to resume
            print(f"\n🔍 Checking database to resume progress...")
            res = await session.execute(
                text("SELECT content FROM kb_embeddings WHERE kb_source LIKE :pfx"),
                {"pfx": f"{KB_SOURCE}%"},
            )
            existing_pcf_ids = set()
            import re
            for row in res:
                content = row[0]
                # Extract PCF ID from content string: "(PCF ID: 12345)"
                match = re.search(r'\(PCF ID: (\d+)\)', content)
                if match:
                    existing_pcf_ids.add(match.group(1))
            print(f"   Found {len(existing_pcf_ids)} chunks already in the DB. Skipping them.")

        print(f"🚀 Embedding & inserting {total} chunks...\n")
        skipped = 0
        inserted = 0

        for idx, chunk in enumerate(chunks, 1):
            if chunk["pcf_id"] in existing_pcf_ids:
                skipped += 1
                continue

            label = chunk["text"].split("\n")[4][:60]  # "Name: ..." line
            print(f"[{idx}/{total}] {label}")

            vector = await generate_embedding(chunk["text"])
            vector_str = "[" + ",".join(map(str, vector)) + "]"

            await session.execute(
                text("""
                    INSERT INTO kb_embeddings (kb_source, content, embedding)
                    VALUES (:source, :content, CAST(:vector AS vector))
                """),
                {
                    "source":  chunk["kb_source"],
                    "content": chunk["text"],
                    "vector":  vector_str,
                },
            )

            inserted += 1

            # Commit in batches of 50 to avoid long transactions
            if inserted % 50 == 0:
                await session.commit()
                print(f"   💾 Committed {inserted} new chunks...")

            import asyncio as _asyncio
            await _asyncio.sleep(RATE_LIMIT_DELAY)

        await session.commit()

    print(f"\n🎉 Done! {inserted} NEW chunks embedded. (Skipped {skipped} already in DB).")


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed APQC PCF into kb_embeddings")
    parser.add_argument("--dry-run", action="store_true", help="Parse and print sample, no DB writes")
    parser.add_argument("--reset", action="store_true", help="Delete all existing APQC data before seeding")
    args = parser.parse_args()

    chunks = build_chunks()

    print("\n--- SAMPLE CHUNK (first) ---")
    print(chunks[0]["text"])
    print(f"\nkb_source : {chunks[0]['kb_source']}")
    print(f"pcf_id    : {chunks[0]['pcf_id']}")

    if args.dry_run:
        print("\n[DRY RUN] Skipping embedding & DB insertion. Pass no flag to seed for real.")
        sys.exit(0)

    asyncio.run(seed_database(chunks, reset=args.reset))