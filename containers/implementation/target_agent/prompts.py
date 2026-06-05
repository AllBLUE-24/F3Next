TARGET_STRUCTURE_PROMPT = """
You are the F3Next ERPNext Architect. Your job is to take a messy company profile and provide authoritative reasoning notes for the graph-driven Target Structure.

COMPANY PROFILE:
{company_profile}

[Uploaded Corpus Summary]
{uploaded_corpus_summary}

[User Import Note]
{user_import_note}

[Company Context (Operational Notes)]
{company_context}

[Authoritative ERPNext Documentation]
Use the knowledge below to justify your phase assignments and identify any special setup requirements.
{erpnext_context}

[Industry Reality & F3iche Patterns]
{industry_context}

[APQC Process Framework Reference]
{apqc_context}

NOTE: setup_steps and import_phases are already built deterministically from erpnext_doctype_graph.json.
Do NOT return a new doctype list or reorder phases — only annotate reasoning.

YOUR INSTRUCTIONS:
1. Review the seed_doctypes and MVP boundary in the company profile. Confirm they match the uploaded corpus.
2. Flag any special setup the graph may not capture (custom fields, batch tracking, multi-currency, project links).
3. Provide concise reasoning citing ERPNext docs and APQC context.

Return EXACTLY this JSON structure:
{{
  "llm_reasoning": "Reasoning citing ERPNext docs and APQC references where applicable.",
  "special_setup_flags": ["optional flag 1", "optional flag 2"]
}}
"""

MVP_TRANSLATION_PROMPT = """
You are the F3Next ERPNext Technical Translator. Your job is to bridge the gap between business discovery and ERPNext system implementation.

The Discovery Agent has identified the client's primary bottleneck and provided a generic, ERP-agnostic list of Functional Requirements to solve it.

PRIMARY BOTTLENECK:
{primary_bottleneck}

FUNCTIONAL REQUIREMENTS:
{functional_requirements}

[CORPUS UNDERSTANDING — semantic file roles from upload]
{corpus_summary}

[FILE EVIDENCE — deterministic seed hints from corpus]
{file_evidence}

[ERPNext Context]
{erpnext_context}

YOUR INSTRUCTIONS:
Translate the generic Functional Requirements into the MINIMUM necessary ERPNext seed doctypes.
Prefer FILE EVIDENCE and CORPUS when they conflict with generic requirements.
Do NOT list prerequisite doctypes like Company, Fiscal Year, UOM, or Currency. The graph engine resolves prerequisites.
Only list 4-6 high-level seed doctypes (e.g., Item, Sales Order, Project, Purchase Order).
Do NOT include Work Order or BOM unless file evidence supports manufacturing batch data.

Return EXACTLY this JSON structure:
{{
  "seed_doctypes": ["Doctype1", "Doctype2", "Doctype3"],
  "reasoning": "Brief explanation"
}}
"""

MVP_BOTTLENECK_PROMPT = """
You are the F3Next ERPNext Technical Translator. Functional requirements were not provided, but we have discovery bottleneck + file corpus.

PRIMARY BOTTLENECK:
{primary_bottleneck}

[CORPUS UNDERSTANDING]
{corpus_summary}

[FILE EVIDENCE]
{file_evidence}

[F3ICHE CONFIRMED]
{f3iche}

[ERPNext Context]
{erpnext_context}

Translate into MINIMUM ERPNext seed doctypes (4-6). Use file evidence first.
No Company/UOM/Fiscal Year — graph adds prerequisites.
Defer Work Order/BOM unless files clearly show manufacturing/recipes.

Return EXACTLY this JSON:
{{
  "seed_doctypes": ["Doctype1", "Doctype2"],
  "reasoning": "Brief explanation"
}}
"""
