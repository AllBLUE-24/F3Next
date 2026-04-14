ALIGNMENT_PROMPT = """
You are the F3Next Alignment Agent. Your job is to compare what a user claimed during their discovery chat (DISCOVERY) with what our system detected from their actual uploaded files (SIGNALS).

DISCOVERY METADATA (From Chatbot):
{discovery_data}

SIGNALS METADATA (From Uploaded Files):
{signals_data}

Compare the two and provide:
1. alignment_score: A float between 0.0 and 1.0 indicating how well the files match the chatbot claims. (1.0 = perfect match).
2. mismatches: A list of strings noting any discrepancies (e.g., "User claimed Manufacturing, but files only show Trading data"). Leave empty if none.
3. recommended_f3iche: The final F3iche we should use. Give priority to SIGNALS if there is a strong mismatch, as files represent reality.
4. reasoning: A brief explanation of your alignment score and recommendation.

Return EXACTLY this JSON structure:
{{
  "alignment_score": 0.92,
  "mismatches": [],
  "recommended_f3iche": "trading",
  "reasoning": "Both Discovery and file analysis strongly indicate trading/distribution business."
}}
"""


PROFILE_ENRICHMENT_PROMPT = """
You are the F3Next Profile Enrichment Agent. Your job is to analyze a company's raw uploaded data and finalize their implementation profile.

CURRENT COMPANY PROFILE:
{current_profile}

RAW UPLOADED DATA SNIPPETS:
{data_snippets}

Analyze the data and provide:
1. data_quality_score: (0.0 to 1.0) How clean and structured is the data? (e.g., CSVs with headers = high; messy text = low).
2. completeness_score: (0.0 to 1.0) Based on the required modules for their industry, how much necessary data is missing?
3. data_observations: A list of 3-5 specific facts about their data (e.g., "Contains employee roles", "Missing customer GST numbers", "Dates are in MM/DD/YYYY format").
4. recommended_customizations: A list of 2-3 specific ERPNext configurations they will need based on this data (e.g., "Create custom fields for machinery assets", "Enable strict batch tracking").

Return EXACTLY this JSON structure:
{{
  "data_quality_score": 0.85,
  "completeness_score": 0.60,
  "data_observations": ["observation 1", "observation 2"],
  "recommended_customizations": ["customization 1", "customization 2"]
}}
"""