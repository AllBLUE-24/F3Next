"""
Ensure ERPNext site prerequisites before IS import (Company discovery, Warehouses).

Post-onboarding sites: read live Company + abbr from Frappe; never re-onboard.
Greenfield sites (zero companies): run ERPNext setup_complete wizard (fixtures,
Company, COA, Transit warehouse type, fiscal year) — not a bare Company POST.
"""
from __future__ import annotations

import json
import uuid
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

_COUNTRY_SETUP_DEFAULTS: Dict[str, Dict[str, str]] = {
    "India": {
        "language": "English",
        "timezone": "Asia/Kolkata",
        "currency": "INR",
        "chart_of_accounts": "India - Chart of Accounts",
    },
}

_DEFAULT_COUNTRY = "India"

_WAREHOUSE_LINK_FIELDS = frozenset({
    "warehouse",
    "default_warehouse",
    "source_warehouse",
    "target_warehouse",
    "from_warehouse",
    "to_warehouse",
    "s_warehouse",
    "t_warehouse",
    "fg_warehouse",
    "wip_warehouse",
    "scrap_warehouse",
})


async def load_company_context(
    session_id: str,
    company_slug: str = "",
) -> Dict[str, str]:
    """Resolve company name hint from IS profile / slug (not authoritative vs live ERP)."""
    from shared.database.db import AsyncSessionLocal
    from shared.models.is_models import ISCompanyProfile
    from sqlalchemy import select

    ctx: Dict[str, str] = {
        "country": _DEFAULT_COUNTRY,
        "default_currency": "INR",
    }
    try:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ISCompanyProfile.company_name, ISCompanyProfile.f3iche)
                .where(ISCompanyProfile.session_id == uuid.UUID(session_id))
                .order_by(ISCompanyProfile.version.desc())
                .limit(1)
            )
            res = await session.execute(stmt)
            row = res.first()
            if row:
                if row.company_name:
                    ctx["company_name"] = str(row.company_name).strip()
                if row.f3iche:
                    ctx["f3iche"] = str(row.f3iche).strip()
    except Exception:
        pass

    if not ctx.get("company_name") and company_slug and company_slug not in ("unknown", ""):
        ctx["company_name"] = company_slug.replace("-", " ").replace("_", " ").title()

    return ctx


def _warehouse_values_from_row(row: Dict[str, Any], link_fields: Dict[str, str]) -> Set[str]:
    found: Set[str] = set()
    for field_name, value in row.items():
        if not value or not isinstance(value, str):
            continue
        if field_name in _WAREHOUSE_LINK_FIELDS or link_fields.get(field_name) == "Warehouse":
            found.add(value.strip())
    for _tname, items in row.items():
        if not isinstance(items, list):
            continue
        for child in items:
            if isinstance(child, dict):
                found |= _warehouse_values_from_row(child, link_fields)
    return found


def collect_warehouse_names(
    phases: Dict[str, Any],
    s3,
    link_fields: Dict[str, str],
) -> Set[str]:
    """Scan all mapped import payloads for Warehouse link field values."""
    names: Set[str] = set()
    for phase_data in (phases or {}).values():
        for step in phase_data.get("steps", []):
            if step.get("action") != "create":
                continue
            r2_key = step.get("data_source")
            if not r2_key or r2_key in ("pending_mapping", "none"):
                continue
            try:
                resp = s3.get_object(Bucket="clean-data", Key=r2_key)
                payload = json.loads(resp["Body"].read().decode("utf-8"))
                for row in payload.get("records", []):
                    if isinstance(row, dict):
                        names |= _warehouse_values_from_row(row, link_fields)
            except Exception:
                continue
    return {n for n in names if n}


