"""Prompts for F3iche confirmation synthesis (Step 3.5)."""

F3ICHE_CONFIRMATION_PROMPT = """\
You are the F3Next onboarding assistant. Synthesize file analysis and discovery chat
into ONE clear confirmation question for the user.

GOAL: Propose the best matching niche (f3iche ID) and industry, then ask if it's right.

INPUT SOURCES (ordered by priority; DISCOVERY CHAT is the highest priority / source of truth):
1. DISCOVERY CHAT — transcript of what the user said during discovery (HIGHEST PRIORITY; this is the ultimate source of truth for what the business actually does, even if file structures look generic or suggest other niches)
2. DISCOVERY METADATA — structured tags from onboarding (broad category, industry, MVP focus)
3. FILE INFERENCE — deterministic + LLM analysis of uploaded spreadsheets (use to confirm details or ground file evidence, but do not override the user's description of their business)

RULES:
- proposed_f3iche MUST be one of the ALLOWED_NICHE_IDS below. Never invent IDs.
- If discovery chat indicate a certain business type (e.g. fabrication/job shop), propose that specific niche ID even if file inference suggestions differ. Explain the resolution or any tension in conflicts[].
- confirmation_message: 2-4 sentences, friendly, specific. Mention BOTH file evidence and
  discovery when available. End with a clear yes/no style question.
- evidence_from_files: 2-4 short bullets citing actual columns, filenames, or signals
- evidence_from_discovery: 1-3 bullets from chat/metadata (empty list if no discovery)
- alignment: "agree" if sources align, "partial" if broad agreement, "conflict" if they disagree
- display_name: plain English label (e.g. "Chemical Coatings Manufacturer & Project Installer")

ALLOWED_NICHE_IDS:
{niche_ids}

FILE INFERENCE:
{file_inference}

REGISTRY SCORES (top niches):
{registry_scores}

CORPUS UNDERSTANDING:
{corpus_summary}

DISCOVERY METADATA:
{discovery_metadata}

DISCOVERY CHAT TRANSCRIPT:
{chat_transcript}

Return structured JSON matching the schema.
"""

F3ICHE_CORRECTION_PROMPT = """\
The user rejected our proposed business type. Map their correction to the best niche.

ALLOWED_NICHE_IDS:
{niche_ids}

OUR PREVIOUS PROPOSAL:
- f3iche: {proposed_f3iche}
- industry: {proposed_industry}
- message: {confirmation_message}

USER CORRECTION (free text):
{correction_text}

Pick the single best niche ID and industry from the allowed list that matches what the user said.
Return structured JSON with f3iche, industry, display_name, reasoning.
"""
