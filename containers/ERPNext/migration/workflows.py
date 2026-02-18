from datetime import timedelta
from temporalio import workflow
from typing import Dict, Any

# Import activity definitions
with workflow.unsafe.imports_passed_through():
    from .activities import (
        download_and_extract_schema,
        generate_mapping_proposal,
        transform_and_upload,
        trigger_validation_agent
    )

@workflow.defn
class LegacyDataMigrationWorkflow:
    def __init__(self):
        self._mapping_confirmed = False
        self._final_mapping = {}
        # New: Store the AI proposal here so the UI can fetch it
        self._current_proposal = None 

    # --- NEW: QUERY METHOD ---
    # The Frontend calls this to see what the AI found
    @workflow.query
    def get_current_proposal(self) -> Dict[str, Any]:
        return self._current_proposal

    @workflow.signal
    def submit_mapping_correction(self, approved_mapping: dict):
        self._final_mapping = approved_mapping
        self._mapping_confirmed = True

    @workflow.run
    async def run(self, s3_file_key: str, company_slug: str):
        
        # 1. Ingest
        extraction_data = await workflow.execute_activity(
            download_and_extract_schema,
            s3_file_key,
            start_to_close_timeout=timedelta(minutes=2)
        )

        # 2. AI Analysis
        # We save the result to self._current_proposal
        self._current_proposal = await workflow.execute_activity(
            generate_mapping_proposal,
            args=[extraction_data, "Item"], 
            start_to_close_timeout=timedelta(minutes=2)
        )

        # 3. Wait for Human (Frontend Signal)
        await workflow.wait_condition(lambda: self._mapping_confirmed)

        # 4. Transform
        processed_file_key = await workflow.execute_activity(
            transform_and_upload,
            args=[s3_file_key, self._final_mapping, company_slug],
            start_to_close_timeout=timedelta(minutes=5)
        )

        # 5. Validation
        result = await workflow.execute_activity(
            trigger_validation_agent,
            processed_file_key,
            start_to_close_timeout=timedelta(minutes=1)
        )

        return result