def _company_abbr_fallback(
    company_name: str,
    company_slug: str = "",
    warehouse_names: Optional[Set[str]] = None,
) -> str:
    """Guess abbr only for true greenfield create — never overrides live ERP."""
    wh_names = warehouse_names or set()
    suffixes: Dict[str, int] = {}
    for wh in wh_names:
        if " - " in wh:
            suffix = wh.rsplit(" - ", 1)[-1].strip()
            if suffix and len(suffix) <= 6:
                suffixes[suffix] = suffixes.get(suffix, 0) + 1
    if suffixes:
        return max(suffixes, key=suffixes.get)

    slug = (company_slug or "").strip().lower()
    if slug and slug not in ("unknown", ""):
        parts = [p for p in slug.replace("_", "-").split("-") if p]
        if len(parts) >= 2:
            return "".join(p[0] for p in parts).upper()[:10]
        if len(parts) == 1 and len(parts[0]) >= 2:
            return parts[0][:2].upper()

    parts = [p for p in company_name.split() if p]
    if not parts:
        return "CO"
    if len(parts) == 1:
        return parts[0][:4].upper()
    return "".join(p[0] for p in parts).upper()[:10]


def _default_fiscal_year_dates(country: str) -> Tuple[str, str]:
    """Return (fy_start_date, fy_end_date) ISO strings for setup wizard."""
    today = date.today()
    if country == "India":
        if today.month >= 4:
            start_year = today.year
        else:
            start_year = today.year - 1
        return (
            f"{start_year}-04-01",
            f"{start_year + 1}-03-31",
        )
    return (f"{today.year}-01-01", f"{today.year}-12-31")


def _f3iche_to_domain(f3iche: str) -> Optional[str]:
    f = (f3iche or "").lower()
    if "manufactur" in f:
        return "Manufacturing"
    if "retail" in f or "trading" in f:
        return "Retail"
    if "service" in f:
        return "Services"
    return None


