"""Transcript extraction — structured coverage (no hashtag tags)."""

TRANSCRIPT_EXTRACTION_PROMPT = """
You are analyzing a completed ERP discovery conversation between Adi (consultant) and a client.

FULL TRANSCRIPT:
{transcript}

Extract everything the client actually said. Use null for anything never mentioned.
Use natural language in coverage values — do NOT emit hashtag taxonomy tags.

Return ONLY valid JSON:
{{
  "coverage": {{
    "industry":      {{"status": "confirmed"|"partial"|null, "value": "string or null"}},
    "strategy":      {{"status": "confirmed"|"partial"|null, "value": "string or null"}},
    "scale":         {{"status": "confirmed"|"partial"|null, "value": "string or null"}},
    "legacy_system": {{"status": "confirmed"|"partial"|null, "value": "string or null"}},
    "pain_point":    {{"status": "confirmed"|"partial"|null, "value": "string or null"}}
  }},
  "f3iche_hint": "trading|manufacturing|service|null",
  "industry_hint": "string or null"
}}
"""
