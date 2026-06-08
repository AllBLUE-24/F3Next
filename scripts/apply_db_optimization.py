#!/usr/bin/env python3
"""
Apply Phase 2 DB optimizations from docs/DB_OPTIMIZATION.md.

Runs:
  1. docs/sql/add_missing_indexes.sql  (always safe, idempotent)
  2. docs/sql/enable_rls.sql           (only when connection bypasses RLS)

Usage:
  python scripts/apply_db_optimization.py
  python scripts/apply_db_optimization.py --indexes-only
  python scripts/apply_db_optimization.py --skip-rls
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _async_url_to_sync(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


def _password_from_url(url: str) -> str | None:
    parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://"))
    if not parsed.password:
        return None
    return unquote(parsed.password)


def _jwt_role(password: str) -> str | None:
    """Return JWT role claim when the DB password is a Supabase API key."""
    if password.count(".") != 2:
        return None
    try:
        payload = password.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("role")
    except Exception:
        return None


async def _connection_info(conn) -> dict:
    row = await conn.fetchrow(
        """
        SELECT
            current_user AS db_user,
            COALESCE(rolsuper, false) AS is_superuser,
            COALESCE(rolbypassrls, false) AS bypasses_rls
        FROM pg_roles
        WHERE rolname = current_user
        """
    )
    return dict(row) if row else {}


def _split_sql(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    # Strip line comments; keep DO $$ ... $$ blocks intact.
    statements: list[str] = []
    buf: list[str] = []
    in_dollar = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        if re.search(r"\bDO\s+\$\$", line, re.IGNORECASE):
            in_dollar = True
        buf.append(line)
        if in_dollar and stripped.endswith("$$;"):
            in_dollar = False
            statements.append("\n".join(buf).strip())
            buf = []
        elif not in_dollar and stripped.endswith(";"):
            statements.append("\n".join(buf).strip())
            buf = []
    if buf:
        chunk = "\n".join(buf).strip()
        if chunk:
            statements.append(chunk)
    return [s for s in statements if s]


async def _run_sql_file(conn, path: Path, *, retries: int = 3) -> int:
    import asyncpg

    count = 0
    for stmt in _split_sql(path):
        for attempt in range(1, retries + 1):
            try:
                await conn.execute(stmt)
                count += 1
                break
            except asyncpg.DeadlockDetectedError:
                if attempt == retries:
                    raise
                wait = attempt * 2
                print(f"  deadlock on statement {count + 1}, retry {attempt}/{retries} in {wait}s …")
                await asyncio.sleep(wait)
    return count


async def _verify_reads(conn) -> dict[str, int]:
    checks = {
        "projects": "SELECT COUNT(*)::int AS n FROM projects",
        "hooks": "SELECT COUNT(*)::int AS n FROM hooks",
        "context_snapshots": "SELECT COUNT(*)::int AS n FROM context_snapshots",
        "is_sessions": "SELECT COUNT(*)::int AS n FROM is_sessions",
    }
    out: dict[str, int] = {}
    for name, sql in checks.items():
        try:
            row = await conn.fetchrow(sql)
            out[name] = int(row["n"]) if row else -1
        except Exception as exc:
            out[name] = -1
            print(f"  verify {name}: FAILED ({exc})")
    return out


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply DB optimization SQL (Phase 2)")
    parser.add_argument("--indexes-only", action="store_true")
    parser.add_argument("--skip-rls", action="store_true")
    args = parser.parse_args(argv)

    import os

    db_url = os.getenv("DATABASE_URL", "")
    use_sqlite = os.getenv("USE_SQLITE", "true").lower() in ("true", "1", "yes")

    if not db_url or use_sqlite or "sqlite" in db_url:
        print("SKIP: DATABASE_URL not set or USE_SQLITE=true — Phase 2 SQL requires PostgreSQL.")
        print("      Run this script against your Supabase instance before production deploy.")
        return 0

    try:
        import asyncpg
    except ImportError:
        print("ERROR: asyncpg is required. pip install asyncpg")
        return 1

    sync_url = _async_url_to_sync(db_url)
    password = _password_from_url(db_url) or ""
    jwt_role = _jwt_role(password)

    indexes_sql = ROOT / "docs" / "sql" / "add_missing_indexes.sql"
    rls_sql = ROOT / "docs" / "sql" / "enable_rls.sql"

    print(f"Connecting to PostgreSQL as configured in DATABASE_URL …")
    conn = await asyncpg.connect(sync_url)

    try:
        info = await _connection_info(conn)
        print(
            f"  user={info.get('db_user')} "
            f"superuser={info.get('is_superuser')} "
            f"bypasses_rls={info.get('bypasses_rls')} "
            f"jwt_role={jwt_role or 'n/a'}"
        )

        if jwt_role == "anon":
            print("ERROR: DATABASE_URL password decodes to anon role — RLS would break the app.")
            print("       Use the service_role key in DATABASE_URL before enabling RLS.")
            if not args.indexes_only and not args.skip_rls:
                print("       Proceeding with indexes only.")
                args.skip_rls = True

        print(f"\nApplying {indexes_sql.name} …")
        n = await _run_sql_file(conn, indexes_sql)
        print(f"  OK — executed {n} statement(s)")

        if not args.indexes_only and not args.skip_rls:
            rls_safe = bool(info.get("bypasses_rls")) or jwt_role == "service_role"
            if not rls_safe:
                print(
                    "WARN: Connection does not bypass RLS and JWT is not service_role. "
                    "Skipping enable_rls.sql to avoid breaking queries."
                )
            else:
                print(f"\nApplying {rls_sql.name} …")
                n = await _run_sql_file(conn, rls_sql)
                print(f"  OK — executed {n} statement(s)")

                print("\nPost-RLS read verification:")
                counts = await _verify_reads(conn)
                for table, count in counts.items():
                    status = "OK" if count >= 0 else "FAIL"
                    print(f"  {table}: {status} (count={count})")
                if any(v < 0 for v in counts.values()):
                    print("ERROR: Some tables are unreadable after RLS — review policies.")
                    return 1

        print("\nDone.")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