def build_setup_wizard_args(
    *,
    company_name: str,
    company_abbr: str,
    country: str = _DEFAULT_COUNTRY,
    default_currency: str = "INR",
    f3iche: str = "",
    fy_start_date: Optional[str] = None,
    fy_end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Build args dict for ERPNext setup_complete (validated on regww 2026-05)."""
    country = country or _DEFAULT_COUNTRY
    defaults = _COUNTRY_SETUP_DEFAULTS.get(country, _COUNTRY_SETUP_DEFAULTS[_DEFAULT_COUNTRY])
    if not fy_start_date or not fy_end_date:
        fy_start_date, fy_end_date = _default_fiscal_year_dates(country)

    args: Dict[str, Any] = {
        "language": defaults["language"],
        "country": country,
        "timezone": defaults["timezone"],
        "currency": default_currency or defaults["currency"],
        "company_name": company_name,
        "company_abbr": company_abbr,
        "chart_of_accounts": defaults["chart_of_accounts"],
        "fy_start_date": fy_start_date,
        "fy_end_date": fy_end_date,
        "setup_demo": 0,
    }
    domain = _f3iche_to_domain(f3iche)
    if domain:
        args["domain"] = domain
    return args


async def _fiscal_year_dates_from_site(adapter) -> Optional[Tuple[str, str]]:
    try:
        rows = await adapter.list_records(
            "Fiscal Year",
            ["year_start_date", "year_end_date"],
            limit=1,
        )
        if rows:
            start = rows[0].get("year_start_date")
            end = rows[0].get("year_end_date")
            if start and end:
                return str(start), str(end)
    except Exception:
        pass
    return None


async def run_greenfield_setup_wizard(
    adapter,
    *,
    company_name: str,
    company_abbr: str,
    country: str = _DEFAULT_COUNTRY,
    default_currency: str = "INR",
    f3iche: str = "",
    logger=None,
) -> bool:
    """
    Run ERPNext setup_complete when the site has zero companies.

    Creates fixtures (Transit warehouse type, UOM, etc.), Company, COA, FY.
    """
    if not hasattr(adapter, "run_setup_wizard"):
        if logger:
            logger.error("  ❌  Adapter does not support run_setup_wizard")
        return False

    fy_dates = await _fiscal_year_dates_from_site(adapter)
    args = build_setup_wizard_args(
        company_name=company_name,
        company_abbr=company_abbr,
        country=country,
        default_currency=default_currency,
        f3iche=f3iche,
        fy_start_date=fy_dates[0] if fy_dates else None,
        fy_end_date=fy_dates[1] if fy_dates else None,
    )

    if logger:
        logger.info(
            "  🧙  Greenfield setup wizard | company=%s abbr=%s country=%s",
            company_name,
            company_abbr,
            country,
        )

    try:
        result = await adapter.run_setup_wizard(args)
    except Exception as exc:
        if logger:
            logger.error("  ❌  Setup wizard failed: %s", exc)
        return False

    if isinstance(result, dict) and str(result.get("status", "")).lower() == "ok":
        if logger:
            logger.info("  🧙  Setup wizard completed (status=ok)")
        return True

    live = await discover_live_company(adapter, company_name, logger)
    if live and live.get("name"):
        if logger:
            logger.info(
                "  🧙  Setup wizard finished — Company '%s' on site",
                live["name"],
            )
        return True

    if logger:
        logger.error("  ❌  Setup wizard did not create Company (result=%s)", result)
    return False


def _normalize_name(s: str) -> str:
    return " ".join(str(s or "").strip().lower().split())


async def discover_live_company(
    adapter,
    preferred_name: Optional[str] = None,
    logger=None,
) -> Optional[Dict[str, str]]:
    """
    Read Company name + abbr from live Frappe. Returns None if site has no companies.
    """
    try:
        companies = await adapter.list_records(
            "Company",
            ["name", "abbr", "company_name"],
            limit=20,
        )
    except Exception as exc:
        if logger:
            logger.warning("  ⚠️  Could not list Company from live ERP: %s", exc)
        return None

    if not companies:
        return None

    pref_norm = _normalize_name(preferred_name) if preferred_name else ""

    if pref_norm:
        for row in companies:
            for key in ("name", "company_name"):
                val = row.get(key) or ""
                if _normalize_name(val) == pref_norm:
                    return {
                        "name": row.get("name") or val,
                        "abbr": str(row.get("abbr") or "").strip(),
                    }
        for row in companies:
            name = row.get("name") or row.get("company_name") or ""
            if pref_norm in _normalize_name(name):
                return {
                    "name": row.get("name") or name,
                    "abbr": str(row.get("abbr") or "").strip(),
                }

    row = companies[0]
    name = row.get("name") or row.get("company_name") or ""
    return {
        "name": name,
        "abbr": str(row.get("abbr") or "").strip(),
    }


async def resolve_company_for_import(
    adapter,
    *,
    session_id: str,
    company_slug: str = "",
    warehouse_names: Optional[Set[str]] = None,
    country: str = "India",
    default_currency: str = "INR",
    logger,
) -> Optional[Dict[str, Any]]:
    """
    Live-API-first company resolution.

    Returns dict: name, abbr, source (live|live_fallback|setup_wizard), created (bool).
    """
    ctx = await load_company_context(session_id, company_slug)
    preferred = ctx.get("company_name", "")

    live = await discover_live_company(adapter, preferred or None, logger)
    if live and live.get("name"):
        if preferred and _normalize_name(live["name"]) != _normalize_name(preferred):
            if logger:
                logger.info(
                    "  🏢  Using live Company '%s' (abbr=%s); profile had '%s'",
                    live["name"],
                    live.get("abbr") or "?",
                    preferred,
                )
        else:
            if logger:
                logger.info(
                    "  🏢  Discovered live Company '%s' (abbr=%s)",
                    live["name"],
                    live.get("abbr") or "?",
                )
        return {
            "name": live["name"],
            "abbr": live.get("abbr") or "",
            "source": "live",
            "created": False,
        }

    # Site has companies but none matched preferred — still use live default
    try:
        any_cos = await adapter.list_records("Company", ["name", "abbr"], limit=1)
    except Exception:
        any_cos = []
    if any_cos:
        fallback = await discover_live_company(adapter, None, logger)
        if fallback and logger:
            logger.warning(
                "  🏢  Profile company '%s' not on site — using live '%s' (abbr=%s)",
                preferred or "?",
                fallback["name"],
                fallback.get("abbr") or "?",
            )
        if fallback:
            return {
                "name": fallback["name"],
                "abbr": fallback.get("abbr") or "",
                "source": "live_fallback",
                "created": False,
            }

    # True greenfield — zero companies: ERPNext setup wizard (not bare Company POST)
    if not preferred:
        if logger:
            logger.error("  ❌  Site has no Company and no profile company name")
        return None

    abbr = _company_abbr_fallback(preferred, company_slug, warehouse_names)
    wizard_ok = await run_greenfield_setup_wizard(
        adapter,
        company_name=preferred,
        company_abbr=abbr,
        country=country,
        default_currency=default_currency,
        f3iche=ctx.get("f3iche", ""),
        logger=logger,
    )
    if not wizard_ok:
        if logger:
            logger.error("  ❌  Greenfield setup wizard failed for '%s'", preferred)
        return None

    rediscovered = await discover_live_company(adapter, preferred, logger)
    if rediscovered and rediscovered.get("name"):
        if logger:
            logger.info(
                "  🏢  Greenfield: setup wizard created Company '%s' (abbr=%s)",
                rediscovered["name"],
                rediscovered.get("abbr") or abbr,
            )
        return {
            "name": rediscovered["name"],
            "abbr": rediscovered.get("abbr") or abbr,
            "source": "setup_wizard",
            "created": True,
        }

    if logger:
        logger.error("  ❌  Setup wizard ran but Company '%s' not found on site", preferred)
    return None


async def discover_fiscal_year_exists(adapter, logger) -> bool:
    """Return True if any Fiscal Year exists on the live site (post-onboarding)."""
    try:
        rows = await adapter.list_records("Fiscal Year", ["name"], limit=1)
        return bool(rows)
    except Exception as exc:
        if logger:
            logger.warning("  ⚠️  Could not list Fiscal Year from live ERP: %s", exc)
        return False


async def _resolve_parent_warehouse(
    adapter,
    company_name: str,
    company_abbr: str,
    logger,
) -> tuple[Optional[str], str]:
    """Return (parent_group_warehouse_name, company_abbr from live data)."""
    abbr = company_abbr or ""
    try:
        rows = await adapter.list_records(
            "Warehouse",
            ["name", "company", "is_group"],
            filters=[["company", "=", company_name]],
            limit=50,
        )
    except Exception as exc:
        logger.warning("  ⚠️  Could not list warehouses: %s", exc)
        return None, abbr

    for wh in rows or []:
        name = wh.get("name") or ""
        if wh.get("is_group") == 1 or "all warehouses" in name.lower():
            if " - " in name:
                abbr = name.split(" - ")[-1].strip() or abbr
            return name, abbr

    if rows:
        first = rows[0].get("name") or ""
        if " - " in first:
            abbr = first.split(" - ")[-1].strip() or abbr
        return first, abbr

    if not abbr:
        live_co = await discover_live_company(adapter, company_name, logger)
        abbr = (live_co or {}).get("abbr") or ""

    parent = f"All Warehouses - {abbr}" if abbr else "All Warehouses"
    try:
        await adapter.create_record(
            "Warehouse",
            {
                "warehouse_name": "All Warehouses",
                "company": company_name,
                "is_group": 1,
            },
        )
        logger.info("  📦  Created parent warehouse group '%s'", parent)
        return parent, abbr
    except ValueError as exc:
        if "already exist" in str(exc).lower():
            return parent, abbr
        logger.warning("  ⚠️  Parent warehouse group create failed: %s", exc)
    except Exception as exc:
        logger.warning("  ⚠️  Parent warehouse group create failed: %s", exc)

    return None, abbr


def _parse_warehouse_label(full_name: str, default_abbr: str) -> tuple[str, str]:
    """Parse 'Stores - GS' → (warehouse_name, abbr). Custom names stay intact."""
    if " - " in full_name:
        base, suffix = full_name.rsplit(" - ", 1)
        base = base.strip()
        suffix = suffix.strip()
        if base and suffix and len(suffix) <= 6 and suffix.upper() == suffix:
            return base, suffix
    return full_name.strip(), default_abbr


def _is_duplicate_warehouse_error(exc: Exception) -> bool:
    err = str(exc).lower()
    return (
        "already exist" in err
        or "duplicate" in err
        or "duplicateentry" in err
        or "1062" in err
    )


async def _find_warehouse_by_base(
    adapter,
    wh_base: str,
    company_name: str,
    company_abbr: str,
) -> Optional[str]:
    """Find canonical warehouse name when CSV suffix differs from live company abbr."""
    try:
        rows = await adapter.list_records(
            "Warehouse",
            ["name", "warehouse_name"],
            filters=[["company", "=", company_name]],
            limit=100,
        )
    except Exception:
        return None

    preferred = f"{wh_base} - {company_abbr}" if company_abbr else ""
    for row in rows or []:
        name = (row.get("name") or "").strip()
        if name == preferred or name == wh_base:
            return name
        wn = (row.get("warehouse_name") or "").strip()
        if wn == wh_base and name:
            return name
        if name.startswith(f"{wh_base} - "):
            if not preferred or name == preferred:
                return name
            if not company_abbr:
                return name

    if preferred:
        for row in rows or []:
            if (row.get("name") or "").strip() == preferred:
                return preferred
    return None


async def ensure_warehouse(
    adapter,
    full_name: str,
    company_name: str,
    parent_wh: Optional[str],
    default_abbr: str,
    logger,
) -> bool:
    """Create a single warehouse if it does not exist."""
    wh_base, _csv_abbr = _parse_warehouse_label(full_name, default_abbr)

    try:
        exists = await adapter.list_records(
            "Warehouse",
            ["name"],
            filters=[["name", "=", full_name]],
            limit=1,
        )
        if exists:
            return True
    except Exception:
        pass

    canonical = await _find_warehouse_by_base(adapter, wh_base, company_name, default_abbr)
    if canonical:
        if canonical != full_name and logger:
            logger.info(
                "  📦  Warehouse '%s' already exists as '%s'",
                full_name,
                canonical,
            )
        return True

    record: Dict[str, Any] = {
        "warehouse_name": wh_base,
        "company": company_name,
        "is_group": 0,
    }
    if parent_wh:
        record["parent_warehouse"] = parent_wh

    try:
        await adapter.create_record("Warehouse", record)
        logger.info("  📦  Created warehouse '%s' (from '%s')", wh_base, full_name)
        return True
    except ValueError as exc:
        if _is_duplicate_warehouse_error(exc):
            return True
        logger.warning("  ⚠️  Warehouse '%s' create failed: %s", full_name, exc)
        return False
    except Exception as exc:
        if _is_duplicate_warehouse_error(exc):
            return True
        logger.warning("  ⚠️  Warehouse '%s' create failed: %s", full_name, exc)
        return False


async def site_has_company(adapter, logger=None) -> bool:
    """True when ERPNext already has at least one Company (setup wizard or onboarding done)."""
    live = await discover_live_company(adapter, None, logger)
    return bool(live and live.get("name"))


async def ensure_site_prerequisites(
    adapter,
    *,
    session_id: str,
    company_slug: str,
    phases: Dict[str, Any],
    s3,
    link_fields: Dict[str, str],
    logger,
) -> Dict[str, Any]:
    """
    Discover live Company; gap-fill missing Warehouses only.
    Greenfield (no Company): run ERPNext setup_complete wizard.
    Returns summary with authoritative company_name + abbr from Frappe.
    """
    ctx = await load_company_context(session_id, company_slug)
    wh_names = collect_warehouse_names(phases, s3, link_fields)

    summary: Dict[str, Any] = {
        "company_name": "",
        "company_abbr": "",
        "company_source": "",
        "company_created": False,
        "warehouses_requested": len(wh_names),
        "warehouses_created": 0,
        "warehouses_failed": 0,
    }

    resolved = await resolve_company_for_import(
        adapter,
        session_id=session_id,
        company_slug=company_slug,
        warehouse_names=wh_names,
        country=ctx.get("country", "India"),
        default_currency=ctx.get("default_currency", "INR"),
        logger=logger,
    )
    if not resolved:
        logger.warning("  ⚠️  Could not resolve Company from live ERP — skipping warehouse seed")
        return summary

    company_name = resolved["name"]
    company_abbr = resolved.get("abbr") or ""
    summary.update({
        "company_name": company_name,
        "company_abbr": company_abbr,
        "company_source": resolved.get("source", ""),
        "company_created": bool(resolved.get("created")),
    })

    parent_wh, abbr = await _resolve_parent_warehouse(
        adapter, company_name, company_abbr, logger,
    )
    created = failed = 0
    for wh in sorted(wh_names):
        ok = await ensure_warehouse(adapter, wh, company_name, parent_wh, abbr, logger)
        if ok:
            created += 1
        else:
            failed += 1

    summary["warehouses_created"] = created
    summary["warehouses_failed"] = failed
    return summary
