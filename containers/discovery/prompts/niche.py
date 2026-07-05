"""LLM prompt for resolving discovery transcript to a concrete F3iche niche id."""

NICHE_RESOLUTION_PROMPT = """
You map a completed discovery conversation to exactly one F3iche business model template.

TRANSCRIPT:
{transcript}

COVERAGE SUMMARY:
{coverage_summary}

BROAD BUSINESS TYPE: {broad_f3iche}
INDUSTRY: {industry}

VALID F3ICHE NICHE IDs (you MUST pick exactly one from this list):
{niche_id_list}

Rules:
- Match how the business actually operates — not a single keyword.
- Custom furniture, countertops, quote-to-order, Instagram sales without a factory → do NOT pick manufacturing_project_chemical unless they run a chemical plant.
- Industrial epoxy/coatings with factory production and/or turnkey site projects → manufacturing_project_chemical.
- Pure distribution/trading → trading_* niches. Field service/facilities → service_* niches.

Return ONLY valid JSON, no markdown:
{{
  "f3iche_niche_id": "one id from the list above",
  "reasoning": "one sentence"
}}
"""
