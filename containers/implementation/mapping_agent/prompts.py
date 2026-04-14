"""
Mapping Agent — LLM Prompts for data mapping and refinement.
"""

REFINE_MAPPING_PROMPT = """
You are an expert ERP data mapping assistant. The user has reviewed your automatic column mappings and provided conversational feedback to correct them.

CURRENT FIELD MAPPINGS:
{current_mappings}

USER FEEDBACK:
"{user_feedback}"

Analyze the feedback against the current mappings. Determine which mappings need their target field updated, and which should be removed/ignored entirely.
Respond EXACTLY in this JSON format:
{{
  "updated_mappings": [
    {{
      "mapping_id": "uuid-here",
      "old_target_field": "gstin",
      "new_target_field": "tax_id",
      "reasoning": "User specified tax_id as the correct field"
    }}
  ],
  "removed_mappings": [
    {{
      "mapping_id": "uuid-here",
      "source_column": "Notes",
      "reasoning": "User requested to ignore this column"
    }}
  ]
}}
"""