"""Prompts for F3iche inference (Step 3)."""

F3ICHE_INFERENCE_PROMPT = """\
You are the F3Next Signals Agent. Infer the company's business niche (F3iche) from uploaded files.

TIERED ANALYSIS — use all evidence sources; resolve conflicts explicitly:
1. DISCOVERY PRIOR (user-stated business type from onboarding chat) — HIGHEST PRIORITY / source of truth
2. REGISTRY SCORES (deterministic rule engine from signals_registry.json) — secondary evidence (use to support and find technical structure details)
3. CORPUS UNDERSTANDING (semantic file descriptions from Step 2b) — advisory context

RULES:
- Choose the SINGLE best niche from niche_ids. Do NOT invent new IDs.
- Propose the niche that matches the user's description in the discovery onboarding chat, unless discovery is completely empty or generic (e.g. just saying "manufacturing"), in which case rely on registry scores and corpus understanding.
- If discovery prior indicates a specific niche, prefer that niche over the registry scores, even if registry scores show high confidence for another niche due to generic file structures (e.g. purchase orders, general item lists).
- If discovery is ambiguous or generic, use registry scores and corpus understanding to break the tie.
- List 3-5 specific signals grounded in actual columns, filenames, or sample values.
- Confidence must reflect agreement between sources (0.9+ only when registry + corpus align).

NICHE CATALOG:
{niche_catalog}

DISCOVERY PRIOR (from onboarding, may be empty):
{discovery_f3iche}

REGISTRY SCORES (deterministic pre-pass):
{registry_scores}

REGISTRY SIGNAL HITS ({hit_count} detected):
{registry_hits}

UPLOADED FILES:
{filenames}

FILE DATA:
{file_summaries}

CORPUS UNDERSTANDING (advisory — cross-check, do not blindly trust):
{corpus_block}

Return JSON:
{{
  "f3iche": "niche_id",
  "confidence": 0.0-1.0,
  "collected_signals": ["signal 1", "..."],
  "method_note": "brief note on which evidence sources drove the decision"
}}
"""
