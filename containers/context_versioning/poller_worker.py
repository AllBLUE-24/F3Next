"""
CVS scheduled poller — safety net when webhooks are missed.

Every 30 minutes (configurable), starts a full-layer CVS sync for projects whose latest snapshot
is older than 20 minutes (or missing) while deployment credentials exist.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(message)s")
logger = logging.getLogger("cvs_poller")

POLL_INTERVAL_SEC = int(os.getenv("CVS_POLL_INTERVAL_SEC", "1800"))
STALE_MINUTES = int(os.getenv("CVS_POLL_STALE_MINUTES", "20"))


async def _stale_projects():
    from sqlalchemy import func, select

    from shared.database.db import AsyncSessionLocal
    from shared.models.core import Project
    from shared.models.cvs_models import ContextSnapshot

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STALE_MINUTES)
    stale: list[tuple[str, str]] = []

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Project).where(Project.deployment_details.isnot(None)))
        projects = res.scalars().all()

    for p in projects:
        dep = p.deployment_details or {}
        if not dep.get("api_key"):
            continue
        async with AsyncSessionLocal() as session:
            r2 = await session.execute(
                select(func.max(ContextSnapshot.created_at)).where(ContextSnapshot.project_id == p.id)
            )
            mx = r2.scalar()
        if mx is None or mx < cutoff:
            stale.append((str(p.id), p.company_slug or str(p.id)))

    return stale


async def poll_once() -> int:
    from temporalio.client import Client
    from temporalio.common import WorkflowIDReusePolicy

    from containers.context_versioning.cvs_workflow.workflow import CVSUpdateInput, CVSUpdateWorkflow
    from shared.cvs_profile import load_cvs_company_profile

    host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    client = await Client.connect(host)
    started = 0

    for project_id, _slug_hint in await _stale_projects():
        try:
            company_slug, company_profile = await load_cvs_company_profile(project_id)
        except Exception as e:
            logger.warning("Poller: skip project=%s (%s)", project_id, e)
            continue

        inp = CVSUpdateInput(
            project_id=project_id,
            company_slug=company_slug,
            company_profile=company_profile,
            trigger_event="scheduled",
            layers=["master_data", "transaction_intel"],
            trigger_doctype=None,
            doc_name=None,
            event_payload={"reason": "stale_poll", "ts": time.time()},
        )
        wf_id = f"cvs-poll-{project_id}-{int(time.time())}"
        try:
            await client.start_workflow(
                CVSUpdateWorkflow.run,
                inp,
                id=wf_id,
                task_queue="cvs-main-queue",
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
            )
            started += 1
            logger.info("Poller: started %s for project=%s", wf_id, project_id)
        except Exception as e:
            logger.error("Poller: failed project=%s: %s", project_id, e)

    return started


async def main_loop() -> None:
    logger.info("CVS poller started — interval=%ss stale>%sm", POLL_INTERVAL_SEC, STALE_MINUTES)
    while True:
        try:
            n = await poll_once()
            logger.info("CVS poller cycle complete — workflows_started=%d", n)
        except Exception as e:
            logger.exception("CVS poller cycle error: %s", e)
        await asyncio.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    asyncio.run(main_loop())
