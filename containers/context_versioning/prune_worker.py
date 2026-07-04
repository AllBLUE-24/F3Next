"""
CVS retention worker — daily prune of historical snapshot rows in Supabase.

Full snapshot payloads remain in R2; Supabase keeps only the latest version
per (project_id, layer). Also deletes context_events older than retention window.

Runs daily by default (configurable via CVS_PRUNE_INTERVAL_SEC).
"""

from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(message)s")
logger = logging.getLogger("cvs_prune")

INTERVAL_SEC = int(os.getenv("CVS_PRUNE_INTERVAL_SEC", "86400"))
EVENTS_RETENTION_DAYS = int(os.getenv("CVS_EVENTS_RETENTION_DAYS", "30"))


async def main_loop() -> None:
    from containers.context_versioning.context_store.activities import prune_old_snapshots_core

    logger.info(
        "CVS prune worker started — interval=%ss events_retention=%sd",
        INTERVAL_SEC,
        EVENTS_RETENTION_DAYS,
    )
    while True:
        try:
            result = await prune_old_snapshots_core(
                {
                    "events_retention_days": EVENTS_RETENTION_DAYS,
                    "vacuum": True,
                }
            )
            logger.info("CVS prune cycle — %s", result)
        except Exception as e:
            logger.exception("CVS prune cycle error: %s", e)
        await asyncio.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    asyncio.run(main_loop())
