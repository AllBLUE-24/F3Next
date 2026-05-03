"""
CVS recovery loop — re-triggers Temporal for stuck context_events.

Runs every 5 minutes by default (configurable via CVS_RECOVERY_INTERVAL_SEC).
"""

from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(message)s")
logger = logging.getLogger("cvs_recovery")

INTERVAL_SEC = int(os.getenv("CVS_RECOVERY_INTERVAL_SEC", "300"))


async def main_loop() -> None:
    from containers.context_versioning.context_store.activities import recover_stuck_events_core

    logger.info("CVS recovery worker started — interval=%ss", INTERVAL_SEC)
    while True:
        try:
            result = await recover_stuck_events_core({"stale_minutes": 5})
            logger.info("CVS recovery cycle — %s", result)
        except Exception as e:
            logger.exception("CVS recovery cycle error: %s", e)
        await asyncio.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    asyncio.run(main_loop())
