"""
containers/knowledge_base/seed_erpnext_docs.py

Scrapes ERPNext documentation from docs.erpnext.com, chunks it
semantically by heading, and embeds each chunk into kb_embeddings.

This populates Layer 2 of the F3Next knowledge stack:
  Layer 1 — APQC PCF        (business process standards, ERP-agnostic)
  Layer 2 — ERPNext Docs    (system-specific knowledge)      ← THIS FILE
  Layer 3 — F3iche + CVS    (company-specific knowledge)

Usage:
  # Dry-run (scrape + chunk only, no DB write):
  python -m containers.knowledge_base.seed_erpnext_docs --dry-run

  # Seed priority modules only (fastest, covers most use-cases):
  python -m containers.knowledge_base.seed_erpnext_docs --priority-only

  # Full seed (all modules, ~1000+ pages — takes hours):
  python -m containers.knowledge_base.seed_erpnext_docs
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ── Path bootstrap ─────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_ROOT))

load_dotenv()

from llm_router import api_keys, key_pool       # noqa: E402
from shared.database.db import AsyncSessionLocal # noqa: E402
from sqlalchemy import text                      # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

SITEMAP_URL      = "https://docs.frappe.io/sitemap.xml"
DOCS_BASE        = "https://docs.frappe.io"
KB_SOURCE        = "erpnext_docs"

EMBEDDING_MODEL  = "models/gemini-embedding-001"
EMBED_URL_TPL    = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"{EMBEDDING_MODEL}:embedContent?key={{key}}"
)

RATE_LIMIT_DELAY = 2          # seconds between embeds (60 RPM limit)
PAGE_FETCH_DELAY = 0.5        # seconds between page fetches (polite crawling)
REQUEST_TIMEOUT  = 15         # seconds per HTTP request
COMMIT_BATCH     = 50         # commit to DB every N chunks

# Modules to prioritize — covers 90% of ERP operations
PRIORITY_MODULES = {
    "selling", "buying", "stock", "accounts", "manufacturing",
    "crm", "hr", "human-resources", "projects", "assets",
    "purchase", "payment",
}

# URL path segments to SKIP — reduce noise, save tokens
SKIP_SEGMENTS = {
    "v11", "v12", "v13", "v14",  # skip legacy versions (we focus on current)
    "healthcare",   # vertical-specific, rarely needed
    "education",    # vertical-specific
    "nonprofit",    # vertical-specific
    "non_profit",   # vertical-specific
    "restaurant",   # vertical-specific
    "agriculture",  # vertical-specific
}

# HTML selectors to extract content (try in order until one yields text)
CONTENT_SELECTORS = [
    "article",
    "main",
    ".doc-content",
    ".page-content",
    "#main-content",
    "body",
]

# ── Step 1: Parse Sitemap ──────────────────────────────────────────────────────

def fetch_sitemap_urls(priority_only: bool = False) -> list[str]:
    """
    Parse the sitemap and return filtered doc URLs.
    - Always excludes legacy v13 and vertical-specific modules.
    - If priority_only=True, only returns URLs from PRIORITY_MODULES.
    """
    logger.info("Fetching sitemap from %s ...", SITEMAP_URL)
    resp = requests.get(SITEMAP_URL, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "xml")
    all_urls = [loc.get_text(strip=True) for loc in soup.find_all("loc")]
    logger.info("Sitemap has %d total URLs", len(all_urls))

    filtered = []
    for url in all_urls:
        path = urlparse(url).path.lower()
        segments = path.strip("/").split("/")
        segments_set = set(segments)

        # Skip vertical-specific domains
        if segments_set & SKIP_SEGMENTS:
            continue

        # Skip weird duplicate paths in the sitemap
        if "erpnext.erpnext.com" in path:
            continue

        # Must be an ERPNext document
        if "/erpnext/" not in path:
            continue

        # Priority filter: check if any segment in the URL path matches a priority module
        if priority_only:
            if not (segments_set & PRIORITY_MODULES):
                continue

        filtered.append(url)

    logger.info("After filtering: %d URLs to scrape", len(filtered))
    return filtered


# ── Step 2: Scrape a Single Page ──────────────────────────────────────────────

def _extract_module_from_url(url: str) -> str:
    """Derive the ERPNext module name from the URL path."""
    parts = urlparse(url).path.strip("/").split("/")
    # e.g. /docs/user/manual/en/selling/sales-order → "selling"
    try:
        en_idx = parts.index("en")
        return parts[en_idx + 1] if en_idx + 1 < len(parts) else "general"
    except ValueError:
        # e.g. /erpnext/sales-order → last path before final segment
        return parts[-2] if len(parts) >= 2 else "general"


def _html_to_clean_text(soup: BeautifulSoup) -> str:
    """Strip navigation, headers, footers, scripts, styles from HTML soup."""
    for tag in soup.find_all(["nav", "header", "footer", "script",
                               "style", "aside", ".sidebar", ".toc"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def scrape_page(url: str) -> Optional[dict]:
    """
    Fetch and parse a single doc page.
    Returns { title, module, url, text } or None on failure.
    """
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={
            "User-Agent": "F3Next-KnowledgeSeeder/1.0 (internal; contact@f3next.in)"
        })
        if resp.status_code == 404:
            return None
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract title
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-1]

        # Extract main content
        content_el = None
        for selector in CONTENT_SELECTORS:
            content_el = soup.select_one(selector)
            if content_el:
                break

        if not content_el:
            content_el = soup

        text = _html_to_clean_text(content_el)

        # Minimum viable content length (skip empty/stub pages)
        if len(text.strip()) < 200:
            return None

        return {
            "title":  title,
            "module": _extract_module_from_url(url),
            "url":    url,
            "text":   text,
        }

    except requests.RequestException as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


# ── Step 3: Semantic Chunking ──────────────────────────────────────────────────

def _chunk_by_headings(text: str, max_chars: int = 1200) -> list[str]:
    """
    Split text at heading boundaries (##, ###, lines ending in :).
    Each chunk is limited to max_chars to stay within embedding limits.
    Overlapping windows are NOT used — heading boundaries are more natural
    for ERP docs where each section covers one concept.
    """
    # Split at Markdown-style headings OR lines that look like section headers
    heading_pattern = re.compile(r'\n(?=#{1,4} |\n[A-Z][^\n]{5,60}\n[-=]+)', re.MULTILINE)
    raw_sections = heading_pattern.split(text)

    chunks = []
    current = ""
    for section in raw_sections:
        section = section.strip()
        if not section:
            continue
        if len(current) + len(section) < max_chars:
            current += "\n\n" + section
        else:
            if current.strip():
                chunks.append(current.strip())
            # If a single section exceeds max_chars, split it further by sentences
            if len(section) > max_chars:
                sentences = re.split(r'(?<=[.!?])\s+', section)
                sub = ""
                for sent in sentences:
                    if len(sub) + len(sent) < max_chars:
                        sub += " " + sent
                    else:
                        if sub.strip():
                            chunks.append(sub.strip())
                        sub = sent
                if sub.strip():
                    chunks.append(sub.strip())
                current = ""
            else:
                current = section

    if current.strip():
        chunks.append(current.strip())

    return chunks


def build_chunks_from_page(page: dict) -> list[dict]:
    """
    Convert a scraped page into a list of embedding-ready chunks.

    Each chunk:
      {
        "text":      str,   # rich text sent to Gemini embedding API
        "kb_source": str,   # "erpnext_docs"
        "url":       str,   # source URL for provenance
        "module":    str,   # ERPNext module name
      }
    """
    raw_chunks = _chunk_by_headings(page["text"])
    result = []

    for i, chunk_text in enumerate(raw_chunks):
        # Prepend rich metadata header to every chunk — this is what gets embedded
        # The metadata makes similarity search far more accurate
        rich_text = (
            f"[ERPNext Documentation]\n"
            f"Module: {page['module'].replace('-', ' ').title()}\n"
            f"Page: {page['title']}\n"
            f"URL: {page['url']}\n\n"
            f"{chunk_text}"
        )
        result.append({
            "text":      rich_text,
            "kb_source": KB_SOURCE,
            "url":       page["url"],
            "module":    page["module"],
        })

    return result


# ── Step 4: Embed ──────────────────────────────────────────────────────────────

def _embed(text: str) -> list[float]:
    """Call Gemini embedding API with automatic key rotation."""
    if not api_keys:
        raise RuntimeError("No Gemini API keys found. Check GEMINI_API_KEYS env var.")

    max_attempts = len(api_keys) + 1
    for attempt in range(max_attempts):
        key = next(key_pool)
        try:
            resp = requests.post(
                EMBED_URL_TPL.format(key=key),
                headers={"Content-Type": "application/json"},
                json={
                    "model":   EMBEDDING_MODEL,
                    "content": {"parts": [{"text": text}]},
                },
                timeout=30,
            )
            data = resp.json()
            if "error" in data:
                msg = data["error"].get("message", "").lower()
                if any(tok in msg for tok in ("429", "quota", "exhausted", "denied", "403", "permission", "invalid")):
                    logger.warning("API issue (quota or invalid key) — rotating key (attempt %d)", attempt + 1)
                    time.sleep(5)
                    continue
                raise RuntimeError(f"Gemini embed error: {data['error']}")
            return data["embedding"]["values"]
        except RuntimeError:
            raise
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            logger.warning("Embed attempt %d failed: %s — retrying", attempt + 1, e)

    raise RuntimeError("All Gemini API keys exhausted.")


# ── Step 5: Insert ─────────────────────────────────────────────────────────────

async def seed_database(all_chunks: list[dict], resume: bool = False) -> None:
    """Embed each chunk and insert into kb_embeddings."""
    total = len(all_chunks)

    async with AsyncSessionLocal() as session:
        if not resume:
            logger.info("Clearing existing '%s' rows ...", KB_SOURCE)
            await session.execute(
                text("DELETE FROM kb_embeddings WHERE kb_source LIKE :pfx"),
                {"pfx": f"{KB_SOURCE}%"},
            )
            await session.commit()
            existing_texts = set()
            logger.info("Cleared. Starting embedding of %d chunks...", total)
        else:
            logger.info("Resume mode active. Fetching existing chunks to prevent duplicates...")
            result = await session.execute(
                text("SELECT content FROM kb_embeddings WHERE kb_source = :src"),
                {"src": KB_SOURCE}
            )
            existing_texts = {row[0] for row in result}
            logger.info("Found %d existing chunks in DB. Resuming...", len(existing_texts))

        for idx, chunk in enumerate(all_chunks, 1):
            page_label = chunk["url"].split("/")[-1]
            
            # Skip if already in the database
            if chunk["text"] in existing_texts:
                logger.info("[%d/%d] Skipping (Already Embedded): %s", idx, total, page_label)
                continue

            logger.info("[%d/%d] Embedding: %s — %s", idx, total, chunk["module"], page_label)

            vector      = _embed(chunk["text"])
            vector_str  = "[" + ",".join(map(str, vector)) + "]"

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

            if idx % COMMIT_BATCH == 0:
                await session.commit()
                logger.info("  💾 Committed %d/%d", idx, total)

            await asyncio.sleep(RATE_LIMIT_DELAY)

        await session.commit()

    logger.info("🎉 Done! ERPNext doc chunks embedded and saved.")

# ── Orchestrator ───────────────────────────────────────────────────────────────

async def run(priority_only: bool = False, dry_run: bool = False, resume: bool = False) -> None:
    urls = fetch_sitemap_urls(priority_only=priority_only)

    # --- NEW FAST-RESUME LOGIC ---
    if resume and not dry_run:
        logger.info("🔍 Fast-Resume: Checking DB for already processed URLs to skip scraping...")
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                text("SELECT content FROM kb_embeddings WHERE kb_source = :src"),
                {"src": KB_SOURCE}
            )
            existing_urls = set()
            import re
            for row in res:
                # Extract the URL from the rich text chunk header
                match = re.search(r'URL:\s+(https?://[^\n]+)', row[0])
                if match:
                    existing_urls.add(match.group(1).strip())
        
        # Filter the URLs list to only those we haven't seen
        original_count = len(urls)
        urls = [u for u in urls if u not in existing_urls]
        logger.info("✅ Fast-Resume: Found %d URLs already embedded. Only %d left to scrape!", 
                    original_count - len(urls), len(urls))
    # -----------------------------

    all_chunks: list[dict] = []
    skipped = 0

    for i, url in enumerate(urls, 1):
        logger.info("[%d/%d] Scraping: %s", i, len(urls), url)
        page = scrape_page(url)
        time.sleep(PAGE_FETCH_DELAY)

        if not page:
            skipped += 1
            continue

        chunks = build_chunks_from_page(page)
        all_chunks.extend(chunks)
        logger.info("  → %d chunks (total so far: %d)", len(chunks), len(all_chunks))

    logger.info("Scraping complete. Pages: %d scraped, %d skipped. Total chunks: %d",
                len(urls) - skipped, skipped, len(all_chunks))

    if not all_chunks:
        logger.warning("No new chunks generated (everything might already be embedded).")
        return

    # Print sample chunk
    logger.info("\n--- SAMPLE CHUNK ---\n%s\n---", all_chunks[0]["text"][:600])

    if dry_run:
        logger.info("[DRY RUN] Skipping DB insertion. %d chunks ready.", len(all_chunks))
        return

    await seed_database(all_chunks, resume=resume)


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed ERPNext docs into kb_embeddings")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Scrape and chunk only — do not embed or write to DB"
    )
    parser.add_argument(
        "--priority-only", action="store_true",
        help="Only scrape priority modules (Selling, Buying, Stock, Accounts, etc.)"
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip deletion and only embed chunks that are not already in the database"
    )
    args = parser.parse_args()

    asyncio.run(run(
        priority_only=args.priority_only, 
        dry_run=args.dry_run, 
        resume=args.resume
    ))