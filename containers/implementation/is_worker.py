"""
containers/is/is_worker.py

Temporal worker for the Implementation System (IS).
Registers all IS workflows and activities, then polls the is-queue.

Run with:
    python -m containers.implementation.is_worker
or via Docker:
    CMD ["python", "-m", "containers.implementation.is_worker"]
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
from dotenv import load_dotenv
load_dotenv()


from temporalio.client import Client
from temporalio.worker import Worker

from containers.implementation.is_workflow.workflow import ImplementationWorkflow, TASK_QUEUE
from containers.implementation.signals_agent.activities    import infer_f3iche, verify_f3iche
from containers.implementation.profile_agent.activities    import build_company_profile, merge_company_profile
from containers.implementation.target_agent.activities     import build_target_structure
from containers.implementation.mapping_agent.activities    import map_file_to_erpnext, infer_doctype_from_columns
from containers.implementation.validation_agent.activities import validate_mapped_data
from containers.implementation.import_agent.activities     import build_import_plan, execute_import_phase
from containers.implementation.virus_scan_agent.activities import virus_scan_quarantine
from containers.implementation.file_io.fetch_clean_files   import fetch_clean_files
from containers.implementation.file_io.persist_profile     import persist_profile
from containers.implementation.file_io.persist_session     import persist_session
from containers.implementation.file_io.persist_mapping     import persist_mapping
from containers.implementation.file_io.persist_import_run  import persist_import_run

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    host = os.getenv("TEMPORAL_HOST")
    client = await Client.connect(host)
    logger.info("IS worker connected to Temporal at %s", host)

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
        worker = Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[
                ImplementationWorkflow,
            ],
            activities=[
                        # signals_agent
                        infer_f3iche,
                        verify_f3iche,
                        # profile_agent
                        build_company_profile,
                        merge_company_profile,
                        # target_agent
                        build_target_structure,
                        # mapping_agent
                        map_file_to_erpnext,
                        infer_doctype_from_columns,
                        # validation_agent
                        validate_mapped_data,
                        # import_agent
                        build_import_plan,
                        execute_import_phase,
                        # virus_scan_agent
                        virus_scan_quarantine,
                        # file_io
                        fetch_clean_files,
                        persist_profile,
                        persist_session,
                        persist_mapping,
                        persist_import_run,
                       ],
            activity_executor=activity_executor,
        )
    
        logger.info("IS worker polling queue: %s", TASK_QUEUE)
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())