"""
Supabase storage reporting — read-only helpers for disk diagnostics.

CVS retention (context_snapshots + context_events) lives in
containers/context_versioning/context_store/activities.py — prune_old_snapshots_core.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

CVS_VACUUM_TABLES = ["context_snapshots", "context_events"]


async def connect_asyncpg():
    import asyncpg

    from shared.database.db import DATABASE_URL

    sync_url = (DATABASE_URL or "").replace("postgresql+asyncpg://", "postgresql://")
    if not sync_url or "sqlite" in sync_url:
        raise RuntimeError("PostgreSQL DATABASE_URL required")
    return await asyncpg.connect(sync_url, statement_cache_size=0)


async def report_storage(conn) -> dict[str, Any]:
    """Return database size and per-table breakdown."""
    db_row = await conn.fetchrow(
        """
        SELECT pg_database_size(current_database()) AS bytes,
               pg_size_pretty(pg_database_size(current_database())) AS pretty
        """
    )
    tables = await conn.fetch(
        """
        SELECT
            relname AS table_name,
            pg_total_relation_size(relid)::bigint AS total_bytes,
            pg_size_pretty(pg_total_relation_size(relid)) AS total_pretty,
            COALESCE(n_live_tup, 0)::bigint AS row_estimate
        FROM pg_catalog.pg_stat_user_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(relid) DESC
        """
    )
    return {
        "database_bytes": int(db_row["bytes"]) if db_row else 0,
        "database_pretty": db_row["pretty"] if db_row else "?",
        "tables": [dict(r) for r in tables],
    }


async def vacuum_cvs_tables(conn) -> list[str]:
    """Reclaim physical disk for CVS tables only."""
    vacuumed: list[str] = []
    await conn.execute("SET statement_timeout = 0")
    for name in CVS_VACUUM_TABLES:
        try:
            await conn.execute(f"VACUUM FULL {name}")
            vacuumed.append(name)
        except Exception as e:
            logger.warning("VACUUM FULL %s failed: %s", name, e)
    return vacuumed
